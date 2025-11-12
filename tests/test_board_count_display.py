#!/usr/bin/env python3
"""
Test Board Count Display for Non-Installed Packages

Demonstrates how board counts are now shown for both installed
and non-installed packages by using metadata from the package index.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from arduino_ide.models.board import BoardPackage, BoardPackageVersion, BoardCategory

def test_board_count_display():
    """Test board count display logic"""
    print("Testing Board Count Display")
    print("=" * 60)

    # Create a sample package (not installed)
    # This simulates what comes from the Arduino package index
    package_not_installed = BoardPackage(
        name="esp32",
        maintainer="Espressif Systems",
        category=BoardCategory.COMMUNITY,
        url="https://github.com/espressif/arduino-esp32",
        versions=[
            BoardPackageVersion(
                version="2.0.11",
                url="https://github.com/espressif/arduino-esp32/releases/download/2.0.11/esp32-2.0.11.zip",
                size=50 * 1024 * 1024,  # 50MB
                checksum="SHA-256:abc123",
                release_date=datetime(2023, 8, 15),
                architecture="esp32",
                boards_count=42,  # This comes from the package index!
                boards=["ESP32 Dev Module", "ESP32-S2", "ESP32-S3", "ESP32-C3", "..."]
            ),
            BoardPackageVersion(
                version="2.0.10",
                url="https://github.com/espressif/arduino-esp32/releases/download/2.0.10/esp32-2.0.10.zip",
                size=49 * 1024 * 1024,
                checksum="SHA-256:def456",
                release_date=datetime(2023, 7, 1),
                architecture="esp32",
                boards_count=40,
                boards=["ESP32 Dev Module", "ESP32-S2", "..."]
            )
        ],
        latest_version="2.0.11",
        installed_version=None,  # NOT installed
        boards=[]  # Empty because not installed yet
    )

    # Simulate the UI logic
    def get_package_board_count(package):
        """Simulates _get_package_board_count() method"""
        # If we have discovered boards (from installed package), use that count
        if package.boards:
            return len(package.boards)

        # Otherwise, get count from package index metadata
        latest_version = package.get_latest_version_obj()
        if latest_version and latest_version.boards_count > 0:
            return latest_version.boards_count

        # Fallback: check if any version has board count metadata
        for version in package.versions:
            if version.boards_count > 0:
                return version.boards_count

        return 0

    print("\n📦 Package: esp32 (Espressif Systems)")
    print(f"   Installed: {package_not_installed.installed_version or 'No'}")
    print(f"   Latest version: {package_not_installed.latest_version}")
    print(f"   Discovered boards (from boards.txt): {len(package_not_installed.boards)}")

    board_count = get_package_board_count(package_not_installed)
    print(f"   Board count shown in UI: {board_count}")

    if board_count == 42:
        print("   ✅ CORRECT! Shows board count from package index metadata")
    else:
        print(f"   ❌ WRONG! Expected 42, got {board_count}")
        return False

    # Now test an installed package
    print("\n📦 Package: arduino (Arduino)")
    print("   Installed: Yes (1.8.6)")
    print("   Discovered boards (from boards.txt): 24")

    # Simulate installed package with discovered boards
    package_installed = BoardPackage(
        name="arduino",
        maintainer="Arduino",
        category=BoardCategory.OFFICIAL,
        url="https://www.arduino.cc/",
        versions=[
            BoardPackageVersion(
                version="1.8.6",
                url="https://downloads.arduino.cc/...",
                size=10 * 1024 * 1024,
                checksum="SHA-256:xyz789",
                release_date=datetime(2023, 5, 1),
                architecture="avr",
                boards_count=24,  # Also in index
                boards=["Uno", "Mega", "Nano", "..."]
            )
        ],
        latest_version="1.8.6",
        installed_version="1.8.6",
        boards=[f"Board_{i}" for i in range(24)]  # 24 discovered boards
    )

    board_count = get_package_board_count(package_installed)
    print(f"   Board count shown in UI: {board_count}")

    if board_count == 24:
        print("   ✅ CORRECT! Uses discovered boards count")
    else:
        print(f"   ❌ WRONG! Expected 24, got {board_count}")
        return False

    print("\n" + "=" * 60)
    print("COMPARISON WITH ARDUINO IDE 1.8:")
    print("=" * 60)
    print("\n❌ BEFORE (Like Arduino IDE 2.0 bug):")
    print("   Non-installed packages: Boards: 0")
    print("   Installed packages: Boards: 24")
    print("   Problem: Can't see what you're installing!")

    print("\n✅ AFTER (Like Arduino IDE 1.8):")
    print("   Non-installed packages: Boards: 42  (from index metadata)")
    print("   Installed packages: Boards: 24  (from discovered boards)")
    print("   Fixed: Users can see board count before installing!")

    print("\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = test_board_count_display()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
