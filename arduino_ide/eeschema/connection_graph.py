"""
Connection Graph - Electrical connectivity analysis
Based on KiCad's connection_graph.cpp/h structure
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from arduino_ide.models.circuit_domain import (
    ComponentInstance,
    Connection,
    Net,
    NetNode,
    Pin,
    PinType,
)

logger = logging.getLogger(__name__)


class ConnectionGraph:
    """
    Analyzes electrical connectivity in a schematic.
    Corresponds to KiCad's CONNECTION_GRAPH class.
    """

    def __init__(self):
        self._nets: Dict[str, Net] = {}
        self._nodes: Dict[str, NetNode] = {}
        self._net_counter = 1

    def build_graph(
        self,
        components: Dict[str, ComponentInstance],
        connections: Dict[str, Connection],
        component_definitions: Dict,
    ):
        """Build the connection graph from components and connections"""
        self._nets.clear()
        self._nodes.clear()
        self._net_counter = 1

        # Create nodes for each pin
        pin_to_node: Dict[Tuple[str, str], str] = {}
        for comp_id, comp in components.items():
            comp_def = component_definitions.get(comp.definition_id)
            if not comp_def:
                continue

            for pin in comp_def.pins:
                node_id = f"{comp_id}:{pin.id}"
                node = NetNode(
                    node_id=node_id,
                    component_id=comp_id,
                    pin_id=pin.id,
                    net_id=None,
                )
                self._nodes[node_id] = node
                pin_to_node[(comp_id, pin.id)] = node_id

        # Connect nodes via connections
        for conn_id, conn in connections.items():
            from_node_id = pin_to_node.get((conn.from_component, conn.from_pin))
            to_node_id = pin_to_node.get((conn.to_component, conn.to_pin))

            if not from_node_id or not to_node_id:
                continue

            from_node = self._nodes[from_node_id]
            to_node = self._nodes[to_node_id]

            # Merge nodes into the same net
            if from_node.net_id and to_node.net_id:
                # Both have nets, merge them
                if from_node.net_id != to_node.net_id:
                    self._merge_nets(from_node.net_id, to_node.net_id)
            elif from_node.net_id:
                # Only from has a net
                to_node.net_id = from_node.net_id
                self._nets[from_node.net_id].nodes.append(to_node_id)
            elif to_node.net_id:
                # Only to has a net
                from_node.net_id = to_node.net_id
                self._nets[to_node.net_id].nodes.append(from_node_id)
            else:
                # Neither has a net, create new one
                net_id = f"Net{self._net_counter}"
                self._net_counter += 1
                net = Net(
                    net_id=net_id,
                    name=net_id,
                    nodes=[from_node_id, to_node_id],
                )
                self._nets[net_id] = net
                from_node.net_id = net_id
                to_node.net_id = net_id

        logger.info(f"Built connection graph with {len(self._nets)} nets and {len(self._nodes)} nodes")

    def _merge_nets(self, net_id1: str, net_id2: str):
        """Merge two nets into one"""
        if net_id1 not in self._nets or net_id2 not in self._nets:
            return

        net1 = self._nets[net_id1]
        net2 = self._nets[net_id2]

        # Merge net2 into net1
        net1.nodes.extend(net2.nodes)

        # Update all nodes in net2 to point to net1
        for node_id in net2.nodes:
            if node_id in self._nodes:
                self._nodes[node_id].net_id = net_id1

        # Remove net2
        del self._nets[net_id2]

    def get_net_for_pin(self, component_id: str, pin_id: str) -> Optional[Net]:
        """Get the net connected to a specific pin"""
        node_id = f"{component_id}:{pin_id}"
        node = self._nodes.get(node_id)
        if not node or not node.net_id:
            return None
        return self._nets.get(node.net_id)

    def get_all_nets(self) -> List[Net]:
        """Get all nets in the graph"""
        return list(self._nets.values())

    def get_unconnected_pins(self, components: Dict, component_definitions: Dict) -> List[Tuple[str, str]]:
        """Get list of unconnected pins"""
        unconnected = []
        for comp_id, comp in components.items():
            comp_def = component_definitions.get(comp.definition_id)
            if not comp_def:
                continue

            for pin in comp_def.pins:
                node_id = f"{comp_id}:{pin.id}"
                node = self._nodes.get(node_id)
                if not node or not node.net_id:
                    unconnected.append((comp_id, pin.id))

        return unconnected

    def generate_netlist(self) -> str:
        """Generate netlist string representation"""
        lines = ["# Netlist", ""]
        for net in self._nets.values():
            lines.append(f"Net: {net.name}")
            for node_id in net.nodes:
                node = self._nodes.get(node_id)
                if node:
                    lines.append(f"  - {node.component_id}.{node.pin_id}")
            lines.append("")
        return "\n".join(lines)
