# Component Library

This folder contains electronic component definitions for the Arduino IDE circuit designer. Each component is stored as a separate JSON file, making it easy to add new components without modifying code.

## Folder Structure

```
component_library/
├── arduino_boards/    # Arduino and microcontroller boards
├── leds/             # Light Emitting Diodes
├── resistors/        # Resistors (various values and types)
├── capacitors/       # Capacitors (ceramic, electrolytic, etc.)
├── transistors/      # BJT, MOSFET, and other transistors
├── ics/             # Integrated circuits (logic gates, op-amps, timers, MCUs)
├── sensors/         # Sensors (temperature, motion, light, gas, etc.)
├── motors/          # DC motors, servo motors, stepper motors
├── buttons/         # Buttons, switches, and input devices
├── potentiometers/  # Variable resistors and potentiometers
├── breadboards/     # Breadboards and prototyping supplies
└── misc/            # Other components
```

## Component File Format

Each component is defined in a JSON file with the following structure:

### Basic Example (LED)

```json
{
  "id": "led_red_5mm_standard",
  "name": "Red 5mm LED",
  "component_type": "led",
  "description": "Standard red 5mm Light Emitting Diode",
  "width": 30,
  "height": 50,
  "pins": [
    {
      "id": "anode",
      "label": "+",
      "pin_type": "power",
      "position": [15, 0]
    },
    {
      "id": "cathode",
      "label": "-",
      "pin_type": "ground",
      "position": [15, 50]
    }
  ],
  "metadata": {
    "manufacturer": "Generic",
    "forward_voltage": "2.0V",
    "forward_current": "20mA",
    "color": "Red",
    "wavelength": "625nm"
  }
}
```

### Advanced Example (Arduino Uno)

```json
{
  "id": "arduino_uno",
  "name": "Arduino Uno",
  "component_type": "arduino_board",
  "description": "Arduino Uno R3 microcontroller board based on ATmega328P",
  "width": 200,
  "height": 150,
  "pins": [
    {"id": "D0", "label": "D0", "pin_type": "digital", "position": [0, 0]},
    {"id": "D1", "label": "D1", "pin_type": "digital", "position": [20, 0]},
    {"id": "D2", "label": "D2", "pin_type": "digital", "position": [40, 0]},
    {"id": "D3", "label": "D3~", "pin_type": "pwm", "position": [60, 0]},
    {"id": "5V", "label": "5V", "pin_type": "power", "position": [0, 50]},
    {"id": "3V3", "label": "3.3V", "pin_type": "power", "position": [20, 50]},
    {"id": "GND1", "label": "GND", "pin_type": "ground", "position": [40, 50]},
    {"id": "A0", "label": "A0", "pin_type": "analog", "position": [0, 100]}
  ],
  "metadata": {
    "manufacturer": "Arduino",
    "microcontroller": "ATmega328P",
    "operating_voltage": "5V",
    "input_voltage": "7-12V",
    "digital_io_pins": 14,
    "analog_input_pins": 6,
    "flash_memory": "32KB",
    "sram": "2KB",
    "eeprom": "1KB",
    "clock_speed": "16MHz",
    "datasheet_url": "https://docs.arduino.cc/hardware/uno-rev3"
  }
}
```

## Field Definitions

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the component (use lowercase, underscores) |
| `name` | string | Human-readable component name |
| `component_type` | string | Component category (see types below) |
| `description` | string | Brief description of the component |
| `width` | number | Visual width in pixels |
| `height` | number | Visual height in pixels |
| `pins` | array | Array of pin objects (see below) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `image_path` | string | Path to component image (relative to component_library/) |
| `datasheet_url` | string | URL to component datasheet |
| `metadata` | object | Additional component-specific data (manufacturer, specs, etc.) |

### Component Types

Valid values for `component_type`:

- `arduino_board` - Arduino and compatible boards
- `led` - Light Emitting Diodes
- `resistor` - Fixed resistors
- `capacitor` - Capacitors (all types)
- `transistor` - BJT, MOSFET, etc.
- `ic` - Integrated circuits
- `sensor` - Sensors (temperature, motion, light, etc.)
- `motor` - DC, servo, stepper motors
- `servo` - Servo motors (subcategory)
- `button` - Buttons and switches
- `potentiometer` - Variable resistors
- `breadboard` - Breadboards
- `wire` - Wires and jumpers
- `battery` - Batteries and power supplies

### Pin Object Format

Each pin in the `pins` array must have:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique pin identifier (within this component) |
| `label` | string | Pin label shown on component |
| `pin_type` | string | Pin type (see below) |
| `position` | array | [x, y] coordinates relative to component top-left |

### Pin Types

Valid values for `pin_type`:

- `digital` - Digital I/O pin
- `analog` - Analog input/output pin
- `pwm` - PWM-capable digital pin
- `power` - Power supply pin (VCC, 5V, 3.3V, etc.)
- `ground` - Ground pin (GND)
- `i2c` - I2C communication pin (SDA/SCL)
- `spi` - SPI communication pin (MOSI/MISO/SCK/CS)
- `serial` - Serial communication pin (TX/RX)

## Adding New Components

To add a new component to the library:

1. **Choose the correct folder** based on component type
2. **Create a JSON file** with a descriptive name (e.g., `led_blue_10mm_high_brightness.json`)
3. **Follow the format** shown in the examples above
4. **Test your component** by loading it in the circuit designer
5. **Restart the IDE** or reload components to see your new component

### Naming Conventions

- Use lowercase for file names
- Use underscores instead of spaces
- Include key specifications in the name
- Examples:
  - `resistor_220_1_4w_5pct.json` (220Ω, 1/4W, 5% tolerance)
  - `led_green_5mm_high_brightness.json`
  - `ic_timer_555_dip8.json`
  - `sensor_temp_dht22_high_precision.json`

## Metadata Recommendations

Add relevant specifications in the `metadata` object:

### For LEDs
```json
"metadata": {
  "color": "Red",
  "size": "5mm",
  "forward_voltage": "2.0V",
  "forward_current": "20mA",
  "wavelength": "625nm",
  "brightness": "1000mcd"
}
```

### For Resistors
```json
"metadata": {
  "resistance": "220Ω",
  "tolerance": "5%",
  "power_rating": "0.25W",
  "type": "Carbon Film"
}
```

### For ICs
```json
"metadata": {
  "manufacturer": "Texas Instruments",
  "part_number": "NE555P",
  "package": "DIP-8",
  "operating_voltage": "4.5-16V",
  "datasheet_url": "https://..."
}
```

### For Sensors
```json
"metadata": {
  "sensor_type": "Temperature & Humidity",
  "range_temperature": "-40 to 80°C",
  "range_humidity": "0-100%",
  "accuracy_temperature": "±0.5°C",
  "accuracy_humidity": "±2%",
  "interface": "1-Wire"
}
```

## Component Generation Scripts

You can also create Python scripts to generate multiple component files programmatically:

```python
import json
import os

# Generate resistor components
e24_values = [10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 43, 47, 51, 56, 62, 68, 75, 82, 91]
wattages = ["1/8W", "1/4W", "1/2W", "1W"]
tolerances = ["1%", "5%", "10%"]

for multiplier in [1, 10, 100, 1000, 10000, 100000, 1000000]:
    for base in e24_values:
        for wattage in wattages:
            for tolerance in tolerances:
                value = base * multiplier
                component = {
                    "id": f"resistor_{value}_{wattage.replace('/', 'div')}_{tolerance.replace('%', 'pct')}",
                    "name": f"{value}Ω {wattage} {tolerance} Resistor",
                    "component_type": "resistor",
                    "description": f"{value} Ohm resistor {wattage} {tolerance} tolerance",
                    "width": 60,
                    "height": 20,
                    "pins": [
                        {"id": "pin1", "label": "1", "pin_type": "power", "position": [0, 10]},
                        {"id": "pin2", "label": "2", "pin_type": "power", "position": [60, 10]}
                    ],
                    "metadata": {
                        "resistance": f"{value}Ω",
                        "tolerance": tolerance,
                        "power_rating": wattage
                    }
                }

                filename = f"arduino_ide/component_library/resistors/{component['id']}.json"
                with open(filename, 'w') as f:
                    json.dump(component, f, indent=2)
```

## Tips and Best Practices

1. **Be consistent** - Follow existing naming conventions
2. **Include metadata** - The more information, the better
3. **Test your components** - Make sure they load correctly
4. **Use meaningful IDs** - IDs should describe the component
5. **Document specifications** - Add datasheets and technical details
6. **Organize by category** - Put files in the correct folder
7. **Keep files small** - One component per file for easy management
8. **Share your components** - Contribute useful components back to the project

## Validation

The component loader will validate your JSON files and report errors if:

- Required fields are missing
- Invalid component_type or pin_type values
- Invalid JSON syntax
- Duplicate component IDs

Check the logs for detailed error messages if a component fails to load.

## Contributing

To contribute components to the project:

1. Create your component files following this format
2. Test them thoroughly
3. Submit a pull request with your new components
4. Include a brief description of what you're adding

Happy component creating!
