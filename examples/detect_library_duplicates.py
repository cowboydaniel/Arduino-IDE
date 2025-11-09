#!/usr/bin/env python3
"""
Example: Detect and Resolve Library Duplicates

This script demonstrates how to use the library duplicate detection
functionality in the Arduino IDE.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arduino_ide.services.library_manager import LibraryManager


def main():
    """Main function to demonstrate duplicate detection"""
    print("Arduino Library Duplicate Detection")
    print("=" * 50)
    print()

    # Initialize library manager
    manager = LibraryManager()

    # 1. Detect all duplicate installations
    print("1. Detecting duplicate library installations...")
    duplicates = manager.detect_duplicate_installations()

    if duplicates:
        print(f"Found {len(duplicates)} libraries with duplicate installations:\n")
        for lib_name, installations in duplicates.items():
            print(f"Library: {lib_name}")
            for install in installations:
                print(f"  - v{install['version']} at {install['path']} ({install['source']})")
            print()
    else:
        print("No duplicate installations found.")
        print()

    # 2. Find libraries with multiple versions
    print("\n2. Finding libraries with multiple versions installed...")
    multiple_versions = manager.find_multiple_versions()

    if multiple_versions:
        print(f"Found {len(multiple_versions)} libraries with multiple versions:\n")
        for lib_name, versions in multiple_versions.items():
            print(f"{lib_name}: {', '.join(versions)}")
    else:
        print("No libraries with multiple versions found.")

    # 3. Get a detailed summary
    print("\n3. Detailed Summary:")
    print("-" * 50)
    summary = manager.get_duplicate_summary()
    print(summary)

    # 4. Demonstrate dry-run resolution (if duplicates exist)
    if duplicates:
        print("\n4. Simulating duplicate resolution (dry-run):")
        print("-" * 50)
        for lib_name in list(duplicates.keys())[:1]:  # Just show one example
            print(f"\nResolving duplicates for: {lib_name}")
            result = manager.resolve_duplicates(lib_name, dry_run=True)

            if result["kept"]:
                print(f"Would keep: v{result['kept']['version']} at {result['kept']['path']}")

            if result["removed"]:
                print("Would remove:")
                for removed in result["removed"]:
                    print(f"  - v{removed['version']} at {removed['path']}")

            if result["errors"]:
                print("Errors:")
                for error in result["errors"]:
                    print(f"  - {error}")

    print("\n" + "=" * 50)
    print("Detection complete!")
    print("\nTo actually resolve duplicates, you can use:")
    print("  manager.resolve_duplicates(library_name, dry_run=False)")
    print()


if __name__ == "__main__":
    main()
