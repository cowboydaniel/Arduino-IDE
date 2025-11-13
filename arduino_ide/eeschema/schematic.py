"""
Schematic - Core schematic data model
Based on KiCad's schematic.cpp/h structure
"""

import copy
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


class Schematic(QObject):
    """
    Core schematic model managing components, connections, sheets and electrical rules.
    Corresponds to KiCad's SCHEMATIC class.
    """

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

        logger.info("Schematic model initialized")

    def _create_default_symbol_adapter(self) -> KiCADSymbolAdapter:
        """Create default KiCAD symbol adapter"""
        return KiCADSymbolAdapter(
            library_paths=KICAD_GLOBAL_SYMBOL_LIBRARY_PATHS,
            cache_dir=KICAD_PROJECT_CACHE_DIR
        )

    def _reset_circuit_state(self):
        """Reset all circuit state"""
        self._component_definitions.clear()
        self._components.clear()
        self._connections.clear()
        self._sheets.clear()
        self._sheet_templates.clear()
        self._sheet_instances.clear()
        self._nets.clear()
        self._buses.clear()
        self._differential_pairs.clear()
        self._annotation_counters.clear()
        self._next_component_id = 1
        self._next_connection_id = 1
        self._next_sheet_index = 1
        self._next_net_id = 1

    def _init_component_library(self):
        """Initialize component definitions from KiCAD symbol libraries"""
        logger.info("Loading KiCAD symbol libraries...")
        try:
            all_symbols = self._symbol_adapter.get_all_symbols()
            for symbol_name, definition in all_symbols.items():
                self._component_definitions[definition.id] = definition
            logger.info(f"Loaded {len(self._component_definitions)} component definitions")
        except Exception as e:
            logger.error(f"Failed to load symbol libraries: {e}")

    def _ensure_root_sheet(self):
        """Ensure root sheet exists"""
        if self._root_sheet_id not in self._sheets:
            root = Sheet(
                sheet_id=self._root_sheet_id,
                name="Root",
                file_path=None,
                parent_id=None,
            )
            self._sheets[self._root_sheet_id] = root
            self._active_sheet_id = self._root_sheet_id
            self.sheets_changed.emit()

    # Component management
    def add_component(self, definition_id: str, x: float, y: float, sheet_id: Optional[str] = None) -> str:
        """Add a component instance to the schematic"""
        if definition_id not in self._component_definitions:
            raise ValueError(f"Component definition '{definition_id}' not found")

        if sheet_id is None:
            sheet_id = self._active_sheet_id or self._root_sheet_id

        instance_id = f"comp_{self._next_component_id}"
        self._next_component_id += 1

        comp_def = self._component_definitions[definition_id]
        reference = self._generate_reference(comp_def.component_type)

        instance = ComponentInstance(
            instance_id=instance_id,
            definition_id=definition_id,
            x=x,
            y=y,
            rotation=0.0,
            sheet_id=sheet_id,
            properties={"reference": reference, "value": ""},
        )

        self._components[instance_id] = instance
        self.component_added.emit(instance_id)
        self.circuit_changed.emit()
        return instance_id

    def _generate_reference(self, comp_type: ComponentType) -> str:
        """Generate unique reference designator"""
        prefix = self._ANNOTATION_PREFIXES.get(comp_type, "U")
        counter = self._annotation_counters.get(comp_type, 0) + 1
        self._annotation_counters[comp_type] = counter
        return f"{prefix}{counter}"

    def remove_component(self, instance_id: str):
        """Remove a component from the schematic"""
        if instance_id not in self._components:
            return

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

    def move_component(self, instance_id: str, x: float, y: float):
        """Move a component to a new position"""
        if instance_id not in self._components:
            return
        self._components[instance_id].x = x
        self._components[instance_id].y = y
        self.component_moved.emit(instance_id, x, y)
        self.circuit_changed.emit()

    def get_component_instance(self, instance_id: str) -> Optional[ComponentInstance]:
        """Get component instance by ID"""
        return self._components.get(instance_id)

    def get_component_definition(self, definition_id: str) -> Optional[ComponentDefinition]:
        """Get component definition by ID"""
        return self._component_definitions.get(definition_id)

    def get_all_component_definitions(self) -> List[ComponentDefinition]:
        """Get all component definitions"""
        return list(self._component_definitions.values())

    def update_component_properties(self, instance_id: str, properties: Dict[str, Any]):
        """Update component properties"""
        if instance_id not in self._components:
            return
        self._components[instance_id].properties.update(properties)
        self.circuit_changed.emit()

    # Connection management
    def add_connection(
        self,
        from_component: str,
        from_pin: str,
        to_component: str,
        to_pin: str,
        wire_color: str = "#424242",
        connection_type: str = "wire",
        sheet_id: Optional[str] = None,
    ) -> str:
        """Add a connection between two pins"""
        if sheet_id is None:
            sheet_id = self._active_sheet_id or self._root_sheet_id

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
            sheet_id=sheet_id,
        )

        self._connections[connection_id] = connection
        self.connection_added.emit(connection_id)
        self.circuit_changed.emit()
        return connection_id

    def remove_connection(self, connection_id: str):
        """Remove a connection"""
        if connection_id not in self._connections:
            return
        del self._connections[connection_id]
        self.connection_removed.emit(connection_id)
        self.circuit_changed.emit()

    # Sheet management
    def create_sheet(self, name: str, parent_id: Optional[str] = None) -> Sheet:
        """Create a new sheet"""
        sheet_id = f"sheet_{self._next_sheet_index}"
        self._next_sheet_index += 1

        if parent_id is None:
            parent_id = self._active_sheet_id or self._root_sheet_id

        sheet = Sheet(
            sheet_id=sheet_id,
            name=name,
            file_path=None,
            parent_id=parent_id,
        )

        self._sheets[sheet_id] = sheet
        self.sheets_changed.emit()
        return sheet

    def get_sheets(self) -> List[Sheet]:
        """Get all sheets"""
        return list(self._sheets.values())

    def get_active_sheet_id(self) -> Optional[str]:
        """Get active sheet ID"""
        return self._active_sheet_id

    def set_active_sheet(self, sheet_id: str):
        """Set active sheet"""
        if sheet_id not in self._sheets:
            return
        self._active_sheet_id = sheet_id
        self.active_sheet_changed.emit(sheet_id)

    def get_components_for_sheet(self, sheet_id: Optional[str]) -> List[ComponentInstance]:
        """Get all components for a sheet"""
        if sheet_id is None:
            sheet_id = self._active_sheet_id or self._root_sheet_id
        return [comp for comp in self._components.values() if comp.sheet_id == sheet_id]

    def get_connections_for_sheet(self, sheet_id: Optional[str]) -> List[Connection]:
        """Get all connections for a sheet"""
        if sheet_id is None:
            sheet_id = self._active_sheet_id or self._root_sheet_id
        return [conn for conn in self._connections.values() if conn.sheet_id == sheet_id]

    # Validation
    def validate_circuit(self) -> Tuple[bool, List[str]]:
        """Validate circuit and check for ERC violations"""
        errors = []

        # Check for unconnected pins
        for comp_id, comp in self._components.items():
            comp_def = self._component_definitions.get(comp.definition_id)
            if not comp_def:
                continue

            connected_pins = set()
            for conn in self._connections.values():
                if conn.from_component == comp_id:
                    connected_pins.add(conn.from_pin)
                if conn.to_component == comp_id:
                    connected_pins.add(conn.to_pin)

            for pin in comp_def.pins:
                if pin.pin_type in (PinType.POWER, PinType.GROUND) and pin.id not in connected_pins:
                    errors.append(f"Unconnected {pin.pin_type.value} pin: {comp_id}.{pin.id}")

        is_valid = len(errors) == 0
        self.circuit_validated.emit(is_valid, errors)
        return is_valid, errors

    # State management
    def export_circuit_state(self) -> Dict:
        """Export circuit state for serialization"""
        return {
            "components": {k: v.__dict__ for k, v in self._components.items()},
            "connections": {k: v.__dict__ for k, v in self._connections.items()},
            "sheets": {k: v.__dict__ for k, v in self._sheets.items()},
            "active_sheet_id": self._active_sheet_id,
        }

    def load_circuit_state(self, state: Dict):
        """Load circuit state from serialization"""
        self._reset_circuit_state()
        # TODO: Implement full state loading
        self.circuit_changed.emit()

    def clear_circuit(self):
        """Clear all circuit data"""
        self._reset_circuit_state()
        self._ensure_root_sheet()
        self.circuit_changed.emit()
