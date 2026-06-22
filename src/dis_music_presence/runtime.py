from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import replace

from .artwork import ArtworkError, ArtworkManager
from .discord_ipc import DiscordError, DiscordIpcClient
from .formatter import PresenceFormatter
from .models import FormattedPresence, MediaActivity
from .settings import Settings
from .sources import AppleMusicProvider, PlexProvider, SourceProvider, SpotifyProvider

LOGGER = logging.getLogger(__name__)


class PresenceRuntime:
    def __init__(
        self,
        settings: Settings,
        providers: list[SourceProvider] | None = None,
        discord_factory: Callable[[str], DiscordIpcClient] = DiscordIpcClient,
        dry_run: bool = False,
    ) -> None:
        self.settings = settings
        self.providers = providers or build_providers(settings)
        self.formatter = PresenceFormatter(settings)
        self.artwork = ArtworkManager(settings, allow_upload=not dry_run)
        self.discord_factory = discord_factory
        self.dry_run = dry_run
        self._discord: DiscordIpcClient | None = None
        self._last_presence_key: tuple[str, str] | None = None

    def tick(self) -> str:
        activity = self._select_activity()
        if activity is None:
            return self._clear_if_needed()

        presence = self.formatter.format(activity)
        if presence is None:
            return self._clear_if_needed()

        try:
            artwork = self.artwork.resolve(activity)
        except ArtworkError as exc:
            LOGGER.warning("Artwork unavailable: %s", exc)
            artwork = None
        if artwork is not None:
            presence = replace(presence, image_url=artwork.image_url, image_text=artwork.image_text)

        presence_key = (presence.text, presence.image_url)
        if presence_key == self._last_presence_key:
            return f"unchanged: {presence.text}"

        self._set_presence(presence)
        self._last_presence_key = presence_key
        return f"updated: {presence.text}"

    def run_forever(self) -> None:
        interval = max(3, self.settings.int("app.poll_interval_seconds", 15))
        try:
            while True:
                message = self.tick()
                LOGGER.info(message)
                time.sleep(interval)
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        if self._discord is not None:
            try:
                self._discord.clear_activity()
            except DiscordError as exc:
                LOGGER.warning("Could not clear Discord presence: %s", exc)
            finally:
                self._discord.close()
                self._discord = None
        try:
            self.artwork.cleanup()
        except ArtworkError as exc:
            LOGGER.warning("Could not clean up artwork: %s", exc)
        self._last_presence_key = None

    def _select_activity(self) -> MediaActivity | None:
        provider_by_name = {provider.name: provider for provider in self.providers}
        for name in _effective_source_priority(self.settings, self.providers):
            provider = provider_by_name.get(name)
            if provider is None:
                LOGGER.warning("Configured source %s is not available.", name)
                continue
            activity = provider.poll()
            LOGGER.debug("%s reported %s: %s", provider.name, activity.kind.value, activity.message)
            if activity.is_active:
                return activity
        return None

    def _set_presence(self, presence: FormattedPresence) -> None:
        if self.dry_run or not self.settings.bool("discord.enabled", True):
            LOGGER.info("Dry-run presence: %s", presence.text)
            return
        discord = self._discord_client()
        discord.set_activity(presence)

    def _clear_if_needed(self) -> str:
        if self._last_presence_key is None:
            return "idle: no active playback"
        if not self.dry_run and self.settings.bool("discord.enabled", True):
            self._discord_client().clear_activity()
        try:
            self.artwork.cleanup()
        except ArtworkError as exc:
            LOGGER.warning("Could not clean up artwork: %s", exc)
        self._last_presence_key = None
        return "cleared: no active playback"

    def _discord_client(self) -> DiscordIpcClient:
        if self._discord is None:
            self._discord = self.discord_factory(self.settings.get("discord.client_id"))
            self._discord.connect()
        return self._discord


def build_providers(settings: Settings) -> list[SourceProvider]:
    return [AppleMusicProvider(settings), SpotifyProvider(settings), PlexProvider(settings)]


def _effective_source_priority(settings: Settings, providers: list[SourceProvider]) -> list[str]:
    priority = settings.list("app.source_priority", [])
    for provider in providers:
        if provider.name not in priority:
            priority.append(provider.name)
    return priority
