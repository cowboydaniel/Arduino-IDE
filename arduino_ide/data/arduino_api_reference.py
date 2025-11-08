"""
Arduino API Reference Database
Provides contextual information about Arduino functions
"""

ARDUINO_API = {
    "Serial.begin": {
        "title": "Serial Configuration",
        "category": "Serial Communication",
        "description": "Initializes serial communication with specified baud rate",
        "syntax": "Serial.begin(speed)\nSerial.begin(speed, config)",
        "parameters": [
            {
                "name": "speed",
                "type": "long",
                "description": "Baud rate for serial communication"
            },
            {
                "name": "config",
                "type": "byte",
                "description": "Data bits, parity, and stop bits configuration (optional)"
            }
        ],
        "common_values": [
            {"value": "9600", "description": "Default, reliable for most applications"},
            {"value": "115200", "description": "Faster communication, good for data logging"},
            {"value": "57600", "description": "Common alternative speed"},
            {"value": "38400", "description": "Legacy devices"},
        ],
        "warnings": [
            "⚠️  Serial Monitor baud rate must match this setting",
            "⚠️  Higher baud rates may cause errors with long cables"
        ],
        "tips": [
            "💡 Use 9600 for beginners and debugging",
            "💡 Use 115200 for high-speed data transfer"
        ],
        "example": """
void setup() {
  Serial.begin(9600);
  Serial.println("Ready!");
}
        """.strip()
    },

    "Serial.println": {
        "title": "Serial Print Line",
        "category": "Serial Communication",
        "description": "Prints data to serial port followed by newline",
        "syntax": "Serial.println(val)\nSerial.println(val, format)",
        "parameters": [
            {
                "name": "val",
                "type": "any",
                "description": "Value to print (string, number, etc.)"
            },
            {
                "name": "format",
                "type": "int",
                "description": "Format for numbers (DEC, HEX, OCT, BIN)"
            }
        ],
        "common_values": [
            {"value": "DEC", "description": "Decimal format (default)"},
            {"value": "HEX", "description": "Hexadecimal format"},
            {"value": "BIN", "description": "Binary format"},
        ],
        "warnings": [
            "⚠️  Adds carriage return + line feed (\\r\\n)",
        ],
        "tips": [
            "💡 Use Serial.print() to print without newline",
            "💡 Great for debugging sensor values"
        ],
        "example": """
int value = 42;
Serial.println(value);      // Prints: 42
Serial.println(value, HEX); // Prints: 2A
        """.strip()
    },

    "pinMode": {
        "title": "Pin Mode Configuration",
        "category": "Digital I/O",
        "description": "Configures a digital pin as input or output",
        "syntax": "pinMode(pin, mode)",
        "parameters": [
            {
                "name": "pin",
                "type": "int",
                "description": "Pin number to configure"
            },
            {
                "name": "mode",
                "type": "int",
                "description": "Pin mode: INPUT, OUTPUT, or INPUT_PULLUP"
            }
        ],
        "common_values": [
            {"value": "OUTPUT", "description": "Pin will provide voltage (source/sink current)"},
            {"value": "INPUT", "description": "Pin will read voltage (high impedance)"},
            {"value": "INPUT_PULLUP", "description": "Input with internal pull-up resistor enabled"},
        ],
        "warnings": [
            "⚠️  Call pinMode() in setup() before using the pin",
            "⚠️  Don't exceed 40mA per pin or 200mA total"
        ],
        "tips": [
            "💡 Use INPUT_PULLUP for buttons (no external resistor needed)",
            "💡 OUTPUT pins default to LOW on startup"
        ],
        "example": """
void setup() {
  pinMode(13, OUTPUT);     // LED
  pinMode(2, INPUT_PULLUP); // Button
}
        """.strip()
    },

    "digitalWrite": {
        "title": "Digital Write",
        "category": "Digital I/O",
        "description": "Sets a digital pin to HIGH or LOW",
        "syntax": "digitalWrite(pin, value)",
        "parameters": [
            {
                "name": "pin",
                "type": "int",
                "description": "Pin number to write to"
            },
            {
                "name": "value",
                "type": "int",
                "description": "HIGH (5V) or LOW (0V)"
            }
        ],
        "common_values": [
            {"value": "HIGH", "description": "5V (or 3.3V on some boards)"},
            {"value": "LOW", "description": "0V (ground)"},
        ],
        "warnings": [
            "⚠️  Pin must be configured as OUTPUT first",
            "⚠️  Don't connect LEDs without current-limiting resistor"
        ],
        "tips": [
            "💡 Typical LED resistor: 220Ω - 1kΩ",
            "💡 Use for controlling LEDs, relays, motors (with driver)"
        ],
        "example": """
pinMode(13, OUTPUT);
digitalWrite(13, HIGH);  // LED on
delay(1000);
digitalWrite(13, LOW);   // LED off
        """.strip()
    },

    "digitalRead": {
        "title": "Digital Read",
        "category": "Digital I/O",
        "description": "Reads the value from a digital pin",
        "syntax": "digitalRead(pin)",
        "parameters": [
            {
                "name": "pin",
                "type": "int",
                "description": "Pin number to read from"
            }
        ],
        "common_values": [],
        "warnings": [
            "⚠️  Pin should be configured as INPUT or INPUT_PULLUP",
            "⚠️  Floating inputs may give random values"
        ],
        "tips": [
            "💡 Returns HIGH or LOW",
            "💡 Use INPUT_PULLUP for reliable button reading"
        ],
        "example": """
pinMode(2, INPUT_PULLUP);
int buttonState = digitalRead(2);
if (buttonState == LOW) {
  // Button pressed
}
        """.strip()
    },

    "analogRead": {
        "title": "Analog Read",
        "category": "Analog I/O",
        "description": "Reads analog voltage from a pin (0-1023)",
        "syntax": "analogRead(pin)",
        "parameters": [
            {
                "name": "pin",
                "type": "int",
                "description": "Analog pin number (A0-A5 on Uno)"
            }
        ],
        "common_values": [],
        "warnings": [
            "⚠️  Returns value 0-1023 (10-bit resolution)",
            "⚠️  Input voltage must be 0-5V (or 0-3.3V on some boards)"
        ],
        "tips": [
            "💡 Convert to voltage: voltage = value * (5.0 / 1023.0)",
            "💡 Takes ~100 microseconds to complete",
            "💡 No need to call pinMode() for analog inputs"
        ],
        "example": """
int sensorValue = analogRead(A0);
float voltage = sensorValue * (5.0 / 1023.0);
Serial.println(voltage);
        """.strip()
    },

    "analogWrite": {
        "title": "Analog Write (PWM)",
        "category": "Analog I/O",
        "description": "Writes a PWM value to a pin (0-255)",
        "syntax": "analogWrite(pin, value)",
        "parameters": [
            {
                "name": "pin",
                "type": "int",
                "description": "PWM-capable pin (marked with ~ on Uno)"
            },
            {
                "name": "value",
                "type": "int",
                "description": "Duty cycle: 0 (always off) to 255 (always on)"
            }
        ],
        "common_values": [
            {"value": "0", "description": "0% duty cycle (always LOW)"},
            {"value": "127", "description": "50% duty cycle"},
            {"value": "255", "description": "100% duty cycle (always HIGH)"},
        ],
        "warnings": [
            "⚠️  Not true analog - uses PWM (Pulse Width Modulation)",
            "⚠️  Only works on PWM pins (3, 5, 6, 9, 10, 11 on Uno)",
            "⚠️  Default PWM frequency: ~490Hz (pins 5,6: ~980Hz)"
        ],
        "tips": [
            "💡 Use for LED brightness, motor speed control",
            "💡 Add capacitor for smooth analog-like output"
        ],
        "example": """
pinMode(9, OUTPUT);
analogWrite(9, 127);  // 50% brightness
        """.strip()
    },

    "delay": {
        "title": "Delay (Blocking)",
        "category": "Time",
        "description": "Pauses program for specified milliseconds",
        "syntax": "delay(ms)",
        "parameters": [
            {
                "name": "ms",
                "type": "unsigned long",
                "description": "Number of milliseconds to pause"
            }
        ],
        "common_values": [
            {"value": "1000", "description": "1 second"},
            {"value": "500", "description": "0.5 seconds"},
            {"value": "100", "description": "0.1 seconds"},
        ],
        "warnings": [
            "⚠️  Blocks all code execution (nothing else runs)",
            "⚠️  Can't read sensors or respond to inputs during delay"
        ],
        "tips": [
            "💡 For non-blocking delays, use millis() instead",
            "💡 Good for simple examples, avoid in complex programs"
        ],
        "example": """
digitalWrite(13, HIGH);
delay(1000);  // Wait 1 second
digitalWrite(13, LOW);
        """.strip()
    },

    "millis": {
        "title": "Milliseconds Counter",
        "category": "Time",
        "description": "Returns time since program started (in milliseconds)",
        "syntax": "millis()",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Overflows after ~50 days (returns to 0)",
            "⚠️  Resolution: 1-2 milliseconds"
        ],
        "tips": [
            "💡 Use for non-blocking delays and timing",
            "💡 Better than delay() for responsive programs"
        ],
        "example": """
unsigned long previousMillis = 0;
const long interval = 1000;

void loop() {
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    // Do something every 1 second
  }
}
        """.strip()
    },

    "attachInterrupt": {
        "title": "Attach Interrupt",
        "category": "Interrupts",
        "description": "Attaches interrupt handler to a pin",
        "syntax": "attachInterrupt(digitalPinToInterrupt(pin), ISR, mode)",
        "parameters": [
            {
                "name": "interrupt",
                "type": "int",
                "description": "Interrupt number (use digitalPinToInterrupt(pin))"
            },
            {
                "name": "ISR",
                "type": "function",
                "description": "Interrupt service routine to call"
            },
            {
                "name": "mode",
                "type": "int",
                "description": "When to trigger: LOW, CHANGE, RISING, FALLING"
            }
        ],
        "common_values": [
            {"value": "RISING", "description": "Trigger when pin goes LOW to HIGH"},
            {"value": "FALLING", "description": "Trigger when pin goes HIGH to LOW"},
            {"value": "CHANGE", "description": "Trigger on any change"},
            {"value": "LOW", "description": "Trigger when pin is LOW"},
        ],
        "warnings": [
            "⚠️  ISR should be short and fast",
            "⚠️  Can't use delay() inside ISR",
            "⚠️  Uno only supports interrupts on pins 2 and 3"
        ],
        "tips": [
            "💡 Use volatile variables shared with ISR",
            "💡 Great for counting pulses or detecting events"
        ],
        "example": """
volatile int counter = 0;

void setup() {
  pinMode(2, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(2), count, RISING);
}

void count() {
  counter++;
}
        """.strip()
    },

    "Wire.begin": {
        "title": "I2C Initialization",
        "category": "Communication (I2C)",
        "description": "Initializes I2C communication",
        "syntax": "Wire.begin()\nWire.begin(address)",
        "parameters": [
            {
                "name": "address",
                "type": "int",
                "description": "I2C slave address (optional, for slave mode)"
            }
        ],
        "common_values": [],
        "warnings": [
            "⚠️  Requires #include <Wire.h>",
            "⚠️  Uses pins A4 (SDA) and A5 (SCL) on Uno",
            "⚠️  Needs pull-up resistors (4.7kΩ typical)"
        ],
        "tips": [
            "💡 Call once in setup()",
            "💡 Multiple devices can share the I2C bus"
        ],
        "example": """
#include <Wire.h>

void setup() {
  Wire.begin();  // Master mode
}
        """.strip()
    },

    "SPI.begin": {
        "title": "SPI Initialization",
        "category": "Communication (SPI)",
        "description": "Initializes SPI communication",
        "syntax": "SPI.begin()",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Requires #include <SPI.h>",
            "⚠️  Uses pins 11 (MOSI), 12 (MISO), 13 (SCK) on Uno",
            "⚠️  Need separate CS (chip select) pin per device"
        ],
        "tips": [
            "💡 Much faster than I2C",
            "💡 Use for SD cards, displays, sensors"
        ],
        "example": """
#include <SPI.h>

void setup() {
  SPI.begin();
}
        """.strip()
    },
}


def get_api_info(function_name):
    """Get API information for a function name"""
    # Direct match
    if function_name in ARDUINO_API:
        return ARDUINO_API[function_name]

    # Try to match base function (e.g., "Serial.print" matches "Serial.println")
    for key in ARDUINO_API:
        if function_name.startswith(key) or key.startswith(function_name):
            return ARDUINO_API[key]

    return None


def get_all_functions():
    """Get list of all documented functions"""
    return list(ARDUINO_API.keys())
