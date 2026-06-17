from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dis_music_presence.models import ActivityKind
from dis_music_presence.settings import DEFAULT_SETTINGS, Settings
from dis_music_presence.sources.apple_music import AppleMusicProvider
from dis_music_presence.sources.apple_music import _matches_windows_apple_music, _parse_windows_sessions


class AppleMusicProviderTests(unittest.TestCase):
    def test_non_macos_is_unavailable(self) -> None:
        settings = Settings(path=Path("dmp.settings"), values=dict(DEFAULT_SETTINGS))
        provider = AppleMusicProvider(settings)

        with patch("platform.system", return_value="Linux"):
            activity = provider.poll()

        self.assertEqual(activity.kind, ActivityKind.UNAVAILABLE)

    def test_uses_configured_timeout(self) -> None:
        values = dict(DEFAULT_SETTINGS)
        values["apple_music.timeout_seconds"] = "12"
        settings = Settings(path=Path("dmp.settings"), values=values)
        provider = AppleMusicProvider(settings)

        with patch("platform.system", return_value="Darwin"), patch(
            "subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout="not_running\n", stderr=""),
        ) as run:
            provider.poll()

        self.assertEqual(run.call_args.kwargs["timeout"], 12)

    def test_windows_media_session_poll_returns_listening_activity(self) -> None:
        settings = Settings(path=Path("dmp.settings"), values=dict(DEFAULT_SETTINGS))
        provider = AppleMusicProvider(settings)
        output = (
            '{"source_app_user_model_id":"AppleInc.AppleMusic_123!App",'
            '"playback_status":"Playing","title":"Song","artist":"Artist","album":"Album"}'
        )

        with patch("platform.system", return_value="Windows"), patch(
            "subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout=output, stderr=""),
        ) as run:
            activity = provider.poll()

        self.assertEqual(activity.kind, ActivityKind.LISTENING)
        self.assertEqual(activity.source, "Apple Music")
        self.assertEqual(activity.title, "Song")
        self.assertEqual(activity.artist, "Artist")
        self.assertEqual(activity.album, "Album")
        self.assertEqual(run.call_args.args[0][0], "powershell")

    def test_windows_media_session_without_apple_music_is_idle(self) -> None:
        settings = Settings(path=Path("dmp.settings"), values=dict(DEFAULT_SETTINGS))
        provider = AppleMusicProvider(settings)
        output = (
            '{"source_app_user_model_id":"SpotifyAB.SpotifyMusic_123!Spotify",'
            '"playback_status":"Playing","title":"Song","artist":"Artist","album":"Album"}'
        )

        with patch("platform.system", return_value="Windows"), patch(
            "subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout=output, stderr=""),
        ):
            activity = provider.poll()

        self.assertEqual(activity.kind, ActivityKind.IDLE)
        self.assertIn("not found", activity.message)

    def test_windows_media_session_parser_accepts_single_object(self) -> None:
        sessions = _parse_windows_sessions('{"source_app_user_model_id":"AppleInc.AppleMusic_123!App"}')

        self.assertEqual(sessions, [{"source_app_user_model_id": "AppleInc.AppleMusic_123!App"}])

    def test_windows_media_session_match_uses_configured_ids(self) -> None:
        session = {"source_app_user_model_id": "com.example.custom-player"}

        self.assertTrue(_matches_windows_apple_music(session, ["custom-player"]))

    def test_windows_media_session_match_ignores_track_text(self) -> None:
        session = {
            "source_app_user_model_id": "SpotifyAB.SpotifyMusic_123!Spotify",
            "title": "Apple Music Preview",
        }

        self.assertFalse(_matches_windows_apple_music(session, []))


if __name__ == "__main__":
    unittest.main()
