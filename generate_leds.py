#!/usr/bin/env python3
"""Generate LED component definitions for the component library."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Data tables describing the LED combinations we want to generate.
# ---------------------------------------------------------------------------

COLORS: List[Dict[str, object]] = [
    {
        "key": "red",
        "display": "Red",
        "forward_voltage": (1.8, 2.2),
        "forward_current_ma": 20,
        "wavelength": "620-630nm",
        "brightness_mcd": (800, 1500),
        "description": "classic red indicator color",
    },
    {
        "key": "green",
        "display": "Green",
        "forward_voltage": (2.8, 3.2),
        "forward_current_ma": 20,
        "wavelength": "520-530nm",
        "brightness_mcd": (900, 1800),
        "description": "high-visibility green emission",
    },
    {
        "key": "blue",
        "display": "Blue",
        "forward_voltage": (3.0, 3.4),
        "forward_current_ma": 20,
        "wavelength": "460-470nm",
        "brightness_mcd": (600, 1400),
        "description": "deep blue output",
    },
    {
        "key": "yellow",
        "display": "Yellow",
        "forward_voltage": (2.0, 2.4),
        "forward_current_ma": 20,
        "wavelength": "585-595nm",
        "brightness_mcd": (900, 1500),
        "description": "bright amber-yellow emission",
    },
    {
        "key": "amber",
        "display": "Amber",
        "forward_voltage": (2.0, 2.4),
        "forward_current_ma": 20,
        "wavelength": "600-610nm",
        "brightness_mcd": (900, 1600),
        "description": "amber indicator output",
    },
    {
        "key": "orange",
        "display": "Orange",
        "forward_voltage": (2.0, 2.3),
        "forward_current_ma": 20,
        "wavelength": "600-610nm",
        "brightness_mcd": (950, 1700),
        "description": "orange indicator color",
    },
    {
        "key": "white",
        "display": "White",
        "forward_voltage": (3.0, 3.4),
        "forward_current_ma": 20,
        "wavelength": "CCT 5600K",
        "brightness_mcd": (3500, 5500),
        "description": "neutral white phosphor LED",
    },
    {
        "key": "warm_white",
        "display": "Warm White",
        "forward_voltage": (2.9, 3.3),
        "forward_current_ma": 20,
        "wavelength": "CCT 3000K",
        "brightness_mcd": (3200, 5000),
        "description": "warm white illumination",
    },
    {
        "key": "cool_white",
        "display": "Cool White",
        "forward_voltage": (3.0, 3.4),
        "forward_current_ma": 20,
        "wavelength": "CCT 6500K",
        "brightness_mcd": (3600, 5600),
        "description": "cool white output",
    },
    {
        "key": "uv",
        "display": "Ultraviolet",
        "forward_voltage": (3.2, 3.6),
        "forward_current_ma": 20,
        "wavelength": "395-405nm",
        "brightness_mcd": (1200, 1800),
        "description": "near-UV emission",
    },
    {
        "key": "infrared",
        "display": "Infrared",
        "forward_voltage": (1.4, 1.7),
        "forward_current_ma": 20,
        "wavelength": "940nm",
        "brightness_mcd": (0, 0),
        "description": "940nm IR emitter",
    },
    {
        "key": "cyan",
        "display": "Cyan",
        "forward_voltage": (2.9, 3.3),
        "forward_current_ma": 20,
        "wavelength": "500-510nm",
        "brightness_mcd": (800, 1600),
        "description": "cyan indicator output",
    },
    {
        "key": "rgb",
        "display": "RGB",
        "forward_voltage_channels": {
            "R": (1.8, 2.2),
            "G": (2.9, 3.2),
            "B": (3.0, 3.3),
        },
        "forward_current_ma": 20,
        "wavelength_channels": {
            "R": "620-630nm",
            "G": "520-530nm",
            "B": "460-470nm",
        },
        "brightness_channels": {
            "R": (700, 1100),
            "G": (1200, 1800),
            "B": (400, 700),
        },
        "pin_layout": "four_pin",
        "description": "tri-color RGB package",
    },
    {
        "key": "bi_color_red_green",
        "display": "Bi-Color Red/Green",
        "forward_voltage_channels": {
            "Red": (1.8, 2.2),
            "Green": (2.9, 3.2),
        },
        "forward_current_ma": 20,
        "wavelength_channels": {
            "Red": "620-630nm",
            "Green": "520-530nm",
        },
        "brightness_channels": {
            "Red": (900, 1400),
            "Green": (1100, 1800),
        },
        "pin_layout": "three_pin",
        "description": "dual-color indicator",
    },
]

SIZES: List[Dict[str, object]] = [
    {"key": "3mm", "display": "3mm", "width": 20, "height": 40, "mount": "THT"},
    {"key": "5mm", "display": "5mm", "width": 30, "height": 50, "mount": "THT"},
    {"key": "8mm", "display": "8mm", "width": 36, "height": 56, "mount": "THT"},
    {"key": "10mm", "display": "10mm", "width": 44, "height": 64, "mount": "THT"},
    {"key": "1206", "display": "SMD 1206", "width": 42, "height": 24, "mount": "SMD"},
    {"key": "3528", "display": "SMD 3528", "width": 48, "height": 28, "mount": "SMD"},
]

LED_TYPES: List[Dict[str, object]] = [
    {
        "key": "standard",
        "display": "Standard",
        "description": "Standard clear lens indicator LED.",
        "brightness_scale": 1.0,
        "forward_voltage_offset": 0.0,
        "forward_current_ma": 20,
        "metadata": {
            "lens_type": "Clear",
            "viewing_angle": "25°",
            "notes": "General-purpose indicator LED.",
        },
    },
    {
        "key": "diffused",
        "display": "Diffused",
        "description": "Diffused epoxy lens LED with wide viewing angle.",
        "brightness_scale": 0.65,
        "forward_voltage_offset": 0.0,
        "forward_current_ma": 20,
        "metadata": {
            "lens_type": "Diffused",
            "viewing_angle": "60°",
            "notes": "Even light distribution through frosted lens.",
        },
    },
    {
        "key": "high_brightness",
        "display": "High Brightness",
        "description": "High-intensity LED for daylight visibility.",
        "brightness_scale": 1.8,
        "forward_voltage_offset": 0.1,
        "forward_current_ma": 30,
        "metadata": {
            "lens_type": "Clear",
            "viewing_angle": "20°",
            "notes": "Designed for maximum luminous output.",
        },
    },
    {
        "key": "rgb",
        "display": "RGB",
        "description": "Multi-die LED with separate red, green, and blue channels.",
        "brightness_scale": 1.0,
        "forward_voltage_offset": 0.05,
        "forward_current_ma": 20,
        "current_per_channel": True,
        "pin_layout": "four_pin",
        "metadata": {
            "lens_type": "Clear",
            "viewing_angle": "40°",
            "notes": "Common anode tri-color LED.",
        },
    },
    {
        "key": "bi_color",
        "display": "Bi-Color",
        "description": "Dual-die LED allowing two colors from a shared package.",
        "brightness_scale": 0.85,
        "forward_voltage_offset": 0.0,
        "forward_current_ma": 20,
        "current_per_channel": True,
        "pin_layout": "three_pin",
        "metadata": {
            "lens_type": "Diffused",
            "viewing_angle": "45°",
            "notes": "Common anode dual-color configuration.",
        },
    },
]

OUTPUT_DIR = Path("arduino_ide/component_library/leds")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def format_voltage(min_v: float, max_v: float) -> str:
    if abs(min_v - max_v) < 1e-3:
        return f"{min_v:.1f}V"
    return f"{min_v:.1f}-{max_v:.1f}V"


def format_brightness(min_mcd: float, max_mcd: float) -> str:
    if max_mcd <= 0:
        return "N/A"
    if abs(min_mcd - max_mcd) < 1e-3:
        return f"{int(round(max_mcd))}mcd"
    return f"{int(round(min_mcd))}-{int(round(max_mcd))}mcd"


def calculate_forward_voltage(color: Dict[str, object], led_type: Dict[str, object]) -> str:
    offset = float(led_type.get("forward_voltage_offset", 0.0))
    if "forward_voltage_channels" in color:
        parts = []
        for channel, (min_v, max_v) in color["forward_voltage_channels"].items():
            parts.append(f"{channel}: {format_voltage(min_v + offset, max_v + offset)}")
        return " / ".join(parts)
    min_v, max_v = color["forward_voltage"]
    return format_voltage(min_v + offset, max_v + offset)


def calculate_forward_current(color: Dict[str, object], led_type: Dict[str, object]) -> str:
    current = int(led_type.get("forward_current_ma", color.get("forward_current_ma", 20)))
    per_channel = bool(led_type.get("current_per_channel", False) or "forward_voltage_channels" in color)
    if per_channel:
        return f"{current}mA per channel"
    return f"{current}mA"


def calculate_brightness(color: Dict[str, object], led_type: Dict[str, object]) -> str:
    scale = float(led_type.get("brightness_scale", 1.0))
    if "brightness_channels" in color:
        parts = []
        for channel, (min_mcd, max_mcd) in color["brightness_channels"].items():
            min_scaled = min_mcd * scale
            max_scaled = max_mcd * scale
            parts.append(f"{channel}: {format_brightness(min_scaled, max_scaled)}")
        return " / ".join(parts)
    min_mcd, max_mcd = color["brightness_mcd"]
    min_scaled = min_mcd * scale
    max_scaled = max_mcd * scale
    return format_brightness(min_scaled, max_scaled)


def resolve_wavelength(color: Dict[str, object]) -> str:
    if "wavelength_channels" in color:
        parts = [f"{channel}: {value}" for channel, value in color["wavelength_channels"].items()]
        return " / ".join(parts)
    return str(color["wavelength"])


def resolve_pin_layout(color: Dict[str, object], led_type: Dict[str, object]) -> str:
    if led_type.get("pin_layout") == "four_pin" or color.get("pin_layout") == "four_pin":
        return "four_pin"
    if led_type.get("pin_layout") == "three_pin" or color.get("pin_layout") == "three_pin":
        return "three_pin"
    return "two_pin"


def create_pins(layout: str, width: int, height: int, color_key: str, type_key: str) -> List[Dict[str, object]]:
    center_x = width / 2
    if layout == "three_pin":
        labels = ("C1", "C2")
        if "bi_color" in color_key or type_key == "bi_color":
            labels = ("R", "G")
        return [
            {
                "id": "common_anode",
                "label": "+",
                "pin_type": "power",
                "position": [round(center_x), 0],
            },
            {
                "id": "cathode_a",
                "label": labels[0],
                "pin_type": "ground",
                "position": [round(width * 0.25), height],
            },
            {
                "id": "cathode_b",
                "label": labels[1],
                "pin_type": "ground",
                "position": [round(width * 0.75), height],
            },
        ]
    if layout == "four_pin":
        labels = ("1", "2", "3")
        if "rgb" in color_key or type_key == "rgb":
            labels = ("R", "G", "B")
        return [
            {
                "id": "common_anode",
                "label": "+",
                "pin_type": "power",
                "position": [round(center_x), 0],
            },
            {
                "id": "cathode_1",
                "label": labels[0],
                "pin_type": "ground",
                "position": [round(width * 0.2), height],
            },
            {
                "id": "cathode_2",
                "label": labels[1],
                "pin_type": "ground",
                "position": [round(center_x), height],
            },
            {
                "id": "cathode_3",
                "label": labels[2],
                "pin_type": "ground",
                "position": [round(width * 0.8), height],
            },
        ]
    # Default two-pin layout.
    return [
        {
            "id": "anode",
            "label": "+",
            "pin_type": "power",
            "position": [round(center_x), 0],
        },
        {
            "id": "cathode",
            "label": "-",
            "pin_type": "ground",
            "position": [round(center_x), height],
        },
    ]


def build_metadata(color: Dict[str, object], size: Dict[str, object], led_type: Dict[str, object]) -> Dict[str, object]:
    metadata = {
        "manufacturer": "Generic",
        "color": color["display"],
        "size": size["display"],
        "forward_voltage": calculate_forward_voltage(color, led_type),
        "forward_current": calculate_forward_current(color, led_type),
        "wavelength": resolve_wavelength(color),
        "brightness": calculate_brightness(color, led_type),
        "mounting_type": size["mount"],
        "led_type": led_type["display"],
        "package": f"{size['display']} {size['mount']} LED",
    }
    metadata.update(led_type.get("metadata", {}))
    if "description" in color:
        metadata.setdefault("notes", color["description"])
    return metadata


def build_description(color: Dict[str, object], size: Dict[str, object], led_type: Dict[str, object]) -> str:
    base = led_type["description"]
    details = color.get("description", "high quality LED emission")
    size_info = f"{size['display']} package"
    return f"{base} This {details} comes in a {size_info}."


def generate_led_components() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for color in COLORS:
        for size in SIZES:
            for led_type in LED_TYPES:
                component_id = f"led_{color['key']}_{size['key']}_{led_type['key']}"
                filename = OUTPUT_DIR / f"{component_id}.json"
                layout = resolve_pin_layout(color, led_type)
                pins = create_pins(layout, int(size["width"]), int(size["height"]), str(color["key"]), str(led_type["key"]))
                component = {
                    "id": component_id,
                    "name": f"{color['display']} {size['display']} {led_type['display']} LED",
                    "component_type": "led",
                    "description": build_description(color, size, led_type),
                    "width": int(size["width"]),
                    "height": int(size["height"]),
                    "pins": pins,
                    "metadata": build_metadata(color, size, led_type),
                }
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(component, f, indent=2, ensure_ascii=False)
                count += 1
    return count


def main() -> None:
    print("Generating LED component definitions...")
    count = generate_led_components()
    print(f"✓ Generated {count} LED components in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
