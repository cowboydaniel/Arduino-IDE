"""Centralized application metadata and configuration values."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional

APP_NAME = "Arduino IDE Modern"
APP_ORGANIZATION = "Arduino IDE Modern"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "A modern Arduino development environment inspired by Arduino's ecosystem."
APP_AUTHORS = ("Arduino IDE Modern Team",)
APP_WEBSITE = "https://www.arduino.cc/"
APP_SOURCE_REPO = "https://github.com/arduino"
APP_ISSUE_TRACKER = "https://github.com/arduino/Arduino/issues"

ABOUT_CREDITS = (
    "Design & Development: Arduino IDE Modern Team",
    "Built with PySide6",
)


def _expand_path_list(raw_value: str) -> List[Path]:
    """Expand a path list from an environment variable."""

    if not raw_value:
        return []

    paths: List[Path] = []
    for chunk in raw_value.split(os.pathsep):
        chunk = chunk.strip()
        if not chunk:
            continue
        paths.append(Path(chunk).expanduser())
    return paths


DEFAULT_KICAD_GLOBAL_PATHS: List[Path] = [
    Path.home() / ".local/share/kicad/symbols",
    Path.home() / "Library/Application Support/kicad/symbols",
    Path("/usr/share/kicad/symbols"),
    Path("/usr/local/share/kicad/symbols"),
]

KICAD_GLOBAL_SYMBOL_LIBRARY_PATHS = tuple(
    _expand_path_list(os.environ.get("ARDUINO_IDE_KICAD_SYMBOL_PATHS"))
    or DEFAULT_KICAD_GLOBAL_PATHS
)

KICAD_PROJECT_CACHE_DIR = Path(
    os.environ.get(
        "ARDUINO_IDE_KICAD_CACHE_DIR",
        Path.home() / ".arduino_ide" / "kicad_cache",
    )
).expanduser()


# ---------------------------------------------------------------------------
# Official Arduino CLI
# ---------------------------------------------------------------------------

def get_arduino_cli_path() -> Optional[Path]:
    """Locate the official ``arduino-cli`` binary.

    Resolution order:
    1. ``ARDUINO_CLI_PATH`` environment variable (explicit override)
    2. ``arduino-cli`` on the system ``PATH``
    """
    env_path = os.environ.get("ARDUINO_CLI_PATH")
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.is_file():
            return candidate

    found = shutil.which("arduino-cli")
    if found:
        return Path(found)

    return None
