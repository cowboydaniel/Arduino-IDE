"""Tests for library path expansion in the ``arduino-cli`` wrapper."""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path


def _load_cli_class():
    project_root = Path(__file__).resolve().parents[1]
    cli_path = project_root / "arduino-cli"
    loader = importlib.machinery.SourceFileLoader("arduino_cli_module", str(cli_path))
    spec = importlib.util.spec_from_loader("arduino_cli_module", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module.ArduinoCLI


def test_expand_library_directories_discovers_children(tmp_path):
    ArduinoCLI = _load_cli_class()
    cli = ArduinoCLI()

    libs_root = tmp_path / "libraries"
    (libs_root / "EEPROM" / "src").mkdir(parents=True)
    (libs_root / "EEPROM" / "src" / "EEPROM.h").write_text("", encoding="utf-8")

    (libs_root / "FooLib").mkdir()
    (libs_root / "FooLib" / "library.properties").write_text("name=FooLib\n", encoding="utf-8")

    expanded = cli._expand_library_directories([libs_root])

    assert (libs_root / "EEPROM").resolve() in expanded
    assert (libs_root / "FooLib").resolve() in expanded


def test_expand_library_directories_accepts_direct_library(tmp_path):
    ArduinoCLI = _load_cli_class()
    cli = ArduinoCLI()

    library = tmp_path / "CustomLib"
    (library / "src").mkdir(parents=True)
    (library / "src" / "CustomLib.h").write_text("", encoding="utf-8")

    expanded = cli._expand_library_directories([library])

    assert expanded == [library.resolve()]
