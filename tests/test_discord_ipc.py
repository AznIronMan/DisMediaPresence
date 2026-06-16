from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dis_music_presence.discord_ipc import MAX_ACTIVITY_FIELD_LENGTH, build_activity_payload
from dis_music_presence.models import FormattedPresence


class DiscordIpcTests(unittest.TestCase):
    def test_listening_payload_uses_details_for_visible_status(self) -> None:
        presence = FormattedPresence(
            text="Listening to \u266a Artist - Song",
            activity_type=2,
            source="Apple Music",
        )

        payload = build_activity_payload(presence)

        self.assertEqual(payload["type"], 2)
        self.assertEqual(payload["details"], "\u266a Artist - Song")
        self.assertEqual(payload["name"], "\u266a Artist - Song")
        self.assertEqual(payload["status_display_type"], 2)
        self.assertEqual(payload["state"], "Apple Music")

    def test_watching_payload_strips_duplicate_prefix(self) -> None:
        presence = FormattedPresence(
            text="Watching Movie Name",
            activity_type=3,
            source="Plex",
        )

        payload = build_activity_payload(presence)

        self.assertEqual(payload["details"], "Movie Name")

    def test_activity_fields_are_truncated_to_discord_limit(self) -> None:
        long_text = "Listening to " + ("A" * 180)
        presence = FormattedPresence(text=long_text, activity_type=2, source="Apple Music")

        payload = build_activity_payload(presence)

        self.assertLessEqual(len(str(payload["details"])), MAX_ACTIVITY_FIELD_LENGTH)
        self.assertTrue(str(payload["details"]).endswith("..."))


if __name__ == "__main__":
    unittest.main()
