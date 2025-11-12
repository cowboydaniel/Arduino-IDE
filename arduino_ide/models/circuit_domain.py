"""Circuit domain models used by the circuit service."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ComponentType(Enum):
    """Types of circuit components."""

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
    """Types of pins."""

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
    """Pin on a component."""

    id: str
    label: str
    pin_type: PinType
    position: Tuple[float, float]


@dataclass
class ComponentDefinition:
    """Definition of a circuit component."""

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
class SymbolUnit:
    """Represents a symbol unit for multi-unit components."""

    unit_id: str
    name: str
    pins: List[Pin] = field(default_factory=list)


@dataclass
class HierarchicalPort:
    """Represents a hierarchical port for sheet interfaces."""

    name: str
    pin_type: PinType
    direction: str = "bidirectional"
    net_name: Optional[str] = None


@dataclass
class SheetInstance:
    """Concrete instantiation of a sheet in the hierarchy."""

    instance_id: str
    sheet_id: str
    parent_path: Tuple[str, ...] = field(default_factory=tuple)
    ports: Dict[str, HierarchicalPort] = field(default_factory=dict)


@dataclass
class Sheet:
    """Hierarchical sheet definition."""

    sheet_id: str
    name: str
    symbol_units: Dict[str, SymbolUnit] = field(default_factory=dict)
    ports: Dict[str, HierarchicalPort] = field(default_factory=dict)
    instances: Dict[str, SheetInstance] = field(default_factory=dict)


@dataclass
class ComponentInstance:
    """Instance of a component in the circuit."""

    instance_id: str
    definition_id: str
    x: float
    y: float
    rotation: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)
    annotation: Optional[str] = None
    sheet_path: Tuple[str, ...] = field(default_factory=tuple)
    unit_assignments: Dict[str, str] = field(default_factory=dict)


@dataclass
class NetNode:
    """Represents a pin that participates in a net."""

    component_id: str
    pin_id: str
    pin_type: PinType
    sheet_path: Tuple[str, ...] = field(default_factory=tuple)


@dataclass
class Net:
    """Electrical net grouping multiple pins."""

    name: str
    nodes: List[NetNode] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    bus: Optional[str] = None
    differential_pair: Optional[str] = None


@dataclass
class DifferentialPair:
    """Differential pair definition linking two nets."""

    name: str
    positive_net: str
    negative_net: str


@dataclass
class Bus:
    """A bus that aggregates multiple nets."""

    name: str
    nets: Set[str] = field(default_factory=set)
    differential_pairs: Dict[str, DifferentialPair] = field(default_factory=dict)


@dataclass
class Connection:
    """Connection between two pins."""

    connection_id: str
    from_component: str
    from_pin: str
    to_component: str
    to_pin: str
    wire_color: str = "#000000"
    net_name: Optional[str] = None


@dataclass
class ElectricalRuleDiagnostic:
    """Represents a validation diagnostic."""

    code: str
    message: str
    severity: str = "error"
    related_net: Optional[str] = None
    related_component: Optional[str] = None
