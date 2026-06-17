from __future__ import annotations

import json
import platform
import subprocess

from ..models import ActivityKind, MediaActivity, MediaType
from ..settings import Settings
from .base import SourceCapability, SourceProvider


APPLESCRIPT = """
tell application "System Events"
    if not (exists process "Music") then return "not_running"
end tell

tell application "Music"
    if player state is not playing then
        return "idle" & linefeed & (player state as string)
    end if

    set currentTrack to current track
    set trackName to ""
    set artistName to ""
    set albumName to ""

    try
        set trackName to name of currentTrack
    end try
    try
        set artistName to artist of currentTrack
    end try
    try
        set albumName to album of currentTrack
    end try

    return "playing" & linefeed & trackName & linefeed & artistName & linefeed & albumName
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


class AppleMusicProvider(SourceProvider):
    name = "apple_music"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def capability(self) -> SourceCapability:
        enabled = self.settings.bool("apple_music.enabled", True)
        system = platform.system()
        supported = system in {"Darwin", "Windows"}
        if not enabled:
            return SourceCapability(self.name, False, supported, True, "Apple Music source is disabled.")
        if not supported:
            return SourceCapability(self.name, enabled, False, True, "Apple Music is supported on macOS and best-effort Windows only.")
        if system == "Windows":
            return SourceCapability(self.name, enabled, True, True, "Apple Music Windows source is best-effort and untested.")
        return SourceCapability(self.name, enabled, True, True, "Apple Music source is available.")

    def poll(self) -> MediaActivity:
        capability = self.capability()
        if not capability.enabled:
            return MediaActivity.idle(self.name, capability.message)
        if not capability.supported:
            return MediaActivity.unavailable(self.name, capability.message)

        if platform.system() == "Windows":
            return self._poll_windows()

        return self._poll_macos()

    def _poll_macos(self) -> MediaActivity:
        try:
            result = subprocess.run(
                ["osascript", "-e", APPLESCRIPT],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.settings.int("apple_music.timeout_seconds", 10),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return MediaActivity.error(self.name, f"Apple Music check failed: {exc}")

        if result.returncode != 0:
            message = (result.stderr or result.stdout or "Apple Music automation failed.").strip()
            return MediaActivity.error(self.name, message)

        lines = result.stdout.splitlines()
        state = lines[0].strip() if lines else ""
        if state == "not_running":
            return MediaActivity.idle(self.name, "Apple Music is not running.")
        if state == "idle":
            player_state = lines[1].strip() if len(lines) > 1 else "idle"
            return MediaActivity.idle(self.name, f"Apple Music is {player_state}.")
        if state != "playing":
            return MediaActivity.idle(self.name, "Apple Music is not playing.")

        title = lines[1].strip() if len(lines) > 1 else ""
        artist = lines[2].strip() if len(lines) > 2 else ""
        album = lines[3].strip() if len(lines) > 3 else ""
        if not title:
            return MediaActivity.error(self.name, "Apple Music is playing but track metadata is unavailable.")

        return MediaActivity(
            kind=ActivityKind.LISTENING,
            source="Apple Music",
            media_type=MediaType.MUSIC,
            title=title,
            artist=artist,
            album=album,
            player_state="playing",
        )

    def _poll_windows(self) -> MediaActivity:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", WINDOWS_MEDIA_SESSION_SCRIPT],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.settings.int("apple_music.timeout_seconds", 10),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return MediaActivity.error(self.name, f"Apple Music Windows check failed: {exc}")

        if result.returncode != 0:
            message = (result.stderr or result.stdout or "Windows media session check failed.").strip()
            return MediaActivity.error(self.name, message)

        sessions = _parse_windows_sessions(result.stdout)
        if not sessions:
            return MediaActivity.idle(self.name, "No Windows media sessions are active.")

        matches = [
            session
            for session in sessions
            if _matches_windows_apple_music(session, self.settings.list("apple_music.windows_app_ids", []))
        ]
        if not matches:
            return MediaActivity.idle(self.name, "Apple Music Windows session was not found.")

        playing = [session for session in matches if str(session.get("playback_status", "")).casefold() == "playing"]
        selected = playing[0] if playing else matches[0]
        if not playing:
            status = str(selected.get("playback_status") or "idle")
            return MediaActivity.idle(self.name, f"Apple Music Windows is {status}.")

        title = str(selected.get("title") or "").strip()
        artist = str(selected.get("artist") or selected.get("album_artist") or "").strip()
        album = str(selected.get("album") or "").strip()
        if not title:
            return MediaActivity.error(self.name, "Apple Music Windows is playing but track metadata is unavailable.")

        return MediaActivity(
            kind=ActivityKind.LISTENING,
            source="Apple Music",
            media_type=MediaType.MUSIC,
            title=title,
            artist=artist,
            album=album,
            player_state="playing",
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


def _matches_windows_apple_music(session: dict[str, object], configured_ids: list[str]) -> bool:
    source_id = str(session.get("source_app_user_model_id") or "")
    candidates = configured_ids or [
        "AppleMusic",
        "Apple Music",
        "AppleInc.AppleMusic",
        "AppleInc.AppleMusicWin",
        "Apple.Music",
        "Microsoft.AppleMusic",
    ]
    return any(candidate.casefold() in source_id.casefold() for candidate in candidates if candidate.strip())
