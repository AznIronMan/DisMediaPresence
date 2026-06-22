from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dis_music_presence.runtime import _effective_source_priority
from dis_music_presence.settings import DEFAULT_SETTINGS, Settings


def _settings(**overrides: str) -> Settings:
    values = dict(DEFAULT_SETTINGS)
    values.update(overrides)
    return Settings(path=Path("dmp.settings"), values=values)


class RuntimeTests(unittest.TestCase):
    def test_effective_priority_appends_new_sources_for_legacy_settings(self) -> None:
        providers = [_Provider("apple_music"), _Provider("spotify"), _Provider("plex")]

        priority = _effective_source_priority(_settings(**{"app.source_priority": "apple_music,plex"}), providers)

        self.assertEqual(priority, ["apple_music", "plex", "spotify"])


class _Provider:
    def __init__(self, name: str) -> None:
        self.name = name


if __name__ == "__main__":
    unittest.main()
