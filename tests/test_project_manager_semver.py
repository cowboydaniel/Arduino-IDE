"""Tests for ProjectManager semantic version resolution."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import sys

from packaging.version import Version, InvalidVersion

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arduino_ide.models import (
    Library,
    LibraryType,
    LibraryVersion,
    ProjectConfig,
    ProjectDependency,
)
from arduino_ide.services.project_manager import ProjectManager


class DummyLibraryManager:
    """Simple library manager stub for testing."""

    def __init__(self, libraries):
        self._libraries = libraries

    def get_library(self, name):
        return self._libraries.get(name)


def make_library(name: str, versions: List[str], installed_version: Optional[str] = None) -> Library:
    """Create a library instance with the given versions for tests."""

    version_objects: list[LibraryVersion] = []
    base_date = datetime(2024, 1, 1)
    for index, version in enumerate(versions):
        version_objects.append(
            LibraryVersion(
                version=version,
                url=f"https://example.com/{name}/{version}.zip",
                size=0,
                checksum="",
                release_date=base_date + timedelta(days=index),
            )
        )

    latest = None
    parsed_versions: List[Version] = []
    for version in versions:
        try:
            parsed_versions.append(Version(version))
        except InvalidVersion:
            continue

    latest = max(parsed_versions) if parsed_versions else None

    library = Library(
        name=name,
        author="Tester",
        description="",
        category="General",
        lib_type=LibraryType.COMMUNITY,
        versions=version_objects,
        latest_version=str(latest) if latest else None,
    )

    if installed_version:
        library.installed_version = installed_version

    return library


def make_project_manager(library_name: str, dependency_version: str, library: Library) -> ProjectManager:
    project = ProjectConfig(
        name="Demo",
        dependencies={
            library_name: ProjectDependency(name=library_name, version=dependency_version)
        },
    )

    manager = ProjectManager(library_manager=DummyLibraryManager({library_name: library}))
    manager.current_project = project
    return manager


def test_wildcard_selects_highest_version():
    library = make_library("Example", ["1.0.0", "1.5.0", "0.9.0"])
    manager = make_project_manager("Example", "*", library)

    plan = manager.create_install_plan()

    assert plan.to_install == [("Example", "1.5.0")]


def test_caret_constraint_uses_highest_compatible_version():
    library = make_library("Example", ["1.2.5", "1.9.0", "2.0.0"])
    manager = make_project_manager("Example", "^1.2.0", library)

    plan = manager.create_install_plan()

    assert ("Example", "1.9.0") in plan.to_install


def test_range_constraint_selects_within_bounds():
    library = make_library("Example", ["2.0.0", "1.5.0", "1.0.0"])
    manager = make_project_manager("Example", ">=1.0.0,<2.0.0", library)

    plan = manager.create_install_plan()

    assert ("Example", "1.5.0") in plan.to_install


def test_exact_version_requests_update_when_installed_differs():
    library = make_library("Example", ["1.0.0", "1.1.0", "1.2.0"], installed_version="1.0.0")
    manager = make_project_manager("Example", "1.1.0", library)

    plan = manager.create_install_plan()

    assert ("Example", "1.0.0", "1.1.0") in plan.to_update


def test_conflict_added_when_no_versions_match_constraint():
    library = make_library("Example", ["1.0.0", "1.1.0"])
    manager = make_project_manager("Example", ">=2.0.0", library)

    plan = manager.create_install_plan()

    assert any("No available versions" in conflict for conflict in plan.conflicts)
