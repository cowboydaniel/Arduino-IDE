import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from arduino_ide.models.library import Library, LibraryIndex, LibraryType
from arduino_ide.services.library_manager import LibraryManager


@pytest.fixture
def library_manager(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    manager = LibraryManager()
    manager.library_index = LibraryIndex()
    manager.installed_libraries = {}
    return manager


def _create_library(manager: LibraryManager, name: str, files: dict) -> Library:
    lib_path = Path(manager.libraries_dir) / name
    for relative_path, content in files.items():
        file_path = lib_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    library = Library(
        name=name,
        author="Test Author",
        description="Test library",
        category="Test",
        lib_type=LibraryType.COMMUNITY,
        installed_version="1.0.0",
    )
    library.install_path = str(lib_path)

    manager.library_index.libraries.append(library)
    manager.installed_libraries[name] = "1.0.0"
    return library


def test_detect_conflicts_identifies_duplicate_headers(library_manager):
    _create_library(
        library_manager,
        "Wire",
        {"src/Wire.h": "#pragma once\n", "src/Wire.cpp": ""},
    )
    _create_library(
        library_manager,
        "AltWire",
        {"src/Wire.h": "#pragma once\n", "src/AltWire.cpp": ""},
    )

    conflicts = library_manager.detect_conflicts("Wire")

    assert conflicts, "Expected duplicate header conflict to be reported"
    assert any("Wire.h" in conflict for conflict in conflicts)
    assert any("AltWire" in conflict for conflict in conflicts)


def test_detect_conflicts_identifies_namespace_collisions(library_manager):
    _create_library(
        library_manager,
        "SPIHelper",
        {"src/SPI/Helper.h": "#pragma once\n"},
    )
    _create_library(
        library_manager,
        "SPIBus",
        {"src/SPI/Bus.h": "#pragma once\n"},
    )

    conflicts = library_manager.detect_conflicts("SPIHelper")

    assert conflicts, "Expected namespace collision to be reported"
    assert any("Namespace directory 'SPI'" in conflict for conflict in conflicts)
    assert any("SPIBus" in conflict for conflict in conflicts)


def test_detect_conflicts_without_overlaps_returns_empty(library_manager):
    _create_library(
        library_manager,
        "FooLib",
        {"src/Foo.h": "#pragma once\n"},
    )
    _create_library(
        library_manager,
        "BarLib",
        {"src/Bar.h": "#pragma once\n"},
    )

    conflicts = library_manager.detect_conflicts("FooLib")

    assert conflicts == []
