#!/usr/bin/env python3
"""
Debug script to diagnose board discovery issues
"""
 
import sys
from pathlib import Path
 
# Add project to path
sys.path.insert(0, str(Path(__file__).parent))
 
from arduino_ide.services.board_manager import BoardManager
from arduino_ide.services.boards_txt_parser import BoardsTxtParser
 
def main():
    print("=" * 70)
    print("Board Discovery Debug")
    print("=" * 70)
    print()
 
    # Initialize BoardManager
    bm = BoardManager()
 
    print("1. Checking packages directory...")
    print(f"   Path: {bm.packages_dir}")
    print(f"   Exists: {bm.packages_dir.exists()}")
 
    if bm.packages_dir.exists():
        subdirs = list(bm.packages_dir.iterdir())
        print(f"   Contents: {len(subdirs)} items")
        for item in subdirs:
            print(f"     - {item.name}")
    print()
 
    print("2. Scanning for boards.txt files...")
    boards_txt_files = []
    if bm.packages_dir.exists():
        for boards_txt in bm.packages_dir.rglob("boards.txt"):
            boards_txt_files.append(boards_txt)
            print(f"   Found: {boards_txt}")
 
    if not boards_txt_files:
        print(f"   ✗ No boards.txt files found!")
        print(f"   Expected location: {bm.packages_dir}/arduino/avr/*/boards.txt")
    print()
 
    print("3. Testing board discovery...")
    try:
        boards = bm._discover_boards_from_installed_platforms()
        print(f"   ✓ Discovered {len(boards)} boards")
 
        if boards:
            print(f"   First 10 boards:")
            for board in boards[:10]:
                print(f"     - {board.name} ({board.fqbn})")
                print(f"       CPU: {board.specs.cpu}, Flash: {board.specs.flash}")
        else:
            print(f"   ✗ No boards discovered")
    except Exception as e:
        print(f"   ✗ Error during discovery: {e}")
        import traceback
        traceback.print_exc()
    print()
 
    print("4. Testing boards.txt parser directly...")
    if boards_txt_files:
        for boards_txt in boards_txt_files[:1]:  # Test first file
            print(f"   Parsing: {boards_txt}")
 
            # Extract package and architecture from path
            # Path format: .../packages/arduino/avr/1.8.6/boards.txt
            parts = boards_txt.parts
            if 'packages' in parts:
                idx = parts.index('packages')
                if len(parts) > idx + 3:
                    package_name = parts[idx + 1]
                    architecture = parts[idx + 2]
 
                    print(f"   Package: {package_name}")
                    print(f"   Architecture: {architecture}")
 
                    try:
                        boards = BoardsTxtParser.parse_boards_txt(
                            boards_txt, package_name, architecture
                        )
                        print(f"   ✓ Parsed {len(boards)} boards")
 
                        if boards:
                            for board in boards[:5]:
                                print(f"     - {board.name}: {board.fqbn}")
                    except Exception as e:
                        print(f"   ✗ Parse error: {e}")
                        import traceback
                        traceback.print_exc()
    print()
 
    print("5. Checking installed packages...")
    print(f"   Installed file: {bm.installed_file}")
    print(f"   Exists: {bm.installed_file.exists()}")
 
    if bm.installed_file.exists():
        import json
        with open(bm.installed_file, 'r') as f:
            installed = json.load(f)
        print(f"   Installed packages: {installed}")
    print()
 
    print("6. Testing get_all_boards()...")
    try:
        boards = bm.get_all_boards()
        print(f"   ✓ get_all_boards() returned {len(boards)} boards")
 
        if boards:
            for board in boards[:5]:
                print(f"     - {board.name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
    print()
 
    print("=" * 70)
    print("Debug complete!")
    print("=" * 70)
 
if __name__ == "__main__":
    main()
 
