from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SETTINGS: dict[str, str] = {
    "app.poll_interval_seconds": "15",
    "app.source_priority": "apple_music,spotify,plex",
    "discord.enabled": "true",
    "discord.client_id": "",
    "format.listening": "Listening to {artist} - {title}",
    "format.watching_movie": "Watching {title}",
    "format.watching_episode": "Watching {show_title} - {episode_code} - {episode_title}",
    "artwork.provider": "tmpfiles",
    "artwork.upload.path": "",
    "artwork.custom_url": "",
    "artwork.custom_text": "",
    "artwork.filebin.path": "",
    "artwork.filebin.base_url": "https://filebin.net",
    "artwork.filebin.bin": "",
    "artwork.filebin.delete_on_shutdown": "true",
    "artwork.tmpfiles.base_url": "https://tmpfiles.org",
    "artwork.apple_music.enabled": "true",
    "artwork.spotify.enabled": "true",
    "artwork.plex.enabled": "true",
    "artwork.plex.image_fields": "thumb,grandparent_thumb,parent_thumb,art",
    "artwork.plex.width": "600",
    "artwork.plex.height": "900",
    "artwork.plex.format": "jpg",
    "artwork.apple_catalog.enabled": "true",
    "artwork.apple_catalog.country": "US",
    "artwork.apple_catalog.size": "600",
    "apple_music.enabled": "true",
    "apple_music.timeout_seconds": "10",
    "apple_music.windows_app_ids": "AppleMusic,Apple Music,AppleInc.AppleMusic,AppleInc.AppleMusicWin,Apple.Music,Microsoft.AppleMusic",
    "spotify.enabled": "false",
    "spotify.timeout_seconds": "10",
    "spotify.windows_app_ids": "Spotify,Spotify.exe,SpotifyAB.SpotifyMusic,SpotifyMusic",
    "spotify.linux_player_names": "spotify",
    "plex.enabled": "false",
    "plex.provider": "auto",
    "tautulli.url": "",
    "tautulli.api_key": "",
    "plex.url": "",
    "plex.token": "",
    "plex.user_names": "",
    "plex.username": "",
    "plex.user_id": "",
}

SECRET_KEY_PARTS = ("token", "api_key", "secret", "password")


class SettingsError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    path: Path
    values: dict[str, str]

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)

    def bool(self, key: str, default: bool = False) -> bool:
        value = self.values.get(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def int(self, key: str, default: int) -> int:
        value = self.values.get(key)
        if value is None or value == "":
            return default
        try:
            return int(value)
        except ValueError as exc:
            raise SettingsError(f"Setting {key!r} must be an integer.") from exc

    def list(self, key: str, default: list[str] | None = None) -> list[str]:
        value = self.values.get(key)
        if not value:
            return list(default or [])
        return [part.strip() for part in value.split(",") if part.strip()]

    def redacted(self) -> dict[str, str]:
        return {key: redact_value(key, value) for key, value in sorted(self.values.items())}


def settings_path(path: str | Path | None = None) -> Path:
    return Path(path or "dmp.settings").expanduser().resolve()


def init_settings(path: str | Path | None = None, force: bool = False) -> Path:
    target = settings_path(path)
    if target.exists() and not force:
        load_settings(target)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(target)) as conn:
            _init_schema(conn)
            conn.execute("DELETE FROM settings")
            conn.executemany(
                "INSERT INTO settings(key, value) VALUES(?, ?)",
                sorted(DEFAULT_SETTINGS.items()),
            )
            conn.commit()
    except sqlite3.DatabaseError as exc:
        raise SettingsError(f"Could not initialize settings at {target}: {exc}") from exc
    return target


def load_settings(path: str | Path | None = None, create: bool = False) -> Settings:
    target = settings_path(path)
    if not target.exists():
        if create:
            init_settings(target)
        else:
            raise SettingsError(f"Settings file not found: {target}. Run `dmp config init` first.")

    try:
        with closing(sqlite3.connect(target)) as conn:
            _init_schema(conn)
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
    except sqlite3.DatabaseError as exc:
        raise SettingsError(f"Settings file is invalid or unreadable: {target}") from exc

    values = dict(DEFAULT_SETTINGS)
    values.update({str(key): str(value) for key, value in rows})
    return Settings(path=target, values=values)


def set_setting(path: str | Path | None, key: str, value: str) -> None:
    target = settings_path(path)
    if key not in DEFAULT_SETTINGS:
        valid = ", ".join(sorted(DEFAULT_SETTINGS))
        raise SettingsError(f"Unknown setting {key!r}. Valid settings: {valid}")
    if not target.exists():
        raise SettingsError(f"Settings file not found: {target}. Run `dmp config init` first.")
    try:
        with closing(sqlite3.connect(target)) as conn:
            _init_schema(conn)
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            conn.commit()
    except sqlite3.DatabaseError as exc:
        raise SettingsError(f"Could not update setting {key!r}: {exc}") from exc


def redact_value(key: str, value: str) -> str:
    lowered = key.lower()
    if any(part in lowered for part in SECRET_KEY_PARTS):
        if not value:
            return ""
        return "<redacted>"
    return value


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS settings ("
        "key TEXT PRIMARY KEY, "
        "value TEXT NOT NULL)"
    )
    conn.execute("PRAGMA user_version = 1")
