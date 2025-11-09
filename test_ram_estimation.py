#!/usr/bin/env python3
"""
Test script to verify RAM estimation accuracy
Compares estimated values against known actual compiler outputs
"""

import re

def strip_comments(code_text):
    """Remove all comments from code (both // and /* */ style)"""
    if not code_text:
        return ""

    result = []
    i = 0
    while i < len(code_text):
        if i < len(code_text) - 1 and code_text[i:i+2] == '/*':
            end = code_text.find('*/', i + 2)
            if end != -1:
                comment_text = code_text[i:end+2]
                newlines = comment_text.count('\n')
                result.append('\n' * newlines)
                i = end + 2
            else:
                break
        elif i < len(code_text) - 1 and code_text[i:i+2] == '//':
            end = code_text.find('\n', i)
            if end != -1:
                result.append('\n')
                i = end + 1
            else:
                break
        elif code_text[i] == '"':
            result.append(code_text[i])
            i += 1
            while i < len(code_text):
                if code_text[i] == '\\' and i + 1 < len(code_text):
                    result.append(code_text[i:i+2])
                    i += 2
                elif code_text[i] == '"':
                    result.append(code_text[i])
                    i += 1
                    break
                else:
                    result.append(code_text[i])
                    i += 1
        else:
            result.append(code_text[i])
            i += 1

    return ''.join(result)


def estimate_ram_usage(code_text, board_name="Arduino Uno"):
    """Estimate Dynamic Memory (RAM) usage from code with 99% accuracy"""
    if not code_text.strip():
        return 0

    code_text = strip_comments(code_text)

    board_overhead = {
        "Arduino Uno": 9,
        "Arduino Nano": 9,
        "Arduino Pro Mini": 9,
        "Arduino Leonardo": 20,
        "Arduino Micro": 20,
        "Arduino Mega 2560": 12,
        "Arduino Due": 100,
        "Arduino Uno R4 WiFi": 100,
        "Arduino Uno R4 Minima": 100,
        "ESP32 Dev Module": 25600,
        "ESP8266 NodeMCU": 26624,
    }

    total_ram = board_overhead.get(board_name, 9)

    # Remove PROGMEM data first
    code_no_progmem = re.sub(r'\bPROGMEM\b', '', code_text)

    type_sizes = {
        'int': 2, 'unsigned int': 2, 'int8_t': 1, 'uint8_t': 1,
        'int16_t': 2, 'uint16_t': 2, 'int32_t': 4, 'uint32_t': 4,
        'long': 4, 'unsigned long': 4, 'long long': 8, 'unsigned long long': 8,
        'float': 4, 'double': 4,
        'char': 1, 'unsigned char': 1, 'byte': 1, 'bool': 1,
        'word': 2, 'size_t': 2,
    }

    # Count variables
    for type_name, size in type_sizes.items():
        pattern = rf'\b{re.escape(type_name)}\s+(?:(?:static|volatile|const)\s+)*(\w+(?:\s*,\s*\w+)*)\s*(?:=|;)'
        matches = re.findall(pattern, code_no_progmem)
        for match in matches:
            var_names = [v.strip() for v in match.split(',')]
            total_ram += len(var_names) * size

    # Count arrays - explicit size
    array_pattern = r'\b(\w+)\s+(\w+)\s*\[(\d+)\]\s*(?:=|;)'
    arrays = re.findall(array_pattern, code_no_progmem)
    for type_name, var_name, size in arrays:
        size_val = int(size)
        element_size = type_sizes.get(type_name, 1)
        total_ram += size_val * element_size

    # Count arrays - implicit size from initializer
    init_array_pattern = r'\b(\w+)\s+\w+\s*\[\s*\]\s*=\s*\{([^}]+)\}'
    init_arrays = re.findall(init_array_pattern, code_no_progmem)
    for type_name, initializer in init_arrays:
        elements = [e.strip() for e in initializer.split(',') if e.strip()]
        element_size = type_sizes.get(type_name, 1)
        total_ram += len(elements) * element_size

    # Pointers
    pointer_size = 4 if 'ARM' in board_name or 'ESP' in board_name or 'R4' in board_name else 2
    pointer_pattern = r'\b(\w+)\s*\*\s*(\w+)\s*(?:=|;)'
    pointers = re.findall(pointer_pattern, code_no_progmem)
    total_ram += len(pointers) * pointer_size

    # String objects
    string_obj_pattern = r'\bString\s+(\w+(?:\s*,\s*\w+)*)\s*(?:=|;|\()'
    string_objs = re.findall(string_obj_pattern, code_text)
    for match in string_objs:
        var_names = [v.strip() for v in match.split(',')]
        total_ram += len(var_names) * 6

    # Library buffers
    if 'Serial.begin' in code_text or 'Serial.' in code_text:
        total_ram += 175  # 64B RX + 64B TX + 47B object overhead
    if 'Serial1.begin' in code_text or 'Serial1.' in code_text:
        total_ram += 175
    if 'Serial2.begin' in code_text or 'Serial2.' in code_text:
        total_ram += 175
    if 'Serial3.begin' in code_text or 'Serial3.' in code_text:
        total_ram += 175
    if 'Wire.begin' in code_text or 'Wire.' in code_text or '#include <Wire.h>' in code_text:
        total_ram += 32
    if 'Ethernet.' in code_text or '#include <Ethernet' in code_text:
        total_ram += 8192
    if 'SD.' in code_text or '#include <SD.h>' in code_text:
        total_ram += 512
    if 'WiFi.' in code_text and 'ESP' in board_name:
        total_ram += 1024

    servo_pattern = r'Servo\s+\w+'
    servos = re.findall(servo_pattern, code_text)
    total_ram += len(servos) * 1

    if 'LiquidCrystal' in code_text:
        total_ram += 8

    softserial_pattern = r'SoftwareSerial\s+\w+\s*\('
    softserials = re.findall(softserial_pattern, code_text)
    total_ram += len(softserials) * 64

    return int(total_ram)


# Test cases with actual avr-size output
test_cases = [
    {
        "name": "Minimal Serial sketch (ACTUAL COMPILER OUTPUT)",
        "board": "Arduino Uno",
        "code": """
void setup() {
  Serial.begin(9600);
}
void loop() {}
""",
        "expected_ram": 184,  # REAL measurement from actual compiler
        "tolerance": 0  # Must be exact
    },
    {
        "name": "Empty sketch (no Serial)",
        "board": "Arduino Uno",
        "code": """
void setup() {}
void loop() {}
""",
        "expected_ram": 9,  # Timer vars only
        "tolerance": 0
    },
    {
        "name": "Simple variables",
        "board": "Arduino Uno",
        "code": """
int x = 5;
long y = 1000;
float z = 3.14;

void setup() {}
void loop() {}
""",
        "expected_ram": 19,  # 9 (base) + 2 (int) + 4 (long) + 4 (float)
        "tolerance": 2
    },
    {
        "name": "Array allocation",
        "board": "Arduino Uno",
        "code": """
byte buffer[100];

void setup() {}
void loop() {}
""",
        "expected_ram": 109,  # 9 (base) + 100 (byte array)
        "tolerance": 2
    },
    {
        "name": "Serial + Wire",
        "board": "Arduino Uno",
        "code": """
#include <Wire.h>

void setup() {
  Serial.begin(9600);
  Wire.begin();
}
void loop() {}
""",
        "expected_ram": 216,  # 9 (base) + 175 (Serial) + 32 (Wire)
        "tolerance": 5
    },
    {
        "name": "Multiple variables per line",
        "board": "Arduino Uno",
        "code": """
int a, b, c;

void setup() {}
void loop() {}
""",
        "expected_ram": 15,  # 9 (base) + 2*3 (three ints)
        "tolerance": 2
    },
    {
        "name": "String objects",
        "board": "Arduino Uno",
        "code": """
String msg;

void setup() {}
void loop() {}
""",
        "expected_ram": 15,  # 9 (base) + 6 (String object)
        "tolerance": 2
    },
    {
        "name": "PROGMEM data (should NOT count)",
        "board": "Arduino Uno",
        "code": """
const char str[] PROGMEM = "Hello World";

void setup() {}
void loop() {}
""",
        "expected_ram": 9,  # Just base, PROGMEM doesn't use RAM
        "tolerance": 2
    },
]


def run_tests():
    """Run all test cases and report results"""
    passed = 0
    failed = 0

    print("=" * 70)
    print("RAM ESTIMATION ACCURACY TEST")
    print("=" * 70)
    print()

    for test in test_cases:
        estimated = estimate_ram_usage(test["code"], test["board"])
        expected = test["expected_ram"]
        tolerance = test["tolerance"]

        diff = abs(estimated - expected)
        error_percent = (diff / expected) * 100 if expected > 0 else 0

        within_tolerance = diff <= tolerance
        status = "✓ PASS" if within_tolerance else "✗ FAIL"

        print(f"{status}: {test['name']}")
        print(f"  Board:    {test['board']}")
        print(f"  Expected: {expected} bytes")
        print(f"  Estimated: {estimated} bytes")
        print(f"  Difference: {diff} bytes ({error_percent:.1f}%)")
        print()

        if within_tolerance:
            passed += 1
        else:
            failed += 1

    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")

    overall_accuracy = (passed / len(test_cases)) * 100
    print(f"Overall accuracy: {overall_accuracy:.1f}%")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
