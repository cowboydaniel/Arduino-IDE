"""Circuit Service utilities for circuit editing workflows."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from arduino_ide.models.circuit_domain import (
    Bus,
    ComponentDefinition,
    ComponentInstance,
    ComponentType,
    Connection,
    DifferentialPair,
    ElectricalRuleDiagnostic,
    HierarchicalPort,
    Net,
    NetNode,
    Pin,
    PinType,
    Sheet,
    SheetInstance,
    SymbolUnit,
)

logger = logging.getLogger(__name__)


class CircuitService(QObject):
    """Service for managing circuit design and validation."""

    _ANNOTATION_PREFIXES: Dict[ComponentType, str] = {
        ComponentType.RESISTOR: "R",
        ComponentType.CAPACITOR: "C",
        ComponentType.LED: "D",
        ComponentType.BUTTON: "S",
        ComponentType.POTENTIOMETER: "RV",
        ComponentType.SERVO: "M",
        ComponentType.MOTOR: "M",
        ComponentType.SENSOR: "U",
        ComponentType.BREADBOARD: "BRD",
        ComponentType.IC: "U",
        ComponentType.TRANSISTOR: "Q",
        ComponentType.WIRE: "W",
        ComponentType.BATTERY: "BAT",
        ComponentType.ARDUINO_BOARD: "A",
    }

    # Signals
    component_added = Signal(str)  # instance_id
    component_removed = Signal(str)
    component_moved = Signal(str, float, float)  # id, x, y
    connection_added = Signal(str)  # connection_id
    connection_removed = Signal(str)
    circuit_validated = Signal(bool, list)  # is_valid, error_list
    circuit_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._component_definitions: Dict[str, ComponentDefinition] = {}
        self._components: Dict[str, ComponentInstance] = {}
        self._connections: Dict[str, Connection] = {}
        self._nets: Dict[str, Net] = {}
        self._buses: Dict[str, Bus] = {}
        self._sheets: Dict[str, Sheet] = {}
        self._sheet_instances: Dict[str, SheetInstance] = {}
        self._differential_pairs: Dict[str, DifferentialPair] = {}

        self._next_component_id = 1
        self._next_connection_id = 1
        self._next_net_id = 1
        self._next_bus_id = 1
        self._next_sheet_instance_id = 1

        self._annotation_counters: Dict[ComponentType, int] = {}

        # Initialize component library
        self._init_component_library()

        logger.info("Circuit service initialized")


    def _init_component_library(self):
        """Initialize library of available components from JSON files"""

        # Find component library directory
        service_dir = Path(__file__).parent
        component_lib_dir = service_dir.parent / "component_library"

        if not component_lib_dir.exists():
            logger.warning(f"Component library directory not found: {component_lib_dir}")
            logger.info("Component library initialized with 0 components")
            return

        # Load all JSON component files
        component_count = 0
        error_count = 0

        for json_file in component_lib_dir.rglob("*.json"):
            # Skip README and other non-component files
            if json_file.name.lower() in ["readme.json", "package.json"]:
                continue

            try:
                component_def = self._load_component_from_json(json_file)
                if component_def:
                    self.register_component(component_def)
                    component_count += 1
            except Exception as e:
                logger.error(f"Failed to load component from {json_file}: {e}")
                error_count += 1

        logger.info(f"Component library initialized with {component_count} components")
        if error_count > 0:
            logger.warning(f"Failed to load {error_count} component files")

    def _load_component_from_json(self, json_path: Path) -> Optional[ComponentDefinition]:
        """Load a component definition from a JSON file"""

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate required fields
            required_fields = ["id", "name", "component_type", "description", "width", "height", "pins"]
            for field in required_fields:
                if field not in data:
                    logger.error(f"Component {json_path.name} missing required field: {field}")
                    return None

            # Parse component type
            try:
                component_type = ComponentType(data["component_type"])
            except ValueError:
                logger.error(f"Invalid component_type '{data['component_type']}' in {json_path.name}")
                return None

            # Parse pins
            pins = []
            for pin_data in data["pins"]:
                try:
                    pin_type = PinType(pin_data["pin_type"])
                    pin = Pin(
                        id=pin_data["id"],
                        label=pin_data["label"],
                        pin_type=pin_type,
                        position=(pin_data["position"][0], pin_data["position"][1])
                    )
                    pins.append(pin)
                except (ValueError, KeyError, IndexError) as e:
                    logger.error(f"Invalid pin definition in {json_path.name}: {e}")
                    return None

            # Create component definition
            component_def = ComponentDefinition(
                id=data["id"],
                name=data["name"],
                component_type=component_type,
                width=float(data["width"]),
                height=float(data["height"]),
                pins=pins,
                image_path=data.get("image_path"),
                description=data["description"],
                datasheet_url=data.get("metadata", {}).get("datasheet_url")
            )

            return component_def

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {json_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading component from {json_path}: {e}")
            return None


    def register_component(self, component_def: ComponentDefinition):
        """Register a component definition"""
        self._component_definitions[component_def.id] = component_def
        logger.debug(f"Registered component: {component_def.id}")


    def get_component_definition(self, component_id: str) -> Optional[ComponentDefinition]:
        """Get component definition by ID"""
        return self._component_definitions.get(component_id)


    def get_all_component_definitions(self) -> List[ComponentDefinition]:
        """Get all component definitions"""
        return list(self._component_definitions.values())


    def get_components_by_type(self, component_type: ComponentType) -> List[ComponentDefinition]:
        """Get components of a specific type"""
        return [c for c in self._component_definitions.values() if c.component_type == component_type]

    # ------------------------------------------------------------------
    # Annotation helpers

    def _annotate_component(self, component: ComponentInstance) -> None:
        """Assign or refresh the reference designator for a component."""

        comp_def = self.get_component_definition(component.definition_id)
        if not comp_def:
            return

        prefix = self._ANNOTATION_PREFIXES.get(comp_def.component_type, "U")
        next_index = self._annotation_counters.get(comp_def.component_type, 0) + 1
        self._annotation_counters[comp_def.component_type] = next_index
        component.annotation = f"{prefix}{next_index}"

    def renumber_annotations(self) -> None:
        """Recalculate reference designators in KiCAD-compatible order."""

        self._annotation_counters.clear()
        sorted_components = sorted(
            self._components.values(),
            key=lambda comp: (
                self.get_component_definition(comp.definition_id).component_type.value,
                comp.instance_id,
            ),
        )

        for component in sorted_components:
            self._annotate_component(component)

    # ------------------------------------------------------------------
    # Net and bus management

    def _generate_net_name(self, is_power: bool = False) -> str:
        """Generate a unique net name."""

        prefix = "PWR" if is_power else "NET"
        while True:
            candidate = f"{prefix}{self._next_net_id:03}"
            self._next_net_id += 1
            if candidate not in self._nets:
                return candidate

    def create_net(
        self,
        name: Optional[str] = None,
        *,
        attributes: Optional[Dict[str, str]] = None,
        is_power: bool = False,
    ) -> Net:
        """Create a new net with optional metadata."""

        attributes = attributes or {}
        if not name:
            name = self._generate_net_name(is_power=is_power)

        if name in self._nets:
            raise ValueError(f"Net '{name}' already exists")

        if is_power:
            attributes.setdefault("type", "power")

        net = Net(name=name, attributes=attributes)
        self._nets[name] = net
        return net

    def get_net(self, name: str) -> Optional[Net]:
        """Return a net by name."""

        return self._nets.get(name)

    def list_nets(self) -> List[Net]:
        """Return all nets."""

        return list(self._nets.values())

    def _detach_pin_from_any_net(self, component_id: str, pin_id: str) -> None:
        for net in self._nets.values():
            before = len(net.nodes)
            net.nodes = [
                node
                for node in net.nodes
                if not (node.component_id == component_id and node.pin_id == pin_id)
            ]
            if before != len(net.nodes):
                logger.debug(
                    "Removed %s.%s from net %s", component_id, pin_id, net.name
                )

    def _find_net_for_pin(self, component_id: str, pin_id: str) -> Optional[Net]:
        """Return the net that contains the given pin if any."""

        for net in self._nets.values():
            for node in net.nodes:
                if node.component_id == component_id and node.pin_id == pin_id:
                    return net
        return None

    def assign_pin_to_net(
        self,
        component_id: str,
        pin_id: str,
        net_name: str,
        sheet_path: Optional[Tuple[str, ...]] = None,
        *,
        pin_type: Optional[PinType] = None,
        allow_virtual: bool = False,
    ) -> bool:
        """Assign the given pin to a net, creating the net if missing."""

        if component_id not in self._components and not allow_virtual:
            return False

        sheet_path = sheet_path or tuple()
        net = self._nets.get(net_name) or self.create_net(net_name)

        self._detach_pin_from_any_net(component_id, pin_id)

        comp_def = None
        if component_id in self._components:
            comp_def = self.get_component_definition(self._components[component_id].definition_id)
        pin_obj = next((p for p in comp_def.pins if p.id == pin_id), None) if comp_def else None
        resolved_pin_type = pin_type or (pin_obj.pin_type if pin_obj else PinType.DIGITAL)

        node = NetNode(
            component_id=component_id,
            pin_id=pin_id,
            pin_type=resolved_pin_type,
            sheet_path=sheet_path,
        )
        net.nodes.append(node)
        return True

    def remove_net(self, net_name: str) -> bool:
        """Remove a net from the design."""

        if net_name not in self._nets:
            return False

        del self._nets[net_name]
        for connection in self._connections.values():
            if connection.net_name == net_name:
                connection.net_name = None
        for bus in self._buses.values():
            bus.nets.discard(net_name)
            for pair_name, pair in list(bus.differential_pairs.items()):
                if net_name in (pair.positive_net, pair.negative_net):
                    del bus.differential_pairs[pair_name]
        for pair_name, pair in list(self._differential_pairs.items()):
            if net_name in (pair.positive_net, pair.negative_net):
                del self._differential_pairs[pair_name]
        return True

    def renumber_nets(self) -> None:
        """Renumber nets in a deterministic order for export."""

        mapping: Dict[str, str] = {}
        sorted_items = sorted(self._nets.items(), key=lambda item: item[0])
        for index, (old_name, _) in enumerate(sorted_items, start=1):
            mapping[old_name] = f"NET{index:03}"

        new_nets: Dict[str, Net] = {}
        for old_name, net in sorted_items:
            new_name = mapping[old_name]
            net.name = new_name
            new_nets[new_name] = net

        for connection in self._connections.values():
            if connection.net_name in mapping:
                connection.net_name = mapping[connection.net_name]

        for bus in self._buses.values():
            bus.nets = {mapping.get(net, net) for net in bus.nets}
            bus.differential_pairs = {
                name: DifferentialPair(
                    name=pair.name,
                    positive_net=mapping.get(pair.positive_net, pair.positive_net),
                    negative_net=mapping.get(pair.negative_net, pair.negative_net),
                )
                for name, pair in bus.differential_pairs.items()
            }

        for pair_name, pair in list(self._differential_pairs.items()):
            self._differential_pairs[pair_name] = DifferentialPair(
                name=pair.name,
                positive_net=mapping.get(pair.positive_net, pair.positive_net),
                negative_net=mapping.get(pair.negative_net, pair.negative_net),
            )

        self._nets = new_nets
        self._next_net_id = len(self._nets) + 1

    def create_bus(self, name: Optional[str] = None, nets: Optional[List[str]] = None) -> Bus:
        """Create a bus that groups nets."""

        if not name:
            name = f"BUS{self._next_bus_id:02}"
            self._next_bus_id += 1

        if name in self._buses:
            raise ValueError(f"Bus '{name}' already exists")

        bus = Bus(name=name)
        self._buses[name] = bus

        if nets:
            for net_name in nets:
                self.add_net_to_bus(net_name, name)

        return bus

    def add_net_to_bus(self, net_name: str, bus_name: str) -> bool:
        """Associate a net with a bus."""

        net = self._nets.get(net_name)
        bus = self._buses.get(bus_name)
        if not net or not bus:
            return False

        bus.nets.add(net.name)
        net.bus = bus.name
        return True

    def define_differential_pair(
        self,
        pair_name: str,
        positive_net: str,
        negative_net: str,
        bus_name: Optional[str] = None,
    ) -> DifferentialPair:
        """Register a differential pair between two nets."""

        if positive_net not in self._nets or negative_net not in self._nets:
            raise ValueError("Both nets must exist for differential pair definition")

        pair = DifferentialPair(
            name=pair_name,
            positive_net=positive_net,
            negative_net=negative_net,
        )
        self._differential_pairs[pair_name] = pair
        self._nets[positive_net].differential_pair = pair_name
        self._nets[negative_net].differential_pair = pair_name

        if bus_name:
            bus = self._buses.get(bus_name) or self.create_bus(bus_name)
            bus.differential_pairs[pair_name] = pair

        return pair

    # ------------------------------------------------------------------
    # Sheet and hierarchy helpers

    def define_sheet(
        self,
        sheet_id: str,
        name: str,
        *,
        ports: Optional[List[HierarchicalPort]] = None,
        units: Optional[List[SymbolUnit]] = None,
    ) -> Sheet:
        """Register a sheet definition."""

        sheet = Sheet(sheet_id=sheet_id, name=name)
        for port in ports or []:
            sheet.ports[port.name] = port
        for unit in units or []:
            sheet.symbol_units[unit.unit_id] = unit

        self._sheets[sheet_id] = sheet
        return sheet

    def instantiate_sheet(
        self,
        sheet_id: str,
        parent_path: Optional[Tuple[str, ...]] = None,
    ) -> SheetInstance:
        """Instantiate a hierarchical sheet."""

        if sheet_id not in self._sheets:
            raise ValueError(f"Sheet '{sheet_id}' is not defined")

        instance_id = f"sheet_{self._next_sheet_instance_id}"
        self._next_sheet_instance_id += 1

        sheet = self._sheets[sheet_id]
        ports = {
            name: HierarchicalPort(
                name=port.name,
                pin_type=port.pin_type,
                direction=port.direction,
                net_name=port.net_name,
            )
            for name, port in sheet.ports.items()
        }

        instance = SheetInstance(
            instance_id=instance_id,
            sheet_id=sheet_id,
            parent_path=tuple(parent_path or tuple()),
            ports=ports,
        )
        sheet.instances[instance_id] = instance
        self._sheet_instances[instance_id] = instance
        return instance

    def bind_port_to_net(self, sheet_instance_id: str, port_name: str, net_name: str) -> bool:
        """Bind a hierarchical port to a net."""

        instance = self._sheet_instances.get(sheet_instance_id)
        if not instance or port_name not in instance.ports:
            return False

        port = instance.ports[port_name]
        port.net_name = net_name
        self.assign_pin_to_net(
            sheet_instance_id,
            port_name,
            net_name,
            instance.parent_path,
            pin_type=port.pin_type,
            allow_virtual=True,
        )
        return True


    def add_component(self, component_id: str, x: float, y: float) -> Optional[ComponentInstance]:
        """Add a component instance to the circuit"""
        comp_def = self.get_component_definition(component_id)
        if not comp_def:
            logger.error(f"Component definition not found: {component_id}")
            return None

        instance_id = f"comp_{self._next_component_id}"
        self._next_component_id += 1

        instance = ComponentInstance(
            instance_id=instance_id,
            definition_id=component_id,
            x=x,
            y=y
        )

        self._components[instance_id] = instance
        self._annotate_component(instance)
        self.component_added.emit(instance_id)
        self.circuit_changed.emit()

        logger.debug(f"Added component: {instance_id} ({component_id})")
        return instance


    def remove_component(self, instance_id: str) -> bool:
        """Remove a component from the circuit"""
        if instance_id not in self._components:
            return False

        # Remove all connections to this component
        connections_to_remove = [
            conn_id for conn_id, conn in self._connections.items()
            if conn.from_component == instance_id or conn.to_component == instance_id
        ]

        for conn_id in connections_to_remove:
            self.remove_connection(conn_id)

        for net in self._nets.values():
            net.nodes = [n for n in net.nodes if n.component_id != instance_id]

        del self._components[instance_id]
        self.component_removed.emit(instance_id)
        self.renumber_annotations()
        self.circuit_changed.emit()

        logger.debug(f"Removed component: {instance_id}")
        return True


    def move_component(self, instance_id: str, x: float, y: float) -> bool:
        """Move a component to new position"""
        if instance_id not in self._components:
            return False

        component = self._components[instance_id]
        component.x = x
        component.y = y

        self.component_moved.emit(instance_id, x, y)
        self.circuit_changed.emit()

        return True


    def rotate_component(self, instance_id: str, rotation: float) -> bool:
        """Rotate a component"""
        if instance_id not in self._components:
            return False

        component = self._components[instance_id]
        component.rotation = rotation % 360

        self.circuit_changed.emit()
        return True


    def add_connection(
        self,
        from_component: str,
        from_pin: str,
        to_component: str,
        to_pin: str,
        wire_color: str = "#000000",
        net_name: Optional[str] = None,
    ) -> Optional[Connection]:
        """Add a connection between two pins"""

        # Validate components exist
        if from_component not in self._components or to_component not in self._components:
            logger.error("Component not found in circuit")
            return None

        # Check if connection already exists
        for conn in self._connections.values():
            if ((conn.from_component == from_component and conn.from_pin == from_pin) or
                (conn.to_component == from_component and conn.to_pin == from_pin)):
                logger.warning(f"Pin already connected: {from_component}.{from_pin}")
                return None

        connection_id = f"conn_{self._next_connection_id}"
        self._next_connection_id += 1

        net = self._nets.get(net_name) if net_name else None
        if net_name and net is None:
            net = self.create_net(net_name)
        if net is None:
            net = self.create_net()

        self.assign_pin_to_net(from_component, from_pin, net.name)
        self.assign_pin_to_net(to_component, to_pin, net.name)

        connection = Connection(
            connection_id=connection_id,
            from_component=from_component,
            from_pin=from_pin,
            to_component=to_component,
            to_pin=to_pin,
            wire_color=wire_color,
            net_name=net.name,
        )

        self._connections[connection_id] = connection
        self.connection_added.emit(connection_id)
        self.circuit_changed.emit()

        logger.debug(f"Added connection: {from_component}.{from_pin} -> {to_component}.{to_pin}")
        return connection


    def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection"""
        if connection_id not in self._connections:
            return False

        connection = self._connections.pop(connection_id)
        self._detach_pin_from_any_net(connection.from_component, connection.from_pin)
        self._detach_pin_from_any_net(connection.to_component, connection.to_pin)
        self.connection_removed.emit(connection_id)
        self.circuit_changed.emit()

        logger.debug(f"Removed connection: {connection_id}")
        return True


    def get_circuit_components(self) -> List[ComponentInstance]:
        """Get all components in the circuit"""
        return list(self._components.values())

    def get_circuit_connections(self) -> List[Connection]:
        """Get all connections in the circuit"""
        return list(self._connections.values())

    def run_electrical_rules_check(self) -> List[ElectricalRuleDiagnostic]:
        """Execute ERC checks similar to KiCAD."""

        diagnostics: List[ElectricalRuleDiagnostic] = []
        drive_pin_types = {PinType.DIGITAL, PinType.PWM, PinType.SPI, PinType.SERIAL, PinType.I2C}

        for net in self._nets.values():
            pin_types = {node.pin_type for node in net.nodes}
            if PinType.POWER in pin_types and PinType.GROUND in pin_types:
                diagnostics.append(
                    ElectricalRuleDiagnostic(
                        code="ERC_SHORT",
                        message=f"Potential short between power and ground on {net.name}",
                        severity="error",
                        related_net=net.name,
                    )
                )

            drive_nodes = [node for node in net.nodes if node.pin_type in drive_pin_types]
            if len(drive_nodes) > 1:
                diagnostics.append(
                    ElectricalRuleDiagnostic(
                        code="ERC_PIN_CONFLICT",
                        message=f"Net {net.name} ties multiple driven outputs together",
                        severity="error",
                        related_net=net.name,
                    )
                )

            analog_nodes = [node for node in net.nodes if node.pin_type == PinType.ANALOG]
            if analog_nodes and drive_nodes:
                diagnostics.append(
                    ElectricalRuleDiagnostic(
                        code="ERC_ANALOG_DIGITAL_MIX",
                        message=f"Analog and driven pins share net {net.name}",
                        severity="warning",
                        related_net=net.name,
                    )
                )

        for component in self._components.values():
            comp_def = self.get_component_definition(component.definition_id)
            if not comp_def:
                continue

            for pin in comp_def.pins:
                if pin.pin_type not in (PinType.POWER, PinType.GROUND):
                    continue

                net = self._find_net_for_pin(component.instance_id, pin.id)
                if net:
                    continue

                severity = "error" if pin.pin_type == PinType.POWER else "warning"
                diagnostics.append(
                    ElectricalRuleDiagnostic(
                        code="ERC_UNCONNECTED_POWER",
                        message=f"{component.annotation or component.instance_id} missing {pin.pin_type.value} connection",
                        severity=severity,
                        related_component=component.instance_id,
                    )
                )

        if not any(
            self.get_component_definition(comp.definition_id).component_type == ComponentType.ARDUINO_BOARD
            for comp in self._components.values()
        ):
            diagnostics.append(
                ElectricalRuleDiagnostic(
                    code="ERC_NO_CONTROLLER",
                    message="Circuit has no Arduino controller",
                    severity="warning",
                )
            )

        return diagnostics

    def validate_circuit(self) -> Tuple[bool, List[ElectricalRuleDiagnostic]]:
        """Validate the circuit for common electrical errors."""

        diagnostics = self.run_electrical_rules_check()
        is_valid = not any(diag.severity == "error" for diag in diagnostics)
        serialized = [
            {
                "code": diag.code,
                "message": diag.message,
                "severity": diag.severity,
                "related_net": diag.related_net,
                "related_component": diag.related_component,
            }
            for diag in diagnostics
        ]
        self.circuit_validated.emit(is_valid, serialized)
        return is_valid, diagnostics


    def clear_circuit(self):
        """Clear all components and connections"""
        self._components.clear()
        self._connections.clear()
        self._nets.clear()
        self._buses.clear()
        self._sheets.clear()
        self._sheet_instances.clear()
        self._differential_pairs.clear()
        self._annotation_counters.clear()
        self._next_component_id = 1
        self._next_connection_id = 1
        self._next_net_id = 1
        self._next_bus_id = 1
        self._next_sheet_instance_id = 1
        self.circuit_changed.emit()
        logger.info("Circuit cleared")


    def save_circuit(self, file_path: str) -> bool:
        """Save circuit to JSON file"""
        try:
            data = {
                "components": [
                    {
                        "instance_id": c.instance_id,
                        "definition_id": c.definition_id,
                        "x": c.x,
                        "y": c.y,
                        "rotation": c.rotation,
                        "properties": c.properties,
                        "annotation": c.annotation,
                        "sheet_path": list(c.sheet_path),
                        "unit_assignments": c.unit_assignments,
                    }
                    for c in self._components.values()
                ],
                "connections": [
                    {
                        "connection_id": c.connection_id,
                        "from_component": c.from_component,
                        "from_pin": c.from_pin,
                        "to_component": c.to_component,
                        "to_pin": c.to_pin,
                        "wire_color": c.wire_color,
                        "net_name": c.net_name,
                    }
                    for c in self._connections.values()
                ],
                "nets": [
                    {
                        "name": net.name,
                        "attributes": net.attributes,
                        "bus": net.bus,
                        "differential_pair": net.differential_pair,
                        "nodes": [
                            {
                                "component_id": node.component_id,
                                "pin_id": node.pin_id,
                                "pin_type": node.pin_type.value,
                                "sheet_path": list(node.sheet_path),
                            }
                            for node in net.nodes
                        ],
                    }
                    for net in self._nets.values()
                ],
                "buses": [
                    {
                        "name": bus.name,
                        "nets": sorted(bus.nets),
                        "differential_pairs": {
                            name: {
                                "positive": pair.positive_net,
                                "negative": pair.negative_net,
                            }
                            for name, pair in bus.differential_pairs.items()
                        },
                    }
                    for bus in self._buses.values()
                ],
                "sheets": [
                    {
                        "sheet_id": sheet.sheet_id,
                        "name": sheet.name,
                        "ports": {
                            name: {
                                "pin_type": port.pin_type.value,
                                "direction": port.direction,
                            }
                            for name, port in sheet.ports.items()
                        },
                        "instances": {
                            instance_id: {
                                "parent_path": list(instance.parent_path),
                                "ports": {
                                    pname: {
                                        "pin_type": port.pin_type.value,
                                        "direction": port.direction,
                                        "net_name": port.net_name,
                                    }
                                    for pname, port in instance.ports.items()
                                },
                            }
                            for instance_id, instance in sheet.instances.items()
                        },
                    }
                    for sheet in self._sheets.values()
                ],
            }

            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Circuit saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save circuit: {e}")
            return False


    def load_circuit(self, file_path: str) -> bool:
        """Load circuit from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            self.clear_circuit()

            # Load components
            for comp_data in data.get("components", []):
                component = ComponentInstance(
                    instance_id=comp_data["instance_id"],
                    definition_id=comp_data["definition_id"],
                    x=comp_data["x"],
                    y=comp_data["y"],
                    rotation=comp_data.get("rotation", 0.0),
                    properties=comp_data.get("properties", {}),
                    annotation=comp_data.get("annotation"),
                    sheet_path=tuple(comp_data.get("sheet_path", [])),
                    unit_assignments=comp_data.get("unit_assignments", {}),
                )
                self._components[component.instance_id] = component

            self._annotation_counters.clear()
            for component in self._components.values():
                comp_def = self.get_component_definition(component.definition_id)
                if not comp_def or not component.annotation:
                    continue
                prefix = self._ANNOTATION_PREFIXES.get(comp_def.component_type, "U")
                if component.annotation.startswith(prefix):
                    suffix = component.annotation[len(prefix):]
                    if suffix.isdigit():
                        current = self._annotation_counters.get(comp_def.component_type, 0)
                        self._annotation_counters[comp_def.component_type] = max(current, int(suffix))

            # Load connections
            for conn_data in data.get("connections", []):
                connection = Connection(
                    connection_id=conn_data["connection_id"],
                    from_component=conn_data["from_component"],
                    from_pin=conn_data["from_pin"],
                    to_component=conn_data["to_component"],
                    to_pin=conn_data["to_pin"],
                    wire_color=conn_data.get("wire_color", "#000000"),
                    net_name=conn_data.get("net_name"),
                )
                self._connections[connection.connection_id] = connection

            if self._components:
                max_id = max(
                    (int(comp_id.split("_")[1]) for comp_id in self._components.keys() if comp_id.startswith("comp_")),
                    default=0,
                )
                self._next_component_id = max_id + 1
            if self._connections:
                max_conn = max(
                    (int(conn_id.split("_")[1]) for conn_id in self._connections.keys() if conn_id.startswith("conn_")),
                    default=0,
                )
                self._next_connection_id = max_conn + 1

            for net_data in data.get("nets", []):
                net = Net(
                    name=net_data["name"],
                    attributes=net_data.get("attributes", {}),
                    bus=net_data.get("bus"),
                    differential_pair=net_data.get("differential_pair"),
                    nodes=[
                        NetNode(
                            component_id=node["component_id"],
                            pin_id=node["pin_id"],
                            pin_type=PinType(node["pin_type"]),
                            sheet_path=tuple(node.get("sheet_path", [])),
                        )
                        for node in net_data.get("nodes", [])
                    ],
                )
                self._nets[net.name] = net

            self._next_net_id = len(self._nets) + 1

            for bus_data in data.get("buses", []):
                bus = Bus(name=bus_data["name"])
                bus.nets = set(bus_data.get("nets", []))
                bus.differential_pairs = {
                    name: DifferentialPair(
                        name=name,
                        positive_net=pair_info["positive"],
                        negative_net=pair_info["negative"],
                    )
                    for name, pair_info in bus_data.get("differential_pairs", {}).items()
                }
                self._buses[bus.name] = bus
                for name, pair in bus.differential_pairs.items():
                    self._differential_pairs[name] = pair

            if self._buses:
                max_bus = max(
                    (
                        int(bus_name[3:])
                        for bus_name in self._buses
                        if bus_name.startswith("BUS") and bus_name[3:].isdigit()
                    ),
                    default=0,
                )
                self._next_bus_id = max_bus + 1

            for sheet_data in data.get("sheets", []):
                sheet = Sheet(sheet_id=sheet_data["sheet_id"], name=sheet_data.get("name", sheet_data["sheet_id"]))
                for name, port in sheet_data.get("ports", {}).items():
                    sheet.ports[name] = HierarchicalPort(
                        name=name,
                        pin_type=PinType(port["pin_type"]),
                        direction=port.get("direction", "bidirectional"),
                    )
                for instance_id, instance_data in sheet_data.get("instances", {}).items():
                    ports = {
                        pname: HierarchicalPort(
                            name=pname,
                            pin_type=PinType(port_data["pin_type"]),
                            direction=port_data.get("direction", "bidirectional"),
                            net_name=port_data.get("net_name"),
                        )
                        for pname, port_data in instance_data.get("ports", {}).items()
                    }
                    instance = SheetInstance(
                        instance_id=instance_id,
                        sheet_id=sheet.sheet_id,
                        parent_path=tuple(instance_data.get("parent_path", [])),
                        ports=ports,
                    )
                    sheet.instances[instance_id] = instance
                    self._sheet_instances[instance_id] = instance
                self._sheets[sheet.sheet_id] = sheet

            if self._sheet_instances:
                max_sheet = max(
                    (
                        int(instance_id.split("_")[1])
                        for instance_id in self._sheet_instances
                        if instance_id.startswith("sheet_")
                    ),
                    default=0,
                )
                self._next_sheet_instance_id = max_sheet + 1

            self.circuit_changed.emit()
            logger.info(f"Circuit loaded from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load circuit: {e}")
            return False


    def generate_connection_list(self) -> str:
        """Generate a text description of connections"""
        lines = ["Circuit Connections:", "=" * 50]

        for conn in self._connections.values():
            from_comp = self._components[conn.from_component]
            to_comp = self._components[conn.to_component]

            from_def = self.get_component_definition(from_comp.definition_id)
            to_def = self.get_component_definition(to_comp.definition_id)

            net_info = f" [{conn.net_name}]" if conn.net_name else ""
            line = f"{from_def.name} ({conn.from_pin}) -> {to_def.name} ({conn.to_pin}){net_info}"
            lines.append(line)

        return "\n".join(lines)
