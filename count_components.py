#!/usr/bin/env python3
"""
Count the actual components in the library
"""

from pathlib import Path

def count_components():
    """Count total components by scanning the component library directories"""

    counts = {}

    # Base path to component library
    base_path = Path("arduino_ide/component_library")

    if not base_path.exists():
        print(f"Warning: Component library path '{base_path}' not found")
        return counts

    # Category mapping for better display names
    category_names = {
        "arduino_boards": "Arduino Boards",
        "leds": "LEDs",
        "resistors": "Resistors",
        "capacitors": "Capacitors",
        "transistors": "Transistors",
        "ics": "ICs",
        "sensors": "Sensors",
        "motors": "Motors",
        "buttons": "Buttons & Switches",
        "potentiometers": "Potentiometers",
        "breadboards": "Breadboards"
    }

    # Count JSON files in each category directory
    for category_dir in sorted(base_path.iterdir()):
        if category_dir.is_dir():
            # Count all JSON files recursively in this category
            json_count = len(list(category_dir.glob("**/*.json")))

            if json_count > 0:
                # Use friendly name if available, otherwise use directory name
                category_name = category_names.get(category_dir.name, category_dir.name.replace("_", " ").title())
                counts[category_name] = json_count

    return counts

def main():
    print("=" * 60)
    print("CIRCUIT COMPONENT LIBRARY - COMPONENT COUNT")
    print("=" * 60)

    counts = count_components()

    total = 0
    for category, count in counts.items():
        print(f"{category:30s}: {count:5,d}")
        total += count

    print("=" * 60)
    print(f"{'TOTAL COMPONENTS':30s}: {total:5,d}")
    print("=" * 60)

    if total >= 5000:
        print(f"\n✓ SUCCESS! Generated {total:,} components (target: 5,000+)")
    else:
        print(f"\n✗ WARNING: Only {total:,} components (target: 5,000+)")

if __name__ == "__main__":
    main()
