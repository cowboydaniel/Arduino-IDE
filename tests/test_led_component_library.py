"""Tests for generated LED component library entries."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LED_DIR = Path(__file__).resolve().parents[1] / "arduino_ide" / "component_library" / "leds"
REQUIRED_METADATA_FIELDS = {"color", "size", "forward_voltage", "forward_current", "wavelength", "brightness"}


@lru_cache(maxsize=1)
def load_led_components():
    led_files = sorted(LED_DIR.glob("led_*.json"))
    components = []
    for path in led_files:
        with path.open("r", encoding="utf-8") as handle:
            components.append((path, json.load(handle)))
    return components


def test_led_component_count():
    components = load_led_components()
    assert len(components) == 420, "Expected exactly 420 LED component definitions"


def test_led_metadata_fields_present():
    components = load_led_components()
    for path, data in components:
        assert data["component_type"] == "led", f"{path.name} has unexpected component_type"
        metadata = data.get("metadata", {})
        missing = REQUIRED_METADATA_FIELDS - metadata.keys()
        assert not missing, f"{path.name} missing metadata fields: {sorted(missing)}"


def test_led_pin_layout_matches_type():
    components = load_led_components()
    for path, data in components:
        pin_count = len(data.get("pins", []))
        led_id = data["id"]
        metadata_type = data.get("metadata", {}).get("led_type", "")
        metadata_color = data.get("metadata", {}).get("color", "")

        if "rgb" in led_id or metadata_type == "RGB" or metadata_color == "RGB":
            assert pin_count == 4, f"RGB LED {path.name} should expose four pins"
        elif "bi_color" in led_id or metadata_type == "Bi-Color" or "Bi-Color" in metadata_color:
            assert pin_count == 3, f"Bi-color LED {path.name} should expose three pins"
        else:
            assert pin_count == 2, f"Single-color LED {path.name} should expose two pins"
