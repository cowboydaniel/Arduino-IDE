"""
Toolchain Manager - Automatic download and management of Arduino AVR toolchain
"""

import os
import sys
import tarfile
import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import shutil

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False


class ToolchainManager:
    """Manages Arduino AVR toolchain installation and access"""

    # Toolchain download URLs for different platforms
    TOOLCHAIN_URLS = {
        'Linux_x86_64': 'https://downloads.arduino.cc/tools/avr-gcc-7.3.0-atmel3.6.1-arduino7-x86_64-pc-linux-gnu.tar.bz2',
        'Linux_i686': 'https://downloads.arduino.cc/tools/avr-gcc-7.3.0-atmel3.6.1-arduino7-i686-pc-linux-gnu.tar.bz2',
        'Darwin': 'https://downloads.arduino.cc/tools/avr-gcc-7.3.0-atmel3.6.1-arduino5-x86_64-apple-darwin14.tar.bz2',
        'Windows_AMD64': 'https://downloads.arduino.cc/tools/avr-gcc-7.3.0-atmel3.6.1-arduino7-i686-w64-mingw32.zip',
        'Windows_x86': 'https://downloads.arduino.cc/tools/avr-gcc-7.3.0-atmel3.6.1-arduino7-i686-w64-mingw32.zip',
    }

    def __init__(self, tools_dir: Optional[Path] = None):
        """Initialize toolchain manager

        Args:
            tools_dir: Custom tools directory. If None, uses ~/.arduino-ide/tools
        """
        if tools_dir is None:
            self.tools_dir = Path.home() / '.arduino-ide' / 'tools'
        else:
            self.tools_dir = Path(tools_dir)

        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.avr_dir = self.tools_dir / 'avr-gcc'

    def get_platform_key(self) -> str:
        """Get platform identifier for toolchain download"""
        system = platform.system()
        machine = platform.machine()

        if system == 'Linux':
            if machine == 'x86_64':
                return 'Linux_x86_64'
            else:
                return 'Linux_i686'
        elif system == 'Darwin':
            return 'Darwin'
        elif system == 'Windows':
            if machine == 'AMD64' or machine == 'x86_64':
                return 'Windows_AMD64'
            else:
                return 'Windows_x86'
        else:
            raise RuntimeError(f"Unsupported platform: {system} {machine}")

    def is_installed(self) -> bool:
        """Check if toolchain is installed"""
        avr_gcc = self.get_avr_gcc_path()
        avr_size = self.get_avr_size_path()
        return avr_gcc.exists() and avr_size.exists()

    def get_avr_gcc_path(self) -> Path:
        """Get path to avr-gcc executable"""
        if platform.system() == 'Windows':
            return self.avr_dir / 'bin' / 'avr-gcc.exe'
        return self.avr_dir / 'bin' / 'avr-gcc'

    def get_avr_size_path(self) -> Path:
        """Get path to avr-size executable"""
        if platform.system() == 'Windows':
            return self.avr_dir / 'bin' / 'avr-size.exe'
        return self.avr_dir / 'bin' / 'avr-size'

    def get_avr_objcopy_path(self) -> Path:
        """Get path to avr-objcopy executable"""
        if platform.system() == 'Windows':
            return self.avr_dir / 'bin' / 'avr-objcopy.exe'
        return self.avr_dir / 'bin' / 'avr-objcopy'

    def download_toolchain(self, progress_callback=None) -> bool:
        """Download and install AVR toolchain

        Args:
            progress_callback: Optional callback function(downloaded, total)

        Returns:
            True if successful, False otherwise
        """
        try:
            platform_key = self.get_platform_key()
            url = self.TOOLCHAIN_URLS.get(platform_key)

            if not url:
                print(f"✗ No toolchain available for platform: {platform_key}", file=sys.stderr)
                return False

            print(f"Downloading AVR toolchain for {platform_key}...")
            print(f"URL: {url}")

            # Download to temporary file
            archive_name = url.split('/')[-1]
            temp_file = self.tools_dir / archive_name

            # Download with progress
            def reporthook(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    print(f"\rDownloading: {mb_downloaded:.1f}/{mb_total:.1f} MB ({percent}%)", end='', flush=True)
                if progress_callback:
                    progress_callback(downloaded, total_size)

            # Download using requests library if available (more reliable)
            try:
                if HAS_REQUESTS:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': '*/*',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive'
                    }
                    response = requests.get(url, headers=headers, stream=True, timeout=30)
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
                        url,
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
                # If download fails, try fallback to system package
                print(f"\n✗ Download failed: {e}", file=sys.stderr)
                print("Attempting to use system AVR toolchain...", file=sys.stderr)
                return self._try_system_toolchain()
            print()  # New line after progress

            # Extract archive
            print("Extracting toolchain...")
            if archive_name.endswith('.tar.bz2'):
                with tarfile.open(temp_file, 'r:bz2') as tar:
                    # Extract to tools directory
                    tar.extractall(self.tools_dir)
                    # The archive usually extracts to a directory like 'avr'
                    # Rename it to 'avr-gcc' for consistency
                    extracted = self.tools_dir / 'avr'
                    if extracted.exists() and not self.avr_dir.exists():
                        extracted.rename(self.avr_dir)
            elif archive_name.endswith('.zip'):
                import zipfile
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    zip_ref.extractall(self.tools_dir)
                    extracted = self.tools_dir / 'avr'
                    if extracted.exists() and not self.avr_dir.exists():
                        extracted.rename(self.avr_dir)

            # Clean up archive
            temp_file.unlink()

            # Verify installation
            if self.is_installed():
                print("✓ AVR toolchain installed successfully")
                return True
            else:
                print("✗ Toolchain installation failed - tools not found", file=sys.stderr)
                return False

        except Exception as e:
            print(f"✗ Failed to download toolchain: {e}", file=sys.stderr)
            return False

    def _try_system_toolchain(self) -> bool:
        """Try to use system-installed AVR toolchain as fallback

        Returns:
            True if system toolchain is available, False otherwise
        """
        try:
            # Check if avr-gcc is in PATH
            result = subprocess.run(
                ['which', 'avr-gcc'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                system_avr_gcc = Path(result.stdout.strip())
                system_bin_dir = system_avr_gcc.parent

                # Create avr-gcc directory structure
                self.avr_dir.mkdir(parents=True, exist_ok=True)
                local_bin_dir = self.avr_dir / 'bin'
                local_bin_dir.mkdir(parents=True, exist_ok=True)

                # Create symlinks to system tools
                tools = ['avr-gcc', 'avr-g++', 'avr-size', 'avr-objcopy', 'avr-objdump', 'avr-ar']
                for tool in tools:
                    system_tool = system_bin_dir / tool
                    local_tool = local_bin_dir / tool
                    if system_tool.exists() and not local_tool.exists():
                        try:
                            local_tool.symlink_to(system_tool)
                        except Exception:
                            # If symlink fails, copy the file
                            shutil.copy2(system_tool, local_tool)

                if self.is_installed():
                    print("✓ Using system AVR toolchain")
                    return True

        except Exception as e:
            print(f"✗ Failed to use system toolchain: {e}", file=sys.stderr)

        return False

    def ensure_installed(self) -> bool:
        """Ensure toolchain is installed, download if necessary

        Returns:
            True if toolchain is available, False otherwise
        """
        if self.is_installed():
            return True

        print("AVR toolchain not found. Installing automatically...")

        # First try system toolchain
        if self._try_system_toolchain():
            return True

        # If system toolchain not available, try downloading
        return self.download_toolchain()

    def get_version(self) -> Optional[str]:
        """Get avr-gcc version string"""
        if not self.is_installed():
            return None

        try:
            result = subprocess.run(
                [str(self.get_avr_gcc_path()), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # First line usually contains version
                return result.stdout.split('\n')[0]
        except Exception:
            pass

        return None
