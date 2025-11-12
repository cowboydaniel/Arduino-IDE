"""
Board Manager Service

Handles board package search, installation, and management.
"""

import os
import json
import shutil
import zipfile
import tarfile
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests

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
    Board, BoardPackage, BoardIndex, BoardPackageVersion,
    BoardPackageURL, BoardStatus, BoardCategory, BoardSpecs
)


class BoardManager(QObject):
    """Manages Arduino board packages"""

    # Signals (only functional with Qt)
    if HAS_QT:
        package_installed = Signal(str, str)  # (name, version)
        package_uninstalled = Signal(str)  # (name)
        package_updated = Signal(str, str, str)  # (name, old_version, new_version)
        index_updated = Signal()
        progress_changed = Signal(int)  # Progress percentage
        status_message = Signal(str)  # Status message

    # Arduino Board Package Index URL
    PACKAGE_INDEX_URL = "https://downloads.arduino.cc/packages/package_index.json"

    def __init__(self, parent=None, cli_runner=None):
        if HAS_QT:
            super().__init__(parent)
        else:
            super().__init__()

        # CLI runner for arduino-cli integration
        self.cli_runner = cli_runner

        # Initialize paths
        self.base_dir = Path.home() / ".arduino-ide-modern"
        self.packages_dir = self.base_dir / "packages"
        self.cache_dir = self.base_dir / "cache"
        self.index_file = self.cache_dir / "package_index.json"
        self.installed_file = self.cache_dir / "installed_packages.json"
        self.urls_file = self.cache_dir / "package_urls.json"

        # Create directories
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Board index
        self.board_index = BoardIndex()
        self.board_index.package_urls = BoardIndex.POPULAR_URLS.copy()
        self.installed_packages: Dict[str, str] = {}  # name -> version

        # Load data
        self._load_package_urls()
        self._load_installed_packages()
        self._load_board_index()

    def _emit_signal(self, signal_name: str, *args):
        """Safely emit a signal if it exists and Qt is available"""
        if HAS_QT and hasattr(self, signal_name):
            signal = getattr(self, signal_name)
            if signal is not None:
                signal.emit(*args)

    def _load_package_urls(self):
        """Load custom package URLs"""
        if self.urls_file.exists():
            try:
                with open(self.urls_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Update enabled status and add custom URLs
                url_map = {url.url: url for url in self.board_index.package_urls}

                for url_data in data:
                    url_str = url_data.get("url", "")
                    if url_str in url_map:
                        url_map[url_str].enabled = url_data.get("enabled", False)
                    else:
                        # Custom URL
                        self.board_index.package_urls.append(
                            BoardPackageURL(
                                name=url_data.get("name", "Custom"),
                                url=url_str,
                                enabled=url_data.get("enabled", False)
                            )
                        )
            except Exception as e:
                print(f"Error loading package URLs: {e}")

    def _save_package_urls(self):
        """Save package URLs"""
        data = [
            {
                "name": url.name,
                "url": url.url,
                "enabled": url.enabled
            }
            for url in self.board_index.package_urls
        ]

        with open(self.urls_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _load_installed_packages(self):
        """Load installed packages from file"""
        if self.installed_file.exists():
            try:
                with open(self.installed_file, 'r', encoding='utf-8') as f:
                    self.installed_packages = json.load(f)
            except Exception as e:
                print(f"Error loading installed packages: {e}")
                self.installed_packages = {}

    def _save_installed_packages(self):
        """Save installed packages to file"""
        with open(self.installed_file, 'w', encoding='utf-8') as f:
            json.dump(self.installed_packages, f, indent=2)

    def _get_installed_versions_for_package(self, package_name: str) -> List[str]:
        """Return versions recorded for a given package name.

        The installed packages file stores entries either as raw package names
        (e.g. ``arduino``) or platform identifiers (e.g. ``arduino:avr``).
        This helper normalizes lookups so callers can reason in terms of
        package names without worrying about how the key was recorded.
        """

        versions = []
        for installed_name, version in self.installed_packages.items():
            if installed_name == package_name or \
               installed_name.startswith(f"{package_name}:"):
                versions.append(version)
        return versions

    def _load_board_index(self):
        """Load board index from cache"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Parse packages
                packages = []
                for pkg_data in data.get("packages", []):
                    try:
                        pkg = BoardPackage.from_arduino_index(pkg_data)

                        # Set installation status
                        installed_versions = self._get_installed_versions_for_package(pkg.name)
                        if installed_versions:
                            pkg.installed_version = installed_versions[-1]

                        packages.append(pkg)
                    except Exception as e:
                        print(f"Error parsing package: {e}")

                self.board_index.packages = packages
                self.board_index.last_updated = datetime.fromisoformat(
                    data.get("last_updated", datetime.now().isoformat())
                )
            except Exception as e:
                print(f"Error loading board index: {e}")

    def update_index(self, force: bool = False) -> bool:
        """Update board package index from Arduino servers"""
        self._emit_signal('status_message',"Updating board package index...")

        # Check if update is needed
        if not force and self.index_file.exists():
            age = datetime.now() - datetime.fromtimestamp(self.index_file.stat().st_mtime)
            if age.total_seconds() < 3600:  # Less than 1 hour old
                self._emit_signal('status_message',"Board index is up to date")
                return True

        try:
            # Fetch main index
            all_packages = []

            # Arduino official index
            response = requests.get(self.PACKAGE_INDEX_URL, timeout=30)
            if response.status_code == 200:
                data = response.json()
                all_packages.extend(data.get("packages", []))

            # Fetch enabled third-party indexes
            for package_url in self.board_index.package_urls:
                if package_url.enabled:
                    try:
                        response = requests.get(package_url.url, timeout=30)
                        if response.status_code == 200:
                            data = response.json()
                            all_packages.extend(data.get("packages", []))
                    except Exception as e:
                        print(f"Error fetching {package_url.name}: {e}")

            # Save to cache
            cache_data = {
                "packages": all_packages,
                "last_updated": datetime.now().isoformat()
            }

            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)

            # Reload index
            self._load_board_index()

            self._emit_signal('status_message',"Board package index updated successfully")
            self._emit_signal('index_updated')
            return True

        except Exception as e:
            self._emit_signal('status_message',f"Error updating index: {str(e)}")
            return False

    def get_package(self, name: str) -> Optional[BoardPackage]:
        """Get package by name"""
        return self.board_index.get_package(name)

    def get_board(self, fqbn: str) -> Optional[Board]:
        """Get board by FQBN"""
        board = self.board_index.get_board(fqbn)
        if board:
            return board

        # Fallback to on-demand discovery. This keeps the method resilient if
        # the caller has not yet triggered a full board refresh (for example
        # when compiling immediately after installing a core).
        self._discover_boards_from_installed_platforms()
        return self.board_index.get_board(fqbn)

    def search_boards(self, query: str = "", features: Optional[List[str]] = None,
                     architecture: Optional[str] = None,
                     installed_only: bool = False) -> List[Board]:
        """Search boards with filters"""
        return self.board_index.search_boards(
            query=query,
            features=features,
            architecture=architecture,
            installed_only=installed_only
        )

    def search_packages(self, query: str = "", category: Optional[BoardCategory] = None,
                       installed_only: bool = False,
                       updates_only: bool = False) -> List[BoardPackage]:
        """Search board packages"""
        results = []
        query_lower = query.lower()

        for pkg in self.board_index.packages:
            # Filter by query
            if query and query_lower not in pkg.name.lower() and \
               query_lower not in pkg.maintainer.lower() and \
               query_lower not in pkg.description.lower():
                continue

            # Filter by category
            if category and pkg.category != category:
                continue

            # Filter installed only
            if installed_only and not pkg.installed_version:
                continue

            # Filter updates only
            if updates_only and not pkg.has_update():
                continue

            results.append(pkg)

        return results

    def install_package(self, name: str, version: Optional[str] = None) -> bool:
        """Install a board package/platform.

        Args:
            name: Can be either package name (e.g., "arduino") or platform ID (e.g., "arduino:avr")
            version: Specific version to install, or None for latest

        Returns:
            True if installation succeeded, False otherwise
        """
        # Parse platform ID if provided (format: "package:architecture")
        if ":" in name:
            parts = name.split(":")
            package_name = parts[0]
            architecture = parts[1] if len(parts) > 1 else None
        else:
            package_name = name
            architecture = None

        package = self.get_package(package_name)
        if not package:
            self._emit_signal('status_message',f"Package '{package_name}' not found")
            return False

        # Find the specific platform version to install
        pkg_version = None
        platform_arch = architecture

        if architecture:
            # Look for specific architecture in package versions
            for v in package.versions:
                # Check if this version has the requested architecture
                # We'll need to extract architecture info from version data
                if not version or v.version == version:
                    pkg_version = v
                    break
        else:
            # No architecture specified, use latest version
            if not version:
                version = package.latest_version

            if not version:
                self._emit_signal('status_message',f"No version found for '{package_name}'")
                return False

            pkg_version = package.get_version(version)

        if not pkg_version:
            self._emit_signal('status_message',f"Version '{version}' not found for '{package_name}'")
            return False

        self._emit_signal('status_message',f"Installing {name} v{pkg_version.version}...")

        try:
            # Download package
            self._emit_signal('status_message',f"Downloading {name}...")
            response = requests.get(pkg_version.url, timeout=120, stream=True)

            if response.status_code != 200:
                self._emit_signal('status_message',f"Failed to download: HTTP {response.status_code}")
                return False

            # Save to temp file
            suffix = '.tar.gz' if pkg_version.url.endswith('.tar.gz') else '.zip'
            if pkg_version.url.endswith('.tar.bz2'):
                suffix = '.tar.bz2'

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        self._emit_signal('progress_changed',progress)

                tmp_path = tmp_file.name

            # Extract package
            self._emit_signal('status_message',f"Extracting {name}...")

            # Use architecture from version data if not specified in name
            if not platform_arch and pkg_version.architecture:
                platform_arch = pkg_version.architecture
            elif not platform_arch:
                platform_arch = "unknown"

            install_path = self.packages_dir / package_name / platform_arch / pkg_version.version

            # Remove existing installation
            if install_path.exists():
                shutil.rmtree(install_path)

            install_path.mkdir(parents=True, exist_ok=True)

            # Extract archive
            if suffix == '.tar.gz':
                with tarfile.open(tmp_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(install_path)
            elif suffix == '.tar.bz2':
                with tarfile.open(tmp_path, 'r:bz2') as tar_ref:
                    tar_ref.extractall(install_path)
            else:
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    zip_ref.extractall(install_path)

            # Clean up temp file
            os.unlink(tmp_path)

            # Update installed packages (use full platform ID)
            platform_id = f"{package_name}:{platform_arch}" if platform_arch != "unknown" else package_name
            self.installed_packages[platform_id] = pkg_version.version
            self._save_installed_packages()

            # Update package object
            package.installed_version = pkg_version.version

            self._emit_signal('status_message',f"Successfully installed {name} v{pkg_version.version}")
            self._emit_signal('package_installed',name, pkg_version.version)
            return True

        except Exception as e:
            self._emit_signal('status_message',f"Error installing {name}: {str(e)}")
            return False

    def uninstall_package(self, name: str) -> bool:
        """Uninstall a board package/platform.

        Args:
            name: Can be either package name (e.g., "arduino") or platform ID (e.g., "arduino:avr")

        Returns:
            True if uninstallation succeeded, False otherwise
        """
        # Find the actual installed key - it might be stored with or without architecture
        installed_key = None
        if name in self.installed_packages:
            installed_key = name
        else:
            # Check if any installed package matches (handle partial names)
            for key in self.installed_packages.keys():
                if key == name or key.startswith(f"{name}:"):
                    installed_key = key
                    break

        if not installed_key:
            self._emit_signal('status_message',f"Package '{name}' is not installed")
            return False

        # Parse platform ID from the installed key
        if ":" in installed_key:
            parts = installed_key.split(":")
            package_name = parts[0]
            architecture = parts[1] if len(parts) > 1 else None
        else:
            package_name = installed_key
            architecture = None

        version = self.installed_packages[installed_key]

        try:
            # Build install path based on structure
            if architecture:
                install_path = self.packages_dir / package_name / architecture / version
            else:
                install_path = self.packages_dir / package_name / version

            if install_path.exists():
                shutil.rmtree(install_path)

            # Remove empty parent directories
            if architecture:
                arch_dir = self.packages_dir / package_name / architecture
                if arch_dir.exists() and not list(arch_dir.iterdir()):
                    arch_dir.rmdir()

            pkg_dir = self.packages_dir / package_name
            if pkg_dir.exists() and not list(pkg_dir.iterdir()):
                pkg_dir.rmdir()

            del self.installed_packages[installed_key]
            self._save_installed_packages()

            # Update package object
            package = self.get_package(package_name)
            if package:
                package.installed_version = None

            self._emit_signal('status_message',f"Successfully uninstalled {installed_key}")
            self._emit_signal('package_uninstalled',installed_key)
            return True

        except Exception as e:
            self._emit_signal('status_message',f"Error uninstalling {name}: {str(e)}")
            return False

    def update_package(self, name: str, version: Optional[str] = None) -> bool:
        """Update a board package"""
        package = self.get_package(name)
        if not package:
            return False

        old_version = package.installed_version
        if not old_version:
            self._emit_signal('status_message',f"Package '{name}' is not installed")
            return False

        if not version:
            version = package.latest_version

        if old_version == version:
            self._emit_signal('status_message',f"Package '{name}' is already up to date")
            return False

        # Install new version
        if self.install_package(name, version):
            self._emit_signal('package_updated',name, old_version, version)
            return True

        return False

    def add_package_url(self, name: str, url: str) -> bool:
        """Add a custom package URL"""
        # Check if URL already exists
        for pkg_url in self.board_index.package_urls:
            if pkg_url.url == url:
                self._emit_signal('status_message',"URL already exists")
                return False

        # Add new URL
        new_url = BoardPackageURL(name=name, url=url, enabled=True)
        self.board_index.package_urls.append(new_url)
        self._save_package_urls()

        self._emit_signal('status_message',f"Added package URL: {name}")
        return True

    def remove_package_url(self, url: str) -> bool:
        """Remove a package URL"""
        for pkg_url in self.board_index.package_urls:
            if pkg_url.url == url:
                self.board_index.package_urls.remove(pkg_url)
                self._save_package_urls()
                self._emit_signal('status_message',"Package URL removed")
                return True

        return False

    def toggle_package_url(self, url: str) -> bool:
        """Toggle package URL enabled status"""
        for pkg_url in self.board_index.package_urls:
            if pkg_url.url == url:
                pkg_url.enabled = not pkg_url.enabled
                self._save_package_urls()
                return pkg_url.enabled

        return False

    def get_board_comparison(self, fqbns: List[str]) -> Dict:
        """Get comparison data for multiple boards"""
        boards = []
        for fqbn in fqbns:
            board = self.get_board(fqbn)
            if board:
                boards.append(board)

        if not boards:
            return {}

        # Build comparison table
        comparison = {
            "boards": [board.name for board in boards],
            "CPU": [board.specs.cpu for board in boards],
            "Clock": [board.specs.clock for board in boards],
            "Flash": [board.specs.flash for board in boards],
            "RAM": [board.specs.ram for board in boards],
            "Price": [board.price for board in boards],
            "WiFi": ["✅" if board.specs.wifi else "❌" for board in boards],
            "Bluetooth": ["✅" if board.specs.bluetooth else "❌" for board in boards],
            "USB": ["✅" if board.specs.usb else "❌" for board in boards],
            "ADC": [board.specs.adc_resolution for board in boards],
            "DAC": ["✅" if board.specs.dac else "❌" for board in boards],
            "Touch": [str(board.specs.touch_pins) if board.specs.touch_pins > 0 else "❌" for board in boards],
            "RTC": ["✅" if board.specs.rtc else "❌" for board in boards],
            "Power": [board.specs.power_typical for board in boards],
            "Sleep Mode": ["✅" if board.specs.sleep_mode else "❌" for board in boards],
            "Best For": [", ".join(board.best_for) if board.best_for else "N/A" for board in boards],
        }

        return comparison

    def get_all_boards(self) -> List[Board]:
        """Get all boards from installed platforms by parsing boards.txt files"""
        return self._discover_boards_from_installed_platforms()

    def _update_board_index_with_discovered_boards(
        self,
        package_boards_map: Dict[str, List[Board]],
        package_versions: Dict[str, set[str]]
    ) -> None:
        """Sync discovered boards into the cached package index."""

        # Reset previously cached board lists so stale entries do not linger if
        # a platform is removed.
        package_lookup: Dict[str, BoardPackage] = {}
        for pkg in self.board_index.packages:
            pkg.boards = []
            package_lookup[pkg.name] = pkg

        for package_name, boards in package_boards_map.items():
            pkg = package_lookup.get(package_name)

            if not pkg:
                # Create a lightweight package entry so the caller can still
                # resolve boards even if the platform did not originate from
                # the Arduino package index (custom platforms, for instance).
                pkg = BoardPackage(
                    name=package_name,
                    maintainer=package_name,
                    category=BoardCategory.COMMUNITY,
                    url="",
                )
                self.board_index.packages.append(pkg)
                package_lookup[package_name] = pkg

            pkg.boards = boards

            # Attempt to set the installed version information so the IDE can
            # indicate the platform's status even when the package index did
            # not provide it (common for custom platforms installed manually).
            if not pkg.installed_version:
                installed_versions = self._get_installed_versions_for_package(package_name)
                if installed_versions:
                    pkg.installed_version = installed_versions[-1]
            if not pkg.installed_version and package_versions.get(package_name):
                # Fall back to the version names derived from the directory
                # structure if we could not determine it from the cache file.
                pkg.installed_version = sorted(package_versions[package_name])[-1]

    def get_architectures(self) -> List[str]:
        """Get all unique architectures"""
        architectures = set()
        for board in self.get_all_boards():
            architectures.add(board.architecture)
        return sorted(list(architectures))

    def _discover_boards_from_installed_platforms(self) -> List[Board]:
        """Discover boards from installed platforms by parsing boards.txt files.

        This implements the Arduino boards platform framework by scanning
        installed platform packages and parsing their boards.txt files.

        Returns:
            List of Board objects discovered from installed platforms
        """
        from .boards_txt_parser import BoardsTxtParser

        boards: List[Board] = []
        package_boards_map: Dict[str, List[Board]] = defaultdict(list)
        package_versions: Dict[str, set[str]] = defaultdict(set)

        # Scan packages directory for installed platforms
        # Structure: packages/package_name/architecture/version/boards.txt
        if not self.packages_dir.exists():
            self._update_board_index_with_discovered_boards(package_boards_map, package_versions)
            return boards

        try:
            # Iterate through package directories (e.g., arduino, esp32)
            for package_dir in self.packages_dir.iterdir():
                if not package_dir.is_dir():
                    continue

                package_name = package_dir.name

                # Iterate through architecture directories (e.g., avr, esp32)
                for arch_dir in package_dir.iterdir():
                    if not arch_dir.is_dir():
                        continue

                    architecture = arch_dir.name

                    # Iterate through version directories (e.g., 1.8.6)
                    for version_dir in arch_dir.iterdir():
                        if not version_dir.is_dir():
                            continue

                        # Look for boards.txt in this platform. Some packages keep the
                        # file directly in the version directory while others nest the
                        # extracted archive in an additional folder (e.g. avr-1.8.6).
                        boards_txt_candidates = []

                        boards_txt = version_dir / "boards.txt"
                        if boards_txt.exists():
                            boards_txt_candidates.append(boards_txt)
                        else:
                            # Handle nested archive directory (common in Arduino
                            # platform packages).
                            for nested_dir in version_dir.iterdir():
                                if not nested_dir.is_dir():
                                    continue

                                nested_boards_txt = nested_dir / "boards.txt"
                                if nested_boards_txt.exists():
                                    boards_txt_candidates.append(nested_boards_txt)

                        for boards_txt_path in boards_txt_candidates:
                            platform_root = boards_txt_path.parent
                            platform_boards = BoardsTxtParser.parse_boards_txt(
                                boards_txt_path,
                                package_name,
                                architecture,
                                platform_root=platform_root,
                            )
                            if platform_boards:
                                boards.extend(platform_boards)
                                package_boards_map[package_name].extend(platform_boards)
                                package_versions[package_name].add(version_dir.name)

        except Exception as e:
            print(f"Error discovering boards from installed platforms: {e}")
        finally:
            self._update_board_index_with_discovered_boards(package_boards_map, package_versions)

        return boards

    # ------------------------------------------------------------------
    # Arduino CLI Integration (Generalized Board Support)
    # ------------------------------------------------------------------
    def get_boards_from_cli(self) -> List[Board]:
        """Get all boards from arduino-cli (installed platforms).

        This method uses arduino-cli to dynamically discover boards from all
        installed platforms, providing support for the entire Arduino ecosystem
        without hardcoding.

        Returns:
            List of Board objects from installed platforms

        Raises:
            RuntimeError: If cli_runner is not configured or command fails
        """
        if not self.cli_runner:
            raise RuntimeError("CLI runner not configured. Cannot fetch boards from arduino-cli.")

        try:
            boards_data = self.cli_runner.list_boards()
            boards = []

            for board_data in boards_data:
                # Parse FQBN to extract architecture and package
                fqbn = board_data.get("fqbn", "")
                name = board_data.get("name", "Unknown Board")
                platform = board_data.get("platform", {})

                # Extract package and architecture from FQBN
                # FQBN format: package:architecture:board_id
                fqbn_parts = fqbn.split(":")
                if len(fqbn_parts) >= 3:
                    package_name = fqbn_parts[0]
                    architecture = fqbn_parts[1]
                else:
                    package_name = platform.get("id", "").split(":")[0] if platform else "unknown"
                    architecture = "unknown"

                # Create Board object with minimal specs
                # Full specs would require parsing boards.txt, which arduino-cli already does
                board = Board(
                    name=name,
                    fqbn=fqbn,
                    architecture=architecture,
                    package_name=package_name,
                    specs=BoardSpecs(
                        cpu="Unknown",
                        clock="Unknown",
                        flash="Unknown",
                        ram="Unknown"
                    ),
                    description=f"Board from {platform.get('name', 'platform')}" if platform else ""
                )

                boards.append(board)

            return boards

        except Exception as e:
            raise RuntimeError(f"Failed to get boards from arduino-cli: {e}")

    def get_platforms_from_cli(self) -> List[Dict[str, Any]]:
        """Get installed platforms from arduino-cli.

        Returns:
            List of platform dictionaries

        Raises:
            RuntimeError: If cli_runner is not configured or command fails
        """
        if not self.cli_runner:
            raise RuntimeError("CLI runner not configured. Cannot fetch platforms from arduino-cli.")

        try:
            return self.cli_runner.list_platforms()
        except Exception as e:
            raise RuntimeError(f"Failed to get platforms from arduino-cli: {e}")

    def search_platforms_via_cli(self, query: str = "") -> List[Dict[str, Any]]:
        """Search for available platforms using arduino-cli.

        Args:
            query: Optional search query

        Returns:
            List of platform dictionaries

        Raises:
            RuntimeError: If cli_runner is not configured or command fails
        """
        if not self.cli_runner:
            raise RuntimeError("CLI runner not configured. Cannot search platforms via arduino-cli.")

        try:
            return self.cli_runner.search_platforms(query)
        except Exception as e:
            raise RuntimeError(f"Failed to search platforms via arduino-cli: {e}")

    def install_platform_via_cli(self, platform_id: str) -> bool:
        """Install a platform using arduino-cli.

        Args:
            platform_id: Platform identifier (e.g., "arduino:avr", "esp32:esp32")

        Returns:
            True if installation succeeded, False otherwise
        """
        if not self.cli_runner:
            self._emit_signal('status_message',"CLI runner not configured")
            return False

        self._emit_signal('status_message',f"Installing platform {platform_id}...")

        try:
            success = self.cli_runner.install_platform(platform_id)
            if success:
                self._emit_signal('status_message',f"Platform {platform_id} installed successfully")
                self._emit_signal('package_installed',platform_id, "latest")
            else:
                self._emit_signal('status_message',f"Failed to install platform {platform_id}")
            return success
        except Exception as e:
            self._emit_signal('status_message',f"Error installing platform: {e}")
            return False

    def uninstall_platform_via_cli(self, platform_id: str) -> bool:
        """Uninstall a platform using arduino-cli.

        Args:
            platform_id: Platform identifier (e.g., "arduino:avr", "esp32:esp32")

        Returns:
            True if uninstallation succeeded, False otherwise
        """
        if not self.cli_runner:
            self._emit_signal('status_message',"CLI runner not configured")
            return False

        self._emit_signal('status_message',f"Uninstalling platform {platform_id}...")

        try:
            success = self.cli_runner.uninstall_platform(platform_id)
            if success:
                self._emit_signal('status_message',f"Platform {platform_id} uninstalled successfully")
                self._emit_signal('package_uninstalled',platform_id)
            else:
                self._emit_signal('status_message',f"Failed to uninstall platform {platform_id}")
            return success
        except Exception as e:
            self._emit_signal('status_message',f"Error uninstalling platform: {e}")
            return False

    def update_cli_index(self) -> bool:
        """Update the arduino-cli platform index.

        Returns:
            True if update succeeded, False otherwise
        """
        if not self.cli_runner:
            self._emit_signal('status_message',"CLI runner not configured")
            return False

        self._emit_signal('status_message',"Updating arduino-cli platform index...")

        try:
            success = self.cli_runner.update_platform_index()
            if success:
                self._emit_signal('status_message',"Platform index updated successfully")
                self._emit_signal('index_updated')
            else:
                self._emit_signal('status_message',"Failed to update platform index")
            return success
        except Exception as e:
            self._emit_signal('status_message',f"Error updating platform index: {e}")
            return False

    def get_board_details_from_cli(self, fqbn: str) -> Optional[Dict[str, Any]]:
        """Get detailed board information from arduino-cli.

        Args:
            fqbn: Fully Qualified Board Name

        Returns:
            Dictionary with board details, or None if not found

        Raises:
            RuntimeError: If cli_runner is not configured
        """
        if not self.cli_runner:
            raise RuntimeError("CLI runner not configured. Cannot get board details from arduino-cli.")

        try:
            return self.cli_runner.get_board_details(fqbn)
        except Exception as e:
            print(f"Failed to get board details for {fqbn}: {e}")
            return None
