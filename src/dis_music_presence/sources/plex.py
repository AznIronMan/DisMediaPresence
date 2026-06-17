from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

from .. import __version__
from ..models import ActivityKind, MediaActivity, MediaType
from ..settings import Settings
from .base import SourceCapability, SourceProvider


TIMEOUT_SECONDS = 6
USER_AGENT = f"DisMusicPresence/{__version__}"
ACTIVE_PLEX_STATES = {"playing", "buffering"}


@dataclass(frozen=True)
class _BackendResult:
    activity: MediaActivity
    terminal: bool = False


class PlexProvider(SourceProvider):
    name = "plex"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def capability(self) -> SourceCapability:
        enabled = self.settings.bool("plex.enabled", False)
        provider = self._provider_mode()
        has_tautulli = bool(self.settings.get("tautulli.url") and self.settings.get("tautulli.api_key"))
        has_plex = bool(self.settings.get("plex.url") and self.settings.get("plex.token"))
        has_user = bool(self._expected_user_names() or self.settings.get("plex.user_id"))

        if not enabled:
            return SourceCapability(self.name, False, True, True, "Plex source is disabled.")
        if provider not in {"auto", "tautulli", "plex"}:
            return SourceCapability(self.name, enabled, True, False, "plex.provider must be auto, tautulli, or plex.")
        if not has_user:
            return SourceCapability(self.name, enabled, True, False, "Configure plex.user_names or plex.user_id.")
        if provider == "tautulli" and not has_tautulli:
            return SourceCapability(self.name, enabled, True, False, "Tautulli URL and API key are required.")
        if provider == "plex" and not has_plex:
            return SourceCapability(self.name, enabled, True, False, "Plex URL and token are required.")
        if provider == "auto" and not (has_tautulli or has_plex):
            return SourceCapability(self.name, enabled, True, False, "Configure Tautulli or direct Plex API settings.")
        return SourceCapability(self.name, enabled, True, True, "Plex source is configured.")

    def diagnostics(self) -> list[str]:
        capability = self.capability()
        if not capability.enabled:
            return []

        provider = self._provider_mode()
        lines = [f"provider={provider}; user_filter={self._user_filter_label()}"]
        if not capability.configured:
            lines.append(f"configuration: {capability.message}")
            return lines

        if provider in {"auto", "tautulli"}:
            if self._tautulli_configured():
                lines.append(self._diagnose_tautulli())
            else:
                lines.append("tautulli: unconfigured")

        if provider in {"auto", "plex"}:
            if self._plex_configured():
                lines.append(self._diagnose_plex())
            else:
                lines.append("plex_api: unconfigured")

        return lines

    def poll(self) -> MediaActivity:
        capability = self.capability()
        if not capability.enabled:
            return MediaActivity.idle(self.name, capability.message)
        if not capability.configured:
            return MediaActivity.unavailable(self.name, capability.message)

        provider = self._provider_mode()
        results: list[MediaActivity] = []

        if provider in {"auto", "tautulli"} and self._tautulli_configured():
            result = self._poll_tautulli()
            if result.activity.is_active or provider == "tautulli" or result.terminal:
                return result.activity
            results.append(result.activity)

        if provider in {"auto", "plex"} and self._plex_configured():
            result = self._poll_plex()
            if result.activity.is_active or provider == "plex" or result.terminal:
                return result.activity
            results.append(result.activity)

        for activity in results:
            if activity.kind is ActivityKind.IDLE:
                return activity
        if results:
            return results[-1]
        return MediaActivity.unavailable(self.name, "No Plex backend is configured.")

    def _poll_tautulli(self) -> _BackendResult:
        base_url = self.settings.get("tautulli.url")
        api_key = self.settings.get("tautulli.api_key")
        try:
            payload = _http_json(base_url, {"apikey": api_key, "cmd": "get_activity"})
        except RuntimeError as exc:
            return _BackendResult(MediaActivity.unavailable(self.name, f"Tautulli unavailable: {exc}"))

        response = payload.get("response", {})
        if response.get("result") != "success":
            message = str(response.get("message") or "Tautulli API returned an error.")
            return _BackendResult(MediaActivity.error(self.name, message), terminal=True)

        data = response.get("data", {})
        sessions = data.get("sessions") or []
        return _BackendResult(self._activity_from_tautulli_sessions(sessions))

    def _poll_plex(self) -> _BackendResult:
        base_url = self.settings.get("plex.url")
        token = self.settings.get("plex.token")
        try:
            xml_data = _http_bytes(base_url, "/status/sessions", {"X-Plex-Token": token})
        except RuntimeError as exc:
            return _BackendResult(MediaActivity.unavailable(self.name, f"Plex server API unavailable: {exc}"))

        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as exc:
            return _BackendResult(MediaActivity.error(self.name, f"Plex server returned invalid XML: {exc}"), terminal=True)

        return _BackendResult(self._activity_from_plex_videos(root.findall(".//Video")))

    def _diagnose_tautulli(self) -> str:
        base_url = self.settings.get("tautulli.url")
        api_key = self.settings.get("tautulli.api_key")
        try:
            payload = _http_json(base_url, {"apikey": api_key, "cmd": "get_activity"})
        except RuntimeError as exc:
            return f"tautulli: unavailable - {exc}"

        response = payload.get("response", {})
        if response.get("result") != "success":
            message = str(response.get("message") or "API returned an error.")
            return f"tautulli: error - {message}"

        data = response.get("data", {})
        sessions = data.get("sessions") or []
        if not isinstance(sessions, list):
            return "tautulli: error - activity response did not include a session list"

        total, matching, active = self._tautulli_session_counts(sessions)
        return f"tautulli: reachable - sessions={total}, matching_user={matching}, active={active}"

    def _diagnose_plex(self) -> str:
        base_url = self.settings.get("plex.url")
        token = self.settings.get("plex.token")
        try:
            xml_data = _http_bytes(base_url, "/status/sessions", {"X-Plex-Token": token})
        except RuntimeError as exc:
            return f"plex_api: unavailable - {exc}"

        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as exc:
            return f"plex_api: error - invalid XML: {exc}"

        total, matching, active = self._plex_video_counts(root.findall(".//Video"))
        return f"plex_api: reachable - sessions={total}, matching_user={matching}, active={active}"

    def _activity_from_tautulli_sessions(self, sessions: list[dict[str, Any]]) -> MediaActivity:
        matching = [session for session in sessions if self._session_matches_user(session)]
        if not matching:
            return MediaActivity.idle(self.name, "No Plex playback for configured user.")

        active = [session for session in matching if _is_active_plex_state(session.get("state"))]
        if not active:
            return MediaActivity.idle(self.name, "Configured Plex user is not actively playing media.")

        session = active[0]
        player_state = _plex_state(session.get("state")) or "playing"
        media_type = str(session.get("media_type") or session.get("type") or "").lower()
        if media_type == "movie":
            return MediaActivity(
                kind=ActivityKind.WATCHING,
                source="Plex",
                media_type=MediaType.MOVIE,
                title=str(session.get("title") or ""),
                player_state=player_state,
                raw=session,
            )

        if media_type == "episode":
            return MediaActivity(
                kind=ActivityKind.WATCHING,
                source="Plex",
                media_type=MediaType.EPISODE,
                title=str(session.get("title") or ""),
                show_title=str(session.get("grandparent_title") or ""),
                season=_optional_int(session.get("parent_media_index")),
                episode=_optional_int(session.get("media_index")),
                episode_title=str(session.get("title") or ""),
                player_state=player_state,
                raw=session,
            )

        return MediaActivity.idle(self.name, f"Unsupported Plex media type: {media_type or 'unknown'}.")

    def _activity_from_plex_videos(self, videos: list[ET.Element]) -> MediaActivity:
        matching = [video for video in videos if self._plex_video_matches_user(video)]
        if not matching:
            return MediaActivity.idle(self.name, "No Plex playback for configured user.")

        active = []
        for video in matching:
            player = video.find("Player")
            state = player.get("state") if player is not None else ""
            if _is_active_plex_state(state):
                active.append(video)
        if not active:
            return MediaActivity.idle(self.name, "Configured Plex user is not actively playing media.")

        video = active[0]
        player = video.find("Player")
        player_state = _plex_state(player.get("state") if player is not None else "") or "playing"
        media_type = (video.get("type") or "").lower()
        if media_type == "movie":
            return MediaActivity(
                kind=ActivityKind.WATCHING,
                source="Plex",
                media_type=MediaType.MOVIE,
                title=video.get("title") or "",
                player_state=player_state,
                raw=_plex_video_raw(video),
            )
        if media_type == "episode":
            return MediaActivity(
                kind=ActivityKind.WATCHING,
                source="Plex",
                media_type=MediaType.EPISODE,
                title=video.get("title") or "",
                show_title=video.get("grandparentTitle") or "",
                season=_optional_int(video.get("parentIndex")),
                episode=_optional_int(video.get("index")),
                episode_title=video.get("title") or "",
                player_state=player_state,
                raw=_plex_video_raw(video),
            )
        return MediaActivity.idle(self.name, f"Unsupported Plex media type: {media_type or 'unknown'}.")

    def _session_matches_user(self, session: dict[str, Any]) -> bool:
        expected_id = self.settings.get("plex.user_id")
        expected_names = self._expected_user_names()
        session_id = str(session.get("user_id") or session.get("user_id_hash") or "")
        session_names = [
            str(session.get("user") or ""),
            str(session.get("username") or ""),
            str(session.get("friendly_name") or ""),
        ]
        if expected_id and session_id == expected_id:
            return True
        if expected_names and any(name.casefold() in expected_names for name in session_names if name):
            return True
        return False

    def _plex_video_matches_user(self, video: ET.Element) -> bool:
        expected_id = self.settings.get("plex.user_id")
        expected_names = self._expected_user_names()
        user = video.find("User")
        if user is None:
            return False
        user_id = user.get("id") or ""
        title = user.get("title") or user.get("username") or ""
        if expected_id and user_id == expected_id:
            return True
        if expected_names and title.casefold() in expected_names:
            return True
        return False

    def _tautulli_session_counts(self, sessions: list[dict[str, Any]]) -> tuple[int, int, int]:
        matching = [session for session in sessions if self._session_matches_user(session)]
        active = [session for session in matching if _is_active_plex_state(session.get("state"))]
        return len(sessions), len(matching), len(active)

    def _plex_video_counts(self, videos: list[ET.Element]) -> tuple[int, int, int]:
        matching = [video for video in videos if self._plex_video_matches_user(video)]
        active = []
        for video in matching:
            player = video.find("Player")
            state = player.get("state") if player is not None else ""
            if _is_active_plex_state(state):
                active.append(video)
        return len(videos), len(matching), len(active)

    def _user_filter_label(self) -> str:
        names = sorted(self._expected_user_names())
        user_id = self.settings.get("plex.user_id")
        labels = []
        if names:
            labels.append("names=" + ",".join(names))
        if user_id:
            labels.append("user_id=<configured>")
        return ";".join(labels) if labels else "none"

    def _expected_user_names(self) -> set[str]:
        names: set[str] = set()
        configured = self.settings.get("plex.user_names")
        legacy = self.settings.get("plex.username")
        for value in (configured, legacy):
            for part in re.split(r"[,|]", value):
                name = part.strip().casefold()
                if name:
                    names.add(name)
        return names

    def _provider_mode(self) -> str:
        return self.settings.get("plex.provider", "auto").strip().lower() or "auto"

    def _tautulli_configured(self) -> bool:
        return bool(self.settings.get("tautulli.url") and self.settings.get("tautulli.api_key"))

    def _plex_configured(self) -> bool:
        return bool(self.settings.get("plex.url") and self.settings.get("plex.token"))


def _http_json(base_url: str, query: dict[str, str]) -> dict[str, Any]:
    data = _http_bytes(base_url, "/api/v2", query)
    try:
        decoded = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON response: {exc}") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("unexpected JSON response")
    return decoded


def _http_bytes(base_url: str, path: str, query: dict[str, str]) -> bytes:
    url = _build_url(base_url, path, query)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc
    except TimeoutError as exc:
        raise RuntimeError("request timed out") from exc


def _build_url(base_url: str, path: str, query: dict[str, str]) -> str:
    base = base_url.rstrip("/")
    parsed = urllib.parse.urlparse(base)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError(f"invalid URL: {base_url}")
    encoded = urllib.parse.urlencode(query)
    return f"{base}{path}?{encoded}"


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _plex_state(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_active_plex_state(value: Any) -> bool:
    return _plex_state(value) in ACTIVE_PLEX_STATES


def _plex_video_raw(video: ET.Element) -> dict[str, Any]:
    return {
        "thumb": video.get("thumb") or "",
        "art": video.get("art") or "",
        "grandparent_thumb": video.get("grandparentThumb") or "",
        "parent_thumb": video.get("parentThumb") or "",
        "rating_key": video.get("ratingKey") or video.get("rating_key") or "",
    }
