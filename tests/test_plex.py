from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dis_music_presence.models import ActivityKind, MediaType
from dis_music_presence.settings import DEFAULT_SETTINGS, Settings
from dis_music_presence.sources.plex import PlexProvider


def _settings(**overrides: str) -> Settings:
    values = dict(DEFAULT_SETTINGS)
    values.update(
        {
            "plex.enabled": "true",
            "plex.provider": "auto",
            "plex.user_names": "alex",
            "tautulli.url": "http://tautulli.local",
            "tautulli.api_key": "key",
            "plex.url": "http://plex.local:32400",
            "plex.token": "token",
        }
    )
    values.update(overrides)
    return Settings(path=Path("dmp.settings"), values=values)


class PlexProviderTests(unittest.TestCase):
    def test_tautulli_episode_matches_configured_user(self) -> None:
        provider = PlexProvider(_settings())
        sessions = [
            {"user": "other", "state": "playing", "media_type": "movie", "title": "Wrong"},
            {
                "user": "alex",
                "state": "playing",
                "media_type": "episode",
                "title": "Pilot",
                "grandparent_title": "Show",
                "parent_media_index": "1",
                "media_index": "2",
            },
        ]

        activity = provider._activity_from_tautulli_sessions(sessions)

        self.assertEqual(activity.kind, ActivityKind.WATCHING)
        self.assertEqual(activity.media_type, MediaType.EPISODE)
        self.assertEqual(activity.show_title, "Show")
        self.assertEqual(activity.season, 1)
        self.assertEqual(activity.episode, 2)

    def test_tautulli_matches_user_aliases(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "AznIronMan,Geoff"}))

        activity = provider._activity_from_tautulli_sessions(
            [{"user": "Geoff", "state": "playing", "media_type": "movie", "title": "Movie"}]
        )

        self.assertEqual(activity.kind, ActivityKind.WATCHING)
        self.assertEqual(activity.media_type, MediaType.MOVIE)
        self.assertEqual(activity.title, "Movie")

    def test_tautulli_accepts_pipe_delimited_aliases(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "AznIronMan|Geoff"}))

        activity = provider._activity_from_tautulli_sessions(
            [{"user": "Geoff", "state": "playing", "media_type": "movie", "title": "Movie"}]
        )

        self.assertEqual(activity.kind, ActivityKind.WATCHING)

    def test_tautulli_requires_matching_user(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "alex"}))

        activity = provider._activity_from_tautulli_sessions(
            [{"user": "other", "state": "playing", "media_type": "movie", "title": "Wrong"}]
        )

        self.assertEqual(activity.kind, ActivityKind.IDLE)

    def test_tautulli_paused_session_is_idle(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "alex"}))

        activity = provider._activity_from_tautulli_sessions(
            [{"user": "alex", "state": "paused", "media_type": "movie", "title": "Movie"}]
        )

        self.assertEqual(activity.kind, ActivityKind.IDLE)

    def test_tautulli_buffering_session_is_active(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "alex"}))

        activity = provider._activity_from_tautulli_sessions(
            [{"user": "alex", "state": "buffering", "media_type": "movie", "title": "Movie"}]
        )

        self.assertEqual(activity.kind, ActivityKind.WATCHING)
        self.assertEqual(activity.player_state, "buffering")

    def test_tautulli_remote_transcoded_session_is_active(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "alex"}))

        activity = provider._activity_from_tautulli_sessions(
            [
                {
                    "user": "alex",
                    "state": "playing",
                    "media_type": "movie",
                    "title": "Remote Movie",
                    "location": "wan",
                    "transcode_decision": "transcode",
                }
            ]
        )

        self.assertEqual(activity.kind, ActivityKind.WATCHING)
        self.assertEqual(activity.title, "Remote Movie")
        self.assertEqual(activity.raw["location"], "wan")
        self.assertEqual(activity.raw["transcode_decision"], "transcode")

    def test_plex_xml_movie_matches_user_id(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "", "plex.username": "", "plex.user_id": "42"}))
        xml = ET.fromstring(
            """
            <MediaContainer>
              <Video type="movie" title="Movie" thumb="/movie-thumb" art="/movie-art" ratingKey="99">
                <User id="42" title="alex" />
                <Player state="playing" />
              </Video>
            </MediaContainer>
            """
        )

        activity = provider._activity_from_plex_videos(xml.findall(".//Video"))

        self.assertEqual(activity.kind, ActivityKind.WATCHING)
        self.assertEqual(activity.media_type, MediaType.MOVIE)
        self.assertEqual(activity.title, "Movie")
        self.assertEqual(activity.raw["thumb"], "/movie-thumb")
        self.assertEqual(activity.raw["art"], "/movie-art")
        self.assertEqual(activity.raw["rating_key"], "99")

    def test_plex_xml_paused_video_is_idle(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "alex"}))
        xml = ET.fromstring(
            """
            <MediaContainer>
              <Video type="movie" title="Paused">
                <User title="alex" />
                <Player state="paused" />
              </Video>
            </MediaContainer>
            """
        )

        activity = provider._activity_from_plex_videos(xml.findall(".//Video"))

        self.assertEqual(activity.kind, ActivityKind.IDLE)

    def test_plex_xml_buffering_video_is_active(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "alex"}))
        xml = ET.fromstring(
            """
            <MediaContainer>
              <Video type="episode" title="Episode" grandparentTitle="Show" parentIndex="3" index="4">
                <User title="alex" />
                <Player state="buffering" />
              </Video>
            </MediaContainer>
            """
        )

        activity = provider._activity_from_plex_videos(xml.findall(".//Video"))

        self.assertEqual(activity.kind, ActivityKind.WATCHING)
        self.assertEqual(activity.media_type, MediaType.EPISODE)
        self.assertEqual(activity.player_state, "buffering")
        self.assertEqual(activity.show_title, "Show")

    def test_plex_xml_remote_transcoded_video_is_active(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "alex"}))
        xml = ET.fromstring(
            """
            <MediaContainer>
              <Video type="movie" title="Remote Movie" thumb="/thumb">
                <User title="alex" />
                <Player state="playing" local="0" remotePublicAddress="203.0.113.10" />
                <TranscodeSession videoDecision="transcode" audioDecision="transcode" />
              </Video>
            </MediaContainer>
            """
        )

        activity = provider._activity_from_plex_videos(xml.findall(".//Video"))

        self.assertEqual(activity.kind, ActivityKind.WATCHING)
        self.assertEqual(activity.title, "Remote Movie")
        self.assertEqual(activity.raw["thumb"], "/thumb")

    def test_tautulli_session_counts_match_configured_user(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "AznIronMan,Geoff"}))
        sessions = [
            {"user": "other", "state": "playing"},
            {"user": "Geoff", "state": "paused"},
            {"username": "AznIronMan", "state": "buffering"},
        ]

        self.assertEqual(provider._tautulli_session_counts(sessions), (3, 2, 1))

    def test_plex_video_counts_match_configured_user(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "alex"}))
        xml = ET.fromstring(
            """
            <MediaContainer>
              <Video type="movie" title="Paused">
                <User title="alex" />
                <Player state="paused" />
              </Video>
              <Video type="movie" title="Playing">
                <User title="alex" />
                <Player state="playing" />
              </Video>
              <Video type="movie" title="Other">
                <User title="other" />
                <Player state="playing" />
              </Video>
            </MediaContainer>
            """
        )

        self.assertEqual(provider._plex_video_counts(xml.findall(".//Video")), (3, 2, 1))

    def test_diagnostics_report_tautulli_and_plex_counts(self) -> None:
        provider = PlexProvider(_settings(**{"plex.user_names": "alex"}))
        tautulli_payload = {
            "response": {
                "result": "success",
                "data": {"sessions": [{"user": "alex", "state": "playing"}]},
            }
        }
        plex_xml = b"""
            <MediaContainer>
              <Video type="movie" title="Movie">
                <User title="alex" />
                <Player state="paused" />
              </Video>
            </MediaContainer>
        """

        with patch("dis_music_presence.sources.plex._http_json", return_value=tautulli_payload), patch(
            "dis_music_presence.sources.plex._http_bytes", return_value=plex_xml
        ):
            diagnostics = provider.diagnostics()

        self.assertIn("provider=auto; user_filter=names=alex", diagnostics)
        self.assertIn("tautulli: reachable - sessions=1, matching_user=1, active=1", diagnostics)
        self.assertIn("plex_api: reachable - sessions=1, matching_user=1, active=0", diagnostics)


if __name__ == "__main__":
    unittest.main()
