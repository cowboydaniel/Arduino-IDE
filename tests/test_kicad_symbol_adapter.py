"""Tests for the KiCAD symbol adapter and CircuitService integration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from arduino_ide.services.kicad_symbol_adapter import KiCADSymbolAdapter
from arduino_ide.services.circuit_service import CircuitService

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "kicad"


def test_kicad_adapter_discovers_reference_symbols(tmp_path):
    adapter = KiCADSymbolAdapter(search_paths=[FIXTURE_DIR], cache_dir=tmp_path / "cache")
    components = adapter.load_components()

    ids = {component.id for component in components}
    assert "reference_symbols:R_Generic" in ids
    assert "reference_symbols:C_Generic" in ids

    resistor = next(component for component in components if component.id.endswith("R_Generic"))
    assert resistor.metadata.get("library") == "reference_symbols"
    assert "res" in resistor.metadata.get("keywords", [])
    assert resistor.datasheet_url == "https://example.com/r"
    assert len(resistor.pins) == 2


def test_kicad_adapter_refreshes_cache_when_library_changes(tmp_path):
    libs_dir = tmp_path / "libs"
    libs_dir.mkdir()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    fixture_path = FIXTURE_DIR / "reference_symbols.kicad_sym"
    working_lib = libs_dir / fixture_path.name
    working_lib.write_text(fixture_path.read_text(), encoding="utf-8")

    adapter = KiCADSymbolAdapter(search_paths=[libs_dir], cache_dir=cache_dir)
    first_pass = adapter.load_components()
    assert any(component.name == "R_Generic" for component in first_pass)

    updated_text = working_lib.read_text(encoding="utf-8").replace(
        '(property "Value" "R_Generic"', '(property "Value" "R_Modified"', 1
    )
    working_lib.write_text(updated_text, encoding="utf-8")
    os.utime(working_lib, None)

    second_pass = adapter.load_components()
    assert any(component.name == "R_Modified" for component in second_pass)


def test_circuit_service_indexes_kicad_symbols(tmp_path):
    adapter = KiCADSymbolAdapter(search_paths=[FIXTURE_DIR], cache_dir=tmp_path / "cache")
    service = CircuitService(symbol_adapter=adapter)

    resistor = service.get_component_definition("reference_symbols:R_Generic")
    assert resistor is not None
    assert resistor.description == "Generic resistor symbol"
    assert resistor.metadata.get("keywords")
