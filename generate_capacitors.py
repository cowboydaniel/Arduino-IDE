#!/usr/bin/env python3
"""Generate capacitor component JSON definitions for the IDE library."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

OUTPUT_DIR = Path("arduino_ide/component_library/capacitors")

CAPACITOR_TYPES: List[Dict[str, object]] = [
    {
        "key": "ceramic",
        "name": "Ceramic",
        "dielectric": "X7R Ceramic",
        "tolerance": "±5%",
        "esr": "0.05Ω @ 100kHz",
        "package": "Radial Lead 5mm",
        "polarized": False,
        "dimensions": {"width": 40, "height": 20},
        "pin_labels": ("1", "2"),
    },
    {
        "key": "electrolytic",
        "name": "Aluminum Electrolytic",
        "dielectric": "Aluminum Oxide",
        "tolerance": "±20%",
        "esr": "0.2Ω @ 120Hz",
        "package": "Radial Can 5x11mm",
        "polarized": True,
        "dimensions": {"width": 32, "height": 48},
        "pin_labels": ("+", "-"),
    },
    {
        "key": "tantalum",
        "name": "Tantalum",
        "dielectric": "Tantalum Pentoxide",
        "tolerance": "±10%",
        "esr": "0.15Ω @ 100kHz",
        "package": "SMD A-Case",
        "polarized": True,
        "dimensions": {"width": 34, "height": 40},
        "pin_labels": ("+", "-"),
    },
    {
        "key": "film",
        "name": "Film",
        "dielectric": "Polypropylene Film",
        "tolerance": "±5%",
        "esr": "0.03Ω @ 10kHz",
        "package": "Radial Box 7.5mm",
        "polarized": False,
        "dimensions": {"width": 42, "height": 22},
        "pin_labels": ("1", "2"),
    },
    {
        "key": "polyester",
        "name": "Polyester",
        "dielectric": "Polyester Film",
        "tolerance": "±10%",
        "esr": "0.08Ω @ 10kHz",
        "package": "Axial Lead 5mm",
        "polarized": False,
        "dimensions": {"width": 45, "height": 18},
        "pin_labels": ("1", "2"),
    },
]

VOLTAGE_CLASSES: Iterable[str] = ["6.3V", "10V", "16V", "25V", "35V", "50V", "100V", "250V"]

CAPACITANCE_VALUES: List[Dict[str, str]] = [
    # pF range (6 values)
    {"value": "1.0", "unit": "pF"},
    {"value": "4.7", "unit": "pF"},
    {"value": "10", "unit": "pF"},
    {"value": "22", "unit": "pF"},
    {"value": "47", "unit": "pF"},
    {"value": "100", "unit": "pF"},
    # nF range (9 values)
    {"value": "0.47", "unit": "nF"},
    {"value": "1.0", "unit": "nF"},
    {"value": "2.2", "unit": "nF"},
    {"value": "4.7", "unit": "nF"},
    {"value": "10", "unit": "nF"},
    {"value": "22", "unit": "nF"},
    {"value": "47", "unit": "nF"},
    {"value": "68", "unit": "nF"},
    {"value": "100", "unit": "nF"},
    # µF range (13 values)
    {"value": "0.47", "unit": "µF"},
    {"value": "1.0", "unit": "µF"},
    {"value": "2.2", "unit": "µF"},
    {"value": "3.3", "unit": "µF"},
    {"value": "4.7", "unit": "µF"},
    {"value": "6.8", "unit": "µF"},
    {"value": "10", "unit": "µF"},
    {"value": "22", "unit": "µF"},
    {"value": "33", "unit": "µF"},
    {"value": "47", "unit": "µF"},
    {"value": "68", "unit": "µF"},
    {"value": "100", "unit": "µF"},
    {"value": "220", "unit": "µF"},
]


def format_capacitance(value: str, unit: str) -> str:
    """Return a printable capacitance string with unit suffix."""
    if unit == "µF":
        unit_symbol = "µF"
    else:
        unit_symbol = unit

    if value.endswith(".0"):
        magnitude = value[:-2]
    else:
        magnitude = value

    return f"{magnitude}{unit_symbol}"


def normalize_for_id(value: str) -> str:
    """Normalize a capacitance or voltage string for use in an ID."""
    normalized = value.lower()
    normalized = normalized.replace("µ", "u")
    normalized = normalized.replace("v", "v")
    normalized = normalized.replace(".", "p")
    normalized = normalized.replace("/", "")
    normalized = normalized.replace(" ", "")
    return normalized


def create_pins(cap_type: Dict[str, object]) -> List[Dict[str, object]]:
    """Create pin definitions for a capacitor type."""
    width = cap_type["dimensions"]["width"]
    height = cap_type["dimensions"]["height"]

    if cap_type["polarized"]:
        positive_id, negative_id = "positive", "negative"
        positive_label, negative_label = cap_type["pin_labels"]
        return [
            {
                "id": positive_id,
                "label": positive_label,
                "pin_type": "power",
                "position": [width / 2, 0],
            },
            {
                "id": negative_id,
                "label": negative_label,
                "pin_type": "ground",
                "position": [width / 2, height],
            },
        ]

    label_a, label_b = cap_type["pin_labels"]
    return [
        {
            "id": "pin1",
            "label": label_a,
            "pin_type": "power",
            "position": [0, height / 2],
        },
        {
            "id": "pin2",
            "label": label_b,
            "pin_type": "power",
            "position": [width, height / 2],
        },
    ]


def generate_capacitor_components() -> int:
    """Generate all capacitor component files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    component_count = 0

    for cap_type in CAPACITOR_TYPES:
        for voltage in VOLTAGE_CLASSES:
            voltage_label = normalize_for_id(voltage)
            for value_info in CAPACITANCE_VALUES:
                display_value = format_capacitance(value_info["value"], value_info["unit"])
                value_label = normalize_for_id(display_value)

                component_id = f"capacitor_{cap_type['key']}_{value_label}_{voltage_label}"
                component_name = f"{display_value} {voltage} {cap_type['name']} Capacitor"
                description = (
                    f"{display_value} {cap_type['name']} capacitor rated for {voltage} "
                    f"with {cap_type['tolerance']} tolerance."
                )

                component = {
                    "id": component_id,
                    "name": component_name,
                    "component_type": "capacitor",
                    "description": description,
                    "width": cap_type["dimensions"]["width"],
                    "height": cap_type["dimensions"]["height"],
                    "pins": create_pins(cap_type),
                    "metadata": {
                        "dielectric_type": cap_type["dielectric"],
                        "capacitance": display_value,
                        "tolerance": cap_type["tolerance"],
                        "voltage_rating": voltage,
                        "esr": cap_type["esr"],
                        "package": cap_type["package"],
                        "polarized": cap_type["polarized"],
                    },
                }

                output_path = OUTPUT_DIR / f"{component_id}.json"
                with output_path.open("w", encoding="utf-8") as fh:
                    json.dump(component, fh, indent=2)
                    fh.write("\n")

                component_count += 1

    return component_count


def main() -> None:
    count = generate_capacitor_components()
    print(f"✓ Generated {count} capacitor components in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
