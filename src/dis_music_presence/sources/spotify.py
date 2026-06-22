from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess

from ..models import ActivityKind, MediaActivity, MediaType
from ..settings import Settings
from .base import SourceCapability, SourceProvider


APPLESCRIPT = """
tell application "System Events"
    if not (exists process "Spotify") then return "not_running"
end tell

tell application id "com.spotify.client"
    set stateText to player state as string
    if stateText is not "playing" then
        return "idle" & linefeed & stateText
    end if

    set currentTrack to current track
    set trackName to ""
    set artistName to ""
    set albumName to ""
    set durationText to ""
    set positionText to ""
    set trackUrl to ""
    set artworkUrl to ""

    try
        set trackName to name of currentTrack
    end try
    try
        set artistName to artist of currentTrack
    end try
    try
        set albumName to album of currentTrack
    end try
    try
        set durationText to duration of currentTrack as string
    end try
    try
        set positionText to player position as string
    end try
    try
        set trackUrl to spotify url of currentTrack
    end try
    try
        set artworkUrl to artwork url of currentTrack
    end try

    return "playing" & linefeed & trackName & linefeed & artistName & linefeed & albumName & linefeed & durationText & linefeed & positionText & linefeed & trackUrl & linefeed & artworkUrl
end tell
""".strip()


WINDOWS_MEDIA_SESSION_SCRIPT = r"""
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
        $_.Name -eq "AsTask" -and
        $_.IsGenericMethod -and
        $_.GetParameters().Count -eq 1
    } |
    Select-Object -First 1

function Await-WinRt($operation, [Type]$resultType) {
    $asTask = $asTaskMethod.MakeGenericMethod($resultType)
    $task = $asTask.Invoke($null, @($operation))
    $task.Wait()
    return $task.Result
}

$managerType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType=WindowsRuntime]
$propertiesType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties, Windows.Media.Control, ContentType=WindowsRuntime]
$managerOperation = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType=WindowsRuntime]::RequestAsync()
$manager = Await-WinRt $managerOperation $managerType
$sessions = @($manager.GetSessions())
$items = foreach ($session in $sessions) {
    $properties = Await-WinRt $session.TryGetMediaPropertiesAsync() $propertiesType
    $playback = $session.GetPlaybackInfo()
    [PSCustomObject]@{
        source_app_user_model_id = $session.SourceAppUserModelId
        playback_status = $playback.PlaybackStatus.ToString()
        title = $properties.Title
        artist = $properties.Artist
        album = $properties.AlbumTitle
        album_artist = $properties.AlbumArtist
    }
}

$items | ConvertTo-Json -Compress -Depth 4
""".strip()


DEFAULT_WINDOWS_APP_IDS = [
    "Spotify",
    "Spotify.exe",
    "SpotifyAB.SpotifyMusic",
    "SpotifyMusic",
]
DEFAULT_LINUX_PLAYER_NAMES = ["spotify"]


class SpotifyProvider(SourceProvider):
    name = "spotify"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def capability(self) -> SourceCapability:
        enabled = self.settings.bool("spotify.enabled", False)
        system = platform.system()
        supported = system in {"Darwin", "Windows", "Linux"}
        if not enabled:
            return SourceCapability(self.name, False, supported, True, "Spotify source is disabled.")
        if not supported:
            return SourceCapability(self.name, enabled, False, True, "Spotify is supported on macOS with best-effort Windows and Linux support.")
        if system == "Windows":
            return SourceCapability(self.name, enabled, True, True, "Spotify Windows source is best-effort through Windows media sessions.")
        if system == "Linux" and not self._linux_tool_available():
            return SourceCapability(self.name, enabled, True, False, "Install playerctl or dbus-send for Spotify Linux support.")
        return SourceCapability(self.name, enabled, True, True, "Spotify source is available.")

    def diagnostics(self) -> list[str]:
        capability = self.capability()
        if not capability.enabled:
            return []
        system = platform.system()
        if system == "Linux":
            return [
                f"playerctl={'available' if shutil.which('playerctl') else 'missing'}",
                f"dbus-send={'available' if shutil.which('dbus-send') else 'missing'}",
                f"player_names={','.join(self._linux_player_names())}",
            ]
        if system == "Windows":
            return [f"windows_app_ids={','.join(self._windows_app_ids())}"]
        return [capability.message]

    def poll(self) -> MediaActivity:
        capability = self.capability()
        if not capability.enabled:
            return MediaActivity.idle(self.name, capability.message)
        if not capability.supported:
            return MediaActivity.unavailable(self.name, capability.message)
        if not capability.configured:
            return MediaActivity.unavailable(self.name, capability.message)

        system = platform.system()
        if system == "Windows":
            return self._poll_windows()
        if system == "Linux":
            return self._poll_linux()
        return self._poll_macos()

    def _poll_macos(self) -> MediaActivity:
        try:
            result = subprocess.run(
                ["osascript", "-e", APPLESCRIPT],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.settings.int("spotify.timeout_seconds", 10),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return MediaActivity.error(self.name, f"Spotify check failed: {exc}")

        if result.returncode != 0:
            message = (result.stderr or result.stdout or "Spotify automation failed.").strip()
            return MediaActivity.error(self.name, message)

        return _activity_from_lines(self.name, result.stdout.splitlines(), idle_label="Spotify")

    def _poll_windows(self) -> MediaActivity:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", WINDOWS_MEDIA_SESSION_SCRIPT],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.settings.int("spotify.timeout_seconds", 10),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return MediaActivity.error(self.name, f"Spotify Windows check failed: {exc}")

        if result.returncode != 0:
            message = (result.stderr or result.stdout or "Windows media session check failed.").strip()
            return MediaActivity.error(self.name, message)

        sessions = _parse_windows_sessions(result.stdout)
        if not sessions:
            return MediaActivity.idle(self.name, "No Windows media sessions are active.")

        matches = [session for session in sessions if _matches_windows_spotify(session, self._windows_app_ids())]
        if not matches:
            return MediaActivity.idle(self.name, "Spotify Windows session was not found.")

        playing = [session for session in matches if str(session.get("playback_status", "")).casefold() == "playing"]
        selected = playing[0] if playing else matches[0]
        if not playing:
            status = str(selected.get("playback_status") or "idle")
            return MediaActivity.idle(self.name, f"Spotify Windows is {status}.")

        return _activity_from_fields(
            self.name,
            title=str(selected.get("title") or ""),
            artist=str(selected.get("artist") or selected.get("album_artist") or ""),
            album=str(selected.get("album") or ""),
            raw={"session": selected},
        )

    def _poll_linux(self) -> MediaActivity:
        if shutil.which("playerctl"):
            activity = self._poll_linux_playerctl()
            if activity.kind is not ActivityKind.UNAVAILABLE:
                return activity
        if shutil.which("dbus-send"):
            return self._poll_linux_dbus()
        return MediaActivity.unavailable(self.name, "Install playerctl or dbus-send for Spotify Linux support.")

    def _poll_linux_playerctl(self) -> MediaActivity:
        last_error = ""
        for player_name in self._linux_player_names():
            try:
                status = subprocess.run(
                    ["playerctl", "-p", player_name, "status"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.settings.int("spotify.timeout_seconds", 10),
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return MediaActivity.error(self.name, f"Spotify Linux playerctl check failed: {exc}")
            if status.returncode != 0:
                last_error = (status.stderr or status.stdout or "").strip()
                continue

            state = status.stdout.strip()
            if state.casefold() != "playing":
                return MediaActivity.idle(self.name, f"Spotify Linux is {state or 'idle'}.")

            metadata = subprocess.run(
                [
                    "playerctl",
                    "-p",
                    player_name,
                    "metadata",
                    "--format",
                    "{{title}}\n{{artist}}\n{{album}}\n{{mpris:artUrl}}\n{{xesam:url}}",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.settings.int("spotify.timeout_seconds", 10),
            )
            if metadata.returncode != 0:
                message = (metadata.stderr or metadata.stdout or "Spotify Linux metadata is unavailable.").strip()
                return MediaActivity.error(self.name, message)
            lines = metadata.stdout.splitlines()
            return _activity_from_fields(
                self.name,
                title=_line(lines, 0),
                artist=_line(lines, 1),
                album=_line(lines, 2),
                artwork_url=_line(lines, 3),
                spotify_url=_line(lines, 4),
                raw={"player": player_name},
            )
        return MediaActivity.unavailable(self.name, last_error or "Spotify Linux player was not found.")

    def _poll_linux_dbus(self) -> MediaActivity:
        last_error = ""
        for player_name in self._linux_player_names():
            destination = f"org.mpris.MediaPlayer2.{player_name}"
            status = _dbus_get_property(destination, "PlaybackStatus", self.settings.int("spotify.timeout_seconds", 10))
            if status.returncode != 0:
                last_error = (status.stderr or status.stdout or "").strip()
                continue
            state = _first_dbus_string(status.stdout)
            if state.casefold() != "playing":
                return MediaActivity.idle(self.name, f"Spotify Linux is {state or 'idle'}.")

            metadata = _dbus_get_property(destination, "Metadata", self.settings.int("spotify.timeout_seconds", 10))
            if metadata.returncode != 0:
                message = (metadata.stderr or metadata.stdout or "Spotify Linux metadata is unavailable.").strip()
                return MediaActivity.error(self.name, message)
            return _activity_from_fields(
                self.name,
                title=_dbus_metadata_string(metadata.stdout, "xesam:title"),
                artist=_dbus_metadata_array_first(metadata.stdout, "xesam:artist"),
                album=_dbus_metadata_string(metadata.stdout, "xesam:album"),
                artwork_url=_dbus_metadata_string(metadata.stdout, "mpris:artUrl"),
                spotify_url=_dbus_metadata_string(metadata.stdout, "xesam:url"),
                raw={"player": player_name},
            )
        return MediaActivity.unavailable(self.name, last_error or "Spotify Linux DBus player was not found.")

    def _windows_app_ids(self) -> list[str]:
        return self.settings.list("spotify.windows_app_ids", DEFAULT_WINDOWS_APP_IDS) or DEFAULT_WINDOWS_APP_IDS

    def _linux_player_names(self) -> list[str]:
        return self.settings.list("spotify.linux_player_names", DEFAULT_LINUX_PLAYER_NAMES) or DEFAULT_LINUX_PLAYER_NAMES

    def _linux_tool_available(self) -> bool:
        return bool(shutil.which("playerctl") or shutil.which("dbus-send"))


def _activity_from_lines(source_name: str, lines: list[str], *, idle_label: str) -> MediaActivity:
    state = _line(lines, 0)
    if state == "not_running":
        return MediaActivity.idle(source_name, f"{idle_label} is not running.")
    if state == "idle":
        player_state = _line(lines, 1) or "idle"
        return MediaActivity.idle(source_name, f"{idle_label} is {player_state}.")
    if state != "playing":
        return MediaActivity.idle(source_name, f"{idle_label} is not playing.")
    return _activity_from_fields(
        source_name,
        title=_line(lines, 1),
        artist=_line(lines, 2),
        album=_line(lines, 3),
        duration_ms=_optional_int(_line(lines, 4)),
        progress_ms=_seconds_to_ms(_line(lines, 5)),
        spotify_url=_line(lines, 6),
        artwork_url=_line(lines, 7),
    )


def _activity_from_fields(
    source_name: str,
    *,
    title: str,
    artist: str = "",
    album: str = "",
    duration_ms: int | None = None,
    progress_ms: int | None = None,
    spotify_url: str = "",
    artwork_url: str = "",
    raw: dict[str, object] | None = None,
) -> MediaActivity:
    clean_title = title.strip()
    if not clean_title:
        return MediaActivity.error(source_name, "Spotify is playing but track metadata is unavailable.")

    raw_values: dict[str, object] = dict(raw or {})
    if duration_ms is not None:
        raw_values["duration_ms"] = duration_ms
    if progress_ms is not None:
        raw_values["progress_ms"] = progress_ms
    if spotify_url:
        raw_values["spotify_url"] = spotify_url.strip()
    if artwork_url:
        raw_values["artwork_url"] = artwork_url.strip()

    return MediaActivity(
        kind=ActivityKind.LISTENING,
        source="Spotify",
        media_type=MediaType.MUSIC,
        title=clean_title,
        artist=artist.strip(),
        album=album.strip(),
        player_state="playing",
        raw=raw_values,
    )


def _parse_windows_sessions(output: str) -> list[dict[str, object]]:
    text = output.strip()
    if not text:
        return []
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(decoded, dict):
        return [decoded]
    if isinstance(decoded, list):
        return [item for item in decoded if isinstance(item, dict)]
    return []


def _matches_windows_spotify(session: dict[str, object], configured_ids: list[str]) -> bool:
    source_id = str(session.get("source_app_user_model_id") or "")
    candidates = configured_ids or DEFAULT_WINDOWS_APP_IDS
    return any(candidate.casefold() in source_id.casefold() for candidate in candidates if candidate.strip())


def _dbus_get_property(destination: str, property_name: str, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "dbus-send",
            "--session",
            "--print-reply",
            f"--dest={destination}",
            "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties.Get",
            "string:org.mpris.MediaPlayer2.Player",
            f"string:{property_name}",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )


def _first_dbus_string(output: str) -> str:
    match = re.search(r'string "((?:[^"\\]|\\.)*)"', output)
    if not match:
        return ""
    return _unescape(match.group(1))


def _dbus_metadata_string(output: str, key: str) -> str:
    block = _dbus_metadata_block(output, key)
    if not block:
        return ""
    return _first_dbus_string(block)


def _dbus_metadata_array_first(output: str, key: str) -> str:
    block = _dbus_metadata_block(output, key)
    if not block:
        return ""
    return _first_dbus_string(block)


def _dbus_metadata_block(output: str, key: str) -> str:
    pattern = rf'dict entry\(\s*string "{re.escape(key)}"\s*variant\s*(.*?)\s*\)'
    match = re.search(pattern, output, re.DOTALL)
    return match.group(1) if match else ""


def _line(lines: list[str], index: int) -> str:
    return lines[index].strip() if len(lines) > index else ""


def _optional_int(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _seconds_to_ms(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(float(value) * 1000)
    except ValueError:
        return None


def _unescape(value: str) -> str:
    return value.replace(r"\"", '"').replace(r"\\", "\\")
