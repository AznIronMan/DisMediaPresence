from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dis_music_presence.cli import main
from dis_music_presence.models import ActivityKind, MediaActivity, MediaType
from dis_music_presence.settings import load_settings
from dis_music_presence.sources.base import SourceCapability


class CliTests(unittest.TestCase):
    def test_version_command(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            code = main(["version"])

        self.assertEqual(code, 0)
        self.assertIn("0.9.1", output.getvalue())

    def test_config_init_and_show(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = str(Path(tmp) / "dmp.settings")
            init_output = StringIO()
            show_output = StringIO()

            with redirect_stdout(init_output):
                init_code = main(["--settings", settings, "config", "init"])
            with redirect_stdout(show_output):
                show_code = main(["--settings", settings, "config", "show"])

            self.assertEqual(init_code, 0)
            self.assertEqual(show_code, 0)
            self.assertIn("app.poll_interval_seconds=15", show_output.getvalue())

    def test_priority_set_updates_source_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = str(Path(tmp) / "dmp.settings")
            with redirect_stdout(StringIO()):
                main(["--settings", settings_path, "config", "init"])
            output = StringIO()

            with redirect_stdout(output):
                code = main(["--settings", settings_path, "priority", "set", "plex"])

            settings = load_settings(settings_path)
            self.assertEqual(code, 0)
            self.assertEqual(settings.get("app.source_priority"), "plex,apple_music")
            self.assertIn("plex > apple_music", output.getvalue())

    def test_status_reports_active_priority_winner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = str(Path(tmp) / "dmp.settings")
            with redirect_stdout(StringIO()):
                main(["--settings", settings_path, "config", "init"])
                main(["--settings", settings_path, "priority", "set", "plex"])
            providers = [
                _FakeProvider(
                    "apple_music",
                    MediaActivity(
                        kind=ActivityKind.LISTENING,
                        source="Apple Music",
                        media_type=MediaType.MUSIC,
                        title="Song",
                        artist="Artist",
                        player_state="playing",
                    ),
                ),
                _FakeProvider(
                    "plex",
                    MediaActivity(
                        kind=ActivityKind.WATCHING,
                        source="Plex",
                        media_type=MediaType.MOVIE,
                        title="Movie",
                        player_state="playing",
                    ),
                ),
            ]
            output = StringIO()

            with patch("dis_music_presence.cli.build_providers", return_value=providers), patch(
                "dis_music_presence.cli.check_discord",
                return_value=SimpleNamespace(available=False, configured=False, message="mock"),
            ), redirect_stdout(output):
                code = main(["--settings", settings_path, "status"])

            self.assertEqual(code, 0)
            text = output.getvalue()
            self.assertIn("Source priority: plex > apple_music", text)
            self.assertIn("Winner: plex - Watching Movie", text)


class _FakeProvider:
    def __init__(self, name: str, activity: MediaActivity) -> None:
        self.name = name
        self.activity = activity

    def poll(self) -> MediaActivity:
        return self.activity

    def diagnostics(self) -> list[str]:
        return []

    def capability(self) -> SourceCapability:
        return SourceCapability(self.name, True, True, True, "mock")


if __name__ == "__main__":
    unittest.main()
