#!/usr/bin/env python3
"""Test extraction of type definitions - simulating the real user scenario"""

import re

def _extract_type_definitions(source: str) -> str:
    """Extract struct, class, and enum definitions from source."""
    import re

    type_defs = []

    # Remove comments
    source_no_comments = re.sub(r'//.*?$', '', source, flags=re.MULTILINE)
    source_no_comments = re.sub(r'/\*.*?\*/', '', source_no_comments, flags=re.DOTALL)

    lines = source_no_comments.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check if this line starts a type definition
        if re.match(r'^\s*(?:typedef\s+)?(struct|class|enum)\s+\w+', line):
            # Found a type definition, collect it including the body
            type_def_lines = [lines[i]]
            brace_count = lines[i].count('{') - lines[i].count('}')
            i += 1

            # Continue collecting lines until braces are balanced
            while i < len(lines) and brace_count > 0:
                type_def_lines.append(lines[i])
                brace_count += lines[i].count('{') - lines[i].count('}')
                i += 1

            # Collect any remaining lines until we hit a semicolon
            while i < len(lines) and not type_def_lines[-1].rstrip().endswith(';'):
                type_def_lines.append(lines[i])
                i += 1
                if ';' in type_def_lines[-1]:
                    break

            type_defs.append('\n'.join(type_def_lines))
        else:
            i += 1

    return '\n\n'.join(type_defs) if type_defs else ''


# Test sketch simulating the user's scenario: manual prototypes at top
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

# Extract type definitions
type_defs = _extract_type_definitions(test_sketch)

print("Extracted type definitions:")
print("="*60)
print(type_defs)
print("="*60)

# Now simulate how the .cpp file would be built
cpp_content = '#include <Arduino.h>\n\n'

if type_defs:
    cpp_content += '// Forward declarations for custom types\n'
    cpp_content += type_defs + '\n\n'

cpp_content += '// Original sketch code\n'
cpp_content += test_sketch

print("\nGenerated .cpp file preview (first 40 lines):")
print("="*60)
for i, line in enumerate(cpp_content.split('\n')[:40], 1):
    print(f"{i:3}: {line}")
print("="*60)

# Check if PointControl definition appears before its first use in prototypes
lines = cpp_content.split('\n')
struct_line = None
first_use_line = None

for i, line in enumerate(lines):
    if 'struct PointControl' in line and struct_line is None:
        struct_line = i
    if 'PointControl&' in line and 'struct PointControl' not in line and first_use_line is None:
        first_use_line = i

print(f"\nAnalysis:")
print(f"  PointControl struct defined at line: {struct_line}")
print(f"  First use of PointControl at line: {first_use_line}")

if struct_line and first_use_line and struct_line < first_use_line:
    print("\n✓ SUCCESS! PointControl is defined BEFORE it's used.")
    print("  This should compile without errors.")
    exit(0)
else:
    print("\n✗ FAILED! PointControl is used before it's defined.")
    print("  This will cause compilation errors.")
    exit(1)
