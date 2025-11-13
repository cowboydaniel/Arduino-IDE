"""
Core Manager - Automatic download and management of Arduino AVR core files
"""

import os
import sys
import shutil
import tarfile
import zipfile
import subprocess
from pathlib import Path
from typing import List, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False


class CoreManager:
    """Manages Arduino AVR core installation and access"""

    # Official Arduino AVR Core repository
    CORE_REPO_URL = "https://github.com/arduino/ArduinoCore-avr"
    CORE_VERSION = "1.8.6"  # Stable version compatible with most sketches

    # Direct download URL for the core archive
    CORE_ARCHIVE_URL = f"https://github.com/arduino/ArduinoCore-avr/archive/refs/tags/{CORE_VERSION}.tar.gz"

    def __init__(self, tools_dir: Optional[Path] = None):
        """Initialize core manager

        Args:
            tools_dir: Custom tools directory. If None, uses ~/.arduino-ide/cores
        """
        if tools_dir is None:
            # Use same location as toolchain
            home_cores = Path.home() / '.arduino-ide' / 'cores'
            project_cores = Path(__file__).parent.parent.parent / '.arduino-ide' / 'cores'

            if home_cores.exists() or not project_cores.exists():
                self.cores_dir = home_cores
            else:
                self.cores_dir = project_cores
        else:
            self.cores_dir = Path(tools_dir)

        self.cores_dir.mkdir(parents=True, exist_ok=True)
        self.avr_core_dir = self.cores_dir / 'arduino-avr'
        self.arduino_h_path = self.avr_core_dir / 'cores' / 'arduino' / 'Arduino.h'

    def is_installed(self) -> bool:
        """Check if Arduino AVR core is installed"""
        return self.arduino_h_path.exists()

    def ensure_builtin_libraries(self, target_dir: Optional[Path] = None,
                                 ensure_core: bool = False) -> List[Path]:
        """Ensure the Arduino core's bundled libraries are available in the IDE.

        Args:
            target_dir: Destination for managed libraries. Defaults to the
                user's ``~/.arduino-ide-modern/libraries`` directory.
            ensure_core: When True, download the core if it is not already
                installed so the bundled libraries can be copied.

        Returns:
            A list of paths that were newly installed.
        """
        if target_dir is None:
            target_dir = Path.home() / '.arduino-ide-modern' / 'libraries'

        if ensure_core and not self.is_installed():
            if not self.download_core():
                return []

        source_dir = self.avr_core_dir / 'libraries'
        if not source_dir.exists():
            return []

        target_dir.mkdir(parents=True, exist_ok=True)

        installed_paths: List[Path] = []
        for library_dir in sorted(source_dir.iterdir()):
            if not library_dir.is_dir():
                continue

            destination = target_dir / library_dir.name
            if destination.exists():
                continue

            try:
                shutil.copytree(library_dir, destination)
                installed_paths.append(destination)
            except FileExistsError:
                continue
            except Exception as exc:  # pragma: no cover - log but do not fail entirely
                print(
                    f"⚠️  Failed to install bundled library '{library_dir.name}': {exc}",
                    file=sys.stderr,
                )

        return installed_paths

    def get_core_path(self) -> Path:
        """Get path to Arduino core directory"""
        return self.avr_core_dir / 'cores' / 'arduino'

    def get_variant_path(self, variant: str = 'standard') -> Path:
        """Get path to board variant directory

        Args:
            variant: Variant name (e.g., 'standard' for Uno)
        """
        return self.avr_core_dir / 'variants' / variant

    def download_core(self, progress_callback=None) -> bool:
        """Download and install Arduino AVR core

        Args:
            progress_callback: Optional callback function(downloaded, total)

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Downloading Arduino AVR Core {self.CORE_VERSION}...")
            print(f"URL: {self.CORE_ARCHIVE_URL}")

            # Download to temporary file
            archive_name = f"ArduinoCore-avr-{self.CORE_VERSION}.tar.gz"
            temp_file = self.cores_dir / archive_name

            # Download with progress
            last_percent = [-1]

            def reporthook(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                    if percent != last_percent[0]:
                        last_percent[0] = percent
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        progress_text = f"Downloading: {mb_downloaded:.1f}/{mb_total:.1f} MB ({percent}%)"
                        sys.stdout.write(f"\r{progress_text:<80}")
                        sys.stdout.flush()
                if progress_callback:
                    progress_callback(downloaded, total_size)

            # Download using requests library if available
            try:
                if HAS_REQUESTS:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (compatible; Arduino-IDE/1.0)',
                        'Accept': '*/*'
                    }
                    response = requests.get(self.CORE_ARCHIVE_URL, headers=headers, stream=True, timeout=30)
                    response.raise_for_status()

                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    block_size = 8192
                    block_num = 0

                    with open(temp_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=block_size):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                block_num += 1
                                reporthook(block_num, block_size, total_size)
                else:
                    # Fallback to urllib
                    req = urllib.request.Request(
                        self.CORE_ARCHIVE_URL,
                        headers={'User-Agent': 'Mozilla/5.0 (compatible; Arduino-IDE/1.0)'}
                    )

                    with urllib.request.urlopen(req) as response:
                        total_size = int(response.headers.get('Content-Length', 0))
                        downloaded = 0
                        block_size = 8192
                        block_num = 0

                        with open(temp_file, 'wb') as f:
                            while True:
                                chunk = response.read(block_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded += len(chunk)
                                block_num += 1
                                reporthook(block_num, block_size, total_size)

            except Exception as e:
                print(f"\n✗ Download failed: {e}", file=sys.stderr)
                if temp_file.exists():
                    temp_file.unlink()
                return False
            print()  # New line after progress

            # Extract archive
            print("Extracting Arduino core files...")
            extract_dir = self.cores_dir / 'temp_extract'
            extract_dir.mkdir(exist_ok=True)

            try:
                with tarfile.open(temp_file, 'r:gz') as tar:
                    tar.extractall(extract_dir)

                # Find the extracted directory (should be ArduinoCore-avr-{version})
                extracted_dirs = list(extract_dir.glob('ArduinoCore-avr-*'))
                if not extracted_dirs:
                    print("✗ Failed to find extracted core directory", file=sys.stderr)
                    return False

                extracted_core = extracted_dirs[0]

                # Move to final location
                if self.avr_core_dir.exists():
                    shutil.rmtree(self.avr_core_dir)

                shutil.move(str(extracted_core), str(self.avr_core_dir))

                # Clean up
                shutil.rmtree(extract_dir)
                temp_file.unlink()

            except Exception as e:
                print(f"✗ Extraction failed: {e}", file=sys.stderr)
                if extract_dir.exists():
                    shutil.rmtree(extract_dir)
                if temp_file.exists():
                    temp_file.unlink()
                return False

            # Verify installation
            if self.is_installed():
                print("✓ Arduino AVR core installed successfully")
                self.ensure_builtin_libraries()
                return True
            else:
                print("✗ Core installation failed - files not found", file=sys.stderr)
                return False

        except Exception as e:
            print(f"✗ Failed to install core: {e}", file=sys.stderr)
            return False

    def ensure_installed(self) -> bool:
        """Ensure Arduino core is installed, download if necessary

        Returns:
            True if core is available, False otherwise
        """
        if self.is_installed():
            self.ensure_builtin_libraries()
            return True

        print("Arduino AVR core not found. Downloading automatically...")
        if self.download_core():
            self.ensure_builtin_libraries()
            return True
        return False

    def get_core_sources(self) -> list[Path]:
        """Get list of all core source files (.c, .cpp, .S) that need to be compiled

        Returns:
            List of source file paths
        """
        if not self.is_installed():
            return []

        core_path = self.get_core_path()
        sources = []

        # Add all .c, .cpp, and .S (assembly) files INCLUDING main.cpp
        for ext in ['*.c', '*.cpp', '*.S']:
            for source in core_path.glob(ext):
                sources.append(source)

        return sources

    def get_version(self) -> str:
        """Get installed core version"""
        if not self.is_installed():
            return "Not installed"

        # Try to read version from platform.txt
        platform_txt = self.avr_core_dir / 'platform.txt'
        if platform_txt.exists():
            try:
                content = platform_txt.read_text(encoding='utf-8')
                for line in content.splitlines():
                    if line.startswith('version='):
                        return line.split('=', 1)[1].strip()
            except Exception:
                pass

        return self.CORE_VERSION
