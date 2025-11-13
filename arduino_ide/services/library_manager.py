"""
Library Manager Service

Handles library search, installation, updates, and dependency resolution.
"""

import os
import json
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Set
from datetime import datetime
import requests
from packaging.version import Version, InvalidVersion

# Optional PySide6 support
try:
    from PySide6.QtCore import QObject, Signal
    HAS_QT = True
except ImportError:
    # Provide stub for non-Qt usage
    QObject = object
    Signal = lambda *args, **kwargs: None
    HAS_QT = False

from ..models import (
    Library, LibraryIndex, LibraryVersion, LibraryDependency,
    LibraryType, LibraryStatus, ProjectConfig, InstallPlan, DependencyTree
)
from .download_manager import DownloadManager
from .core_manager import CoreManager
from .index_updater import IndexUpdater


class LibraryManager(QObject):
    """Manages Arduino libraries"""

    # Signals (only functional with Qt)
    if HAS_QT:
        library_installed = Signal(str, str)  # (name, version)
        library_uninstalled = Signal(str)  # (name)
        library_updated = Signal(str, str, str)  # (name, old_version, new_version)
        index_updated = Signal()
        progress_changed = Signal(int)  # Progress percentage
        status_message = Signal(str)  # Status message

    # Arduino Library Index URL
    LIBRARY_INDEX_URL = "https://downloads.arduino.cc/libraries/library_index.json"
    LIBRARY_INDEX_MIRROR = "https://raw.githubusercontent.com/arduino/library-registry/main/public/library_index.json"

    def __init__(self, parent=None):
        if HAS_QT:
            super().__init__(parent)
        else:
            super().__init__()

        # Initialize paths
        self.base_dir = Path.home() / ".arduino-ide-modern"
        self.libraries_dir = self.base_dir / "libraries"
        self.cache_dir = self.base_dir / "cache"
        self.index_file = self.cache_dir / "library_index.json"
        self.installed_file = self.cache_dir / "installed_libraries.json"

        # Create directories
        self.libraries_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Library index
        self.library_index = LibraryIndex()
        self.installed_libraries: Dict[str, str] = {}  # name -> version
        self.installed_library_paths: Dict[str, str] = {}  # name -> install path

        # Enhanced services
        self.download_manager = DownloadManager(self.cache_dir, parent=self)
        self.index_updater = IndexUpdater(self.cache_dir, parent=self)

        # Connect signals
        self.download_manager.progress_changed.connect(
            lambda p: self.progress_changed.emit(p.percentage)
        )
        self.download_manager.status_message.connect(self.status_message.emit)
        self.index_updater.status_message.connect(self.status_message.emit)

        # Load data
        self._load_installed_libraries()
        self._load_library_index()

    def _load_installed_libraries(self):
        """Load installed libraries from file"""
        if self.installed_file.exists():
            try:
                with open(self.installed_file, 'r', encoding='utf-8') as f:
                    self.installed_libraries = json.load(f)
            except Exception as e:
                print(f"Error loading installed libraries: {e}")
                self.installed_libraries = {}

        # Also scan libraries directory
        self._scan_installed_libraries()
        self._ensure_builtin_libraries_available()

    def _scan_installed_libraries(self):
        """Scan libraries directory for installed libraries"""
        if not self.libraries_dir.exists():
            return

        # Reset the path mapping on each scan so we do not keep stale entries
        self.installed_library_paths = {}

        for lib_dir in sorted(self.libraries_dir.iterdir(), key=lambda p: p.name.lower()):
            if not lib_dir.is_dir():
                continue

            props_file = lib_dir / "library.properties"
            display_name = lib_dir.name
            version = "unknown"

            if props_file.exists():
                try:
                    props = self._parse_library_properties(props_file)
                    display_name = props.get("name", display_name) or display_name
                    version = props.get("version", version)
                    self.installed_libraries[display_name] = version
                except Exception as e:
                    print(f"Error reading {props_file}: {e}")

            # Track the actual installation path even if metadata is missing so
            # features like example discovery can resolve the on-disk location.
            self.installed_library_paths[display_name] = str(lib_dir)

    def _ensure_builtin_libraries_available(self):
        """Install bundled libraries from the AVR core on first run."""
        if self.installed_libraries:
            return

        if self.libraries_dir.exists() and any(self.libraries_dir.iterdir()):
            return

        core_manager = CoreManager()
        newly_installed = core_manager.ensure_builtin_libraries(self.libraries_dir, ensure_core=True)

        if newly_installed:
            # Rescan so the freshly installed libraries are indexed immediately
            self._scan_installed_libraries()
            self._save_installed_libraries()

    def _parse_library_properties(self, path: Path) -> Dict[str, str]:
        """Parse library.properties file"""
        props = {}
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    props[key.strip()] = value.strip()
        return props

    def _save_installed_libraries(self):
        """Save installed libraries to file"""
        with open(self.installed_file, 'w', encoding='utf-8') as f:
            json.dump(self.installed_libraries, f, indent=2)

    def get_library_search_paths(self) -> List[Path]:
        """Return directories that should be exposed to ``arduino-cli``."""

        search_paths: List[Path] = []

        if self.libraries_dir:
            search_paths.append(self.libraries_dir)

        for path_hint in self.installed_library_paths.values():
            candidate = Path(path_hint).parent
            if candidate not in search_paths and candidate.exists():
                search_paths.append(candidate)

        return search_paths

    def _resolve_install_root(self, library_name: str) -> Optional[Path]:
        """Return the on-disk installation directory for a library if present."""

        path_hint = self.installed_library_paths.get(library_name)
        if path_hint:
            path = Path(path_hint)
            if path.exists():
                return path

        library = self.get_library(library_name)
        if library and library.install_path:
            path = Path(library.install_path)
            if path.exists():
                return path

        candidate = self.libraries_dir / library_name
        if candidate.exists():
            return candidate

        # Fall back to a case-insensitive search to handle unusual naming
        # conventions (e.g. "Adafruit_BusIO" vs "Adafruit BusIO").
        if self.libraries_dir.exists():
            target = library_name.lower()
            for lib_dir in self.libraries_dir.iterdir():
                if lib_dir.is_dir() and lib_dir.name.lower() == target:
                    return lib_dir

        return None

    def _read_library_display_name(self, lib_dir: Path) -> Optional[str]:
        """Attempt to read the library's display name from its metadata."""

        props_file = lib_dir / "library.properties"
        if not props_file.exists():
            return None

        try:
            props = self._parse_library_properties(props_file)
        except Exception as exc:  # pragma: no cover - diagnostic only
            print(f"Error reading {props_file}: {exc}")
            return None

        return props.get("name")

    @staticmethod
    def _normalise_example_identifier(relative_path: Path) -> str:
        """Convert an example path to a stable identifier for the UI."""

        if relative_path.suffix.lower() == ".ino":
            relative_no_ext = relative_path.with_suffix("")
        else:
            relative_no_ext = relative_path

        parent = relative_no_ext.parent
        if (
            relative_path.suffix.lower() == ".ino"
            and parent != Path(".")
            and relative_no_ext.name.lower() == parent.name.lower()
        ):
            return parent.as_posix()

        if parent == Path("."):
            return relative_no_ext.name

        return relative_no_ext.as_posix()

    def _discover_example_identifiers(self, examples_dir: Path) -> Set[str]:
        """Enumerate example identifiers within an ``examples`` directory."""

        example_ids: Set[str] = set()
        for ino_file in examples_dir.rglob("*.ino"):
            try:
                relative = ino_file.relative_to(examples_dir)
            except ValueError:
                continue

            identifier = self._normalise_example_identifier(relative)
            if identifier:
                example_ids.add(identifier)

        return example_ids

    def get_installed_library_examples(self) -> Dict[str, List[str]]:
        """Return a mapping of installed libraries to their example identifiers."""

        libraries_with_examples: Dict[str, Set[str]] = {}
        recorded_names: Set[str] = set()

        for library_name, path_hint in self.installed_library_paths.items():
            install_root = Path(path_hint)
            if not install_root.exists():
                continue

            display_name = self._read_library_display_name(install_root) or library_name
            example_dir = install_root / "examples"
            if not example_dir.is_dir():
                continue

            identifiers = self._discover_example_identifiers(example_dir)
            if identifiers:
                libraries_with_examples.setdefault(display_name, set()).update(identifiers)
                recorded_names.add(display_name)

        if self.libraries_dir.exists():
            for lib_dir in sorted(self.libraries_dir.iterdir(), key=lambda p: p.name.lower()):
                if not lib_dir.is_dir():
                    continue

                display_name = self._read_library_display_name(lib_dir) or lib_dir.name
                if display_name in recorded_names:
                    continue

                example_dir = lib_dir / "examples"
                if not example_dir.is_dir():
                    continue

                identifiers = self._discover_example_identifiers(example_dir)
                if identifiers:
                    libraries_with_examples.setdefault(display_name, set()).update(identifiers)

        sorted_examples: Dict[str, List[str]] = {}
        for display_name, identifiers in libraries_with_examples.items():
            sorted_examples[display_name] = sorted(
                identifiers,
                key=lambda item: [part.lower() for part in item.split("/")],
            )

        return dict(sorted(sorted_examples.items(), key=lambda item: item[0].lower()))

    def _load_library_index(self):
        """Load library index from cache"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Parse libraries
                # Arduino library index uses FLAT structure: each entry is one version
                # We need to group entries by library name and aggregate versions
                libraries_dict = {}  # name -> aggregated library data

                for lib_entry in data.get("libraries", []):
                    try:
                        lib_name = lib_entry.get("name", "")
                        if not lib_name:
                            continue

                        # If this library hasn't been seen, create entry with versions array
                        if lib_name not in libraries_dict:
                            # Create base library entry with versions array
                            libraries_dict[lib_name] = {
                                "name": lib_name,
                                "author": lib_entry.get("author", ""),
                                "maintainer": lib_entry.get("maintainer", ""),
                                "sentence": lib_entry.get("sentence", ""),
                                "paragraph": lib_entry.get("paragraph", ""),
                                "website": lib_entry.get("website", ""),
                                "category": lib_entry.get("category", "Uncategorized"),
                                "architectures": lib_entry.get("architectures", ["*"]),
                                "types": lib_entry.get("types", []),
                                "repository": lib_entry.get("repository", ""),
                                "url": lib_entry.get("website", ""),
                                "license": lib_entry.get("license", ""),
                                "versions": []
                            }

                        # Add this version to the versions array
                        version_entry = {
                            "version": lib_entry.get("version", ""),
                            "url": lib_entry.get("url", ""),
                            "archiveFileName": lib_entry.get("archiveFileName", ""),
                            "size": lib_entry.get("size", 0),
                            "checksum": lib_entry.get("checksum", ""),
                            "dependencies": lib_entry.get("dependencies", []),
                            "architectures": lib_entry.get("architectures", ["*"]),
                        }

                        # Try to parse release date from various possible fields
                        release_date = None
                        for date_field in ["releaseDate", "release_date", "date"]:
                            if date_field in lib_entry:
                                try:
                                    release_date = lib_entry[date_field]
                                    break
                                except:
                                    pass

                        if not release_date:
                            # Use a default date if none provided
                            release_date = "2000-01-01T00:00:00Z"

                        version_entry["releaseDate"] = release_date

                        libraries_dict[lib_name]["versions"].append(version_entry)

                    except Exception as e:
                        print(f"Error parsing library entry: {e}")

                # Convert aggregated dict to Library objects
                libraries = []
                for lib_name, lib_data in libraries_dict.items():
                    try:
                        lib = Library.from_arduino_index(lib_data)

                        # Set installation status
                        if lib.name in self.installed_libraries:
                            lib.installed_version = self.installed_libraries[lib.name]
                            lib.install_path = str(self.libraries_dir / lib.name)

                        libraries.append(lib)
                    except Exception as e:
                        print(f"Error parsing library {lib_name}: {e}")

                self.library_index.libraries = libraries
                self.library_index.last_updated = datetime.fromisoformat(
                    data.get("last_updated", datetime.now().isoformat())
                )
            except Exception as e:
                print(f"Error loading library index: {e}")

    def update_index(self, force: bool = False) -> bool:
        """Update library index from Arduino servers"""
        self.status_message.emit("Updating library index...")

        # Use the enhanced index updater
        success = self.index_updater.update_index(
            index_url=self.LIBRARY_INDEX_URL,
            index_file=self.index_file,
            force=force,
            cache_duration_hours=1
        )

        if success:
            # Reload index
            self._load_library_index()
            self.index_updated.emit()

        return success

    def search_libraries(self, query: str = "", category: Optional[str] = None,
                        architecture: Optional[str] = None,
                        installed_only: bool = False,
                        updates_only: bool = False,
                        official_only: bool = False,
                        has_examples: bool = False,
                        actively_maintained: bool = False) -> List[Library]:
        """Search libraries with advanced filters"""
        results = self.library_index.search(
            query=query,
            category=category,
            architecture=architecture,
            installed_only=installed_only,
            updates_only=updates_only
        )

        # Additional filters
        if official_only:
            results = [lib for lib in results if lib.lib_type == LibraryType.OFFICIAL]

        if has_examples:
            results = [lib for lib in results if lib.examples]

        if actively_maintained:
            results = [lib for lib in results
                      if lib.stats and lib.stats.actively_maintained]

        return results

    def get_library(self, name: str) -> Optional[Library]:
        """Get library by name"""
        return self.library_index.get_library(name)

    def install_library(self, name: str, version: Optional[str] = None,
                       resolve_dependencies: bool = True) -> bool:
        """Install a library"""
        library = self.get_library(name)
        if not library:
            self.status_message.emit(f"Library '{name}' not found")
            return False

        # Determine version to install
        if not version:
            version = library.latest_version

        if not version:
            self.status_message.emit(f"No version found for '{name}'")
            return False

        lib_version = library.get_version(version)
        if not lib_version:
            self.status_message.emit(f"Version '{version}' not found for '{name}'")
            return False

        # Check for existing duplicates before installation
        duplicates = self.detect_duplicate_installations()
        if name in duplicates:
            self.status_message.emit(
                f"Warning: {name} has {len(duplicates[name])} existing installation(s). "
                f"Installing will create another copy."
            )
            # Log the existing installations
            for install in duplicates[name]:
                self.status_message.emit(
                    f"  Existing: v{install['version']} at {install['path']} ({install['source']})"
                )

        self.status_message.emit(f"Installing {name} v{version}...")

        try:
            # Use enhanced download manager with mirror fallback
            self.status_message.emit(f"Downloading {name}...")

            # Get all download URLs (primary + mirrors)
            download_urls = lib_version.get_download_urls() if hasattr(lib_version, 'get_download_urls') else [lib_version.url]

            # Download with enhanced manager
            filename = f"{name}-{version}.zip"
            result = self.download_manager.download(
                urls=download_urls,
                filename=filename,
                expected_checksum=lib_version.checksum if lib_version.checksum else None,
                expected_size=lib_version.size if lib_version.size > 0 else None,
                resume=True
            )

            if not result.success:
                self.status_message.emit(f"Failed to download: {result.error_message}")
                return False

            tmp_path = str(result.file_path)

            # Extract library
            self.status_message.emit(f"Extracting {name}...")
            install_path = self.libraries_dir / name

            # Remove existing installation
            if install_path.exists():
                shutil.rmtree(install_path)

            # Extract zip
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                # Get root folder name
                names = zip_ref.namelist()
                if names:
                    root_folder = names[0].split('/')[0]

                    # Extract to temp location
                    temp_extract = self.cache_dir / "temp_extract"
                    if temp_extract.exists():
                        shutil.rmtree(temp_extract)

                    zip_ref.extractall(temp_extract)

                    # Move to final location
                    shutil.move(str(temp_extract / root_folder), str(install_path))

                    # Clean up
                    if temp_extract.exists():
                        shutil.rmtree(temp_extract)

            # Keep downloaded file in cache for potential reinstall
            # (download_manager handles caching)

            # Update installed libraries
            self.installed_libraries[name] = version
            self._save_installed_libraries()

            # Update library object
            library.installed_version = version
            library.install_path = str(install_path)
            self.installed_library_paths[name] = str(install_path)

            self.status_message.emit(f"Successfully installed {name} v{version}")
            self.library_installed.emit(name, version)

            # Install dependencies
            if resolve_dependencies and lib_version.dependencies:
                for dep in lib_version.dependencies:
                    if not dep.optional:
                        dep_lib = self.get_library(dep.name)
                        if dep_lib and not dep_lib.installed_version:
                            self.install_library(dep.name, dep.version, resolve_dependencies=True)

            return True

        except Exception as e:
            self.status_message.emit(f"Error installing {name}: {str(e)}")
            return False

    def uninstall_library(self, name: str) -> bool:
        """Uninstall a library"""
        if name not in self.installed_libraries:
            self.status_message.emit(f"Library '{name}' is not installed")
            return False

        install_path = self._resolve_install_root(name) or (self.libraries_dir / name)

        try:
            if install_path.exists():
                shutil.rmtree(install_path)

            del self.installed_libraries[name]
            self._save_installed_libraries()
            if name in self.installed_library_paths:
                del self.installed_library_paths[name]

            # Update library object
            library = self.get_library(name)
            if library:
                library.installed_version = None
                library.install_path = None

            self.status_message.emit(f"Successfully uninstalled {name}")
            self.library_uninstalled.emit(name)
            return True

        except Exception as e:
            self.status_message.emit(f"Error uninstalling {name}: {str(e)}")
            return False

    def update_library(self, name: str, version: Optional[str] = None) -> bool:
        """Update a library"""
        library = self.get_library(name)
        if not library:
            return False

        old_version = library.installed_version
        if not old_version:
            self.status_message.emit(f"Library '{name}' is not installed")
            return False

        if not version:
            version = library.latest_version

        if old_version == version:
            self.status_message.emit(f"Library '{name}' is already up to date")
            return False

        # Install new version
        if self.install_library(name, version):
            self.library_updated.emit(name, old_version, version)
            return True

        return False

    def update_all_libraries(self) -> int:
        """Update all libraries with available updates"""
        libraries_to_update = self.library_index.get_libraries_with_updates()
        updated_count = 0

        for library in libraries_to_update:
            if self.update_library(library.name):
                updated_count += 1

        return updated_count

    def get_example_sketch_path(self, library_name: str, example_name: str) -> Optional[Path]:
        """Return the path to an example sketch for an installed library.

        The Arduino ecosystem organises library examples under the library's
        ``examples`` directory.  Each example usually lives in its own folder
        that contains an ``.ino`` file with the same name as the folder.  This
        helper searches the installed library tree for the requested example,
        supporting nested folders such as ``01.Basics/Blink`` and direct ``.ino``
        references like ``Blink/Blink.ino``.

        Args:
            library_name: Name of the installed library.
            example_name: Example identifier (folder path or ``.ino`` name).

        Returns:
            Path to the example sketch if found, otherwise ``None``.
        """

        if not example_name:
            return None

        install_root = self._resolve_install_root(library_name)
        if not install_root:
            return None

        examples_dir = install_root / "examples"
        if not examples_dir.exists():
            return None

        # Normalise the requested example so we can support nested folders and
        # both POSIX and Windows separators.
        normalised_request = example_name.replace("\\", "/").strip("/\\")
        if not normalised_request:
            return None

        request_path = Path(normalised_request)

        # When the caller already specifies a file (e.g. "Blink/Blink.ino"),
        # try to resolve it directly and fall back to a case-insensitive search.
        if request_path.suffix:
            direct_file = examples_dir / request_path
            if direct_file.exists():
                return direct_file

            target_name = request_path.name.lower()
            for candidate in examples_dir.rglob("*.ino"):
                if candidate.name.lower() == target_name:
                    return candidate

            return None

        search_directories: List[Path] = []

        direct_directory = examples_dir / request_path
        if direct_directory.is_dir():
            search_directories.append(direct_directory)
        else:
            target_name = request_path.name.lower()
            for candidate_dir in examples_dir.rglob("*"):
                if candidate_dir.is_dir() and candidate_dir.name.lower() == target_name:
                    search_directories.append(candidate_dir)

        if not search_directories:
            return None

        target_stem = request_path.name.lower()

        for directory in search_directories:
            # Common Arduino convention: the example .ino matches the folder name.
            preferred_files = [
                directory / f"{directory.name}.ino",
                directory / f"{request_path.name}.ino",
            ]

            for preferred in preferred_files:
                if preferred.exists():
                    return preferred

            # Otherwise, look for the best matching .ino within the directory.
            ino_files = sorted(directory.glob("*.ino"))
            if not ino_files:
                ino_files = sorted(directory.rglob("*.ino"))

            if not ino_files:
                continue

            # Prefer files whose stem matches the requested example name.
            for ino_file in ino_files:
                if ino_file.stem.lower() == target_stem:
                    return ino_file

            # Fall back to the first discovered .ino file.
            return ino_files[0]

        return None

    def resolve_dependencies(self, library_name: str, version: Optional[str] = None) -> InstallPlan:
        """Resolve dependencies for a library"""
        plan = InstallPlan()

        library = self.get_library(library_name)
        if not library:
            plan.conflicts.append(f"Library '{library_name}' not found")
            return plan

        if not version:
            version = library.latest_version

        lib_version = library.get_version(version)
        if not lib_version:
            plan.conflicts.append(f"Version '{version}' not found")
            return plan

        # Build dependency tree
        tree = self._build_dependency_tree(library_name, version)

        # Flatten and categorize
        for lib_name, lib_ver in tree.flatten():
            lib = self.get_library(lib_name)
            if not lib:
                plan.conflicts.append(f"Dependency '{lib_name}' not found")
                continue

            if lib.installed_version:
                if lib.installed_version == lib_ver:
                    plan.already_installed.append((lib_name, lib_ver))
                else:
                    plan.to_update.append((lib_name, lib.installed_version, lib_ver))
            else:
                plan.to_install.append((lib_name, lib_ver))

        return plan

    def _build_dependency_tree(self, library_name: str, version: str) -> DependencyTree:
        """Build dependency tree for a library"""
        tree = DependencyTree(library=library_name, version=version)

        library = self.get_library(library_name)
        if not library:
            return tree

        lib_version = library.get_version(version)
        if not lib_version:
            return tree

        tree.installed = library.installed_version is not None

        for dep in lib_version.dependencies:
            dep_tree = self._build_dependency_tree(dep.name, dep.version)
            dep_tree.optional = dep.optional
            tree.dependencies.append(dep_tree)

        return tree

    def detect_conflicts(self, library_name: str) -> List[str]:
        """Detect potential conflicts when installing a library"""
        conflicts: List[str] = []

        library = self.get_library(library_name)
        if not library:
            return conflicts

        # We only care about libraries that are actually installed on disk
        installed_libraries = [
            lib for lib in self.library_index.get_installed_libraries()
            if lib.install_path or (self.libraries_dir / lib.name).exists()
        ]

        if not installed_libraries:
            return conflicts

        header_occurrences: Dict[str, Dict[str, Set[str]]] = {}
        header_display_names: Dict[str, Dict[str, str]] = {}
        namespace_occurrences: Dict[str, Dict[str, Set[str]]] = {}
        namespace_display_names: Dict[str, Dict[str, str]] = {}

        header_extensions = {".h", ".hpp", ".hh", ".hxx"}
        ignored_namespace_dirs = {"src", "examples", "extras", "docs", "tests", "test"}

        def include_roots(path: Path) -> List[Path]:
            roots: List[Path] = []
            src_path = path / "src"
            if src_path.is_dir():
                roots.append(src_path)
            if path.is_dir():
                roots.append(path)
            # Remove duplicates while maintaining order
            unique_roots = []
            seen: Set[Path] = set()
            for root in roots:
                if root not in seen:
                    unique_roots.append(root)
                    seen.add(root)
            return unique_roots

        for lib in installed_libraries:
            lib_path = Path(lib.install_path) if lib.install_path else self.libraries_dir / lib.name
            if not lib_path.exists():
                continue

            lib_header_map = header_display_names.setdefault(lib.name, {})
            lib_namespace_map = namespace_display_names.setdefault(lib.name, {})

            seen_headers: Set[str] = set()
            seen_namespaces: Set[str] = set()

            for root in include_roots(lib_path):
                if not root.exists():
                    continue

                # Collect namespaces (top-level directories within include root)
                try:
                    for child in root.iterdir():
                        if child.is_dir():
                            ns_key = child.name.lower()
                            if ns_key in ignored_namespace_dirs:
                                continue
                            if ns_key in seen_namespaces:
                                continue
                            namespace_occurrences.setdefault(ns_key, {}).setdefault(lib.name, set()).add(str(child))
                            lib_namespace_map.setdefault(ns_key, child.name)
                            seen_namespaces.add(ns_key)
                except PermissionError:
                    continue

                # Collect header files recursively
                for dirpath, _, filenames in os.walk(root):
                    for filename in filenames:
                        if Path(filename).suffix.lower() not in header_extensions:
                            continue
                        header_key = filename.lower()
                        if header_key in seen_headers:
                            continue
                        header_occurrences.setdefault(header_key, {}).setdefault(lib.name, set()).add(
                            str(Path(dirpath) / filename)
                        )
                        lib_header_map.setdefault(header_key, filename)
                        seen_headers.add(header_key)

        target_headers = header_display_names.get(library_name, {})
        for header_key, header_name in target_headers.items():
            libs_with_header = header_occurrences.get(header_key, {})
            if len(libs_with_header) <= 1:
                continue

            others = [
                f"{other_lib} ({', '.join(sorted(paths))})"
                for other_lib, paths in sorted(libs_with_header.items())
                if other_lib != library_name
            ]
            if not others:
                continue

            conflicts.append(
                "Header '{header}' from {target} also exists in: {others}. "
                "Remove or rename duplicates to avoid ambiguous '#include' resolution.".format(
                    header=header_name,
                    target=library_name,
                    others=", ".join(others)
                )
            )

        target_namespaces = namespace_display_names.get(library_name, {})
        for namespace_key, namespace_name in target_namespaces.items():
            libs_with_namespace = namespace_occurrences.get(namespace_key, {})
            if len(libs_with_namespace) <= 1:
                continue

            others = [
                f"{other_lib} ({', '.join(sorted(paths))})"
                for other_lib, paths in sorted(libs_with_namespace.items())
                if other_lib != library_name
            ]
            if not others:
                continue

            conflicts.append(
                "Namespace directory '{namespace}' from {target} also exists in: {others}. "
                "Consider removing duplicates or adjusting include paths to avoid collisions.".format(
                    namespace=namespace_name,
                    target=library_name,
                    others=", ".join(others)
                )
            )

        return conflicts

    def detect_duplicate_installations(self) -> Dict[str, List[Dict[str, str]]]:
        """Detect duplicate library installations.

        Scans the libraries directory for duplicate installations of the same library,
        which can occur when:
        - The same library is installed multiple times in different subdirectories
        - Multiple versions of the same library are installed
        - Manual installations conflict with package manager installations

        Returns:
            Dictionary mapping library name to list of installation details:
            {
                "LibraryName": [
                    {"version": "1.0.0", "path": "/path/to/lib1", "source": "manual"},
                    {"version": "1.0.0", "path": "/path/to/lib2", "source": "managed"}
                ]
            }
        """
        duplicates: Dict[str, List[Dict[str, str]]] = {}

        if not self.libraries_dir.exists():
            return duplicates

        # Track all library installations by normalized name
        library_installations: Dict[str, List[Dict[str, str]]] = {}

        # Scan the main libraries directory
        for lib_dir in self.libraries_dir.iterdir():
            if not lib_dir.is_dir():
                continue

            # Try to read library.properties
            props_file = lib_dir / "library.properties"
            if props_file.exists():
                try:
                    props = self._parse_library_properties(props_file)
                    lib_name = props.get("name", lib_dir.name)
                    lib_version = props.get("version", "unknown")

                    # Normalize library name for comparison (case-insensitive)
                    normalized_name = lib_name.lower()

                    # Determine installation source
                    # A library is "managed" only if it's tracked AND the version matches AND it's in the standard location
                    is_managed = (
                        lib_name in self.installed_libraries and
                        self.installed_libraries[lib_name] == lib_version and
                        lib_dir.name == lib_name  # Standard naming convention
                    )
                    source = "managed" if is_managed else "manual"

                    installation_info = {
                        "name": lib_name,  # Original name
                        "version": lib_version,
                        "path": str(lib_dir),
                        "source": source
                    }

                    if normalized_name not in library_installations:
                        library_installations[normalized_name] = []
                    library_installations[normalized_name].append(installation_info)

                except Exception as e:
                    print(f"Error reading {props_file}: {e}")

        # Find duplicates (libraries with more than one installation)
        for normalized_name, installations in library_installations.items():
            if len(installations) > 1:
                # Use the original name from the first installation
                original_name = installations[0]["name"]
                duplicates[original_name] = installations

        return duplicates

    def find_multiple_versions(self) -> Dict[str, List[str]]:
        """Find libraries with multiple versions installed.

        Returns:
            Dictionary mapping library name to list of installed versions:
            {"LibraryName": ["1.0.0", "1.2.0", "2.0.0"]}
        """
        multiple_versions: Dict[str, List[str]] = {}

        duplicates = self.detect_duplicate_installations()

        for lib_name, installations in duplicates.items():
            # Extract unique versions
            versions = list(set(install["version"] for install in installations))

            # Only include if there are actually multiple different versions
            if len(versions) > 1:
                # Sort versions (attempt semantic versioning)
                try:
                    sorted_versions = sorted(versions, key=lambda v: Version(v) if v != "unknown" else Version("0.0.0"))
                except InvalidVersion:
                    # Fallback to string sorting
                    sorted_versions = sorted(versions)

                multiple_versions[lib_name] = sorted_versions

        return multiple_versions

    def get_duplicate_summary(self) -> str:
        """Get a human-readable summary of duplicate library installations.

        Returns:
            Formatted string describing all duplicate installations found.
        """
        duplicates = self.detect_duplicate_installations()

        if not duplicates:
            return "No duplicate library installations found."

        lines = ["Duplicate library installations detected:", ""]

        for lib_name, installations in sorted(duplicates.items()):
            lines.append(f"Library: {lib_name}")

            # Group by version
            version_groups: Dict[str, List[Dict[str, str]]] = {}
            for install in installations:
                version = install["version"]
                if version not in version_groups:
                    version_groups[version] = []
                version_groups[version].append(install)

            if len(version_groups) > 1:
                lines.append(f"  ⚠ Multiple versions installed:")
                for version, installs in sorted(version_groups.items()):
                    lines.append(f"    Version {version}:")
                    for install in installs:
                        lines.append(f"      - {install['path']} ({install['source']})")
            else:
                # Same version, different locations
                version = list(version_groups.keys())[0]
                lines.append(f"  ⚠ Version {version} installed in multiple locations:")
                for install in installations:
                    lines.append(f"    - {install['path']} ({install['source']})")

            lines.append("")

        # Add recommendations
        lines.append("Recommendations:")
        lines.append("  - Remove duplicate installations to avoid conflicts")
        lines.append("  - Keep only one version of each library")
        lines.append("  - Use the library manager for installations to avoid manual duplicates")

        return "\n".join(lines)

    def resolve_duplicates(self, library_name: str, keep_version: Optional[str] = None,
                          keep_path: Optional[str] = None, dry_run: bool = True) -> Dict[str, any]:
        """Resolve duplicate library installations by removing unwanted copies.

        Args:
            library_name: Name of the library to resolve duplicates for
            keep_version: Version to keep (if None, keeps the latest)
            keep_path: Specific path to keep (takes precedence over keep_version)
            dry_run: If True, only report what would be done without making changes

        Returns:
            Dictionary with resolution results:
            {
                "kept": {"version": "1.0.0", "path": "/path"},
                "removed": [{"version": "0.9.0", "path": "/path1"}, ...],
                "errors": ["error1", "error2"]
            }
        """
        result = {
            "kept": None,
            "removed": [],
            "errors": []
        }

        duplicates = self.detect_duplicate_installations()

        if library_name not in duplicates:
            result["errors"].append(f"No duplicates found for '{library_name}'")
            return result

        installations = duplicates[library_name]

        # Determine which installation to keep
        installation_to_keep = None

        if keep_path:
            # Keep specific path
            for install in installations:
                if install["path"] == keep_path:
                    installation_to_keep = install
                    break

            if not installation_to_keep:
                result["errors"].append(f"Specified path '{keep_path}' not found")
                return result

        elif keep_version:
            # Keep specific version (prefer managed installations)
            candidates = [i for i in installations if i["version"] == keep_version]
            if candidates:
                # Prefer managed over manual
                managed = [c for c in candidates if c["source"] == "managed"]
                installation_to_keep = managed[0] if managed else candidates[0]
            else:
                result["errors"].append(f"Version '{keep_version}' not found")
                return result

        else:
            # Keep the latest version (prefer managed installations)
            try:
                # Sort by version
                sorted_installs = sorted(
                    installations,
                    key=lambda i: (
                        Version(i["version"]) if i["version"] != "unknown" else Version("0.0.0"),
                        i["source"] == "managed"  # Prefer managed
                    ),
                    reverse=True
                )
                installation_to_keep = sorted_installs[0]
            except InvalidVersion:
                # Fallback: prefer managed, then first
                managed = [i for i in installations if i["source"] == "managed"]
                installation_to_keep = managed[0] if managed else installations[0]

        result["kept"] = installation_to_keep

        # Remove other installations
        for install in installations:
            if install["path"] == installation_to_keep["path"]:
                continue

            if dry_run:
                result["removed"].append(install)
            else:
                try:
                    install_path = Path(install["path"])
                    if install_path.exists():
                        shutil.rmtree(install_path)
                        result["removed"].append(install)

                        # Update installed libraries tracking
                        if install["name"] in self.installed_libraries:
                            # Only remove if this was the tracked version
                            if self.installed_libraries[install["name"]] == install["version"]:
                                if installation_to_keep["source"] == "managed":
                                    # Update to kept version
                                    self.installed_libraries[install["name"]] = installation_to_keep["version"]
                                else:
                                    # Remove from tracking
                                    del self.installed_libraries[install["name"]]

                        self.status_message.emit(
                            f"Removed duplicate: {install['name']} v{install['version']} from {install['path']}"
                        )
                except Exception as e:
                    error_msg = f"Failed to remove {install['path']}: {str(e)}"
                    result["errors"].append(error_msg)
                    self.status_message.emit(error_msg)

        if not dry_run and not result["errors"]:
            self._save_installed_libraries()

        return result

    def get_library_size(self, name: str, version: Optional[str] = None) -> int:
        """Get library size in bytes"""
        library = self.get_library(name)
        if not library:
            return 0

        if not version:
            version = library.latest_version

        lib_version = library.get_version(version)
        if lib_version:
            return lib_version.size

        return 0

    def get_unused_libraries(self, days: int = 180) -> List[Library]:
        """Get libraries that haven't been used in specified days"""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        unused = []

        for library in self.library_index.libraries:
            if library.installed_version:
                if library.last_used:
                    if library.last_used.timestamp() < cutoff:
                        unused.append(library)
                else:
                    # Never used, add to list
                    unused.append(library)

        return unused

    def export_installed_libraries(self, path: Path):
        """Export installed libraries to a file"""
        data = {
            "libraries": [
                {
                    "name": name,
                    "version": version
                }
                for name, version in self.installed_libraries.items()
            ],
            "exported_at": datetime.now().isoformat()
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def import_libraries(self, path: Path) -> int:
        """Import libraries from exported file"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        installed_count = 0
        for lib_data in data.get("libraries", []):
            name = lib_data.get("name")
            version = lib_data.get("version")

            if name and version:
                if self.install_library(name, version):
                    installed_count += 1

        return installed_count

    def install_library_from_zip(self, zip_path: Path) -> bool:
        """Install a library from a ZIP file

        Args:
            zip_path: Path to the ZIP file containing the library

        Returns:
            True if installation was successful, False otherwise
        """
        self.status_message.emit(f"Installing library from ZIP: {zip_path.name}...")

        try:
            # Validate ZIP file exists
            if not zip_path.exists():
                self.status_message.emit(f"Error: ZIP file not found: {zip_path}")
                return False

            # Create temporary extraction directory
            temp_extract = self.cache_dir / "temp_zip_extract"
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
            temp_extract.mkdir(parents=True, exist_ok=True)

            # Extract ZIP file
            self.status_message.emit("Extracting ZIP file...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get all file names
                names = zip_ref.namelist()
                if not names:
                    self.status_message.emit("Error: ZIP file is empty")
                    return False

                # Extract all files
                zip_ref.extractall(temp_extract)

            # Find the library root directory
            # Arduino libraries can be structured as:
            # 1. library.zip contains library_folder/library.properties
            # 2. library.zip contains library.properties directly
            library_root = None
            library_name = None
            library_version = None

            # Check if library.properties is in the root
            root_props = temp_extract / "library.properties"
            if root_props.exists():
                library_root = temp_extract
            else:
                # Look for library.properties in subdirectories
                for item in temp_extract.iterdir():
                    if item.is_dir():
                        props_file = item / "library.properties"
                        if props_file.exists():
                            library_root = item
                            break

            if not library_root:
                self.status_message.emit("Error: No library.properties file found in ZIP")
                shutil.rmtree(temp_extract)
                return False

            # Parse library.properties
            props_file = library_root / "library.properties"
            try:
                props = self._parse_library_properties(props_file)
                library_name = props.get("name")
                library_version = props.get("version", "unknown")

                if not library_name:
                    self.status_message.emit("Error: library.properties missing 'name' field")
                    shutil.rmtree(temp_extract)
                    return False

            except Exception as e:
                self.status_message.emit(f"Error parsing library.properties: {e}")
                shutil.rmtree(temp_extract)
                return False

            # Check if library already exists
            install_path = self.libraries_dir / library_name
            if install_path.exists():
                # Get existing version
                existing_props_file = install_path / "library.properties"
                if existing_props_file.exists():
                    try:
                        existing_props = self._parse_library_properties(existing_props_file)
                        existing_version = existing_props.get("version", "unknown")
                        self.status_message.emit(
                            f"Library '{library_name}' v{existing_version} already installed. "
                            f"Replacing with v{library_version}..."
                        )
                    except:
                        self.status_message.emit(
                            f"Library '{library_name}' already installed. Replacing..."
                        )

                # Remove existing installation
                shutil.rmtree(install_path)

            # Copy library to libraries directory
            self.status_message.emit(f"Installing {library_name} v{library_version}...")
            shutil.copytree(library_root, install_path)

            # Update installed libraries tracking
            self.installed_libraries[library_name] = library_version
            self._save_installed_libraries()

            # Update library object in index if it exists
            library = self.get_library(library_name)
            if library:
                library.installed_version = library_version
                library.install_path = str(install_path)

            # Clean up temporary extraction
            shutil.rmtree(temp_extract)

            self.status_message.emit(f"Successfully installed {library_name} v{library_version} from ZIP")
            self.library_installed.emit(library_name, library_version)

            return True

        except zipfile.BadZipFile:
            self.status_message.emit(f"Error: Invalid ZIP file: {zip_path}")
            return False
        except Exception as e:
            self.status_message.emit(f"Error installing library from ZIP: {str(e)}")
            if temp_extract and temp_extract.exists():
                try:
                    shutil.rmtree(temp_extract)
                except:
                    pass
            return False
