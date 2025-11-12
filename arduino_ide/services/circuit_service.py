"""
Circuit Service
Manages circuit components, connections, and validation
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class CircuitSerializationError(Exception):
    """Raised when circuit data cannot be converted between formats."""


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


@dataclass
class ComponentInstance:
    """Instance of a component in the circuit"""
    instance_id: str
    definition_id: str
    x: float
    y: float
    rotation: float = 0.0  # Degrees
    properties: Dict[str, Any] = field(default_factory=dict)
    sheet_id: str = "root"


@dataclass
class Connection:
    """Connection between two pins"""
    connection_id: str
    from_component: str
    from_pin: str
    to_component: str
    to_pin: str
    wire_color: str = "#000000"


@dataclass
class Sheet:
    """Schematic sheet"""
    sheet_id: str
    name: str
    parent_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)


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

    def __init__(self, parent=None):
        super().__init__(parent)

        self._component_definitions: Dict[str, ComponentDefinition] = {}
        self._components: Dict[str, ComponentInstance] = {}
        self._connections: Dict[str, Connection] = {}
        self._sheets: Dict[str, Sheet] = {}
        self._root_sheet_id = "root"

        self._next_component_id = 1
        self._next_connection_id = 1
        self._next_sheet_index = 1

        self._reset_circuit_state()

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
        self._init_sheet_hierarchy(root_sheet_id, root_sheet_name)
        self._next_component_id = 1
        self._next_connection_id = 1

    def _generate_sheet_id(self) -> str:
        sheet_id = f"sheet_{self._next_sheet_index}"
        self._next_sheet_index += 1
        return sheet_id

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
                      wire_color: str = "#000000") -> Optional[Connection]:
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
            wire_color=wire_color
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
