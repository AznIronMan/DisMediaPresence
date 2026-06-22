"""Forward-compatible DisMediaPresence import package.

The implementation package remains ``dis_music_presence`` so existing imports
and installed entry points keep working after the rebrand.
"""

from __future__ import annotations

import importlib
import sys

_REAL_PACKAGE = "dis_music_presence"
_ALIASED_MODULES = (
    "artwork",
    "cli",
    "discord_ipc",
    "formatter",
    "models",
    "runtime",
    "settings",
    "sources",
    "sources.apple_music",
    "sources.base",
    "sources.plex",
    "sources.spotify",
)

_real_package = importlib.import_module(_REAL_PACKAGE)

APP_NAME = _real_package.APP_NAME
LEGACY_APP_NAME = _real_package.LEGACY_APP_NAME
__version__ = _real_package.__version__

for _module_name in _ALIASED_MODULES:
    sys.modules[f"{__name__}.{_module_name}"] = importlib.import_module(f"{_REAL_PACKAGE}.{_module_name}")

__all__ = ["APP_NAME", "LEGACY_APP_NAME", "__version__"]
