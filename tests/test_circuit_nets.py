import os
import sys

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, os.path.dirname(CURRENT_DIR))

from arduino_ide.services.circuit_service import CircuitService
from arduino_ide.models.circuit_domain import (
    ComponentDefinition,
    ComponentType,
    HierarchicalPort,
    Pin,
    PinType,
)


def _register_test_component(service: CircuitService, component_id: str = "test_power") -> None:
    if service.get_component_definition(component_id):
        return

    pins = [
        Pin(id="VCC", label="VCC", pin_type=PinType.POWER, position=(0.0, 0.0)),
        Pin(id="GND", label="GND", pin_type=PinType.GROUND, position=(5.0, 0.0)),
        Pin(id="IO1", label="IO1", pin_type=PinType.DIGITAL, position=(2.5, 5.0)),
    ]
    definition = ComponentDefinition(
        id=component_id,
        name="Test Power Device",
        component_type=ComponentType.IC,
        width=10.0,
        height=10.0,
        pins=pins,
    )
    service.register_component(definition)


def test_net_management_and_bus_logic():
    service = CircuitService()
    _register_test_component(service)

    comp_a = service.add_component("test_power", 0, 0)
    comp_b = service.add_component("test_power", 20, 0)

    power_conn = service.add_connection(
        comp_a.instance_id,
        "VCC",
        comp_b.instance_id,
        "VCC",
        net_name="PWR_A",
    )
    assert power_conn is not None
    assert power_conn.net_name == "PWR_A"

    net = service.get_net("PWR_A")
    assert net is not None
    assert {node.component_id for node in net.nodes} == {comp_a.instance_id, comp_b.instance_id}

    bus = service.create_bus("MAINBUS", nets=[net.name])
    assert net.bus == bus.name

    io_conn = service.add_connection(
        comp_a.instance_id,
        "IO1",
        comp_b.instance_id,
        "IO1",
    )
    assert io_conn is not None

    pair = service.define_differential_pair("CLK", power_conn.net_name, io_conn.net_name, bus.name)
    assert pair.name == "CLK"
    assert service.get_net(power_conn.net_name).differential_pair == "CLK"

    port = HierarchicalPort(name="OUT", pin_type=PinType.DIGITAL)
    service.define_sheet("child", "Child", ports=[port])
    instance = service.instantiate_sheet("child", parent_path=("ROOT",))
    service.bind_port_to_net(instance.instance_id, "OUT", io_conn.net_name)

    updated_net = service.get_net(io_conn.net_name)
    assert any(node.component_id == instance.instance_id for node in updated_net.nodes)


def test_erc_detects_power_issues():
    service = CircuitService()
    _register_test_component(service)

    comp = service.add_component("test_power", 0, 0)
    diagnostics = service.run_electrical_rules_check()
    assert any(diag.code == "ERC_UNCONNECTED_POWER" for diag in diagnostics)

    service.add_connection(comp.instance_id, "VCC", comp.instance_id, "GND", net_name="SHORT")
    diagnostics = service.run_electrical_rules_check()
    assert any(diag.code == "ERC_SHORT" for diag in diagnostics)
