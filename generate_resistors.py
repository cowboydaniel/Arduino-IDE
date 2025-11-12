#!/usr/bin/env python3
"""
Example script to generate resistor component files programmatically

This demonstrates how to create hundreds or thousands of component files
automatically instead of manually creating each JSON file.
"""

import json
import os
from pathlib import Path

def generate_resistor_components():
    """Generate resistor components for E24 series"""

    output_dir = Path("arduino_ide/component_library/resistors")
    output_dir.mkdir(parents=True, exist_ok=True)

    # E24 series resistor values (precision)
    e24_values = [10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 43, 47, 51, 56, 62, 68, 75, 82, 91]

    wattages = ["1/8W", "1/4W", "1/2W", "1W", "2W"]
    tolerances = ["1%", "5%", "10%"]

    component_count = 0

    # Generate resistors from 1Ω to 10MΩ
    for multiplier, unit_name, unit_symbol in [
        (1, "Ohm", "Ω"),
        (10, "Ohm", "Ω"),
        (100, "Ohm", "Ω"),
        (1000, "kΩ", "k"),
        (10000, "kΩ", "k"),
        (100000, "kΩ", "k"),
        (1000000, "MΩ", "M")
    ]:
        for base_value in e24_values:
            value = base_value * multiplier

            for wattage in wattages:
                for tolerance in tolerances:
                    # Calculate display value
                    if value < 1000:
                        display_value = f"{value}Ω"
                    elif value < 1000000:
                        display_value = f"{value / 1000}kΩ"
                    else:
                        display_value = f"{value / 1000000}MΩ"

                    # Create component ID
                    resistor_id = f"resistor_{value}_{wattage.replace('/', 'div')}_{tolerance.replace('%', 'pct')}"

                    # Color code calculation (simplified)
                    # This is a basic implementation - you'd want to expand this
                    color_codes = {
                        0: "Black", 1: "Brown", 2: "Red", 3: "Orange", 4: "Yellow",
                        5: "Green", 6: "Blue", 7: "Violet", 8: "Gray", 9: "White"
                    }

                    # Create component data
                    component = {
                        "id": resistor_id,
                        "name": f"{display_value} {wattage} {tolerance} Resistor",
                        "component_type": "resistor",
                        "description": f"{display_value} {wattage} carbon film resistor with {tolerance} tolerance",
                        "width": 60,
                        "height": 20,
                        "pins": [
                            {
                                "id": "pin1",
                                "label": "1",
                                "pin_type": "power",
                                "position": [0, 10]
                            },
                            {
                                "id": "pin2",
                                "label": "2",
                                "pin_type": "power",
                                "position": [60, 10]
                            }
                        ],
                        "metadata": {
                            "manufacturer": "Generic",
                            "resistance": display_value,
                            "tolerance": tolerance,
                            "power_rating": wattage,
                            "type": "Carbon Film",
                            "temperature_coefficient": "±100ppm/°C",
                            "max_working_voltage": "250V" if wattage in ["1/8W", "1/4W"] else "500V"
                        }
                    }

                    # Write to file
                    filename = output_dir / f"{resistor_id}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(component, f, indent=2)

                    component_count += 1

    print(f"✓ Generated {component_count} resistor components in {output_dir}")

def main():
    print("=" * 70)
    print("RESISTOR COMPONENT GENERATOR")
    print("=" * 70)
    print()
    print("This script generates E24 series resistor components.")
    print("Components will be saved to: arduino_ide/component_library/resistors/")
    print()

    answer = input("Generate resistor components? (y/N): ")

    if answer.lower() in ['y', 'yes']:
        generate_resistor_components()
        print()
        print("Done! Restart the Arduino IDE to see the new components.")
    else:
        print("Cancelled.")

if __name__ == "__main__":
    main()
