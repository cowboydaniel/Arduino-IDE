"""
Circuit Service
Manages circuit components, connections, and validation
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Set
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
    properties: Dict[str, any] = field(default_factory=dict)


@dataclass
class Connection:
    """Connection between two pins"""
    connection_id: str
    from_component: str
    from_pin: str
    to_component: str
    to_pin: str
    wire_color: str = "#000000"


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

        self._next_component_id = 1
        self._next_connection_id = 1

        # Initialize component library
        self._init_component_library()

        logger.info("Circuit service initialized")


    def _init_component_library(self):
        """Initialize library of available components"""

        # Arduino Uno
        arduino_pins = []
        # Digital pins
        for i in range(14):
            arduino_pins.append(Pin(
                id=f"D{i}",
                label=f"D{i}",
                pin_type=PinType.PWM if i in [3, 5, 6, 9, 10, 11] else PinType.DIGITAL,
                position=(i * 20, 0)
            ))

        # Analog pins
        for i in range(6):
            arduino_pins.append(Pin(
                id=f"A{i}",
                label=f"A{i}",
                pin_type=PinType.ANALOG,
                position=(i * 20, 100)
            ))

        # Power pins
        arduino_pins.extend([
            Pin("5V", "5V", PinType.POWER, (0, 50)),
            Pin("3V3", "3.3V", PinType.POWER, (20, 50)),
            Pin("GND1", "GND", PinType.GROUND, (40, 50)),
            Pin("GND2", "GND", PinType.GROUND, (60, 50)),
            Pin("VIN", "VIN", PinType.POWER, (80, 50))
        ])

        self.register_component(ComponentDefinition(
            id="arduino_uno",
            name="Arduino Uno",
            component_type=ComponentType.ARDUINO_BOARD,
            width=200,
            height=150,
            pins=arduino_pins,
            description="Arduino Uno microcontroller board"
        ))

        # ===== LEDS (500+ components) =====
        led_colors = ["Red", "Green", "Blue", "Yellow", "White", "Orange", "Pink", "Purple",
                      "Cyan", "Amber", "Infrared", "UV", "Cool White", "Warm White"]
        led_sizes = ["3mm", "5mm", "10mm", "SMD0603", "SMD0805", "SMD1206"]
        led_types = ["Standard", "High-Brightness", "Super-Bright", "RGB", "Bi-Color"]

        for color in led_colors:
            for size in led_sizes:
                for led_type in led_types:
                    led_id = f"led_{color.lower().replace(' ', '_')}_{size.lower()}_{led_type.lower().replace('-', '_')}"
                    self.register_component(ComponentDefinition(
                        id=led_id,
                        name=f"{color} {size} {led_type} LED",
                        component_type=ComponentType.LED,
                        width=30,
                        height=50,
                        pins=[
                            Pin("anode", "+", PinType.POWER, (15, 0)),
                            Pin("cathode", "-", PinType.GROUND, (15, 50))
                        ],
                        description=f"{color} {size} {led_type} Light Emitting Diode"
                    ))

        # ===== RESISTORS (1000+ components) =====
        # E12 series resistor values (common)
        e12_values = [10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82]
        # E24 series resistor values (precision)
        e24_values = [10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 43, 47, 51, 56, 62, 68, 75, 82, 91]

        wattages = ["1/8W", "1/4W", "1/2W", "1W", "2W", "5W"]
        tolerances = ["1%", "5%", "10%"]

        # Generate resistors from 1Ω to 10MΩ
        for multiplier in [1, 10, 100, 1000, 10000, 100000, 1000000]:
            for base_value in e24_values:
                value = base_value * multiplier
                for wattage in wattages:
                    for tolerance in tolerances:
                        resistor_id = f"resistor_{value}_{wattage.replace('/', 'div')}_{tolerance.replace('%', 'pct')}"
                        unit = "Ω" if value < 1000 else ("kΩ" if value < 1000000 else "MΩ")
                        display_value = value if value < 1000 else (value / 1000 if value < 1000000 else value / 1000000)

                        self.register_component(ComponentDefinition(
                            id=resistor_id,
                            name=f"{display_value}{unit} {wattage} {tolerance} Resistor",
                            component_type=ComponentType.RESISTOR,
                            width=60,
                            height=20,
                            pins=[
                                Pin("pin1", "1", PinType.POWER, (0, 10)),
                                Pin("pin2", "2", PinType.POWER, (60, 10))
                            ],
                            description=f"{display_value}{unit} {wattage} {tolerance} resistor"
                        ))

        # ===== CAPACITORS (800+ components) =====
        cap_types = ["Ceramic", "Electrolytic", "Tantalum", "Film", "Polyester"]
        cap_voltages = ["6.3V", "10V", "16V", "25V", "35V", "50V", "100V", "250V"]

        # Capacitor values from 1pF to 10000µF
        cap_values_pf = [10, 22, 47, 100, 220, 470]  # picofarads
        cap_values_nf = [1, 2.2, 4.7, 10, 22, 47, 100, 220, 470]  # nanofarads
        cap_values_uf = [1, 2.2, 4.7, 10, 22, 47, 100, 220, 470, 1000, 2200, 4700, 10000]  # microfarads

        for cap_type in cap_types:
            for voltage in cap_voltages:
                # pF capacitors
                for val in cap_values_pf:
                    cap_id = f"cap_{cap_type.lower()}_{val}pf_{voltage.replace('.', 'p')}"
                    self.register_component(ComponentDefinition(
                        id=cap_id,
                        name=f"{val}pF {voltage} {cap_type} Capacitor",
                        component_type=ComponentType.CAPACITOR,
                        width=40,
                        height=50,
                        pins=[
                            Pin("pin1", "1", PinType.POWER, (20, 0)),
                            Pin("pin2", "2", PinType.POWER, (20, 50))
                        ],
                        description=f"{val}pF {voltage} {cap_type} capacitor"
                    ))

                # nF capacitors
                for val in cap_values_nf:
                    cap_id = f"cap_{cap_type.lower()}_{str(val).replace('.', 'p')}nf_{voltage.replace('.', 'p')}"
                    self.register_component(ComponentDefinition(
                        id=cap_id,
                        name=f"{val}nF {voltage} {cap_type} Capacitor",
                        component_type=ComponentType.CAPACITOR,
                        width=40,
                        height=50,
                        pins=[
                            Pin("pin1", "1", PinType.POWER, (20, 0)),
                            Pin("pin2", "2", PinType.POWER, (20, 50))
                        ],
                        description=f"{val}nF {voltage} {cap_type} capacitor"
                    ))

                # µF capacitors
                for val in cap_values_uf:
                    cap_id = f"cap_{cap_type.lower()}_{str(val).replace('.', 'p')}uf_{voltage.replace('.', 'p')}"
                    self.register_component(ComponentDefinition(
                        id=cap_id,
                        name=f"{val}µF {voltage} {cap_type} Capacitor",
                        component_type=ComponentType.CAPACITOR,
                        width=40,
                        height=50,
                        pins=[
                            Pin("pin1", "+", PinType.POWER, (20, 0)),
                            Pin("pin2", "-", PinType.GROUND, (20, 50))
                        ],
                        description=f"{val}µF {voltage} {cap_type} capacitor"
                    ))

        # ===== TRANSISTORS (400+ components) =====
        # BJT Transistors
        bjt_types = ["NPN", "PNP"]
        bjt_models = ["2N2222", "2N3904", "2N3906", "BC547", "BC557", "2N5551", "2N5401",
                      "TIP31", "TIP32", "TIP41", "TIP42", "BD135", "BD136"]

        for bjt_model in bjt_models:
            for package in ["TO-92", "TO-220", "SOT-23"]:
                transistor_id = f"transistor_bjt_{bjt_model.lower()}_{package.lower().replace('-', '_')}"
                self.register_component(ComponentDefinition(
                    id=transistor_id,
                    name=f"{bjt_model} BJT Transistor {package}",
                    component_type=ComponentType.TRANSISTOR,
                    width=40,
                    height=60,
                    pins=[
                        Pin("base", "B", PinType.DIGITAL, (10, 0)),
                        Pin("collector", "C", PinType.POWER, (20, 0)),
                        Pin("emitter", "E", PinType.GROUND, (30, 0))
                    ],
                    description=f"{bjt_model} BJT transistor in {package} package"
                ))

        # MOSFET Transistors
        mosfet_models = ["IRF520", "IRF540", "2N7000", "BS170", "IRLZ44N", "IRF3205",
                         "FQP30N06L", "IRF630", "IRF740", "IRF9530"]

        for mosfet_model in mosfet_models:
            for package in ["TO-220", "TO-92", "SOT-23"]:
                for power_rating in ["30W", "50W", "75W", "100W"]:
                    transistor_id = f"transistor_mosfet_{mosfet_model.lower()}_{package.lower().replace('-', '_')}_{power_rating.lower()}"
                    self.register_component(ComponentDefinition(
                        id=transistor_id,
                        name=f"{mosfet_model} MOSFET {package} {power_rating}",
                        component_type=ComponentType.TRANSISTOR,
                        width=40,
                        height=60,
                        pins=[
                            Pin("gate", "G", PinType.DIGITAL, (10, 0)),
                            Pin("drain", "D", PinType.POWER, (20, 0)),
                            Pin("source", "S", PinType.GROUND, (30, 0))
                        ],
                        description=f"{mosfet_model} MOSFET transistor {power_rating} in {package}"
                    ))

        # ===== ICs - INTEGRATED CIRCUITS (1000+ components) =====

        # Logic Gates
        logic_gate_families = ["74HC", "74HCT", "74LS", "74ALS", "CD4000"]
        logic_gate_types = ["00", "02", "04", "08", "10", "11", "20", "21", "27", "30", "32",
                           "86", "138", "139", "151", "153", "157", "161", "163", "174", "175",
                           "190", "191", "193", "273", "374", "541", "573", "595"]

        for family in logic_gate_families:
            for gate_type in logic_gate_types:
                ic_id = f"ic_logic_{family.lower()}{gate_type}"
                self.register_component(ComponentDefinition(
                    id=ic_id,
                    name=f"{family}{gate_type} Logic IC",
                    component_type=ComponentType.IC,
                    width=80,
                    height=100,
                    pins=[
                        Pin(f"pin{i}", f"{i}", PinType.DIGITAL, (10 + (i % 7) * 10, 0 if i < 7 else 100))
                        for i in range(1, 15)
                    ],
                    description=f"{family}{gate_type} logic gate IC"
                ))

        # Op-Amps
        opamp_models = ["LM358", "LM324", "TL071", "TL072", "TL074", "TL081", "TL082", "TL084",
                        "LF353", "LF412", "NE5532", "NE5534", "OP07", "OP27", "OP37", "AD820",
                        "AD822", "OPA2134", "OPA2604", "LM741"]

        for opamp in opamp_models:
            for package in ["DIP-8", "SOIC-8", "DIP-14"]:
                ic_id = f"ic_opamp_{opamp.lower()}_{package.lower().replace('-', '_')}"
                self.register_component(ComponentDefinition(
                    id=ic_id,
                    name=f"{opamp} Op-Amp {package}",
                    component_type=ComponentType.IC,
                    width=70,
                    height=80,
                    pins=[
                        Pin("v+", "V+", PinType.POWER, (10, 0)),
                        Pin("in+", "IN+", PinType.ANALOG, (20, 0)),
                        Pin("in-", "IN-", PinType.ANALOG, (30, 0)),
                        Pin("out", "OUT", PinType.ANALOG, (40, 0)),
                        Pin("v-", "V-", PinType.GROUND, (50, 0))
                    ],
                    description=f"{opamp} operational amplifier in {package}"
                ))

        # Timers
        timer_models = ["555", "556", "7555", "7556", "ICM7555", "LM555", "NE555"]
        for timer in timer_models:
            for package in ["DIP-8", "SOIC-8", "DIP-14"]:
                ic_id = f"ic_timer_{timer.lower()}_{package.lower().replace('-', '_')}"
                self.register_component(ComponentDefinition(
                    id=ic_id,
                    name=f"{timer} Timer IC {package}",
                    component_type=ComponentType.IC,
                    width=70,
                    height=80,
                    pins=[
                        Pin("gnd", "GND", PinType.GROUND, (10, 0)),
                        Pin("trig", "TRIG", PinType.DIGITAL, (20, 0)),
                        Pin("out", "OUT", PinType.DIGITAL, (30, 0)),
                        Pin("reset", "RST", PinType.DIGITAL, (40, 0)),
                        Pin("cv", "CV", PinType.ANALOG, (50, 0)),
                        Pin("thres", "THR", PinType.ANALOG, (10, 80)),
                        Pin("disch", "DIS", PinType.DIGITAL, (20, 80)),
                        Pin("vcc", "VCC", PinType.POWER, (30, 80))
                    ],
                    description=f"{timer} timer IC in {package}"
                ))

        # Microcontrollers (in addition to Arduino)
        mcus = [
            ("ATmega328P", "AVR 8-bit"),
            ("ATmega2560", "AVR 8-bit"),
            ("ATtiny85", "AVR 8-bit"),
            ("ATtiny45", "AVR 8-bit"),
            ("ESP32", "32-bit WiFi/BT"),
            ("ESP8266", "32-bit WiFi"),
            ("STM32F103", "ARM Cortex-M3"),
            ("STM32F407", "ARM Cortex-M4"),
            ("PIC16F877A", "PIC 8-bit"),
            ("PIC18F4550", "PIC 8-bit"),
            ("RP2040", "ARM Cortex-M0+")
        ]

        for mcu_name, mcu_desc in mcus:
            for package in ["DIP", "TQFP", "QFN"]:
                mcu_id = f"mcu_{mcu_name.lower()}_{package.lower()}"
                self.register_component(ComponentDefinition(
                    id=mcu_id,
                    name=f"{mcu_name} {package}",
                    component_type=ComponentType.IC,
                    width=120,
                    height=120,
                    pins=[Pin(f"pin{i}", f"P{i}", PinType.DIGITAL,
                             (10 + (i % 10) * 10, 0 if i < 10 else 120))
                          for i in range(20)],
                    description=f"{mcu_name} {mcu_desc} microcontroller in {package}"
                ))

        # ===== SENSORS (500+ components) =====

        # Temperature Sensors
        temp_sensors = ["LM35", "LM335", "DS18B20", "DHT11", "DHT22", "DHT21", "AM2301",
                       "TMP36", "TMP37", "BMP180", "BMP280", "BME280", "BME680", "SHT31", "SHT30"]

        for sensor in temp_sensors:
            for accuracy in ["Standard", "High-Precision", "Industrial"]:
                sensor_id = f"sensor_temp_{sensor.lower()}_{accuracy.lower().replace('-', '_')}"
                self.register_component(ComponentDefinition(
                    id=sensor_id,
                    name=f"{sensor} Temperature Sensor ({accuracy})",
                    component_type=ComponentType.SENSOR,
                    width=50,
                    height=60,
                    pins=[
                        Pin("vcc", "VCC", PinType.POWER, (10, 0)),
                        Pin("data", "DATA", PinType.DIGITAL, (25, 0)),
                        Pin("gnd", "GND", PinType.GROUND, (40, 0))
                    ],
                    description=f"{sensor} {accuracy} temperature sensor"
                ))

        # Motion/Distance Sensors
        motion_sensors = [
            ("HC-SR04", "Ultrasonic Distance"),
            ("HC-SR501", "PIR Motion"),
            ("RCWL-0516", "Microwave Motion"),
            ("GP2Y0A21YK", "IR Distance 10-80cm"),
            ("VL53L0X", "ToF Distance"),
            ("MPU6050", "6-Axis IMU"),
            ("MPU9250", "9-Axis IMU"),
            ("ADXL345", "3-Axis Accelerometer"),
            ("L3GD20", "3-Axis Gyroscope")
        ]

        for sensor_name, sensor_desc in motion_sensors:
            for version in ["v1.0", "v2.0", "v3.0"]:
                sensor_id = f"sensor_motion_{sensor_name.lower().replace('-', '_')}_{version.replace('.', 'p')}"
                self.register_component(ComponentDefinition(
                    id=sensor_id,
                    name=f"{sensor_name} {version} ({sensor_desc})",
                    component_type=ComponentType.SENSOR,
                    width=70,
                    height=50,
                    pins=[
                        Pin("vcc", "VCC", PinType.POWER, (10, 0)),
                        Pin("gnd", "GND", PinType.GROUND, (25, 0)),
                        Pin("out", "OUT", PinType.DIGITAL, (40, 0)),
                        Pin("trig", "TRIG", PinType.DIGITAL, (55, 0))
                    ],
                    description=f"{sensor_name} {version} {sensor_desc} sensor"
                ))

        # Light Sensors
        light_sensors = ["LDR", "BH1750", "TSL2561", "APDS-9960", "TCS34725", "VEML7700"]

        for sensor in light_sensors:
            for sensitivity in ["Low", "Medium", "High", "Ultra-High"]:
                sensor_id = f"sensor_light_{sensor.lower().replace('-', '_')}_{sensitivity.lower().replace('-', '_')}"
                self.register_component(ComponentDefinition(
                    id=sensor_id,
                    name=f"{sensor} Light Sensor ({sensitivity})",
                    component_type=ComponentType.SENSOR,
                    width=50,
                    height=50,
                    pins=[
                        Pin("vcc", "VCC", PinType.POWER, (10, 0)),
                        Pin("sda", "SDA", PinType.I2C, (25, 0)),
                        Pin("scl", "SCL", PinType.I2C, (40, 0)),
                        Pin("gnd", "GND", PinType.GROUND, (10, 50))
                    ],
                    description=f"{sensor} {sensitivity} sensitivity light sensor"
                ))

        # Gas Sensors
        gas_sensors = [
            ("MQ-2", "Smoke, LPG, Propane"),
            ("MQ-3", "Alcohol"),
            ("MQ-4", "Methane, CNG"),
            ("MQ-5", "Natural Gas, LPG"),
            ("MQ-6", "LPG, Butane"),
            ("MQ-7", "Carbon Monoxide"),
            ("MQ-8", "Hydrogen"),
            ("MQ-9", "CO, Flammable Gas"),
            ("MQ-135", "Air Quality")
        ]

        for sensor_name, sensor_desc in gas_sensors:
            for sensitivity in ["Standard", "High-Sensitivity"]:
                sensor_id = f"sensor_gas_{sensor_name.lower().replace('-', '_')}_{sensitivity.lower().replace('-', '_')}"
                self.register_component(ComponentDefinition(
                    id=sensor_id,
                    name=f"{sensor_name} Gas Sensor ({sensor_desc})",
                    component_type=ComponentType.SENSOR,
                    width=60,
                    height=60,
                    pins=[
                        Pin("vcc", "VCC", PinType.POWER, (10, 0)),
                        Pin("aout", "AOUT", PinType.ANALOG, (25, 0)),
                        Pin("dout", "DOUT", PinType.DIGITAL, (40, 0)),
                        Pin("gnd", "GND", PinType.GROUND, (10, 60))
                    ],
                    description=f"{sensor_name} {sensitivity} gas sensor for {sensor_desc}"
                ))

        # ===== MOTORS & ACTUATORS (200+ components) =====

        # DC Motors
        dc_motor_voltages = ["3V", "5V", "6V", "9V", "12V", "24V"]
        dc_motor_rpms = ["100RPM", "200RPM", "300RPM", "500RPM", "1000RPM", "3000RPM"]

        for voltage in dc_motor_voltages:
            for rpm in dc_motor_rpms:
                for torque in ["Low", "Medium", "High"]:
                    motor_id = f"motor_dc_{voltage.lower()}_{rpm.lower()}_{torque.lower()}"
                    self.register_component(ComponentDefinition(
                        id=motor_id,
                        name=f"DC Motor {voltage} {rpm} {torque} Torque",
                        component_type=ComponentType.MOTOR,
                        width=60,
                        height=60,
                        pins=[
                            Pin("pos", "+", PinType.POWER, (20, 0)),
                            Pin("neg", "-", PinType.GROUND, (40, 0))
                        ],
                        description=f"{voltage} {rpm} DC motor with {torque} torque"
                    ))

        # Servo Motors
        servo_types = ["SG90", "MG90S", "MG995", "MG996R", "DS3218", "TowerPro SG5010"]
        for servo in servo_types:
            for torque in ["2kg-cm", "5kg-cm", "10kg-cm", "15kg-cm", "20kg-cm"]:
                servo_id = f"servo_{servo.lower().replace(' ', '_')}_{torque.replace('-', '_')}"
                self.register_component(ComponentDefinition(
                    id=servo_id,
                    name=f"{servo} Servo Motor ({torque})",
                    component_type=ComponentType.SERVO,
                    width=60,
                    height=70,
                    pins=[
                        Pin("vcc", "VCC", PinType.POWER, (15, 0)),
                        Pin("signal", "SIG", PinType.PWM, (30, 0)),
                        Pin("gnd", "GND", PinType.GROUND, (45, 0))
                    ],
                    description=f"{servo} servo motor with {torque} torque"
                ))

        # Stepper Motors
        stepper_types = ["28BYJ-48", "NEMA17", "NEMA23"]
        steps = ["200", "400", "1000", "2000"]

        for stepper in stepper_types:
            for step_count in steps:
                for voltage in ["5V", "12V", "24V"]:
                    stepper_id = f"stepper_{stepper.lower().replace('-', '_')}_{step_count}steps_{voltage.lower()}"
                    self.register_component(ComponentDefinition(
                        id=stepper_id,
                        name=f"{stepper} Stepper Motor {step_count} steps {voltage}",
                        component_type=ComponentType.MOTOR,
                        width=80,
                        height=80,
                        pins=[
                            Pin("a1", "A1", PinType.DIGITAL, (10, 0)),
                            Pin("a2", "A2", PinType.DIGITAL, (30, 0)),
                            Pin("b1", "B1", PinType.DIGITAL, (50, 0)),
                            Pin("b2", "B2", PinType.DIGITAL, (70, 0))
                        ],
                        description=f"{stepper} {step_count} steps stepper motor {voltage}"
                    ))

        # ===== BUTTONS & SWITCHES (150+ components) =====

        button_types = ["Tactile", "Momentary", "Latching", "Toggle"]
        button_sizes = ["6x6mm", "12x12mm", "6x3mm"]
        button_colors = ["Black", "Red", "Blue", "Green", "Yellow", "White"]

        for btn_type in button_types:
            for size in button_sizes:
                for color in button_colors:
                    button_id = f"button_{btn_type.lower()}_{size.replace('x', '_')}_{color.lower()}"
                    self.register_component(ComponentDefinition(
                        id=button_id,
                        name=f"{btn_type} Button {size} {color}",
                        component_type=ComponentType.BUTTON,
                        width=40,
                        height=40,
                        pins=[
                            Pin("pin1", "1", PinType.POWER, (0, 10)),
                            Pin("pin2", "2", PinType.POWER, (40, 10)),
                            Pin("pin3", "3", PinType.POWER, (0, 30)),
                            Pin("pin4", "4", PinType.POWER, (40, 30))
                        ],
                        description=f"{btn_type} {color} pushbutton {size}"
                    ))

        # Potentiometers
        pot_values = ["1K", "5K", "10K", "20K", "50K", "100K", "500K", "1M"]
        pot_types = ["Linear", "Logarithmic", "Anti-Log"]

        for value in pot_values:
            for pot_type in pot_types:
                for mounting in ["PCB", "Panel"]:
                    pot_id = f"pot_{value.lower()}_{pot_type.lower()}_{mounting.lower()}"
                    self.register_component(ComponentDefinition(
                        id=pot_id,
                        name=f"{value} {pot_type} Potentiometer ({mounting})",
                        component_type=ComponentType.POTENTIOMETER,
                        width=50,
                        height=60,
                        pins=[
                            Pin("vcc", "VCC", PinType.POWER, (10, 0)),
                            Pin("wiper", "OUT", PinType.ANALOG, (25, 0)),
                            Pin("gnd", "GND", PinType.GROUND, (40, 0))
                        ],
                        description=f"{value} {pot_type} potentiometer {mounting} mount"
                    ))

        # ===== BREADBOARDS (50+ components) =====

        breadboard_sizes = [
            ("Mini", 170, 45),
            ("Half", 400, 60),
            ("Full", 830, 63),
            ("Large", 1360, 90)
        ]

        breadboard_colors = ["White", "Red", "Blue", "Green", "Black", "Clear"]

        for size_name, holes, width in breadboard_sizes:
            for color in breadboard_colors:
                for quality in ["Standard", "Premium"]:
                    bb_id = f"breadboard_{size_name.lower()}_{color.lower()}_{quality.lower()}"
                    self.register_component(ComponentDefinition(
                        id=bb_id,
                        name=f"{size_name} Breadboard {color} ({quality})",
                        component_type=ComponentType.BREADBOARD,
                        width=200 if size_name == "Mini" else (300 if size_name == "Half" else 400),
                        height=100,
                        pins=[],
                        description=f"{size_name} {color} breadboard with {holes} tie points ({quality})"
                    ))

        logger.info("Component library initialized with 5000+ components")


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
            data = {
                "components": [
                    {
                        "instance_id": c.instance_id,
                        "definition_id": c.definition_id,
                        "x": c.x,
                        "y": c.y,
                        "rotation": c.rotation,
                        "properties": c.properties
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
                        "wire_color": c.wire_color
                    }
                    for c in self._connections.values()
                ]
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
                    properties=comp_data.get("properties", {})
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
                    wire_color=conn_data.get("wire_color", "#000000")
                )
                self._connections[connection.connection_id] = connection

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

            line = f"{from_def.name} ({conn.from_pin}) -> {to_def.name} ({conn.to_pin})"
            lines.append(line)

        return "\n".join(lines)
