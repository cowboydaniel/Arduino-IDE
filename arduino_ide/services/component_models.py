"""Core circuit component data models used by the circuit service."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ComponentType(Enum):
    """Supported circuit component types."""

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
    """Known pin electrical functions."""

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
    """Representation of a circuit symbol pin."""

    id: str
    label: str
    pin_type: PinType
    position: Tuple[float, float]


@dataclass
class ComponentDefinition:
    """High level circuit component definition."""

    id: str
    name: str
    component_type: ComponentType
    width: float
    height: float
    pins: List[Pin] = field(default_factory=list)
    image_path: Optional[str] = None
    description: str = ""
    datasheet_url: Optional[str] = None
    metadata: Dict[str, object] = field(default_factory=dict)
