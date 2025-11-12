"""Tests for potentiometer component definitions."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


POTENTIOMETER_DIR = Path(__file__).resolve().parents[1] / "arduino_ide" / "component_library" / "potentiometers"

EXPECTED_RESISTANCES = {
    "1k",
    "2k",
    "5k",
    "10k",
    "20k",
    "50k",
    "100k",
    "1m",
}

EXPECTED_TAPERS = {"linear", "log", "anti_log"}
EXPECTED_MOUNTING_STYLES = {"pcb", "panel"}
REQUIRED_METADATA_KEYS = {
    "manufacturer",
    "resistance",
    "taper",
    "mounting_style",
    "shaft_style",
    "tolerance",
    "power_rating",
    "mechanical_travel",
    "mounting_details",
}


@pytest.fixture(scope="module")
def potentiometer_definitions() -> list[dict]:
    files = sorted(POTENTIOMETER_DIR.glob("*.json"))
    assert files, "No potentiometer component definitions found"

    components = []
    for path in files:
        with path.open("r", encoding="utf-8") as handle:
            components.append(json.load(handle))
    return components


def _split_identifier(identifier: str) -> tuple[str, str, str]:
    """Split a potentiometer identifier into resistance, taper, and mounting segments."""
    assert identifier.startswith("potentiometer_"), f"Unexpected identifier: {identifier}"
    rest = identifier[len("potentiometer_"):]

    for mount in EXPECTED_MOUNTING_STYLES:
        suffix = f"_{mount}"
        if rest.endswith(suffix):
            mounting = mount
            res_and_taper = rest[: -len(suffix)]
            break
    else:  # pragma: no cover - defensive guard
        raise AssertionError(f"Could not determine mounting from {identifier}")

    resistance, taper = res_and_taper.split("_", 1)
    return resistance, taper, mounting


def test_complete_combination_grid(potentiometer_definitions: list[dict]) -> None:
    """Ensure every resistance/taper/mounting combination exists."""
    assert len(potentiometer_definitions) == 48, "Unexpected number of potentiometer definitions"

    combos = {_split_identifier(comp["id"]) for comp in potentiometer_definitions}

    expected_combos = {
        (res, taper, mount)
        for res in EXPECTED_RESISTANCES
        for taper in EXPECTED_TAPERS
        for mount in EXPECTED_MOUNTING_STYLES
    }

    assert combos == expected_combos


def test_potentiometer_pin_layout(potentiometer_definitions: list[dict]) -> None:
    """Potentiometers should expose three analog pins with consistent labels."""
    for component in potentiometer_definitions:
        pins = component.get("pins", [])
        assert len(pins) == 3, f"{component['id']} should define three pins"
        labels = [pin["label"] for pin in pins]
        assert labels == ["CW", "Wiper", "CCW"], f"Unexpected pin order in {component['id']}"
        for pin in pins:
            assert pin["pin_type"] == "analog", f"{component['id']} should use analog pins"
            assert isinstance(pin.get("position"), list) and len(pin["position"]) == 2


def test_metadata_fields_present(potentiometer_definitions: list[dict]) -> None:
    """Metadata should include mechanical and mounting information."""
    for component in potentiometer_definitions:
        metadata = component.get("metadata", {})
        missing = REQUIRED_METADATA_KEYS.difference(metadata)
        assert not missing, f"{component['id']} metadata missing: {sorted(missing)}"

        resistance_code, taper_code, mounting_code = _split_identifier(component["id"])
        assert resistance_code in EXPECTED_RESISTANCES
        assert taper_code in EXPECTED_TAPERS

        normalized_taper = metadata["taper"].lower().replace("-", "_")
        assert normalized_taper in {"linear", "logarithmic", "anti_logarithmic"}

        assert metadata["mounting_style"].lower() == mounting_code
