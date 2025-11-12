#!/usr/bin/env python3
"""Test complete fix: extract types and remove from source"""

import re

def _extract_and_remove_type_definitions(source: str) -> tuple:
    """Extract and remove type definitions from source."""
    import re

    type_defs = []
    original_lines = source.split('\n')

    # Use source without comments for detection
    source_no_comments = re.sub(r'//.*?$', '', source, flags=re.MULTILINE)
    source_no_comments = re.sub(r'/\*.*?\*/', '', source_no_comments, flags=re.DOTALL)
    detection_lines = source_no_comments.split('\n')

    # Track line ranges to remove
    lines_to_remove = set()

    i = 0
    while i < len(detection_lines):
        line = detection_lines[i].strip()

        # Check if this line starts a type definition
        if re.match(r'^\s*(?:typedef\s+)?(struct|class|enum)\s+\w+', line):
            start_line = i
            type_def_lines = [original_lines[i]]
            brace_count = detection_lines[i].count('{') - detection_lines[i].count('}')
            i += 1

            # Continue collecting lines until braces are balanced
            while i < len(detection_lines) and brace_count > 0:
                type_def_lines.append(original_lines[i])
                brace_count += detection_lines[i].count('{') - detection_lines[i].count('}')
                i += 1

            # Collect any remaining lines until we hit a semicolon
            while i < len(detection_lines) and not type_def_lines[-1].rstrip().endswith(';'):
                type_def_lines.append(original_lines[i])
                i += 1
                if ';' in type_def_lines[-1]:
                    break

            # Mark these lines for removal
            for line_num in range(start_line, i):
                lines_to_remove.add(line_num)

            type_defs.append('\n'.join(type_def_lines))
        else:
            i += 1

    # Build source without type definitions
    source_without_types_lines = [
        line for idx, line in enumerate(original_lines)
        if idx not in lines_to_remove
    ]
    source_without_types = '\n'.join(source_without_types_lines)

    type_definitions_string = '\n\n'.join(type_defs) if type_defs else ''

    return type_definitions_string, source_without_types


# Test sketch simulating the user's scenario
test_sketch = """
// Manual prototypes (like the user might have)
void initializePoint(PointControl& point);
void updatePoint(PointControl& point, unsigned long now);
int interpretState(const PointControl& point, int analogValue);

// Custom struct definition
struct PointControl {
  int pin;
  int state;
  unsigned long lastUpdate;
};

// Global variables
PointControl myPoint;

void setup() {
  Serial.begin(9600);
  initializePoint(myPoint);
}

void loop() {
  unsigned long now = millis();
  updatePoint(myPoint, now);
  delay(1000);
}

// Function implementations
void initializePoint(PointControl& point) {
  point.pin = 2;
  point.state = 0;
  point.lastUpdate = 0;
}

void updatePoint(PointControl& point, unsigned long now) {
  point.lastUpdate = now;
  point.state = interpretState(point, analogRead(point.pin));
}

int interpretState(const PointControl& point, int analogValue) {
  return analogValue > 512 ? 1 : 0;
}
"""

# Extract and remove type definitions
type_defs, source_without_types = _extract_and_remove_type_definitions(test_sketch)

print("Extracted type definitions:")
print("="*60)
print(type_defs)
print("="*60)

# Build the complete .cpp file
cpp_content = '#include <Arduino.h>\n\n'

if type_defs:
    cpp_content += '// Forward declarations for custom types\n'
    cpp_content += type_defs + '\n\n'

cpp_content += source_without_types

print("\nGenerated .cpp file preview (first 50 lines):")
print("="*60)
for i, line in enumerate(cpp_content.split('\n')[:50], 1):
    print(f"{i:3}: {line}")
print("="*60)

# Verify no redefinition
struct_count = cpp_content.count('struct PointControl')
print(f"\nAnalysis:")
print(f"  Number of 'struct PointControl' definitions: {struct_count}")

# Check order
lines = cpp_content.split('\n')
struct_line = None
first_use_line = None

for i, line in enumerate(lines):
    if 'struct PointControl' in line and struct_line is None:
        struct_line = i
    if 'PointControl&' in line and 'struct PointControl' not in line and first_use_line is None:
        first_use_line = i

print(f"  PointControl struct defined at line: {struct_line}")
print(f"  First use of PointControl at line: {first_use_line}")

if struct_count == 1 and struct_line and first_use_line and struct_line < first_use_line:
    print("\n✓ PERFECT! Fix is working correctly:")
    print("  - PointControl defined exactly ONCE")
    print("  - PointControl defined BEFORE first use")
    print("  - No redefinition errors will occur")
    print("  - This should compile successfully!")
    exit(0)
else:
    print("\n✗ Issue detected:")
    if struct_count > 1:
        print(f"  - PointControl defined {struct_count} times (redefinition error)")
    if not (struct_line and first_use_line and struct_line < first_use_line):
        print("  - PointControl used before definition")
    exit(1)
