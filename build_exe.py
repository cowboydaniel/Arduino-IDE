#!/usr/bin/env python3
"""
Build script for creating standalone Arduino IDE executable
This script builds a platform-specific executable that works without Python installed.
For Windows .exe: Must be run on Windows
For Linux binary: Must be run on Linux
"""

import subprocess
import sys
import shutil
from pathlib import Path


def main():
    """Build the standalone executable"""
    platform_name = "Windows .exe" if sys.platform == "win32" else "Linux binary"
    exe_name = "Arduino-IDE.exe" if sys.platform == "win32" else "Arduino-IDE"

    print("=" * 70)
    print(f"Arduino IDE Modern - Standalone {platform_name} Builder")
    print("=" * 70)
    print()

    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("[!] PyInstaller not found!")
        print("    Installing PyInstaller...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--break-system-packages", "pyinstaller==6.3.0"
        ])
        print("[OK] PyInstaller installed")

    print()

    # Clean previous builds
    dist_dir = Path("dist")
    build_dir = Path("build")

    if dist_dir.exists():
        print(f"Cleaning {dist_dir}...")
        shutil.rmtree(dist_dir)

    if build_dir.exists():
        print(f"Cleaning {build_dir}...")
        shutil.rmtree(build_dir)

    print()
    print("=" * 70)
    print("Building standalone .exe...")
    print("=" * 70)
    print()
    print("This may take several minutes on the first build...")
    print()

    # Build the executable using the spec file
    try:
        subprocess.check_call([
            sys.executable,
            "-m", "PyInstaller",
            "arduino_ide.spec",
            "--clean"
        ])

        print()
        print("=" * 70)
        print("[SUCCESS] Build completed successfully!")
        print("=" * 70)
        print()
        print(f"The standalone executable is located at:")
        print(f"  {dist_dir.absolute() / exe_name}")
        print()
        if sys.platform == "win32":
            print("You can now distribute this .exe file to any Windows PC,")
            print("even if they don't have Python installed!")
        else:
            print("You can now distribute this binary to Linux systems,")
            print("even if they don't have Python installed!")
            print()
            print("Note: To build a Windows .exe, run this script on Windows")
            print("or use the GitHub Actions workflow to build automatically.")
        print()

    except subprocess.CalledProcessError as e:
        print()
        print("=" * 70)
        print("[ERROR] Build failed!")
        print("=" * 70)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
