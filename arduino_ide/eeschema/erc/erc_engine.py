"""
ERC Engine - Electrical Rules Checking
Based on KiCad's ERC structure
"""

import logging
from typing import Dict, List, Tuple

from arduino_ide.models.circuit_domain import (
    ComponentInstance,
    Connection,
    ElectricalRuleDiagnostic,
    PinType,
)
from arduino_ide.eeschema.connection_graph import ConnectionGraph

logger = logging.getLogger(__name__)


class ERCEngine:
    """
    Electrical Rules Checker for schematics.
    Corresponds to KiCad's ERC functionality.
    """

    def __init__(self):
        self._diagnostics: List[ElectricalRuleDiagnostic] = []

    def run_erc(
        self,
        components: Dict[str, ComponentInstance],
        connections: Dict[str, Connection],
        component_definitions: Dict,
    ) -> Tuple[bool, List[str]]:
        """Run electrical rules check"""
        self._diagnostics.clear()
        errors = []

        # Build connection graph
        graph = ConnectionGraph()
        graph.build_graph(components, connections, component_definitions)

        # Check for unconnected power pins
        errors.extend(self._check_unconnected_power_pins(components, component_definitions, graph))

        # Check for unconnected ground pins
        errors.extend(self._check_unconnected_ground_pins(components, component_definitions, graph))

        # Check for floating inputs
        errors.extend(self._check_floating_inputs(components, component_definitions, graph))

        # Check for conflicting drivers
        errors.extend(self._check_conflicting_drivers(components, component_definitions, graph, connections))

        is_valid = len(errors) == 0
        logger.info(f"ERC completed: {'PASS' if is_valid else 'FAIL'} ({len(errors)} violations)")
        return is_valid, errors

    def _check_unconnected_power_pins(
        self,
        components: Dict,
        component_definitions: Dict,
        graph: ConnectionGraph,
    ) -> List[str]:
        """Check for unconnected power pins"""
        errors = []
        for comp_id, comp in components.items():
            comp_def = component_definitions.get(comp.definition_id)
            if not comp_def:
                continue

            for pin in comp_def.pins:
                if pin.pin_type == PinType.POWER:
                    net = graph.get_net_for_pin(comp_id, pin.id)
                    if not net:
                        reference = comp.properties.get("reference", comp_id)
                        errors.append(f"Unconnected POWER pin: {reference}.{pin.label} ({comp_id}.{pin.id})")

        return errors

    def _check_unconnected_ground_pins(
        self,
        components: Dict,
        component_definitions: Dict,
        graph: ConnectionGraph,
    ) -> List[str]:
        """Check for unconnected ground pins"""
        errors = []
        for comp_id, comp in components.items():
            comp_def = component_definitions.get(comp.definition_id)
            if not comp_def:
                continue

            for pin in comp_def.pins:
                if pin.pin_type == PinType.GROUND:
                    net = graph.get_net_for_pin(comp_id, pin.id)
                    if not net:
                        reference = comp.properties.get("reference", comp_id)
                        errors.append(f"Unconnected GROUND pin: {reference}.{pin.label} ({comp_id}.{pin.id})")

        return errors

    def _check_floating_inputs(
        self,
        components: Dict,
        component_definitions: Dict,
        graph: ConnectionGraph,
    ) -> List[str]:
        """Check for floating input pins"""
        errors = []
        input_types = {PinType.DIGITAL, PinType.ANALOG}

        for comp_id, comp in components.items():
            comp_def = component_definitions.get(comp.definition_id)
            if not comp_def:
                continue

            for pin in comp_def.pins:
                if pin.pin_type in input_types:
                    net = graph.get_net_for_pin(comp_id, pin.id)
                    if not net:
                        reference = comp.properties.get("reference", comp_id)
                        # Only warn for inputs, not all pins
                        if "in" in pin.label.lower() or "input" in pin.label.lower():
                            errors.append(f"Floating input pin: {reference}.{pin.label} ({comp_id}.{pin.id})")

        return errors

    def _check_conflicting_drivers(
        self,
        components: Dict,
        component_definitions: Dict,
        graph: ConnectionGraph,
        connections: Dict,
    ) -> List[str]:
        """Check for multiple drivers on the same net"""
        errors = []

        # Count output pins per net
        for net in graph.get_all_nets():
            output_pins = []
            for node_id in net.nodes:
                parts = node_id.split(":")
                if len(parts) != 2:
                    continue
                comp_id, pin_id = parts
                comp = components.get(comp_id)
                if not comp:
                    continue
                comp_def = component_definitions.get(comp.definition_id)
                if not comp_def:
                    continue

                # Find the pin
                for pin in comp_def.pins:
                    if pin.id == pin_id:
                        # Check if it's an output
                        if "out" in pin.label.lower() or "output" in pin.label.lower():
                            reference = comp.properties.get("reference", comp_id)
                            output_pins.append(f"{reference}.{pin.label}")
                        break

            if len(output_pins) > 1:
                errors.append(f"Multiple drivers on {net.name}: {', '.join(output_pins)}")

        return errors

    def get_diagnostics(self) -> List[ElectricalRuleDiagnostic]:
        """Get all ERC diagnostics"""
        return self._diagnostics
