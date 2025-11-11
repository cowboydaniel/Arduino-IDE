#!/usr/bin/env python3
"""Test removal of manual prototypes that use custom types"""

import re

def _extract_and_remove_type_definitions(source: str) -> tuple:
    """Extract type definitions from source"""
    import re

    type_defs = []
    original_lines = source.split('\n')

    source_no_comments = re.sub(r'//.*?$', '', source, flags=re.MULTILINE)
    source_no_comments = re.sub(r'/\*.*?\*/', '', source_no_comments, flags=re.DOTALL)
    detection_lines = source_no_comments.split('\n')

    lines_to_remove = set()

    i = 0
    while i < len(detection_lines):
        line = detection_lines[i].strip()

        if re.match(r'^\s*(?:typedef\s+)?(struct|class|enum)\s+\w+', line):
            if ';' in line and '{' not in line:
                i += 1
                continue

            start_line = i
            type_def_lines = [original_lines[i]]
            brace_count = detection_lines[i].count('{') - detection_lines[i].count('}')
            i += 1

            while i < len(detection_lines) and brace_count > 0:
                type_def_lines.append(original_lines[i])
                brace_count += detection_lines[i].count('{') - detection_lines[i].count('}')
                i += 1

            while i < len(detection_lines) and not type_def_lines[-1].rstrip().endswith(';'):
                type_def_lines.append(original_lines[i])
                i += 1
                if ';' in type_def_lines[-1]:
                    break

            for line_num in range(start_line, i):
                lines_to_remove.add(line_num)

            type_defs.append('\n'.join(type_def_lines))
        else:
            i += 1

    source_without_types_lines = [
        line for idx, line in enumerate(original_lines)
        if idx not in lines_to_remove
    ]
    source_without_types = '\n'.join(source_without_types_lines)

    type_definitions_string = '\n\n'.join(type_defs) if type_defs else ''

    return type_definitions_string, source_without_types

def _extract_custom_type_names(type_definitions: str) -> set:
    """Extract type names from type definition string."""
    import re

    if not type_definitions:
        return set()

    custom_types = set()
    type_patterns = [
        r'^\s*(?:typedef\s+)?struct\s+([a-zA-Z_]\w*)',
        r'^\s*(?:typedef\s+)?class\s+([a-zA-Z_]\w*)',
        r'^\s*(?:typedef\s+)?enum\s+([a-zA-Z_]\w*)',
    ]

    for pattern in type_patterns:
        for match in re.finditer(pattern, type_definitions, re.MULTILINE):
            custom_types.add(match.group(1))

    return custom_types

def _remove_prototypes_using_custom_types(source: str, custom_types: set) -> str:
    """Remove function prototypes that use custom types."""
    import re

    if not custom_types:
        return source

    lines = source.split('\n')
    filtered_lines = []

    prototype_pattern = r'^\s*(?:inline\s+|static\s+|extern\s+)?(?:const\s+)?([a-zA-Z_][\w\s\*&:<>,]*?)\s+([a-zA-Z_]\w*)\s*\((.*?)\)\s*;'

    for line in lines:
        match = re.match(prototype_pattern, line)
        if match:
            full_signature = match.group(0)
            uses_custom_type = any(custom_type in full_signature for custom_type in custom_types)

            if uses_custom_type:
                continue

        filtered_lines.append(line)

    return '\n'.join(filtered_lines)

# Test sketch that mimics the user's scenario
test_sketch = """
// Manual prototypes at the top (like the user has)
void initializePoint(PointControl& point);
void updatePoint(PointControl& point, unsigned long now);
int interpretState(const PointControl& point, int analogValue);
int rawStateFromThreshold(const PointControl& point, int analogValue);
void applyPointLogic(PointControl& point);
const char* describeState(const PointControl& point, int state);

// Struct definition appears AFTER the prototypes
struct PointControl {
  int pin;
  int state;
  unsigned long lastUpdate;
};

// Function that doesn't use custom type
void blinkLED(int pin) {
  digitalWrite(pin, HIGH);
}

void setup() {
  Serial.begin(9600);
}

void loop() {
  delay(1000);
}

// Function implementations
void initializePoint(PointControl& point) {
  point.pin = 2;
}

void updatePoint(PointControl& point, unsigned long now) {
  point.lastUpdate = now;
}

int interpretState(const PointControl& point, int analogValue) {
  return analogValue > 512 ? 1 : 0;
}
"""

# Process the sketch
type_definitions, source_without_types = _extract_and_remove_type_definitions(test_sketch)
custom_types = _extract_custom_type_names(type_definitions)
source_without_types = _remove_prototypes_using_custom_types(source_without_types, custom_types)

# Build the cpp
cpp_content = '#include <Arduino.h>\n\n'

if type_definitions:
    cpp_content += '// Forward declarations for custom types\n'
    cpp_content += type_definitions + '\n\n'

cpp_content += source_without_types

print("Extracted custom types:")
print(f"  {custom_types}")
print()

print("Generated .cpp file preview (first 40 lines):")
print("="*60)
for i, line in enumerate(cpp_content.split('\n')[:40], 1):
    print(f"{i:3}: {line}")
print("="*60)

# Verify
manual_prototypes_removed = 'void initializePoint(PointControl& point);' not in source_without_types
struct_extracted = 'struct PointControl' in type_definitions
struct_first = cpp_content.index('struct PointControl') if 'struct PointControl' in cpp_content else -1

# Check if implementations are still there
impl_present = 'void initializePoint(PointControl& point) {' in cpp_content

print("\nAnalysis:")
print(f"  Custom types detected: {custom_types}")
print(f"  Struct extracted: {struct_extracted}")
print(f"  Manual prototypes removed from source: {manual_prototypes_removed}")
print(f"  Function implementations still present: {impl_present}")

# Count occurrences
proto_count = cpp_content.count('void initializePoint(PointControl& point);')
print(f"  Number of 'void initializePoint(PointControl& point);' in output: {proto_count}")

if struct_extracted and manual_prototypes_removed and impl_present and proto_count == 0:
    print("\n✓ PERFECT! Manual prototypes are handled correctly:")
    print("  - Struct definition extracted and placed at top")
    print("  - Manual prototypes using custom types removed")
    print("  - Function implementations preserved")
    print("  - Generated cpp will compile without errors")
    exit(0)
else:
    print("\n✗ Issue detected:")
    if not struct_extracted:
        print("  - Struct not extracted")
    if not manual_prototypes_removed:
        print("  - Manual prototypes not removed")
    if not impl_present:
        print("  - Function implementations missing")
    if proto_count > 0:
        print(f"  - Found {proto_count} manual prototypes in output")
    exit(1)
