from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dis_music_presence.models import ActivityKind
from dis_music_presence.settings import DEFAULT_SETTINGS, Settings
from dis_music_presence.sources.spotify import SpotifyProvider
from dis_music_presence.sources.spotify import _matches_windows_spotify, _parse_windows_sessions


def _settings(**overrides: str) -> Settings:
    values = dict(DEFAULT_SETTINGS)
    values.update({"spotify.enabled": "true"})
    values.update(overrides)
    return Settings(path=Path("dmp.settings"), values=values)


def _completed(stdout: str, stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class SpotifyProviderTests(unittest.TestCase):
    def test_macos_reports_not_running_as_idle(self) -> None:
        provider = SpotifyProvider(_settings())

        with patch("dis_music_presence.sources.spotify.platform.system", return_value="Darwin"), patch(
            "dis_music_presence.sources.spotify.subprocess.run",
            return_value=_completed("not_running\n"),
        ):
            activity = provider.poll()

        self.assertEqual(activity.kind, ActivityKind.IDLE)
        self.assertIn("not running", activity.message)

    def test_macos_parses_playing_track(self) -> None:
        provider = SpotifyProvider(_settings())
        output = "\n".join(
            [
                "playing",
                "Song",
                "Artist",
                "Album",
                "245000",
                "12.5",
                "spotify:track:abc",
                "https://i.scdn.co/image/cover",
            ]
        )

        with patch("dis_music_presence.sources.spotify.platform.system", return_value="Darwin"), patch(
            "dis_music_presence.sources.spotify.subprocess.run",
            return_value=_completed(output),
        ):
            activity = provider.poll()

        self.assertEqual(activity.kind, ActivityKind.LISTENING)
        self.assertEqual(activity.source, "Spotify")
        self.assertEqual(activity.title, "Song")
        self.assertEqual(activity.artist, "Artist")
        self.assertEqual(activity.album, "Album")
        self.assertEqual(activity.raw["duration_ms"], 245000)
        self.assertEqual(activity.raw["progress_ms"], 12500)
        self.assertEqual(activity.raw["spotify_url"], "spotify:track:abc")
        self.assertEqual(activity.raw["artwork_url"], "https://i.scdn.co/image/cover")

    def test_windows_matches_spotify_session(self) -> None:
        session = {"source_app_user_model_id": "SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify"}

        self.assertTrue(_matches_windows_spotify(session, []))

    def test_windows_parses_playing_session(self) -> None:
        provider = SpotifyProvider(_settings())
        payload = (
            '{"source_app_user_model_id":"Spotify.exe","playback_status":"Playing",'
            '"title":"Song","artist":"Artist","album":"Album"}'
        )

        with patch("dis_music_presence.sources.spotify.platform.system", return_value="Windows"), patch(
            "dis_music_presence.sources.spotify.subprocess.run",
            return_value=_completed(payload),
        ):
            activity = provider.poll()

        self.assertEqual(activity.kind, ActivityKind.LISTENING)
        self.assertEqual(activity.title, "Song")
        self.assertEqual(activity.artist, "Artist")
        self.assertEqual(activity.album, "Album")

    def test_windows_session_parser_accepts_list_or_object(self) -> None:
        one = _parse_windows_sessions('{"title":"Song"}')
        many = _parse_windows_sessions('[{"title":"One"},{"title":"Two"}]')

        self.assertEqual(len(one), 1)
        self.assertEqual(len(many), 2)

    def test_linux_playerctl_parses_playing_track(self) -> None:
        provider = SpotifyProvider(_settings())
        responses = [
            _completed("Playing\n"),
            _completed("Song\nArtist\nAlbum\nhttps://i.scdn.co/image/cover\nspotify:track:abc\n"),
        ]

        with patch("dis_music_presence.sources.spotify.platform.system", return_value="Linux"), patch(
            "dis_music_presence.sources.spotify.shutil.which",
            side_effect=lambda name: f"/usr/bin/{name}" if name == "playerctl" else None,
        ), patch("dis_music_presence.sources.spotify.subprocess.run", side_effect=responses):
            activity = provider.poll()

        self.assertEqual(activity.kind, ActivityKind.LISTENING)
        self.assertEqual(activity.title, "Song")
        self.assertEqual(activity.raw["artwork_url"], "https://i.scdn.co/image/cover")
        self.assertEqual(activity.raw["spotify_url"], "spotify:track:abc")

    def test_linux_dbus_parses_playing_track(self) -> None:
        provider = SpotifyProvider(_settings())
        status = _completed('method return\n   variant       string "Playing"\n')
        metadata = _completed(
            """
method return
   variant       array [
         dict entry(
            string "xesam:title"
            variant                string "Song"
         )
         dict entry(
            string "xesam:artist"
            variant                array [
                  string "Artist"
               ]
         )
         dict entry(
            string "xesam:album"
            variant                string "Album"
         )
         dict entry(
            string "mpris:artUrl"
            variant                string "https://i.scdn.co/image/cover"
         )
         dict entry(
            string "xesam:url"
            variant                string "spotify:track:abc"
         )
   ]
            """
        )

        with patch("dis_music_presence.sources.spotify.platform.system", return_value="Linux"), patch(
            "dis_music_presence.sources.spotify.shutil.which",
            side_effect=lambda name: f"/usr/bin/{name}" if name == "dbus-send" else None,
        ), patch("dis_music_presence.sources.spotify.subprocess.run", side_effect=[status, metadata]):
            activity = provider.poll()

        self.assertEqual(activity.kind, ActivityKind.LISTENING)
        self.assertEqual(activity.title, "Song")
        self.assertEqual(activity.artist, "Artist")
        self.assertEqual(activity.album, "Album")
        self.assertEqual(activity.raw["artwork_url"], "https://i.scdn.co/image/cover")


if __name__ == "__main__":
    unittest.main()
