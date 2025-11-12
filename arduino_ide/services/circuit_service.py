"""Circuit Service utilities for circuit editing workflows."""

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtCore import QObject, Signal

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

class ComponentType(Enum):
    """Types of circuit components"""
    ARDUINO_BOARD = "arduino_board"
    LED = "led"
    RESISTOR = "resistor"
    BUTTON = "button"
    POTENTIOMETER = "potentiometer"
    SERVO = "servo"
    MOTOR = "motor"
    SENSOR = "sensor"
    BREADBOARD = "breadboard"
    WIRE = "wire"
    BATTERY = "battery"
    CAPACITOR = "capacitor"
    TRANSISTOR = "transistor"
    IC = "ic"


class PinType(Enum):
    """Types of pins"""
    DIGITAL = "digital"
    ANALOG = "analog"
    PWM = "pwm"
    POWER = "power"
    GROUND = "ground"
    I2C = "i2c"
    SPI = "spi"
    SERIAL = "serial"


@dataclass
class Pin:
    """Pin on a component"""
    id: str
    label: str
    pin_type: PinType
    position: Tuple[float, float]  # Relative position on component
    length: float = 20.0
    orientation: str = "left"
    decoration: str = "line"


@dataclass
class ComponentDefinition:
    """Definition of a circuit component"""
    id: str
    name: str
    component_type: ComponentType
    width: float
    height: float
    pins: List[Pin] = field(default_factory=list)
    image_path: Optional[str] = None
    description: str = ""
    datasheet_url: Optional[str] = None
    graphics: List[Dict[str, Any]] = field(default_factory=list)
    units: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ComponentInstance:
    """Instance of a component in the circuit"""
    instance_id: str
    definition_id: str
    x: float
    y: float
    rotation: float = 0.0  # Degrees
    properties: Dict[str, Any] = field(default_factory=dict)
    sheet_id: Optional[str] = None


@dataclass
class Connection:
    """Connection between two pins"""
    connection_id: str
    from_component: str
    from_pin: str
    to_component: str
    to_pin: str
    wire_color: str = "#000000"
    connection_type: str = "wire"


@dataclass
class Sheet:
    """Hierarchical sheet information"""
    sheet_id: str
    name: str
    parent_id: Optional[str] = None
    file_path: Optional[str] = None
    embedded: bool = False


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
    sheets_changed = Signal()
    active_sheet_changed = Signal(str)

    def __init__(self, parent=None, symbol_adapter: Optional["KiCADSymbolAdapter"] = None):
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
        self._next_sheet_id = 1

        self._sheets: Dict[str, Sheet] = {}
        self._active_sheet_id: Optional[str] = None

        # Initialize component library
        self._init_component_library()

        self._ensure_root_sheet()

        logger.info("Circuit service initialized")

    def _ensure_root_sheet(self):
        """Ensure there is always at least one root sheet."""
        if self._sheets:
            if not self._active_sheet_id:
                self._active_sheet_id = next(iter(self._sheets))
            return

        sheet_id = self._generate_sheet_id()
        self._sheets[sheet_id] = Sheet(sheet_id=sheet_id, name="Root Sheet")
        self._active_sheet_id = sheet_id
        self.sheets_changed.emit()
        self.active_sheet_changed.emit(sheet_id)

    def _generate_sheet_id(self) -> str:
        sheet_id = f"sheet_{self._next_sheet_id}"
        self._next_sheet_id += 1
        return sheet_id

    # ------------------------------------------------------------------
    # Sheet management APIs
    # ------------------------------------------------------------------
    def create_sheet(self, name: str, parent_id: Optional[str] = None, embedded: bool = False) -> Sheet:
        sheet_id = self._generate_sheet_id()
        parent = parent_id or self._active_sheet_id
        sheet = Sheet(sheet_id=sheet_id, name=name, parent_id=parent, embedded=embedded)
        self._sheets[sheet_id] = sheet
        self.sheets_changed.emit()
        return sheet

    def open_sheet(self, file_path: str) -> Sheet:
        sheet = self.create_sheet(Path(file_path).stem, None, embedded=False)
        sheet.file_path = file_path
        return sheet

    def embed_sheet(self, file_path: str, parent_id: Optional[str] = None) -> Sheet:
        sheet = self.create_sheet(Path(file_path).stem, parent_id, embedded=True)
        sheet.file_path = file_path
        return sheet

    def set_active_sheet(self, sheet_id: str):
        if sheet_id not in self._sheets:
            return

        self._active_sheet_id = sheet_id
        self.active_sheet_changed.emit(sheet_id)

    def get_active_sheet_id(self) -> str:
        self._ensure_root_sheet()
        return self._active_sheet_id  # type: ignore

    def get_sheets(self) -> List[Sheet]:
        return list(self._sheets.values())


    def _init_component_library(self):
        """Initialize the component library using the KiCAD symbol adapter."""

        self._component_definitions.clear()

        adapter = self._symbol_adapter
        if adapter is None:
            try:
                from .kicad_symbol_adapter import KiCADSymbolAdapter
            except Exception as exc:  # pragma: no cover - defensive import guard
                logger.warning("KiCAD symbol adapter unavailable: %s", exc)
                logger.info("Component library initialized with 0 components")
                return

            adapter = KiCADSymbolAdapter(
                search_paths=config.KICAD_GLOBAL_SYMBOL_LIBRARY_PATHS,
                cache_dir=config.KICAD_PROJECT_CACHE_DIR,
            )
            self._symbol_adapter = adapter

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
                        position=(pin_data["position"][0], pin_data["position"][1]),
                        length=float(pin_data.get("length", 20.0)),
                        orientation=pin_data.get("orientation", "left"),
                        decoration=pin_data.get("decoration", "line"),
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
                datasheet_url=data.get("metadata", {}).get("datasheet_url"),
                graphics=data.get("graphics", []),
                units=data.get("units", []),
            )

        for component_def in components:
            self.register_component(component_def)

        logger.info(
            "Component library initialized with %s KiCAD symbol(s)",
            len(self._component_definitions),
        )


    def register_component(self, component_def: ComponentDefinition):
        """Register a component definition"""
        self._component_definitions[component_def.id] = component_def
        logger.debug(f"Registered component: {component_def.id}")


    def get_component_definition(self, component_id: str) -> Optional[ComponentDefinition]:
        """Get component definition by ID"""
        return self._component_definitions.get(component_id)

    def get_component_instance(self, instance_id: str) -> Optional[ComponentInstance]:
        return self._components.get(instance_id)


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


    def add_component(self, component_id: str, x: float, y: float,
                      sheet_id: Optional[str] = None) -> Optional[ComponentInstance]:
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
            y=y,
            sheet_id=sheet_id or self.get_active_sheet_id()
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

    def update_component_properties(self, instance_id: str, updates: Dict[str, Any]) -> bool:
        if instance_id not in self._components:
            return False

        self._components[instance_id].properties.update(updates)
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


    def add_connection(self, from_component: str, from_pin: str,
                      to_component: str, to_pin: str,
                      wire_color: str = "#000000",
                      connection_type: str = "wire") -> Optional[Connection]:
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
            connection_type=connection_type,
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

    def get_components_for_sheet(self, sheet_id: Optional[str] = None) -> List[ComponentInstance]:
        target_sheet = sheet_id or self.get_active_sheet_id()
        return [c for c in self._components.values() if c.sheet_id == target_sheet]


    def get_circuit_connections(self) -> List[Connection]:
        """Get all connections in the circuit"""
        return list(self._connections.values())

    def get_connections_for_sheet(self, sheet_id: Optional[str] = None) -> List[Connection]:
        target_sheet = sheet_id or self.get_active_sheet_id()
        component_ids = {c.instance_id for c in self.get_components_for_sheet(target_sheet)}
        return [
            conn for conn in self._connections.values()
            if conn.from_component in component_ids and conn.to_component in component_ids
        ]


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
            data = self.export_circuit_state()

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
            self._sheets.clear()

            # Load components
            for comp_data in data.get("components", []):
                component = ComponentInstance(
                    instance_id=comp_data["instance_id"],
                    definition_id=comp_data["definition_id"],
                    x=comp_data["x"],
                    y=comp_data["y"],
                    rotation=comp_data.get("rotation", 0.0),
                    properties=comp_data.get("properties", {}),
                    sheet_id=comp_data.get("sheet_id"),
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
                    connection_type=conn_data.get("connection_type", "wire"),
                )
                self._connections[connection.connection_id] = connection

            for sheet_data in data.get("sheets", []):
                sheet = Sheet(
                    sheet_id=sheet_data["sheet_id"],
                    name=sheet_data["name"],
                    parent_id=sheet_data.get("parent_id"),
                    file_path=sheet_data.get("file_path"),
                    embedded=sheet_data.get("embedded", False),
                )
                self._sheets[sheet.sheet_id] = sheet

            if not self._sheets:
                self._ensure_root_sheet()

            self._active_sheet_id = data.get("active_sheet", self._active_sheet_id)
            if self._active_sheet_id not in self._sheets:
                self._active_sheet_id = next(iter(self._sheets))

            self.sheets_changed.emit()
            self.active_sheet_changed.emit(self._active_sheet_id)
            self.circuit_changed.emit()
            logger.info(f"Circuit loaded from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load circuit: {e}")
            return False

    # ------------------------------------------------------------------
    # State management helpers for undo/redo and tests
    # ------------------------------------------------------------------
    def export_circuit_state(self) -> Dict[str, Any]:
        return {
            "components": [
                {
                    "instance_id": c.instance_id,
                    "definition_id": c.definition_id,
                    "x": c.x,
                    "y": c.y,
                    "rotation": c.rotation,
                    "properties": copy.deepcopy(c.properties),
                    "sheet_id": c.sheet_id,
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
                    "connection_type": c.connection_type,
                }
                for c in self._connections.values()
            ],
            "sheets": [
                {
                    "sheet_id": s.sheet_id,
                    "name": s.name,
                    "parent_id": s.parent_id,
                    "file_path": s.file_path,
                    "embedded": s.embedded,
                }
                for s in self._sheets.values()
            ],
            "active_sheet": self._active_sheet_id,
        }

    def load_circuit_state(self, state: Dict[str, Any]):
        self.clear_circuit()
        self._sheets.clear()

        for comp_data in state.get("components", []):
            component = ComponentInstance(
                instance_id=comp_data["instance_id"],
                definition_id=comp_data["definition_id"],
                x=comp_data["x"],
                y=comp_data["y"],
                rotation=comp_data.get("rotation", 0.0),
                properties=copy.deepcopy(comp_data.get("properties", {})),
                sheet_id=comp_data.get("sheet_id"),
            )
            self._components[component.instance_id] = component

        for conn_data in state.get("connections", []):
            connection = Connection(
                connection_id=conn_data["connection_id"],
                from_component=conn_data["from_component"],
                from_pin=conn_data["from_pin"],
                to_component=conn_data["to_component"],
                to_pin=conn_data["to_pin"],
                wire_color=conn_data.get("wire_color", "#000000"),
                connection_type=conn_data.get("connection_type", "wire"),
            )
            self._connections[connection.connection_id] = connection

        for sheet_data in state.get("sheets", []):
            sheet = Sheet(
                sheet_id=sheet_data["sheet_id"],
                name=sheet_data["name"],
                parent_id=sheet_data.get("parent_id"),
                file_path=sheet_data.get("file_path"),
                embedded=sheet_data.get("embedded", False),
            )
            self._sheets[sheet.sheet_id] = sheet

        if not self._sheets:
            self._ensure_root_sheet()

        self._active_sheet_id = state.get("active_sheet", self._active_sheet_id)
        if self._active_sheet_id not in self._sheets:
            self._active_sheet_id = next(iter(self._sheets))

        self.sheets_changed.emit()
        self.active_sheet_changed.emit(self._active_sheet_id)
        self.circuit_changed.emit()


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
