from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from arduino_ide.services.library_manager import LibraryManager


def test_builtin_libraries_are_bootstrapped(tmp_path, monkeypatch):
    """The library manager should copy bundled libraries on first run."""

    fake_home = tmp_path / "home"
    fake_home.mkdir()

    # Ensure Path.home() points to our temporary directory
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    cores_root = fake_home / ".arduino-ide" / "cores" / "arduino-avr"
    core_include_dir = cores_root / "cores" / "arduino"
    core_include_dir.mkdir(parents=True)
    (core_include_dir / "Arduino.h").write_text("// stub core header\n", encoding="utf-8")

    builtin_source = cores_root / "libraries"
    builtin_source.mkdir(parents=True)

    libraries = {
        "Servo": "Servo.h",
        "Wire": "Wire.h",
        "SD": "SD.h",
    }

    for name, header in libraries.items():
        lib_dir = builtin_source / name
        src_dir = lib_dir / "src"
        src_dir.mkdir(parents=True)
        (lib_dir / "library.properties").write_text(
            f"name={name}\nversion=1.0.0\n", encoding="utf-8"
        )
        (src_dir / header).write_text(f"// {name} header\n", encoding="utf-8")

    manager = LibraryManager()

    managed_root = fake_home / ".arduino-ide-modern" / "libraries"

    for name, header in libraries.items():
        header_path = managed_root / name / "src" / header
        assert header_path.exists(), f"Expected {header_path} to be installed"

    # The manager should now report these libraries as installed
    for name in libraries:
        assert name in manager.installed_libraries
