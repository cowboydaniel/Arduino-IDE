"""
Arduino API Reference Database
Provides contextual information about Arduino functions and C++ language features
"""

from arduino_ide.data.cpp_reference import CPP_REFERENCE

ARDUINO_API = {
    "setup": {
        "title": "setup()",
        "category": "Arduino Core",
        "description": "The setup() function is called once when the Arduino starts. Use it to initialize variables, pin modes, libraries, and serial communication.",
        "syntax": "void setup() {\n  // initialization code\n}",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Runs only once at startup or after reset",
            "⚠️  Must be defined in every Arduino sketch"
        ],
        "tips": [
            "💡 Initialize Serial communication here with Serial.begin()",
            "💡 Set pin modes with pinMode()",
            "💡 Initialize libraries and hardware",
            "💡 Initialize variables that need startup values"
        ],
        "example": """void setup() {
  // Initialize serial communication
  Serial.begin(9600);

  // Set pin modes
  pinMode(13, OUTPUT);
  pinMode(2, INPUT_PULLUP);

  // Initialize variables
  Serial.println("System Ready");
}"""
    },

    "loop": {
        "title": "loop()",
        "category": "Arduino Core",
        "description": "The loop() function runs continuously after setup() completes. This is where your main program logic goes.",
        "syntax": "void loop() {\n  // main code\n}",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Runs continuously in an infinite loop",
            "⚠️  Must be defined in every Arduino sketch",
            "⚠️  Avoid long blocking delays - use millis() instead"
        ],
        "tips": [
            "💡 Runs repeatedly after setup() finishes",
            "💡 Use millis() for non-blocking timing",
            "💡 Keep loop() fast for responsive programs",
            "💡 Put one-time initialization in setup(), not loop()"
        ],
        "example": """void loop() {
  // Read sensor
  int sensorValue = analogRead(A0);

  // Process data
  Serial.println(sensorValue);

  // Wait before next reading
  delay(100);
}"""
    },

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

    "Serial.print": {
        "title": "Serial Print",
        "category": "Serial Communication",
        "description": "Prints data to serial port without newline",
        "syntax": "Serial.print(val)\nSerial.print(val, format)",
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
            "⚠️  Does NOT add newline (use println for that)",
        ],
        "tips": [
            "💡 Use for printing multiple values on one line",
            "💡 Combine with println for formatted output"
        ],
        "example": """Serial.print("Value: ");
Serial.println(42);
// Prints: Value: 42"""
    },

    "Serial.available": {
        "title": "Serial Available",
        "category": "Serial Communication",
        "description": "Returns number of bytes available to read from serial buffer",
        "syntax": "Serial.available()",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Returns 0 if no data available",
        ],
        "tips": [
            "💡 Check before reading to avoid blocking",
            "💡 Use in while loop to read all available data"
        ],
        "example": """if (Serial.available() > 0) {
  char c = Serial.read();
  Serial.print("Received: ");
  Serial.println(c);
}"""
    },

    "Serial.read": {
        "title": "Serial Read",
        "category": "Serial Communication",
        "description": "Reads one byte from serial buffer",
        "syntax": "Serial.read()",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Returns -1 if no data available",
            "⚠️  Removes byte from buffer",
        ],
        "tips": [
            "💡 Check Serial.available() first",
            "💡 Cast to char for character data: char c = (char)Serial.read()"
        ],
        "example": """if (Serial.available() > 0) {
  int data = Serial.read();
  if (data != -1) {
    Serial.println((char)data);
  }
}"""
    },

    "delayMicroseconds": {
        "title": "Microsecond Delay",
        "category": "Time",
        "description": "Pauses program for specified microseconds",
        "syntax": "delayMicroseconds(us)",
        "parameters": [
            {
                "name": "us",
                "type": "unsigned int",
                "description": "Number of microseconds to pause (max ~16383)"
            }
        ],
        "common_values": [
            {"value": "1", "description": "1 microsecond"},
            {"value": "10", "description": "10 microseconds"},
            {"value": "100", "description": "0.1 milliseconds"},
        ],
        "warnings": [
            "⚠️  Blocking delay (like delay())",
            "⚠️  Maximum ~16383 microseconds on 16MHz Arduino",
            "⚠️  Not accurate below ~3 microseconds"
        ],
        "tips": [
            "💡 Use for very short, precise delays",
            "💡 For longer delays, use delay()"
        ],
        "example": """digitalWrite(triggerPin, HIGH);
delayMicroseconds(10);  // 10μs pulse
digitalWrite(triggerPin, LOW);"""
    },

    "micros": {
        "title": "Microseconds Counter",
        "category": "Time",
        "description": "Returns time since program started in microseconds",
        "syntax": "micros()",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Overflows after ~70 minutes",
            "⚠️  Resolution: 4 microseconds on 16MHz Arduino"
        ],
        "tips": [
            "💡 Use for precise timing measurements",
            "💡 Better precision than millis()"
        ],
        "example": """unsigned long start = micros();
// Do something
unsigned long duration = micros() - start;
Serial.println(duration);"""
    },

    "map": {
        "title": "Map (Re-map Number)",
        "category": "Math",
        "description": "Re-maps a number from one range to another",
        "syntax": "map(value, fromLow, fromHigh, toLow, toHigh)",
        "parameters": [
            {
                "name": "value",
                "type": "long",
                "description": "Number to map"
            },
            {
                "name": "fromLow",
                "type": "long",
                "description": "Lower bound of value's current range"
            },
            {
                "name": "fromHigh",
                "type": "long",
                "description": "Upper bound of value's current range"
            },
            {
                "name": "toLow",
                "type": "long",
                "description": "Lower bound of target range"
            },
            {
                "name": "toHigh",
                "type": "long",
                "description": "Upper bound of target range"
            }
        ],
        "common_values": [],
        "warnings": [
            "⚠️  Does not constrain values to output range",
            "⚠️  Uses integer math (may lose precision)"
        ],
        "tips": [
            "💡 Perfect for sensor value conversion",
            "💡 Use constrain() to limit output range",
            "💡 Common: map(analogRead(A0), 0, 1023, 0, 255)"
        ],
        "example": """int sensorValue = analogRead(A0);
// Map 0-1023 to 0-255
int brightness = map(sensorValue, 0, 1023, 0, 255);
analogWrite(ledPin, brightness);"""
    },

    "constrain": {
        "title": "Constrain",
        "category": "Math",
        "description": "Constrains a number to be within a range",
        "syntax": "constrain(x, min, max)",
        "parameters": [
            {
                "name": "x",
                "type": "any number",
                "description": "Number to constrain"
            },
            {
                "name": "min",
                "type": "any number",
                "description": "Minimum value"
            },
            {
                "name": "max",
                "type": "any number",
                "description": "Maximum value"
            }
        ],
        "common_values": [],
        "warnings": [],
        "tips": [
            "💡 Use to prevent values from going out of range",
            "💡 Useful after calculations that might overflow",
            "💡 Combine with map() for safe range conversion"
        ],
        "example": """int speed = constrain(input, 0, 255);
// Ensures speed is between 0 and 255

float temp = constrain(reading, -40, 125);"""
    },

    "random": {
        "title": "Random Number",
        "category": "Math",
        "description": "Generates pseudo-random numbers",
        "syntax": "random(max)\nrandom(min, max)",
        "parameters": [
            {
                "name": "min",
                "type": "long",
                "description": "Lower bound (inclusive, optional, default 0)"
            },
            {
                "name": "max",
                "type": "long",
                "description": "Upper bound (exclusive)"
            }
        ],
        "common_values": [],
        "warnings": [
            "⚠️  Pseudo-random (predictable sequence)",
            "⚠️  Max value is exclusive (not included)"
        ],
        "tips": [
            "💡 Use randomSeed() for different sequences",
            "💡 random(10) returns 0-9",
            "💡 random(5, 10) returns 5-9"
        ],
        "example": """long dice = random(1, 7);  // 1 to 6
Serial.println(dice);

long value = random(100);  // 0 to 99"""
    },

    "randomSeed": {
        "title": "Random Seed",
        "category": "Math",
        "description": "Initializes the pseudo-random number generator",
        "syntax": "randomSeed(seed)",
        "parameters": [
            {
                "name": "seed",
                "type": "unsigned long",
                "description": "Seed value (different seeds produce different sequences)"
            }
        ],
        "common_values": [],
        "warnings": [
            "⚠️  Same seed produces same random sequence"
        ],
        "tips": [
            "💡 Use analogRead on unconnected pin for random seed",
            "💡 Call once in setup()",
            "💡 randomSeed(analogRead(0)) for different sequences each run"
        ],
        "example": """void setup() {
  randomSeed(analogRead(0));
}

void loop() {
  long value = random(100);
  Serial.println(value);
  delay(1000);
}"""
    },

    "tone": {
        "title": "Tone (Generate Sound)",
        "category": "Advanced I/O",
        "description": "Generates a square wave of specified frequency on a pin",
        "syntax": "tone(pin, frequency)\ntone(pin, frequency, duration)",
        "parameters": [
            {
                "name": "pin",
                "type": "int",
                "description": "Pin to output tone"
            },
            {
                "name": "frequency",
                "type": "unsigned int",
                "description": "Frequency in hertz"
            },
            {
                "name": "duration",
                "type": "unsigned long",
                "description": "Duration in milliseconds (optional)"
            }
        ],
        "common_values": [
            {"value": "262", "description": "Middle C (C4)"},
            {"value": "440", "description": "A4 (concert pitch)"},
            {"value": "1000", "description": "1 kHz beep"}
        ],
        "warnings": [
            "⚠️  Can only generate one tone at a time",
            "⚠️  Interferes with PWM on pins 3 and 11",
            "⚠️  Use noTone() to stop"
        ],
        "tips": [
            "💡 Connect speaker/buzzer between pin and ground",
            "💡 Use duration parameter or noTone() to stop",
            "💡 Human hearing: ~20 Hz to 20 kHz"
        ],
        "example": """tone(8, 1000);     // 1kHz tone on pin 8
delay(1000);
noTone(8);         // Stop tone

tone(8, 262, 250); // Middle C for 250ms"""
    },

    "noTone": {
        "title": "No Tone",
        "category": "Advanced I/O",
        "description": "Stops tone generation on a pin",
        "syntax": "noTone(pin)",
        "parameters": [
            {
                "name": "pin",
                "type": "int",
                "description": "Pin to stop tone output"
            }
        ],
        "common_values": [],
        "warnings": [],
        "tips": [
            "💡 Always call after tone() if no duration specified",
            "💡 Stops the tone immediately"
        ],
        "example": """tone(8, 1000);
delay(500);
noTone(8);"""
    },

    "pulseIn": {
        "title": "Pulse In",
        "category": "Advanced I/O",
        "description": "Reads a pulse (HIGH or LOW) on a pin and returns duration in microseconds",
        "syntax": "pulseIn(pin, value)\npulseIn(pin, value, timeout)",
        "parameters": [
            {
                "name": "pin",
                "type": "int",
                "description": "Pin to read pulse from"
            },
            {
                "name": "value",
                "type": "int",
                "description": "Type of pulse to read: HIGH or LOW"
            },
            {
                "name": "timeout",
                "type": "unsigned long",
                "description": "Timeout in microseconds (optional, default 1 second)"
            }
        ],
        "common_values": [],
        "warnings": [
            "⚠️  Blocking function (waits for pulse)",
            "⚠️  Returns 0 if timeout occurs"
        ],
        "tips": [
            "💡 Use for ultrasonic sensors (HC-SR04)",
            "💡 Accurate from 10μs to 3 minutes",
            "💡 Set shorter timeout to avoid long waits"
        ],
        "example": """// Ultrasonic sensor
digitalWrite(trigPin, LOW);
delayMicroseconds(2);
digitalWrite(trigPin, HIGH);
delayMicroseconds(10);
digitalWrite(trigPin, LOW);

long duration = pulseIn(echoPin, HIGH);
long distance = duration * 0.034 / 2;"""
    },
}


def get_api_info(function_name):
    """Get API information for a function name or C++ keyword"""
    # Direct match in Arduino API
    if function_name in ARDUINO_API:
        return ARDUINO_API[function_name]

    # Direct match in C++ reference
    if function_name in CPP_REFERENCE:
        return CPP_REFERENCE[function_name]

    # Try to match base function (e.g., "Serial.print" matches "Serial.println")
    for key in ARDUINO_API:
        if function_name.startswith(key) or key.startswith(function_name):
            return ARDUINO_API[key]

    # Try partial match in C++ reference (for operators and special cases)
    for key in CPP_REFERENCE:
        if function_name.startswith(key) or key.startswith(function_name):
            return CPP_REFERENCE[key]

    return None


def get_all_functions():
    """Get list of all documented functions and C++ keywords"""
    return list(ARDUINO_API.keys()) + list(CPP_REFERENCE.keys())
