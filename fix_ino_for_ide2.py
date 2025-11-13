#!/usr/bin/env python3
"""
Fix .ino files to be compatible with Arduino IDE 2.x preprocessor.

This script removes invalid global control flow statements that Arduino IDE 2.x
might incorrectly extract from function bodies.

Usage:
    python3 fix_ino_for_ide2.py input.ino [output.ino]

If output file is not specified, the input file will be backed up and modified in-place.
"""

import sys
import re
import shutil
from pathlib import Path

def fix_ino_file(input_path: str, output_path: str = None):
    """Fix an .ino file for Arduino IDE 2.x compatibility."""

    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Input file '{input_path}' not found")
        return 1

    # Read the source
    with open(input_file, 'r', encoding='utf-8') as f:
        source = f.read()

    # Create backup
    if output_path is None:
        output_path = str(input_file)
        backup_path = str(input_file) + '.backup'
        shutil.copy2(input_file, backup_path)
        print(f"Created backup: {backup_path}")

    # Remove invalid global control flow statements
    fixed_source = _remove_invalid_global_control_flow(source)

    # Write the fixed source
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fixed_source)

    print(f"Fixed file written to: {output_path}")
    return 0

def _remove_invalid_global_control_flow(source: str) -> str:
    """
    Remove invalid global control flow statements (if/else if/else/while/for/switch)
    that appear outside of function bodies.
    """
    lines = source.split('\n')
    filtered_lines = []

    brace_depth = 0
    in_function = False
    removed_count = 0

    def is_control_flow_statement(line: str) -> bool:
        """Check if a line is a control flow statement with semicolon body."""
        line = line.strip()
        if not line.endswith(';'):
            return False

        control_keywords = ['if', 'else if', 'else', 'while', 'for', 'switch']

        for keyword in control_keywords:
            if keyword == 'else if':
                if re.match(r'^\s*else\s+if\s*\(', line):
                    paren_count = 0
                    for char in line:
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                    if paren_count == 0 and line.rstrip().endswith(');'):
                        return True
            elif keyword == 'else':
                if re.match(r'^\s*else\s*;', line):
                    return True
            elif keyword in ['if', 'while', 'for', 'switch']:
                if re.match(rf'^\s*{keyword}\s*\(', line):
                    paren_count = 0
                    for char in line:
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                    if paren_count == 0 and line.rstrip().endswith(');'):
                        return True

        return False

    for line in lines:
        open_braces = line.count('{')
        close_braces = line.count('}')

        # Check if this line starts a function definition
        if re.match(r'^\s*(?:inline\s+|static\s+)?[a-zA-Z_][\w\s\*&:<>,]*\s+[a-zA-Z_]\w*\s*\([^)]*\)\s*\{', line):
            in_function = True
            brace_depth = 1
            filtered_lines.append(line)
            continue

        # Update brace depth
        brace_depth += open_braces - close_braces

        # If brace_depth goes to 0, we've exited all functions
        if brace_depth <= 0:
            in_function = False
            brace_depth = 0

        # Only filter out control flow statements at global scope
        if not in_function:
            if is_control_flow_statement(line):
                print(f"Removing: {line[:80]}")
                removed_count += 1
                continue

        # Keep this line
        filtered_lines.append(line)

    if removed_count > 0:
        print(f"\nRemoved {removed_count} invalid global control flow statement(s)")
    else:
        print("\nNo invalid global control flow statements found")

    return '\n'.join(filtered_lines)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    sys.exit(fix_ino_file(input_file, output_file))
