from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dis_music_presence.cli import main


class CliTests(unittest.TestCase):
    def test_version_command(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            code = main(["version"])

        self.assertEqual(code, 0)
        self.assertIn("0.6.0", output.getvalue())

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


if __name__ == "__main__":
    unittest.main()
