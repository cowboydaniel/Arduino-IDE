#!/usr/bin/env python3
"""Test handling of forward declarations vs full definitions"""

import sys
import re

# Import the extraction function directly
def _extract_and_remove_type_definitions(source: str) -> tuple:
    """Extract type definitions from source (copy from arduino-cli)"""
    import re

    type_defs = []
    original_lines = source.split('\n')

    # Use source without comments for detection
    source_no_comments = re.sub(r'//.*?$', '', source, flags=re.MULTILINE)
    source_no_comments = re.sub(r'/\*.*?\*/', '', source_no_comments, flags=re.DOTALL)
    detection_lines = source_no_comments.split('\n')

    # Track line ranges to remove from original source
    lines_to_remove = set()

    i = 0
    while i < len(detection_lines):
        line = detection_lines[i].strip()

        # Check if this line starts a type definition
        if re.match(r'^\s*(?:typedef\s+)?(struct|class|enum)\s+\w+', line):
            # Check if this is a forward declaration (ends with semicolon, no braces)
            # We only want to extract FULL definitions, not forward declarations
            if ';' in line and '{' not in line:
                # This is a forward declaration, skip it
                i += 1
                continue

            # Found a type definition start
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

# Test sketch with forward declaration followed by full definition
test_sketch = """
// Forward declaration (should NOT be extracted)
struct PointControl;

// Function prototype using forward declaration
void initializePoint(PointControl& point);

// Full struct definition (should be extracted and hoisted)
struct PointControl {
  int pin;
  int state;
  unsigned long lastUpdate;
};

void setup() {
  Serial.begin(9600);
}

void loop() {
  delay(1000);
}

// Function implementation
void initializePoint(PointControl& point) {
  point.pin = 2;
  point.state = 0;
}
"""

# Extract type definitions
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

print("\nGenerated .cpp file preview:")
print("="*60)
for i, line in enumerate(cpp_content.split('\n')[:40], 1):
    print(f"{i:3}: {line}")
print("="*60)

# Verify
print("\nAnalysis:")
print(f"  Forward declaration 'struct PointControl;' in type_defs: {'struct PointControl;' in type_defs}")
print(f"  Full definition in type_defs: {'{' in type_defs and 'int pin' in type_defs}")

# Count struct PointControl definitions
full_def_count = type_defs.count('struct PointControl {')
forward_decl_in_types = type_defs.count('struct PointControl;')

print(f"  Full definitions in type_defs: {full_def_count}")
print(f"  Forward declarations in type_defs: {forward_decl_in_types}")

# Check if forward declaration is still in source
forward_decl_in_source = 'struct PointControl;' in source_without_types
print(f"  Forward declaration still in source_without_types: {forward_decl_in_source}")

if full_def_count == 1 and forward_decl_in_types == 0 and forward_decl_in_source:
    print("\n✓ PERFECT! Forward declarations are handled correctly:")
    print("  - Forward declaration NOT extracted (remains in source)")
    print("  - Full definition extracted and placed at top")
    print("  - This ensures the type is fully defined before use")
    exit(0)
else:
    print("\n✗ Issue detected:")
    if forward_decl_in_types > 0:
        print("  - Forward declaration was incorrectly extracted")
    if full_def_count != 1:
        print(f"  - Expected 1 full definition, found {full_def_count}")
    if not forward_decl_in_source:
        print("  - Forward declaration was removed from source")
    exit(1)
