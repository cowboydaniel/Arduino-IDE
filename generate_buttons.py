#!/usr/bin/env python3
"""Generate button and switch component definitions."""

import json
from pathlib import Path
import re

BUTTON_DIR = Path("arduino_ide/component_library/buttons")
BUTTON_DIR.mkdir(parents=True, exist_ok=True)

COLORS = [
    ("black", "Black"),
    ("red", "Red"),
    ("blue", "Blue"),
    ("green", "Green"),
    ("yellow", "Yellow"),
]

PIN_TEMPLATES = {
    "spst": [
        {"id": "pin1", "label": "1", "pin_type": "digital", "position": [0.25, 0.9]},
        {"id": "pin2", "label": "2", "pin_type": "digital", "position": [0.75, 0.9]},
    ],
    "spdt": [
        {"id": "common", "label": "COM", "pin_type": "digital", "position": [0.5, 0.1]},
        {"id": "normally_open", "label": "NO", "pin_type": "digital", "position": [0.2, 0.9]},
        {"id": "normally_closed", "label": "NC", "pin_type": "digital", "position": [0.8, 0.9]},
    ],
    "dpdt": [
        {"id": "pole1_common", "label": "P1 COM", "pin_type": "digital", "position": [0.25, 0.1]},
        {"id": "pole1_no", "label": "P1 NO", "pin_type": "digital", "position": [0.25, 0.5]},
        {"id": "pole1_nc", "label": "P1 NC", "pin_type": "digital", "position": [0.25, 0.9]},
        {"id": "pole2_common", "label": "P2 COM", "pin_type": "digital", "position": [0.75, 0.1]},
        {"id": "pole2_no", "label": "P2 NO", "pin_type": "digital", "position": [0.75, 0.5]},
        {"id": "pole2_nc", "label": "P2 NC", "pin_type": "digital", "position": [0.75, 0.9]},
    ],
}


FAMILIES = [
    {
        "key": "tactile",
        "name": "Tactile Pushbutton",
        "description": "Low-profile tactile switch with momentary action, ideal for user input and reset buttons.",
        "sizes": {
            "6x6mm": {"width": 70, "height": 70, "travel": "0.25mm"},
            "6x3mm": {"width": 70, "height": 60, "travel": "0.2mm"},
            "12x12mm": {"width": 100, "height": 100, "travel": "0.35mm"},
        },
        "mountings": {
            "through_hole": "Through-Hole",
            "surface_mount": "Surface Mount",
        },
        "actuation_forces": {
            "160gf": "Light touch",
            "260gf": "Firm touch",
        },
        "pole_configurations": {
            "spst": {
                "template": "spst",
                "pole_and_throw": "SPST (Normally Open)",
                "contact_configuration": "Normally open tactile contacts",
                "electrical_rating": "12VDC 50mA",
                "mechanical_life": "100,000 cycles",
            }
        },
        "colors": COLORS,
    },
    {
        "key": "momentary",
        "name": "Momentary Pushbutton",
        "description": "Panel or PCB mount momentary pushbutton with short travel actuator and tactile feedback.",
        "sizes": {
            "12mm_panel": {"width": 110, "height": 150, "travel": "1.5mm"},
            "16mm_panel": {"width": 120, "height": 170, "travel": "2.0mm"},
            "19mm_panel": {"width": 130, "height": 190, "travel": "2.5mm"},
        },
        "mountings": {
            "panel_mount": "Panel Mount",
            "pcb_mount": "PCB Mount",
        },
        "actuation_forces": {
            "220gf": "Medium travel",
        },
        "pole_configurations": {
            "spdt": {
                "template": "spdt",
                "pole_and_throw": "SPDT (On-On)",
                "contact_configuration": "Single pole double throw momentary action",
                "electrical_rating": "30VDC 300mA",
                "mechanical_life": "50,000 cycles",
            }
        },
        "colors": COLORS,
    },
    {
        "key": "toggle",
        "name": "Toggle Switch",
        "description": "Robust lever toggle switch available for panel or PCB mounting with maintained positions.",
        "sizes": {
            "miniature": {"width": 120, "height": 200, "travel": "2-position"},
            "standard": {"width": 140, "height": 220, "travel": "3-position"},
        },
        "mountings": {
            "panel_mount": "Panel Mount",
            "pcb_right_angle": "PCB Right-Angle",
            "pcb_vertical": "PCB Vertical",
        },
        "actuation_forces": {
            "1.8Ncm": "Maintained toggle torque",
        },
        "pole_configurations": {
            "dpdt": {
                "template": "dpdt",
                "pole_and_throw": "DPDT (On-On)",
                "contact_configuration": "Dual pole double throw maintained",
                "electrical_rating": "250VAC 3A",
                "mechanical_life": "30,000 cycles",
            }
        },
        "colors": COLORS,
    },
]


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def scale_pins(template_key: str, width: float, height: float):
    template = PIN_TEMPLATES[template_key]
    scaled = []
    for pin in template:
        x = round(pin["position"][0] * width, 2)
        y = round(pin["position"][1] * height, 2)
        scaled.append(
            {
                "id": pin["id"],
                "label": pin["label"],
                "pin_type": pin["pin_type"],
                "position": [x, y],
            }
        )
    return scaled


def build_component(family: dict, size_key: str, mounting_key: str, color_key: str, color_name: str,
                    force_value: str, force_desc: str, pole_key: str, pole_data: dict) -> dict:
    size_info = family["sizes"][size_key]
    mounting_name = family["mountings"][mounting_key]

    width = size_info["width"]
    height = size_info["height"]

    pins = scale_pins(pole_data["template"], width, height)

    force_slug = slugify(force_value)
    component_id = "_".join(
        [
            "button",
            family["key"],
            slugify(size_key),
            slugify(mounting_key),
            slugify(color_key),
            force_slug,
            slugify(pole_key),
        ]
    )

    color_title = color_name
    size_label = size_key.replace("_", " ")
    mounting_label = mounting_name
    pole_label = pole_data["pole_and_throw"]

    name = f"{color_title} {family['name']} ({size_label}, {mounting_label}, {pole_label})"

    description = (
        f"{family['description']} Features {pole_label.lower()} contacts with a {force_value} actuation force "
        f"and {mounting_label.lower()} hardware in a {color_title.lower()} finish."
    )

    metadata = {
        "family": family["name"],
        "size": size_label,
        "mounting_style": mounting_label,
        "actuator_color": color_title,
        "actuation_force": f"{force_value} ({force_desc})",
        "pole_and_throw": pole_label,
        "contact_configuration": pole_data["contact_configuration"],
        "electrical_rating": pole_data["electrical_rating"],
        "mechanical_life": pole_data["mechanical_life"],
    }

    if "travel" in size_info:
        metadata["travel"] = size_info["travel"]

    component = {
        "id": component_id,
        "name": name,
        "component_type": "button",
        "description": description,
        "width": width,
        "height": height,
        "pins": pins,
        "metadata": metadata,
    }

    return component


def main():
    # Remove existing button JSON files
    for existing in BUTTON_DIR.glob("*.json"):
        existing.unlink()

    generated = []

    for family in FAMILIES:
        for size_key in family["sizes"].keys():
            for mounting_key in family["mountings"].keys():
                for force_value, force_desc in family["actuation_forces"].items():
                    for color_key, color_name in family["colors"]:
                        for pole_key, pole_data in family["pole_configurations"].items():
                            component = build_component(
                                family,
                                size_key,
                                mounting_key,
                                color_key,
                                color_name,
                                force_value,
                                force_desc,
                                pole_key,
                                pole_data,
                            )
                            generated.append(component)

    for component in generated:
        path = BUTTON_DIR / f"{component['id']}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(component, f, indent=2)

    print(f"Generated {len(generated)} button definitions in {BUTTON_DIR}.")


if __name__ == "__main__":
    main()
