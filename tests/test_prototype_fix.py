#!/usr/bin/env python3
"""Test the prototype generation fix for custom types"""

import re

def _generate_function_prototypes(source: str):
    """
    Generate forward declarations for all user-defined functions in the sketch.
    This is the FIXED version that handles custom types.
    """
    prototypes = []

    # Remove comments to avoid matching function-like patterns in comments
    source_no_comments = re.sub(r'//.*?$', '', source, flags=re.MULTILINE)
    source_no_comments = re.sub(r'/\*.*?\*/', '', source_no_comments, flags=re.DOTALL)

    # Extract all custom type names (structs, classes, enums, typedefs)
    custom_types = set()

    type_patterns = [
        r'^\s*(?:typedef\s+)?struct\s+([a-zA-Z_]\w*)',
        r'^\s*(?:typedef\s+)?class\s+([a-zA-Z_]\w*)',
        r'^\s*(?:typedef\s+)?enum\s+([a-zA-Z_]\w*)',
        r'^\s*typedef\s+.*?\s+([a-zA-Z_]\w*)\s*;',
    ]

    for pattern in type_patterns:
        for match in re.finditer(pattern, source_no_comments, re.MULTILINE):
            custom_types.add(match.group(1))

    # Pattern to match function definitions
    function_pattern = r'^\s*(?:inline\s+|static\s+)?([a-zA-Z_][\w\s\*&:<>,]*?)\s+([a-zA-Z_]\w*)\s*\((.*?)\)\s*(?:\{|$)'

    # Find all function definitions
    for match in re.finditer(function_pattern, source_no_comments, re.MULTILINE):
        return_type = match.group(1).strip()
        function_name = match.group(2).strip()
        parameters = match.group(3).strip()

        # Skip setup() and loop()
        if function_name in ('setup', 'loop'):
            continue

        # Skip if this looks like a class method definition
        if '::' in return_type:
            continue

        # Skip preprocessor directives
        if return_type.startswith('#'):
            continue

        # Skip if return type contains keywords
        skip_keywords = ['class', 'struct', 'enum', 'typedef', 'namespace', 'if', 'while', 'for', 'switch']
        if any(keyword in return_type for keyword in skip_keywords):
            continue

        # Check if the function signature contains any custom types
        full_signature = f"{return_type} {parameters}"
        uses_custom_type = any(custom_type in full_signature for custom_type in custom_types)

        if uses_custom_type:
            # Skip generating prototype for functions using custom types
            continue

        # Build the prototype
        prototype = f"{return_type} {function_name}({parameters});"
        prototypes.append(prototype)

    return prototypes, custom_types


# Test sketch with custom types
test_sketch = """
struct PointControl {
  int pin;
  int state;
  unsigned long lastUpdate;
};

// Functions using custom type
void initializePoint(PointControl& point) {
  point.pin = 2;
}

void updatePoint(PointControl& point, unsigned long now) {
  point.lastUpdate = now;
}

int interpretState(const PointControl& point, int analogValue) {
  return analogValue > 512 ? 1 : 0;
}

// Function with built-in types only
void blinkLED(int pin, int duration) {
  digitalWrite(pin, HIGH);
}

void setup() {
  Serial.begin(9600);
}

void loop() {
  delay(1000);
}
"""

# Test prototype generation
prototypes, custom_types = _generate_function_prototypes(test_sketch)

print("Detected custom types:")
for type_name in custom_types:
    print(f"  {type_name}")

print("\nGenerated prototypes:")
for proto in prototypes:
    print(f"  {proto}")

# Verify results
has_point_control = any('PointControl' in proto for proto in prototypes)
has_blink_led = any('blinkLED' in proto for proto in prototypes)

print("\n" + "="*60)
print("Test results:")
print("="*60)
print(f"  PointControl detected as custom type: {'PointControl' in custom_types}")
print(f"  PointControl prototypes generated: {has_point_control} (should be False)")
print(f"  blinkLED prototype generated: {has_blink_led} (should be True)")

if 'PointControl' in custom_types and not has_point_control and has_blink_led:
    print("\n✓ Test PASSED! Prototype generation correctly handles custom types.")
    print("  - Custom types are detected")
    print("  - Prototypes using custom types are NOT generated")
    print("  - Prototypes using built-in types ARE generated")
    exit(0)
else:
    print("\n✗ Test FAILED!")
    exit(1)
