import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from arduino_ide.models.library import Library, LibraryIndex, LibraryType
from arduino_ide.services.library_manager import LibraryManager


@pytest.fixture
def library_manager(tmp_path, monkeypatch):
    """Create a library manager with a temporary home directory"""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    manager = LibraryManager()
    manager.library_index = LibraryIndex()
    manager.installed_libraries = {}
    return manager


def _create_library(manager: LibraryManager, name: str, version: str,
                   custom_dir: str = None, managed: bool = False) -> Library:
    """Helper to create a library installation"""
    # Determine installation path
    if custom_dir:
        lib_path = Path(manager.libraries_dir) / custom_dir
    else:
        lib_path = Path(manager.libraries_dir) / name

    # Create library.properties file
    lib_path.mkdir(parents=True, exist_ok=True)
    props_file = lib_path / "library.properties"
    props_content = f"""name={name}
version={version}
author=Test Author
maintainer=Test Maintainer
sentence=A test library
category=Test
url=https://example.com
architectures=*
"""
    props_file.write_text(props_content)

    # Create a simple header file
    src_dir = lib_path / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / f"{name}.h").write_text(f"// {name} v{version}\n")

    # Create library object
    library = Library(
        name=name,
        author="Test Author",
        description="Test library",
        category="Test",
        lib_type=LibraryType.COMMUNITY,
        installed_version=version,
    )
    library.install_path = str(lib_path)

    # Add to index
    manager.library_index.libraries.append(library)

    # Mark as managed if requested
    if managed:
        manager.installed_libraries[name] = version

    return library


def test_detect_duplicate_installations_finds_same_library_multiple_locations(library_manager):
    """Test detection of same library installed in multiple locations"""
    # Create the same library in two different directories
    _create_library(library_manager, "Servo", "1.0.0", custom_dir="Servo", managed=True)
    _create_library(library_manager, "Servo", "1.0.0", custom_dir="Servo-backup", managed=False)

    duplicates = library_manager.detect_duplicate_installations()

    assert "Servo" in duplicates
    assert len(duplicates["Servo"]) == 2
    assert any(install["source"] == "managed" for install in duplicates["Servo"])
    assert any(install["source"] == "manual" for install in duplicates["Servo"])


def test_detect_duplicate_installations_finds_multiple_versions(library_manager):
    """Test detection of multiple versions of the same library"""
    _create_library(library_manager, "WiFi", "1.0.0", custom_dir="WiFi-1.0.0", managed=True)
    _create_library(library_manager, "WiFi", "2.0.0", custom_dir="WiFi-2.0.0", managed=False)
    _create_library(library_manager, "WiFi", "1.5.0", custom_dir="WiFi", managed=False)

    duplicates = library_manager.detect_duplicate_installations()

    assert "WiFi" in duplicates
    assert len(duplicates["WiFi"]) == 3

    versions = [install["version"] for install in duplicates["WiFi"]]
    assert "1.0.0" in versions
    assert "1.5.0" in versions
    assert "2.0.0" in versions


def test_detect_duplicate_installations_ignores_unique_libraries(library_manager):
    """Test that unique libraries are not reported as duplicates"""
    _create_library(library_manager, "Servo", "1.0.0", managed=True)
    _create_library(library_manager, "WiFi", "2.0.0", managed=True)
    _create_library(library_manager, "Stepper", "1.1.0", managed=True)

    duplicates = library_manager.detect_duplicate_installations()

    assert len(duplicates) == 0


def test_detect_duplicate_installations_case_insensitive(library_manager):
    """Test that library name matching is case-insensitive"""
    _create_library(library_manager, "servo", "1.0.0", custom_dir="servo-lower", managed=True)
    _create_library(library_manager, "Servo", "1.0.0", custom_dir="Servo-upper", managed=False)
    _create_library(library_manager, "SERVO", "1.0.0", custom_dir="SERVO-caps", managed=False)

    duplicates = library_manager.detect_duplicate_installations()

    # Should detect all as duplicates (case-insensitive)
    assert len(duplicates) == 1
    # The key should be one of the original names
    key = list(duplicates.keys())[0]
    assert key.lower() == "servo"
    assert len(duplicates[key]) == 3


def test_find_multiple_versions_returns_sorted_versions(library_manager):
    """Test that multiple versions are returned in sorted order"""
    _create_library(library_manager, "AsyncTCP", "2.0.0", custom_dir="AsyncTCP-2", managed=False)
    _create_library(library_manager, "AsyncTCP", "1.0.0", custom_dir="AsyncTCP-1", managed=True)
    _create_library(library_manager, "AsyncTCP", "1.5.0", custom_dir="AsyncTCP-1.5", managed=False)

    multiple_versions = library_manager.find_multiple_versions()

    assert "AsyncTCP" in multiple_versions
    assert multiple_versions["AsyncTCP"] == ["1.0.0", "1.5.0", "2.0.0"]


def test_find_multiple_versions_excludes_single_version_duplicates(library_manager):
    """Test that libraries with only one version (but multiple locations) are excluded"""
    _create_library(library_manager, "OneWire", "2.3.5", custom_dir="OneWire", managed=True)
    _create_library(library_manager, "OneWire", "2.3.5", custom_dir="OneWire-copy", managed=False)

    multiple_versions = library_manager.find_multiple_versions()

    # Should not be in multiple_versions since it's the same version
    assert "OneWire" not in multiple_versions


def test_get_duplicate_summary_returns_formatted_output(library_manager):
    """Test that summary output is properly formatted"""
    _create_library(library_manager, "WiFi", "1.0.0", custom_dir="WiFi-old", managed=False)
    _create_library(library_manager, "WiFi", "2.0.0", custom_dir="WiFi-new", managed=True)

    summary = library_manager.get_duplicate_summary()

    assert "Duplicate library installations detected" in summary
    assert "WiFi" in summary
    assert "1.0.0" in summary
    assert "2.0.0" in summary
    assert "Recommendations" in summary


def test_get_duplicate_summary_no_duplicates(library_manager):
    """Test summary when no duplicates exist"""
    _create_library(library_manager, "Servo", "1.0.0", managed=True)

    summary = library_manager.get_duplicate_summary()

    assert "No duplicate library installations found" in summary


def test_resolve_duplicates_dry_run_mode(library_manager):
    """Test that dry_run mode doesn't actually remove files"""
    _create_library(library_manager, "LCD", "1.0.0", custom_dir="LCD-old", managed=False)
    _create_library(library_manager, "LCD", "2.0.0", custom_dir="LCD-new", managed=True)

    old_path = library_manager.libraries_dir / "LCD-old"
    new_path = library_manager.libraries_dir / "LCD-new"

    # Dry run should not delete anything
    result = library_manager.resolve_duplicates("LCD", dry_run=True)

    assert result["kept"]["version"] == "2.0.0"
    assert len(result["removed"]) == 1
    assert result["removed"][0]["version"] == "1.0.0"
    assert len(result["errors"]) == 0

    # Both paths should still exist
    assert old_path.exists()
    assert new_path.exists()


def test_resolve_duplicates_removes_older_versions(library_manager):
    """Test that older versions are removed when not in dry_run mode"""
    _create_library(library_manager, "MQTT", "1.0.0", custom_dir="MQTT-1.0", managed=False)
    _create_library(library_manager, "MQTT", "1.5.0", custom_dir="MQTT-1.5", managed=False)
    _create_library(library_manager, "MQTT", "2.0.0", custom_dir="MQTT-2.0", managed=True)

    old_path_1 = library_manager.libraries_dir / "MQTT-1.0"
    old_path_2 = library_manager.libraries_dir / "MQTT-1.5"
    new_path = library_manager.libraries_dir / "MQTT-2.0"

    # Actually remove duplicates
    result = library_manager.resolve_duplicates("MQTT", dry_run=False)

    assert result["kept"]["version"] == "2.0.0"
    assert len(result["removed"]) == 2
    assert len(result["errors"]) == 0

    # Old paths should be removed
    assert not old_path_1.exists()
    assert not old_path_2.exists()
    # New path should remain
    assert new_path.exists()


def test_resolve_duplicates_keep_specific_version(library_manager):
    """Test keeping a specific version when resolving duplicates"""
    _create_library(library_manager, "NeoPixel", "1.0.0", custom_dir="NeoPixel-1.0", managed=True)
    _create_library(library_manager, "NeoPixel", "2.0.0", custom_dir="NeoPixel-2.0", managed=False)

    path_1 = library_manager.libraries_dir / "NeoPixel-1.0"
    path_2 = library_manager.libraries_dir / "NeoPixel-2.0"

    # Keep version 1.0.0 explicitly
    result = library_manager.resolve_duplicates("NeoPixel", keep_version="1.0.0", dry_run=False)

    assert result["kept"]["version"] == "1.0.0"
    assert len(result["removed"]) == 1
    assert result["removed"][0]["version"] == "2.0.0"

    # Version 1.0.0 should remain
    assert path_1.exists()
    assert not path_2.exists()


def test_resolve_duplicates_keep_specific_path(library_manager):
    """Test keeping a specific path when resolving duplicates"""
    _create_library(library_manager, "Adafruit", "1.0.0", custom_dir="Adafruit-A", managed=False)
    _create_library(library_manager, "Adafruit", "1.0.0", custom_dir="Adafruit-B", managed=True)

    path_a = str(library_manager.libraries_dir / "Adafruit-A")
    path_b = library_manager.libraries_dir / "Adafruit-B"

    # Keep specific path A
    result = library_manager.resolve_duplicates("Adafruit", keep_path=path_a, dry_run=False)

    assert result["kept"]["path"] == path_a
    assert len(result["removed"]) == 1

    # Path A should remain, B should be removed
    assert Path(path_a).exists()
    assert not path_b.exists()


def test_resolve_duplicates_prefers_managed_installations(library_manager):
    """Test that managed installations are preferred over manual ones"""
    _create_library(library_manager, "Preferences", "1.0.0", custom_dir="Prefs-manual", managed=False)
    _create_library(library_manager, "Preferences", "1.0.0", custom_dir="Preferences", managed=True)

    managed_path = library_manager.libraries_dir / "Preferences"
    manual_path = library_manager.libraries_dir / "Prefs-manual"

    # Should prefer managed installation
    result = library_manager.resolve_duplicates("Preferences", dry_run=False)

    assert result["kept"]["source"] == "managed"
    assert managed_path.exists()
    assert not manual_path.exists()


def test_resolve_duplicates_no_duplicates_found(library_manager):
    """Test error handling when no duplicates exist for the library"""
    _create_library(library_manager, "SingleLib", "1.0.0", managed=True)

    result = library_manager.resolve_duplicates("SingleLib", dry_run=True)

    assert result["kept"] is None
    assert len(result["removed"]) == 0
    assert len(result["errors"]) == 1
    assert "No duplicates found" in result["errors"][0]


def test_resolve_duplicates_nonexistent_library(library_manager):
    """Test error handling for non-existent library"""
    result = library_manager.resolve_duplicates("NonExistent", dry_run=True)

    assert result["kept"] is None
    assert len(result["removed"]) == 0
    assert len(result["errors"]) == 1
    assert "No duplicates found" in result["errors"][0]


def test_resolve_duplicates_version_not_found(library_manager):
    """Test error handling when specified version doesn't exist"""
    _create_library(library_manager, "TestLib", "1.0.0", custom_dir="TestLib-1", managed=False)
    _create_library(library_manager, "TestLib", "2.0.0", custom_dir="TestLib-2", managed=True)

    result = library_manager.resolve_duplicates("TestLib", keep_version="3.0.0", dry_run=True)

    assert result["kept"] is None
    assert len(result["removed"]) == 0
    assert len(result["errors"]) == 1
    assert "Version '3.0.0' not found" in result["errors"][0]


def test_detect_duplicates_empty_libraries_directory(library_manager):
    """Test handling of empty libraries directory"""
    # Don't create any libraries
    duplicates = library_manager.detect_duplicate_installations()

    assert len(duplicates) == 0


def test_detect_duplicates_missing_library_properties(library_manager):
    """Test handling of directories without library.properties"""
    # Create a directory without library.properties
    lib_path = library_manager.libraries_dir / "IncompleteLib"
    lib_path.mkdir(parents=True, exist_ok=True)
    (lib_path / "src" / "test.h").parent.mkdir(parents=True, exist_ok=True)
    (lib_path / "src" / "test.h").write_text("// test")

    duplicates = library_manager.detect_duplicate_installations()

    # Should not crash, should return empty
    assert len(duplicates) == 0
