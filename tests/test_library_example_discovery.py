from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from arduino_ide.models import Library, LibraryIndex, LibraryType
from arduino_ide.services.library_manager import LibraryManager


def create_manager(tmp_path: Path) -> LibraryManager:
    """Create a LibraryManager instance that uses a temporary workspace."""
    manager = LibraryManager()
    manager.base_dir = tmp_path
    manager.libraries_dir = tmp_path / "libraries"
    manager.cache_dir = tmp_path / "cache"
    manager.index_file = manager.cache_dir / "library_index.json"
    manager.installed_file = manager.cache_dir / "installed_libraries.json"
    manager.libraries_dir.mkdir(parents=True, exist_ok=True)
    manager.cache_dir.mkdir(parents=True, exist_ok=True)
    manager.library_index = LibraryIndex()
    manager.installed_libraries = {}
    return manager


def add_library(manager: LibraryManager, name: str, install_root: Path) -> Library:
    library = Library(
        name=name,
        author="Tester",
        description="Test library",
        category="Testing",
        lib_type=LibraryType.COMMUNITY,
        installed_version="1.0.0",
        install_path=str(install_root),
    )
    manager.library_index.libraries.append(library)
    manager.installed_libraries[name] = "1.0.0"
    return library


def test_get_example_sketch_path_direct_match(tmp_path):
    manager = create_manager(tmp_path)
    servo_root = manager.libraries_dir / "Servo"
    example_dir = servo_root / "examples" / "Sweep"
    example_dir.mkdir(parents=True)
    sketch_path = example_dir / "Sweep.ino"
    sketch_path.write_text("// test sweep", encoding="utf-8")

    add_library(manager, "Servo", servo_root)

    resolved = manager.get_example_sketch_path("Servo", "Sweep")
    assert resolved == sketch_path

    resolved_with_extension = manager.get_example_sketch_path("Servo", "Sweep/Sweep.ino")
    assert resolved_with_extension == sketch_path


def test_get_example_sketch_path_nested_directory(tmp_path):
    manager = create_manager(tmp_path)
    wifi_root = manager.libraries_dir / "WiFi"
    nested_dir = wifi_root / "examples" / "ESP32" / "WiFiScan"
    nested_dir.mkdir(parents=True)
    sketch_path = nested_dir / "WiFiScan.ino"
    sketch_path.write_text("// wifi scan", encoding="utf-8")

    add_library(manager, "WiFi", wifi_root)

    resolved = manager.get_example_sketch_path("WiFi", "ESP32/WiFiScan")
    assert resolved == sketch_path


def test_get_example_sketch_path_missing_returns_none(tmp_path):
    manager = create_manager(tmp_path)
    add_library(manager, "Stepper", manager.libraries_dir / "Stepper")

    assert manager.get_example_sketch_path("Stepper", "MissingExample") is None
