#!/usr/bin/env python3
"""
Test script for board discovery from installed platforms

This demonstrates the Arduino boards platform framework integration:
1. Update package index from Arduino servers
2. Install a platform (e.g., arduino:avr)
3. Discover boards from installed platform by parsing boards.txt
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from arduino_ide.services.board_manager import BoardManager

def main():
    print("=" * 70)
    print("Arduino Board Discovery Test")
    print("=" * 70)
    print()

    # Initialize BoardManager
    print("1. Initializing BoardManager...")
    bm = BoardManager()
    print(f"   Packages directory: {bm.packages_dir}")
    print(f"   Cache directory: {bm.cache_dir}")
    print()

    # Update package index
    print("2. Updating package index from Arduino servers...")
    print(f"   URL: {BoardManager.PACKAGE_INDEX_URL}")
    success = bm.update_index(force=True)

    if success:
        print(f"   ✓ Index updated successfully")
        print(f"   Packages available: {len(bm.board_index.packages)}")

        if len(bm.board_index.packages) > 0:
            print(f"   First package: {bm.board_index.packages[0].name}")
            print(f"   Platforms in first package: {len(bm.board_index.packages[0].versions)}")
    else:
        print(f"   ✗ Failed to update index")
        print(f"   This may be due to network restrictions in your environment")
    print()

    # Check for arduino package
    print("3. Checking for Arduino AVR package...")
    arduino_pkg = bm.get_package("arduino")
    if arduino_pkg:
        print(f"   ✓ Found Arduino package")
        print(f"   Maintainer: {arduino_pkg.maintainer}")
        print(f"   Versions available: {len(arduino_pkg.versions)}")
        if arduino_pkg.versions:
            latest = arduino_pkg.versions[0]
            print(f"   Latest version: {latest.version}")
            print(f"   Architecture: {latest.architecture}")
            print(f"   Boards: {latest.boards_count}")
    else:
        print(f"   ✗ Arduino package not found in index")
        print(f"   Cannot proceed with installation test")
        return
    print()

    # Check if already installed
    print("4. Checking for installed platforms...")
    boards = bm.get_all_boards()
    print(f"   Boards from installed platforms: {len(boards)}")

    if len(boards) > 0:
        print(f"   First board: {boards[0].name} ({boards[0].fqbn})")
        print(f"   All discovered boards:")
        for board in boards[:10]:  # Show first 10
            print(f"     - {board.name} ({board.fqbn})")
        if len(boards) > 10:
            print(f"     ... and {len(boards) - 10} more")
    else:
        print(f"   No boards found (no platforms installed)")
    print()

    # Prompt for installation if needed
    if len(boards) == 0:
        print("5. To install Arduino AVR Boards, run:")
        print(f"   python3 arduino-cli core install arduino:avr")
        print()
        print("   This will:")
        print("   - Download the arduino:avr platform package")
        print("   - Extract it to ~/.arduino-ide-modern/packages/arduino/avr/")
        print("   - Parse boards.txt to discover Arduino Uno, Mega, Nano, etc.")
        print("   - Make boards available in the IDE")
        print()
    else:
        print("5. Platform installation successful!")
        print(f"   {len(boards)} boards are now available in the IDE")
        print()

    print("=" * 70)
    print("Test complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
