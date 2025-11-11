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
from pathlib import Path
from typing import List, Optional, Dict
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
    BoardPackageURL, BoardStatus, BoardCategory, BoardSpecs, DEFAULT_BOARDS
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
        self._initialize_default_boards()

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
                        if pkg.name in self.installed_packages:
                            pkg.installed_version = self.installed_packages[pkg.name]

                        packages.append(pkg)
                    except Exception as e:
                        print(f"Error parsing package: {e}")

                self.board_index.packages = packages
                self.board_index.last_updated = datetime.fromisoformat(
                    data.get("last_updated", datetime.now().isoformat())
                )
            except Exception as e:
                print(f"Error loading board index: {e}")

    def _initialize_default_boards(self):
        """Initialize with default Arduino boards"""
        # Check if we have any packages
        if not self.board_index.packages:
            # Create a default Arduino AVR package
            default_package = BoardPackage(
                name="Arduino AVR Boards",
                maintainer="Arduino",
                category=BoardCategory.OFFICIAL,
                url="https://arduino.cc",
                boards=DEFAULT_BOARDS,
                latest_version="1.8.6",
            )

            self.board_index.packages.append(default_package)

    def update_index(self, force: bool = False) -> bool:
        """Update board package index from Arduino servers"""
        self.status_message.emit("Updating board package index...")

        # Check if update is needed
        if not force and self.index_file.exists():
            age = datetime.now() - datetime.fromtimestamp(self.index_file.stat().st_mtime)
            if age.total_seconds() < 3600:  # Less than 1 hour old
                self.status_message.emit("Board index is up to date")
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

            self.status_message.emit("Board package index updated successfully")
            self.index_updated.emit()
            return True

        except Exception as e:
            self.status_message.emit(f"Error updating index: {str(e)}")
            return False

    def get_package(self, name: str) -> Optional[BoardPackage]:
        """Get package by name"""
        return self.board_index.get_package(name)

    def get_board(self, fqbn: str) -> Optional[Board]:
        """Get board by FQBN"""
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
        """Install a board package"""
        package = self.get_package(name)
        if not package:
            self.status_message.emit(f"Package '{name}' not found")
            return False

        # Determine version to install
        if not version:
            version = package.latest_version

        if not version:
            self.status_message.emit(f"No version found for '{name}'")
            return False

        pkg_version = package.get_version(version)
        if not pkg_version:
            self.status_message.emit(f"Version '{version}' not found for '{name}'")
            return False

        self.status_message.emit(f"Installing {name} v{version}...")

        try:
            # Download package
            self.status_message.emit(f"Downloading {name}...")
            response = requests.get(pkg_version.url, timeout=120, stream=True)

            if response.status_code != 200:
                self.status_message.emit(f"Failed to download: HTTP {response.status_code}")
                return False

            # Save to temp file
            suffix = '.tar.gz' if pkg_version.url.endswith('.tar.gz') else '.zip'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        self.progress_changed.emit(progress)

                tmp_path = tmp_file.name

            # Extract package
            self.status_message.emit(f"Extracting {name}...")
            install_path = self.packages_dir / name / version

            # Remove existing installation
            if install_path.exists():
                shutil.rmtree(install_path)

            install_path.mkdir(parents=True, exist_ok=True)

            # Extract archive
            if suffix == '.tar.gz':
                with tarfile.open(tmp_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(install_path)
            else:
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    zip_ref.extractall(install_path)

            # Clean up temp file
            os.unlink(tmp_path)

            # Update installed packages
            self.installed_packages[name] = version
            self._save_installed_packages()

            # Update package object
            package.installed_version = version

            self.status_message.emit(f"Successfully installed {name} v{version}")
            self.package_installed.emit(name, version)
            return True

        except Exception as e:
            self.status_message.emit(f"Error installing {name}: {str(e)}")
            return False

    def uninstall_package(self, name: str) -> bool:
        """Uninstall a board package"""
        if name not in self.installed_packages:
            self.status_message.emit(f"Package '{name}' is not installed")
            return False

        version = self.installed_packages[name]
        install_path = self.packages_dir / name / version

        try:
            if install_path.exists():
                shutil.rmtree(install_path)

            # Remove version directory if empty
            pkg_dir = self.packages_dir / name
            if pkg_dir.exists() and not list(pkg_dir.iterdir()):
                pkg_dir.rmdir()

            del self.installed_packages[name]
            self._save_installed_packages()

            # Update package object
            package = self.get_package(name)
            if package:
                package.installed_version = None

            self.status_message.emit(f"Successfully uninstalled {name}")
            self.package_uninstalled.emit(name)
            return True

        except Exception as e:
            self.status_message.emit(f"Error uninstalling {name}: {str(e)}")
            return False

    def update_package(self, name: str, version: Optional[str] = None) -> bool:
        """Update a board package"""
        package = self.get_package(name)
        if not package:
            return False

        old_version = package.installed_version
        if not old_version:
            self.status_message.emit(f"Package '{name}' is not installed")
            return False

        if not version:
            version = package.latest_version

        if old_version == version:
            self.status_message.emit(f"Package '{name}' is already up to date")
            return False

        # Install new version
        if self.install_package(name, version):
            self.package_updated.emit(name, old_version, version)
            return True

        return False

    def add_package_url(self, name: str, url: str) -> bool:
        """Add a custom package URL"""
        # Check if URL already exists
        for pkg_url in self.board_index.package_urls:
            if pkg_url.url == url:
                self.status_message.emit("URL already exists")
                return False

        # Add new URL
        new_url = BoardPackageURL(name=name, url=url, enabled=True)
        self.board_index.package_urls.append(new_url)
        self._save_package_urls()

        self.status_message.emit(f"Added package URL: {name}")
        return True

    def remove_package_url(self, url: str) -> bool:
        """Remove a package URL"""
        for pkg_url in self.board_index.package_urls:
            if pkg_url.url == url:
                self.board_index.package_urls.remove(pkg_url)
                self._save_package_urls()
                self.status_message.emit("Package URL removed")
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
        """Get all available boards"""
        boards = []
        for package in self.board_index.packages:
            boards.extend(package.boards)
        return boards

    def get_architectures(self) -> List[str]:
        """Get all unique architectures"""
        architectures = set()
        for board in self.get_all_boards():
            architectures.add(board.architecture)
        return sorted(list(architectures))

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
                    specs=BoardSpecs(),  # Use default specs; arduino-cli handles the details
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
            self.status_message.emit("CLI runner not configured")
            return False

        self.status_message.emit(f"Installing platform {platform_id}...")

        try:
            success = self.cli_runner.install_platform(platform_id)
            if success:
                self.status_message.emit(f"Platform {platform_id} installed successfully")
                self.package_installed.emit(platform_id, "latest")
            else:
                self.status_message.emit(f"Failed to install platform {platform_id}")
            return success
        except Exception as e:
            self.status_message.emit(f"Error installing platform: {e}")
            return False

    def uninstall_platform_via_cli(self, platform_id: str) -> bool:
        """Uninstall a platform using arduino-cli.

        Args:
            platform_id: Platform identifier (e.g., "arduino:avr", "esp32:esp32")

        Returns:
            True if uninstallation succeeded, False otherwise
        """
        if not self.cli_runner:
            self.status_message.emit("CLI runner not configured")
            return False

        self.status_message.emit(f"Uninstalling platform {platform_id}...")

        try:
            success = self.cli_runner.uninstall_platform(platform_id)
            if success:
                self.status_message.emit(f"Platform {platform_id} uninstalled successfully")
                self.package_uninstalled.emit(platform_id)
            else:
                self.status_message.emit(f"Failed to uninstall platform {platform_id}")
            return success
        except Exception as e:
            self.status_message.emit(f"Error uninstalling platform: {e}")
            return False

    def update_cli_index(self) -> bool:
        """Update the arduino-cli platform index.

        Returns:
            True if update succeeded, False otherwise
        """
        if not self.cli_runner:
            self.status_message.emit("CLI runner not configured")
            return False

        self.status_message.emit("Updating arduino-cli platform index...")

        try:
            success = self.cli_runner.update_platform_index()
            if success:
                self.status_message.emit("Platform index updated successfully")
                self.index_updated.emit()
            else:
                self.status_message.emit("Failed to update platform index")
            return success
        except Exception as e:
            self.status_message.emit(f"Error updating platform index: {e}")
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
