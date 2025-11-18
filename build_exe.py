#!/usr/bin/env python3
"""
Build script for creating standalone Arduino IDE .exe
This script builds a Windows executable that works without Python installed.
"""

import subprocess
import sys
import shutil
from pathlib import Path


def main():
    """Build the standalone executable"""
    print("=" * 70)
    print("Arduino IDE Modern - Standalone .exe Builder")
    print("=" * 70)
    print()

    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("✗ PyInstaller not found!")
        print("  Installing PyInstaller...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--break-system-packages", "pyinstaller==6.3.0"
        ])
        print("✓ PyInstaller installed")

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
        print("✓ Build completed successfully!")
        print("=" * 70)
        print()
        print(f"The standalone executable is located at:")
        print(f"  {dist_dir.absolute() / 'Arduino-IDE.exe'}")
        print()
        print("You can now distribute this .exe file to any Windows PC,")
        print("even if they don't have Python installed!")
        print()

    except subprocess.CalledProcessError as e:
        print()
        print("=" * 70)
        print("✗ Build failed!")
        print("=" * 70)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
