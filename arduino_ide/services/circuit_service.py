"""
Circuit Service
Manages circuit components, connections, and validation
"""

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


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
    """
    Service for managing circuit design and validation
    """

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

    def __init__(self, parent=None):
        super().__init__(parent)

        self._component_definitions: Dict[str, ComponentDefinition] = {}
        self._components: Dict[str, ComponentInstance] = {}
        self._connections: Dict[str, Connection] = {}

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

    def get_component_instance(self, instance_id: str) -> Optional[ComponentInstance]:
        return self._components.get(instance_id)


    def get_all_component_definitions(self) -> List[ComponentDefinition]:
        """Get all component definitions"""
        return list(self._component_definitions.values())


    def get_components_by_type(self, component_type: ComponentType) -> List[ComponentDefinition]:
        """Get components of a specific type"""
        return [c for c in self._component_definitions.values() if c.component_type == component_type]


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

        del self._components[instance_id]
        self.component_removed.emit(instance_id)
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

        del self._connections[connection_id]
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


    def validate_circuit(self) -> Tuple[bool, List[str]]:
        """
        Validate the circuit for common errors
        Returns (is_valid, list_of_errors)
        """
        errors = []

        # Check for Arduino board
        arduino_boards = [c for c in self._components.values()
                         if self.get_component_definition(c.definition_id).component_type == ComponentType.ARDUINO_BOARD]

        if not arduino_boards:
            errors.append("No Arduino board in circuit")

        # Check for floating pins
        connected_pins = set()
        for conn in self._connections.values():
            connected_pins.add((conn.from_component, conn.from_pin))
            connected_pins.add((conn.to_component, conn.to_pin))

        # Check power connections
        for component in self._components.values():
            comp_def = self.get_component_definition(component.definition_id)

            # Skip Arduino and breadboard
            if comp_def.component_type in (ComponentType.ARDUINO_BOARD, ComponentType.BREADBOARD):
                continue

            # Check if component has power connections
            power_pins = [p for p in comp_def.pins if p.pin_type == PinType.POWER]
            ground_pins = [p for p in comp_def.pins if p.pin_type == PinType.GROUND]

            has_power = any((component.instance_id, p.id) in connected_pins for p in power_pins)
            has_ground = any((component.instance_id, p.id) in connected_pins for p in ground_pins)

            if power_pins and not has_power:
                errors.append(f"{comp_def.name} ({component.instance_id}) has no power connection")

            if ground_pins and not has_ground:
                errors.append(f"{comp_def.name} ({component.instance_id}) has no ground connection")

        is_valid = len(errors) == 0

        self.circuit_validated.emit(is_valid, errors)

        return is_valid, errors


    def clear_circuit(self):
        """Clear all components and connections"""
        self._components.clear()
        self._connections.clear()
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

            line = f"{from_def.name} ({conn.from_pin}) -> {to_def.name} ({conn.to_pin})"
            lines.append(line)

        return "\n".join(lines)
