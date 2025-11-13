"""Circuit Service utilities for circuit editing workflows."""

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
)

from arduino_ide.config import (
    KICAD_GLOBAL_SYMBOL_LIBRARY_PATHS,
    KICAD_PROJECT_CACHE_DIR,
)
from arduino_ide.services.kicad_symbol_adapter import KiCADSymbolAdapter

logger = logging.getLogger(__name__)

class CircuitSerializationError(Exception):
    """Raised when circuit data cannot be converted between formats."""


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

    def __init__(self, parent=None, symbol_adapter: Optional[KiCADSymbolAdapter] = None):
        super().__init__(parent)

        self._symbol_adapter = symbol_adapter or self._create_default_symbol_adapter()
        self._component_definitions: Dict[str, ComponentDefinition] = {}
        self._components: Dict[str, ComponentInstance] = {}
        self._connections: Dict[str, Connection] = {}
        self._sheets: Dict[str, Sheet] = {}
        self._sheet_templates: Dict[str, Sheet] = {}
        self._sheet_instances: Dict[str, SheetInstance] = {}
        self._nets: Dict[str, Net] = {}
        self._buses: Dict[str, Bus] = {}
        self._differential_pairs: Dict[str, DifferentialPair] = {}
        self._annotation_counters: Dict[ComponentType, int] = {}
        self._root_sheet_id = "root"
        self._active_sheet_id: Optional[str] = None

        self._next_component_id = 1
        self._next_connection_id = 1
        self._next_sheet_index = 1
        self._next_net_id = 1

        self._reset_circuit_state()

        # Initialize component library
        self._init_component_library()

        self._ensure_root_sheet()

        logger.info("Circuit service initialized")

    def _create_default_symbol_adapter(self) -> Optional[KiCADSymbolAdapter]:
        """Create a KiCAD symbol adapter using application configuration."""

        search_paths = [path for path in KICAD_GLOBAL_SYMBOL_LIBRARY_PATHS if path.exists()]
        if not search_paths:
            logger.warning("No KiCAD symbol library paths discovered from configuration")
            return None

        return KiCADSymbolAdapter(search_paths=search_paths, cache_dir=KICAD_PROJECT_CACHE_DIR)

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
        sheet_id = f"sheet_{self._next_sheet_index}"
        self._next_sheet_index += 1
        return sheet_id

    # ------------------------------------------------------------------
    # Sheet management APIs
    # ------------------------------------------------------------------
    def create_sheet(self, name: str, parent_id: Optional[str] = None, embedded: bool = False) -> Sheet:
        sheet_id = self._generate_sheet_id()
        parent = parent_id or self._active_sheet_id
        sheet = Sheet(sheet_id=sheet_id, name=name, parent_id=parent, embedded=embedded)
        self._sheets[sheet_id] = sheet
        if parent and parent in self._sheets:
            if sheet_id not in self._sheets[parent].children:
                self._sheets[parent].children.append(sheet_id)
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
        if not self._symbol_adapter:
            logger.warning("Component library adapter unavailable; circuit library is empty")
            return

        components = self._symbol_adapter.load_components()
        for component in components:
            self.register_component(component)

        logger.info(
            "Component library initialized with %s KiCAD symbol(s)",
            len(self._component_definitions),
        )

    def _init_sheet_hierarchy(self, root_sheet_id: str, root_sheet_name: str):
        """Initialize the sheet hierarchy with a root sheet."""
        self._root_sheet_id = root_sheet_id
        self._sheets = {
            root_sheet_id: Sheet(
                sheet_id=root_sheet_id,
                name=root_sheet_name,
                parent_id=None,
            )
        }
        self._next_sheet_index = 1

    def _reset_circuit_state(self, root_sheet_id: str = "root", root_sheet_name: str = "Root"):
        """Reset the mutable state for components, connections, and sheets."""
        self._components = {}
        self._connections = {}
        self._nets = {}
        self._buses = {}
        self._differential_pairs = {}
        self._sheet_instances = {}
        self._annotation_counters.clear()
        self._init_sheet_hierarchy(root_sheet_id, root_sheet_name)
        self._next_component_id = 1
        self._next_connection_id = 1
        self._next_net_id = 1
        self._active_sheet_id = None

    @staticmethod
    def _extract_numeric_suffix(value: str) -> int:
        digits = []
        for char in reversed(value):
            if char.isdigit():
                digits.append(char)
            else:
                break

        if not digits:
            return 0

        digits.reverse()
        return int("".join(digits))

    def _next_index_from_ids(self, identifiers: Iterable[str]) -> int:
        max_value = 0
        has_items = False
        for identifier in identifiers:
            has_items = True
            max_value = max(max_value, self._extract_numeric_suffix(identifier))

        if not has_items:
            return 1

        return max_value + 1

    def _refresh_counters(self):
        """Update ID counters based on the current objects."""
        self._next_component_id = self._next_index_from_ids(self._components.keys())
        self._next_connection_id = self._next_index_from_ids(self._connections.keys())

        sheet_numbers = [
            self._extract_numeric_suffix(sheet_id)
            for sheet_id in self._sheets.keys()
            if sheet_id.startswith("sheet_")
        ]
        max_sheet = max(sheet_numbers) if sheet_numbers else 0
        self._next_sheet_index = max_sheet + 1 if max_sheet > 0 else 1

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

    def create_bus(self, name: Optional[str] = None, nets: Optional[Iterable[str]] = None) -> Bus:
        """Create a bus and optionally attach existing nets to it."""

        if not name:
            name = f"BUS{len(self._buses) + 1}"

        if name in self._buses:
            raise ValueError(f"Bus '{name}' already exists")

        bus = Bus(name=name)
        self._buses[name] = bus

        for net_name in nets or []:
            net = self._nets.get(net_name) or self.create_net(net_name)
            net.bus = name
            bus.nets.add(net.name)

        return bus

    def get_bus(self, name: str) -> Optional[Bus]:
        """Return the bus by name if it exists."""

        return self._buses.get(name)

    def list_buses(self) -> List[Bus]:
        """Return all defined buses."""

        return list(self._buses.values())

    def define_differential_pair(
        self,
        name: str,
        positive_net: str,
        negative_net: str,
        bus_name: Optional[str] = None,
    ) -> DifferentialPair:
        """Create or update a differential pair association."""

        if positive_net not in self._nets or negative_net not in self._nets:
            raise ValueError("Differential pair nets must already exist")

        pair = DifferentialPair(name=name, positive_net=positive_net, negative_net=negative_net)
        self._differential_pairs[name] = pair

        for net_name in (positive_net, negative_net):
            net = self._nets[net_name]
            net.differential_pair = name
            if bus_name:
                bus = self._buses.get(bus_name) or self.create_bus(bus_name)
                bus.nets.add(net_name)
                bus.differential_pairs[name] = pair
                net.bus = bus.name

        return pair

    def get_differential_pair(self, name: str) -> Optional[DifferentialPair]:
        return self._differential_pairs.get(name)

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

    def add_component(
        self,
        component_id: str,
        x: float,
        y: float,
        sheet_id: Optional[str] = None,
    ) -> Optional[ComponentInstance]:
        """Add a component instance to the circuit"""
        comp_def = self.get_component_definition(component_id)
        if not comp_def:
            logger.error(f"Component definition not found: {component_id}")
            return None

        if sheet_id is None or sheet_id not in self._sheets:
            sheet_id = self._root_sheet_id

        instance_id = f"comp_{self._next_component_id}"
        self._next_component_id += 1

        instance = ComponentInstance(
            instance_id=instance_id,
            definition_id=component_id,
            x=x,
            y=y,
            sheet_id=sheet_id,
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


    def add_connection(
        self,
        from_component: str,
        from_pin: str,
        to_component: str,
        to_pin: str,
        wire_color: str = "#000000",
        connection_type: str = "wire",
        net_name: Optional[str] = None,
    ) -> Optional[Connection]:
        """Add a connection between two pins"""

        # Validate components exist
        if from_component not in self._components or to_component not in self._components:
            logger.error("Component not found in circuit")
            return None

        # Check if connection already exists
        for conn in self._connections.values():
            if (
                (conn.from_component == from_component and conn.from_pin == from_pin)
                or (conn.to_component == from_component and conn.to_pin == from_pin)
                or (conn.from_component == to_component and conn.from_pin == to_pin)
                or (conn.to_component == to_component and conn.to_pin == to_pin)
            ):
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

    def get_components_for_sheet(self, sheet_id: Optional[str] = None) -> List[ComponentInstance]:
        target_sheet = sheet_id or self.get_active_sheet_id()
        return [c for c in self._components.values() if c.sheet_id == target_sheet]


    def get_connections_for_sheet(self, sheet_id: Optional[str] = None) -> List[Connection]:
        """Return connections that belong to the specified sheet."""

        target_sheet = sheet_id or self.get_active_sheet_id()
        sheet_connections: List[Connection] = []

        for connection in self._connections.values():
            from_component = self._components.get(connection.from_component)
            to_component = self._components.get(connection.to_component)

            if (from_component and from_component.sheet_id == target_sheet) or (
                to_component and to_component.sheet_id == target_sheet
            ):
                sheet_connections.append(connection)

        return sheet_connections


    def get_circuit_connections(self) -> List[Connection]:
        """Get all connections in the circuit"""
        return list(self._connections.values())

    def get_root_sheet(self) -> Sheet:
        """Return the root sheet"""
        return self._sheets[self._root_sheet_id]

    def get_sheet(self, sheet_id: str) -> Optional[Sheet]:
        """Get a sheet by ID"""
        return self._sheets.get(sheet_id)

    def get_components_in_sheet(self, sheet_id: str) -> List[ComponentInstance]:
        """Return components that belong to the specified sheet"""
        return [c for c in self._components.values() if c.sheet_id == sheet_id]

    def add_sheet(
        self,
        name: str,
        parent_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        sheet_id: Optional[str] = None,
    ) -> Sheet:
        """Create a new sheet under the given parent."""
        if parent_id is None:
            parent_id = self._root_sheet_id

        if parent_id not in self._sheets:
            raise CircuitSerializationError(f"Parent sheet '{parent_id}' not found")

        if sheet_id is None:
            sheet_id = self._generate_sheet_id()
        elif sheet_id in self._sheets:
            raise CircuitSerializationError(f"Sheet '{sheet_id}' already exists")
        else:
            self._next_sheet_index = max(self._next_sheet_index, self._extract_numeric_suffix(sheet_id) + 1)

        sheet = Sheet(
            sheet_id=sheet_id,
            name=name,
            parent_id=parent_id,
            properties=properties or {},
        )
        self._sheets[sheet_id] = sheet
        self._sheets[parent_id].children.append(sheet_id)

        return sheet

    def assign_component_to_sheet(self, instance_id: str, sheet_id: str) -> bool:
        """Assign an existing component to a sheet"""
        if instance_id not in self._components or sheet_id not in self._sheets:
            return False

        self._components[instance_id].sheet_id = sheet_id
        self.circuit_changed.emit()
        return True


    def define_sheet(
        self,
        sheet_id: str,
        name: str,
        *,
        ports: Optional[Iterable[HierarchicalPort]] = None,
    ) -> Sheet:
        """Register a reusable sheet definition with optional hierarchical ports."""

        template = Sheet(sheet_id=sheet_id, name=name)
        if ports:
            template.ports = {port.name: copy.deepcopy(port) for port in ports}

        self._sheet_templates[sheet_id] = template
        return template

    def instantiate_sheet(
        self,
        sheet_id: str,
        parent_path: Tuple[str, ...] = tuple(),
    ) -> SheetInstance:
        """Instantiate a sheet definition within the design hierarchy."""

        template = self._sheet_templates.get(sheet_id)
        if not template:
            raise CircuitSerializationError(f"Sheet definition '{sheet_id}' not found")

        instance_index = len(template.instances) + 1
        instance_id = f"{sheet_id}_{instance_index}"
        sheet_instance = SheetInstance(
            instance_id=instance_id,
            sheet_id=sheet_id,
            parent_path=parent_path,
        )

        for port_name, port in template.ports.items():
            sheet_instance.ports[port_name] = copy.deepcopy(port)

        template.instances[instance_id] = sheet_instance
        self._sheet_instances[instance_id] = sheet_instance
        return sheet_instance

    def bind_port_to_net(self, instance_id: str, port_name: str, net_name: str) -> bool:
        """Bind a hierarchical port instance to a net."""

        instance = self._sheet_instances.get(instance_id)
        if not instance or port_name not in instance.ports:
            return False

        port = instance.ports[port_name]
        port.net_name = net_name
        self.assign_pin_to_net(
            instance_id,
            port_name,
            net_name,
            sheet_path=instance.parent_path,
            pin_type=port.pin_type,
            allow_virtual=True,
        )
        return True


    def run_electrical_rules_check(self) -> List[ElectricalRuleDiagnostic]:
        """Perform a lightweight electrical rule check similar to KiCAD."""

        diagnostics: List[ElectricalRuleDiagnostic] = []
        drive_pin_types = {
            PinType.POWER,
            PinType.DIGITAL,
            PinType.PWM,
            PinType.SPI,
            PinType.SERIAL,
        }

        for net in self._nets.values():
            if not net.nodes:
                continue

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

            has_power = any(node.pin_type == PinType.POWER for node in net.nodes)
            has_ground = any(node.pin_type == PinType.GROUND for node in net.nodes)
            if has_power and has_ground:
                diagnostics.append(
                    ElectricalRuleDiagnostic(
                        code="ERC_SHORT",
                        message=f"Power and ground pins shorted on net {net.name}",
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
        self._reset_circuit_state()
        self.circuit_changed.emit()
        logger.info("Circuit cleared")


    def save_circuit(self, file_path: str):
        """Save the circuit to either KiCAD or legacy JSON format."""
        path = Path(file_path)
        suffix = path.suffix.lower()

        try:
            if suffix == ".kicad_sch":
                content = self._serialize_to_kicad()
                path.write_text(content, encoding="utf-8")
                logger.info(f"Circuit saved to KiCAD schematic: {file_path}")
            elif suffix == ".json":
                self._save_legacy_json(path)
                logger.info(f"Circuit saved to legacy JSON: {file_path}")
            else:
                raise CircuitSerializationError(
                    f"Unsupported circuit file format: {path.suffix or 'unknown'}"
                )
        except OSError as exc:
            raise CircuitSerializationError(f"Failed to save circuit: {exc}") from exc

    def load_circuit(self, file_path: str):
        """Load a circuit from KiCAD schematic or legacy JSON."""
        path = Path(file_path)
        suffix = path.suffix.lower()

        try:
            if suffix == ".kicad_sch":
                content = path.read_text(encoding="utf-8")
                self._load_from_kicad(content)
                logger.info(f"Circuit loaded from KiCAD schematic: {file_path}")
            elif suffix == ".json":
                self._load_legacy_json(path)
                logger.info(f"Circuit loaded from legacy JSON: {file_path}")
            else:
                raise CircuitSerializationError(
                    f"Unsupported circuit file format: {path.suffix or 'unknown'}"
                )
        except OSError as exc:
            raise CircuitSerializationError(f"Failed to load circuit: {exc}") from exc

    def import_legacy_json(self, file_path: str):
        """Load a legacy JSON project for one-time migration."""
        path = Path(file_path)
        if path.suffix.lower() != ".json":
            raise CircuitSerializationError("Legacy import expects a JSON file")

        self._load_legacy_json(path)

    def export_to_kicad(self, file_path: str):
        """Explicit helper that always writes a KiCAD schematic."""
        path = Path(file_path)
        if path.suffix.lower() != ".kicad_sch":
            raise CircuitSerializationError("KiCAD export expects a .kicad_sch file")

        content = self._serialize_to_kicad()
        try:
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise CircuitSerializationError(f"Failed to write KiCAD schematic: {exc}") from exc

    def _save_legacy_json(self, path: Path):
        data = {
            "root_sheet_id": self._root_sheet_id,
            "sheets": [
                {
                    "sheet_id": sheet.sheet_id,
                    "name": sheet.name,
                    "parent_id": sheet.parent_id,
                    "properties": sheet.properties,
                    "children": list(sheet.children),
                }
                for sheet in self._sheets.values()
            ],
            "components": [
                {
                    "instance_id": c.instance_id,
                    "definition_id": c.definition_id,
                    "x": c.x,
                    "y": c.y,
                    "rotation": c.rotation,
                    "properties": c.properties,
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
                }
                for c in self._connections.values()
            ],
        }

        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_legacy_json(self, path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CircuitSerializationError(f"Invalid JSON: {exc}") from exc

        sheets_data = data.get("sheets") or []

        if sheets_data:
            root_sheet_id = data.get("root_sheet_id") or sheets_data[0].get("sheet_id", "root")
            root_sheet_name = next(
                (sheet.get("name", "Root") for sheet in sheets_data if sheet.get("sheet_id") == root_sheet_id),
                "Root",
            )
            root_properties = next(
                (sheet.get("properties", {}) for sheet in sheets_data if sheet.get("sheet_id") == root_sheet_id),
                {},
            )
            self._reset_circuit_state(root_sheet_id, root_sheet_name)
            self._sheets[root_sheet_id].properties = root_properties
        else:
            self._reset_circuit_state()

        if sheets_data:
            for sheet in self._sheets.values():
                sheet.children = []

            for sheet_data in sheets_data:
                sheet_id = sheet_data.get("sheet_id")
                if not sheet_id or sheet_id == self._root_sheet_id:
                    continue

                parent_id = sheet_data.get("parent_id") or self._root_sheet_id
                sheet = Sheet(
                    sheet_id=sheet_id,
                    name=sheet_data.get("name", sheet_id),
                    parent_id=parent_id,
                    properties=sheet_data.get("properties", {}),
                    children=[],
                )
                self._sheets[sheet_id] = sheet

            for sheet_data in sheets_data:
                sheet_id = sheet_data.get("sheet_id")
                if not sheet_id or sheet_id not in self._sheets:
                    continue
                children = [child for child in sheet_data.get("children", []) if child in self._sheets]
                self._sheets[sheet_id].children = children

            for sheet in self._sheets.values():
                if sheet.parent_id and sheet.parent_id in self._sheets:
                    parent = self._sheets[sheet.parent_id]
                    if sheet.sheet_id not in parent.children:
                        parent.children.append(sheet.sheet_id)

        self._components = {}
        for comp_data in data.get("components", []):
            sheet_id = comp_data.get("sheet_id", self._root_sheet_id)
            if sheet_id not in self._sheets:
                self._sheets[sheet_id] = Sheet(sheet_id=sheet_id, name=sheet_id, parent_id=self._root_sheet_id)
                self._sheets[self._root_sheet_id].children.append(sheet_id)

            component = ComponentInstance(
                instance_id=comp_data["instance_id"],
                definition_id=comp_data["definition_id"],
                x=comp_data["x"],
                y=comp_data["y"],
                rotation=comp_data.get("rotation", 0.0),
                properties=comp_data.get("properties", {}),
                sheet_id=sheet_id,
            )
            self._components[component.instance_id] = component

        self._connections = {}
        for conn_data in data.get("connections", []):
            connection = Connection(
                connection_id=conn_data["connection_id"],
                from_component=conn_data["from_component"],
                from_pin=conn_data["from_pin"],
                to_component=conn_data["to_component"],
                to_pin=conn_data["to_pin"],
                wire_color=conn_data.get("wire_color", "#000000"),
            )
            self._connections[connection.connection_id] = connection

        self._refresh_counters()
        self.circuit_changed.emit()

    def _serialize_to_kicad(self) -> str:
        tree: List[Any] = [
            "kicad_sch",
            ["version", "20211014"],
            ["generator", "Arduino Circuit Designer"],
            self._serialize_sheet_node(self.get_root_sheet()),
        ]

        for code, connection in enumerate(sorted(self._connections.values(), key=lambda c: c.connection_id), start=1):
            tree.append(self._serialize_net_node(connection, code))

        return _sexpr_format(tree)

    def _serialize_sheet_node(self, sheet: Sheet) -> List[Any]:
        node: List[Any] = [
            "sheet",
            ["id", sheet.sheet_id],
            ["name", sheet.name],
        ]

        for key, value in sorted(sheet.properties.items()):
            node.append(["property", key, self._stringify_property(value)])

        for component in sorted(self.get_components_in_sheet(sheet.sheet_id), key=lambda c: c.instance_id):
            node.append(self._serialize_symbol_node(component))

        for child_id in sheet.children:
            child = self._sheets.get(child_id)
            if child:
                node.append(self._serialize_sheet_node(child))

        return node

    def _serialize_symbol_node(self, component: ComponentInstance) -> List[Any]:
        node: List[Any] = [
            "symbol",
            ["lib_id", component.definition_id],
            ["reference", component.instance_id],
            [
                "at",
                f"{component.x:.4f}",
                f"{component.y:.4f}",
                f"{component.rotation:.4f}",
            ],
            ["property", "sheet_id", component.sheet_id],
        ]

        comp_def = self.get_component_definition(component.definition_id)
        if comp_def:
            node.append(["property", "component_name", comp_def.name])
            node.append(["property", "component_type", comp_def.component_type.value])

        for key, value in sorted(component.properties.items()):
            node.append(["property", key, self._stringify_property(value)])

        return node

    def _serialize_net_node(self, connection: Connection, code: int) -> List[Any]:
        return [
            "net",
            ["code", str(code)],
            ["name", connection.connection_id],
            ["property", "connection_id", connection.connection_id],
            ["property", "wire_color", connection.wire_color],
            ["node", ["ref", connection.from_component], ["pin", connection.from_pin]],
            ["node", ["ref", connection.to_component], ["pin", connection.to_pin]],
        ]

    @staticmethod
    def _stringify_property(value: Any) -> str:
        return json.dumps(value)

    @staticmethod
    def _parse_property_value(value: str) -> Any:
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value

    def _load_from_kicad(self, content: str):
        try:
            tree = _sexpr_parse(content)
        except ValueError as exc:
            raise CircuitSerializationError(f"Invalid KiCAD schematic: {exc}") from exc

        if not tree or tree[0] != "kicad_sch":
            raise CircuitSerializationError("File is not a KiCAD schematic")

        sheet_node = next((child for child in tree[1:] if _sexpr_is(child, "sheet")), None)
        if not sheet_node:
            raise CircuitSerializationError("Schematic missing root sheet")

        root_sheet_id = _sexpr_child_value(sheet_node, "id") or "root"
        root_sheet_name = _sexpr_child_value(sheet_node, "name") or "Root"
        raw_properties = _sexpr_collect_properties(sheet_node)
        root_properties = {key: self._parse_property_value(value) for key, value in raw_properties.items()}

        self._reset_circuit_state(root_sheet_id, root_sheet_name)
        self._sheets[root_sheet_id].properties = root_properties
        self._populate_sheet_from_node(sheet_node, None, is_root=True)

        self._connections = {}
        for child in tree[1:]:
            if _sexpr_is(child, "net"):
                self._create_connection_from_node(child)

        self._refresh_counters()
        self.circuit_changed.emit()

    def _populate_sheet_from_node(
        self,
        node: List[Any],
        parent_id: Optional[str],
        is_root: bool = False,
    ):
        sheet_id = _sexpr_child_value(node, "id") or self._generate_sheet_id()
        sheet_name = _sexpr_child_value(node, "name") or sheet_id
        raw_properties = _sexpr_collect_properties(node)
        properties = {key: self._parse_property_value(value) for key, value in raw_properties.items()}

        if is_root:
            sheet_id = self._root_sheet_id
            sheet = self._sheets[sheet_id]
            sheet.name = sheet_name
            sheet.properties = properties
            sheet.children = []
        else:
            parent_ref = parent_id or self._root_sheet_id
            if sheet_id in self._sheets:
                sheet = self._sheets[sheet_id]
                sheet.name = sheet_name
                sheet.parent_id = parent_ref
                sheet.properties = properties
                sheet.children = []
            else:
                sheet = self.add_sheet(sheet_name, parent_ref, properties, sheet_id=sheet_id)
                sheet.children = []

        for child in node[1:]:
            if isinstance(child, list) and child:
                if child[0] == "symbol":
                    self._create_component_from_symbol(child, sheet_id)
                elif child[0] == "sheet":
                    self._populate_sheet_from_node(child, sheet_id)

    def _create_component_from_symbol(self, node: List[Any], sheet_id: str):
        lib_id = _sexpr_child_value(node, "lib_id")
        if not lib_id:
            raise CircuitSerializationError("Symbol missing lib_id")

        reference = _sexpr_child_value(node, "reference") or f"comp_{self._next_component_id}"
        at_values = _sexpr_child_values(node, "at")
        x = float(at_values[0]) if len(at_values) >= 1 else 0.0
        y = float(at_values[1]) if len(at_values) >= 2 else 0.0
        rotation = float(at_values[2]) if len(at_values) >= 3 else 0.0
        properties = _sexpr_collect_properties(node)
        for system_key in ("sheet_id", "component_name", "component_type"):
            properties.pop(system_key, None)
        decoded_properties = {
            key: self._parse_property_value(value)
            for key, value in properties.items()
        }

        if reference in self._components:
            raise CircuitSerializationError(f"Duplicate component reference '{reference}'")

        component = ComponentInstance(
            instance_id=reference,
            definition_id=lib_id,
            x=x,
            y=y,
            rotation=rotation,
            properties=decoded_properties,
            sheet_id=sheet_id,
        )
        self._components[component.instance_id] = component

    def _create_connection_from_node(self, node: List[Any]):
        properties = _sexpr_collect_properties(node)
        node_entries = [child for child in node[1:] if _sexpr_is(child, "node")]

        if len(node_entries) != 2:
            raise CircuitSerializationError("Each net must describe exactly two nodes")

        refs = []
        for entry in node_entries:
            ref = _sexpr_child_value(entry, "ref")
            pin = _sexpr_child_value(entry, "pin")
            if not ref or not pin:
                raise CircuitSerializationError("Net node missing ref or pin")
            refs.append((ref, pin))

        connection_id = properties.get("connection_id") or f"conn_{self._next_connection_id}"
        connection = Connection(
            connection_id=connection_id,
            from_component=refs[0][0],
            from_pin=refs[0][1],
            to_component=refs[1][0],
            to_pin=refs[1][1],
            wire_color=properties.get("wire_color", "#000000"),
        )
        self._connections[connection.connection_id] = connection

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


def _sexpr_format(node: Any) -> str:
    if isinstance(node, list):
        return "(" + " ".join(_sexpr_format(child) for child in node) + ")"
    return _sexpr_atom(node)


def _sexpr_atom(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return str(value)

    text = str(value)
    if not text:
        return '""'

    needs_quotes = any(ch.isspace() or ch in '()"' for ch in text)
    if needs_quotes:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _sexpr_parse(text: str) -> Any:
    tokens = _sexpr_tokenize(text)
    if not tokens:
        return []

    node, index = _sexpr_parse_tokens(tokens, 0)
    if index != len(tokens):
        raise ValueError("Unexpected tokens after parsing expression")
    return node


def _sexpr_parse_tokens(tokens: List[str], index: int):
    if tokens[index] != "(":
        return tokens[index], index + 1

    items: List[Any] = []
    index += 1
    while index < len(tokens) and tokens[index] != ")":
        token = tokens[index]
        if token == "(":
            child, index = _sexpr_parse_tokens(tokens, index)
            items.append(child)
        else:
            items.append(token)
            index += 1

    if index >= len(tokens):
        raise ValueError("Missing closing parenthesis")

    return items, index + 1


def _sexpr_tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    i = 0
    length = len(text)

    while i < length:
        char = text[i]
        if char in "()":
            tokens.append(char)
            i += 1
        elif char.isspace():
            i += 1
        elif char == '"':
            i += 1
            buffer = []
            while i < length:
                if text[i] == '\\':
                    if i + 1 >= length:
                        raise ValueError("Invalid escape in string literal")
                    buffer.append(text[i + 1])
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                buffer.append(text[i])
                i += 1
            else:
                raise ValueError("Unterminated string literal")
            tokens.append("".join(buffer))
        else:
            start = i
            while i < length and not text[i].isspace() and text[i] not in "()":
                i += 1
            tokens.append(text[start:i])

    return tokens


def _sexpr_child_value(node: List[Any], name: str, default=None):
    child = _sexpr_child(node, name)
    if child is None:
        return default

    if len(child) == 2:
        return child[1]

    return child[1:]


def _sexpr_child_values(node: List[Any], name: str) -> List[Any]:
    child = _sexpr_child(node, name)
    if child is None:
        return []
    return child[1:]


def _sexpr_child(node: List[Any], name: str) -> Optional[List[Any]]:
    for child in node[1:]:
        if isinstance(child, list) and child and child[0] == name:
            return child
    return None


def _sexpr_is(node: Any, name: str) -> bool:
    return isinstance(node, list) and bool(node) and node[0] == name


def _sexpr_collect_properties(node: List[Any]) -> Dict[str, str]:
    properties: Dict[str, str] = {}
    for child in node[1:]:
        if _sexpr_is(child, "property") and len(child) >= 3:
            key = str(child[1])
            value = child[2]
            if isinstance(value, list):
                value = " ".join(str(part) for part in value)
            properties[key] = str(value)
    return properties
