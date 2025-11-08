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
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import requests
from PySide6.QtCore import QObject, Signal

from ..models import (
    Library, LibraryIndex, LibraryVersion, LibraryDependency,
    LibraryType, LibraryStatus, ProjectConfig, InstallPlan, DependencyTree
)


class LibraryManager(QObject):
    """Manages Arduino libraries"""

    # Signals
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
        super().__init__(parent)

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

    def _scan_installed_libraries(self):
        """Scan libraries directory for installed libraries"""
        if not self.libraries_dir.exists():
            return

        for lib_dir in self.libraries_dir.iterdir():
            if lib_dir.is_dir():
                # Try to read library.properties
                props_file = lib_dir / "library.properties"
                if props_file.exists():
                    try:
                        props = self._parse_library_properties(props_file)
                        name = props.get("name", lib_dir.name)
                        version = props.get("version", "unknown")
                        self.installed_libraries[name] = version
                    except Exception as e:
                        print(f"Error reading {props_file}: {e}")

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

    def _load_library_index(self):
        """Load library index from cache"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Parse libraries
                libraries = []
                for lib_data in data.get("libraries", []):
                    try:
                        lib = Library.from_arduino_index(lib_data)

                        # Set installation status
                        if lib.name in self.installed_libraries:
                            lib.installed_version = self.installed_libraries[lib.name]
                            lib.install_path = str(self.libraries_dir / lib.name)

                        libraries.append(lib)
                    except Exception as e:
                        print(f"Error parsing library: {e}")

                self.library_index.libraries = libraries
                self.library_index.last_updated = datetime.fromisoformat(
                    data.get("last_updated", datetime.now().isoformat())
                )
            except Exception as e:
                print(f"Error loading library index: {e}")

    def update_index(self, force: bool = False) -> bool:
        """Update library index from Arduino servers"""
        self.status_message.emit("Updating library index...")

        # Check if update is needed
        if not force and self.index_file.exists():
            age = datetime.now() - datetime.fromtimestamp(self.index_file.stat().st_mtime)
            if age.total_seconds() < 3600:  # Less than 1 hour old
                self.status_message.emit("Library index is up to date")
                return True

        try:
            # Try main URL first
            response = requests.get(self.LIBRARY_INDEX_URL, timeout=30)

            if response.status_code != 200:
                # Try mirror
                response = requests.get(self.LIBRARY_INDEX_MIRROR, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # Save to cache
                data["last_updated"] = datetime.now().isoformat()
                with open(self.index_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f)

                # Reload index
                self._load_library_index()

                self.status_message.emit("Library index updated successfully")
                self.index_updated.emit()
                return True
            else:
                self.status_message.emit(f"Failed to update index: HTTP {response.status_code}")
                return False

        except Exception as e:
            self.status_message.emit(f"Error updating index: {str(e)}")
            return False

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

        self.status_message.emit(f"Installing {name} v{version}...")

        try:
            # Download library
            self.status_message.emit(f"Downloading {name}...")
            response = requests.get(lib_version.url, timeout=60, stream=True)

            if response.status_code != 200:
                self.status_message.emit(f"Failed to download: HTTP {response.status_code}")
                return False

            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        self.progress_changed.emit(progress)

                tmp_path = tmp_file.name

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

            # Clean up temp file
            os.unlink(tmp_path)

            # Update installed libraries
            self.installed_libraries[name] = version
            self._save_installed_libraries()

            # Update library object
            library.installed_version = version
            library.install_path = str(install_path)

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

        install_path = self.libraries_dir / name

        try:
            if install_path.exists():
                shutil.rmtree(install_path)

            del self.installed_libraries[name]
            self._save_installed_libraries()

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
        conflicts = []

        library = self.get_library(library_name)
        if not library:
            return conflicts

        # Check for libraries with same headers
        # This would require scanning library headers
        # For now, return empty list
        # TODO: Implement header conflict detection

        return conflicts

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
