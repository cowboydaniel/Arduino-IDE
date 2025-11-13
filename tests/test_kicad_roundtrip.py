import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arduino_ide.services.circuit_service import (
    CircuitService,
    ComponentDefinition,
    ComponentType,
    Pin,
    PinType,
)


def _register_stub_components(service: CircuitService):
    resistor = ComponentDefinition(
        id="Device:R",
        name="Resistor",
        component_type=ComponentType.RESISTOR,
        width=10,
        height=3,
        pins=[
            Pin(id="1", label="1", pin_type=PinType.ANALOG, position=(0, 0)),
            Pin(id="2", label="2", pin_type=PinType.ANALOG, position=(10, 0)),
        ],
    )

    led = ComponentDefinition(
        id="Device:LED",
        name="LED",
        component_type=ComponentType.LED,
        width=8,
        height=3,
        pins=[
            Pin(id="A", label="A", pin_type=PinType.POWER, position=(0, 0)),
            Pin(id="K", label="K", pin_type=PinType.GROUND, position=(8, 0)),
        ],
    )

    service.register_component(resistor)
    service.register_component(led)


def test_kicad_round_trip_preserves_data(tmp_path):
    service = CircuitService()
    _register_stub_components(service)

    child_sheet = service.add_sheet("Indicators")

    resistor = service.add_component("Device:R", 10.0, 5.0)
    led = service.add_component("Device:LED", 20.0, 5.0, sheet_id=child_sheet.sheet_id)

    resistor.properties["Value"] = "10k"
    led.properties["Color"] = "red"

    connection = service.add_connection(resistor.instance_id, "2", led.instance_id, "A", wire_color="#123456")
    assert connection is not None

    out_file = tmp_path / "roundtrip.kicad_sch"
    service.save_circuit(str(out_file))

    assert out_file.exists(), "KiCAD schematic was not created"

    loaded = CircuitService()
    _register_stub_components(loaded)
    loaded.load_circuit(str(out_file))

    loaded_components = {comp.instance_id: comp for comp in loaded.get_circuit_components()}
    assert set(loaded_components.keys()) == {resistor.instance_id, led.instance_id}

    assert loaded_components[resistor.instance_id].sheet_id == resistor.sheet_id
    assert loaded_components[resistor.instance_id].properties["Value"] == "10k"
    assert loaded_components[led.instance_id].sheet_id == child_sheet.sheet_id
    assert loaded_components[led.instance_id].properties["Color"] == "red"

    loaded_sheet = loaded.get_sheet(child_sheet.sheet_id)
    assert loaded_sheet is not None
    assert loaded_sheet.name == child_sheet.name

    loaded_connections = loaded.get_circuit_connections()
    assert len(loaded_connections) == 1
    loaded_conn = loaded_connections[0]
    assert loaded_conn.wire_color == "#123456"
    assert loaded_conn.from_component == resistor.instance_id
    assert loaded_conn.to_component == led.instance_id


def test_legacy_json_import_and_export(tmp_path):
    legacy_data = {
        "components": [
            {
                "instance_id": "comp_1",
                "definition_id": "Device:R",
                "x": 0,
                "y": 0,
                "rotation": 0,
                "properties": {"Value": "220"},
            },
            {
                "instance_id": "comp_2",
                "definition_id": "Device:LED",
                "x": 5,
                "y": 0,
                "rotation": 0,
                "properties": {},
            },
        ],
        "connections": [
            {
                "connection_id": "conn_1",
                "from_component": "comp_1",
                "from_pin": "1",
                "to_component": "comp_2",
                "to_pin": "A",
                "wire_color": "#abcdef",
            }
        ],
    }

    legacy_file = tmp_path / "legacy.json"
    legacy_file.write_text(json.dumps(legacy_data), encoding="utf-8")

    service = CircuitService()
    _register_stub_components(service)
    service.import_legacy_json(str(legacy_file))

    export_file = tmp_path / "migrated.kicad_sch"
    service.export_to_kicad(str(export_file))
    assert export_file.exists()

    migrated = CircuitService()
    _register_stub_components(migrated)
    migrated.load_circuit(str(export_file))

    assert len(migrated.get_circuit_components()) == 2
    migrated_components = {c.instance_id: c for c in migrated.get_circuit_components()}
    assert migrated_components["comp_1"].properties["Value"] == "220"

    migrated_connections = migrated.get_circuit_connections()
    assert len(migrated_connections) == 1
    assert migrated_connections[0].wire_color == "#abcdef"
