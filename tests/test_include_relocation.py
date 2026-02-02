#!/usr/bin/env python3
"""
Test suite for include, define, and type definition relocation in the Arduino preprocessor.

This tests the fix for the bug where #include statements ended up inside function bodies
when the preprocessor rearranged code.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import by executing the script and extracting the class
cli_path = parent_dir / "arduino-cli"
cli_globals = {'__name__': 'arduino_cli', '__file__': str(cli_path)}
with open(cli_path) as f:
    exec(compile(f.read(), cli_path, 'exec'), cli_globals)

ArduinoCLI = cli_globals['ArduinoCLI']


def test_extract_includes():
    """Test that #include statements are extracted correctly."""
    cli = ArduinoCLI()

    source = '''
#include <EEPROM.h>
#include "BenchmarkHelpers.h"

void setup() {
    Serial.begin(9600);
}

#include <SPI.h>

void loop() {
    // test
}
'''

    includes, source_without = cli._extract_and_relocate_includes(source)

    assert len(includes) == 3, f"Expected 3 includes, got {len(includes)}"
    assert '#include <EEPROM.h>' in includes[0]
    assert '#include "BenchmarkHelpers.h"' in includes[1]
    assert '#include <SPI.h>' in includes[2]
    assert '#include' not in source_without
    print("✓ test_extract_includes passed")


def test_extract_defines():
    """Test that #define statements are extracted correctly."""
    cli = ArduinoCLI()

    source = '''
void printMessage() {
    SERIAL_OUT.println(F_STR("Hello"));
}

#define SERIAL_OUT Serial
#define F_STR(x) F(x)

void setup() {}
void loop() {}
'''

    defines, source_without = cli._extract_and_relocate_defines(source)

    assert len(defines) == 2, f"Expected 2 defines, got {len(defines)}"
    assert '#define SERIAL_OUT Serial' in defines[0]
    assert '#define F_STR(x) F(x)' in defines[1]
    assert '#define SERIAL_OUT' not in source_without
    assert '#define F_STR' not in source_without
    print("✓ test_extract_defines passed")


def test_extract_multiline_define():
    """Test that multi-line #define statements are extracted correctly."""
    cli = ArduinoCLI()

    source = '''
#define MULTI_LINE_MACRO(x) \\
    do { \\
        Serial.println(x); \\
    } while(0)

void setup() {}
void loop() {}
'''

    defines, source_without = cli._extract_and_relocate_defines(source)

    assert len(defines) == 1, f"Expected 1 define, got {len(defines)}"
    assert 'MULTI_LINE_MACRO' in defines[0]
    assert 'do {' in defines[0]
    assert 'while(0)' in defines[0]
    print("✓ test_extract_multiline_define passed")


def test_extract_template_class():
    """Test that template class definitions are extracted correctly."""
    cli = ArduinoCLI()

    source = '''
void useTemplate() {
    MedianCollector<float, 5> collector;
}

template<typename T, int N>
class MedianCollector {
public:
    T values[N];
    int count = 0;

    void add(T value) {
        if (count < N) {
            values[count++] = value;
        }
    }

    T median() const {
        return values[count / 2];
    }
};

void setup() {}
void loop() {}
'''

    type_defs, source_without = cli._extract_and_remove_type_definitions(source)

    assert 'template<typename T, int N>' in type_defs, "Template class not extracted"
    assert 'class MedianCollector' in type_defs, "Class name not in extracted types"
    assert 'T median() const' in type_defs, "Method not in extracted class"
    assert 'template<typename T, int N>' not in source_without, "Template still in source"
    print("✓ test_extract_template_class passed")


def test_extract_global_constants():
    """Test that global constants are extracted correctly."""
    cli = ArduinoCLI()

    source = '''
void useConstant() {
    for (int i = 0; i < kJitterTrials; i++) {}
}

const int kJitterTrials = 5;
constexpr uint32_t kMinDuration = 1000;

void setup() {}
void loop() {}
'''

    constants, source_without = cli._extract_global_constants(source)

    assert len(constants) >= 2, f"Expected at least 2 constants, got {len(constants)}"
    assert any('kJitterTrials' in c for c in constants), "kJitterTrials not extracted"
    assert any('kMinDuration' in c for c in constants), "kMinDuration not extracted"
    print("✓ test_extract_global_constants passed")


def test_full_preprocessing_order():
    """Test that full preprocessing produces correct file order."""
    cli = ArduinoCLI()

    # Simulate a complex sketch with out-of-order declarations
    source = '''
void printDivider() {
    SERIAL_OUT.println(F_STR("========"));
}

void benchmarkWithTemplate() {
    MedianCollector<float, kTrials> collector;
}

#include <EEPROM.h>
#include "BenchmarkHelpers.h"

#define SERIAL_OUT Serial
#define F_STR(x) F(x)

const int kTrials = 5;

template<typename T, int N>
struct MedianCollector {
    T values[N];
    void add(T v) { values[0] = v; }
};

void setup() {
    Serial.begin(9600);
}

void loop() {
}
'''

    # Extract includes
    includes, s1 = cli._extract_and_relocate_includes(source)
    assert len(includes) == 2, "Should extract 2 includes"

    # Extract defines
    defines, s2 = cli._extract_and_relocate_defines(s1)
    assert len(defines) == 2, "Should extract 2 defines"

    # Extract constants
    constants, s3 = cli._extract_global_constants(s2)
    assert len(constants) >= 1, "Should extract at least 1 constant"

    # Extract type definitions
    types, s4 = cli._extract_and_remove_type_definitions(s3)
    assert 'MedianCollector' in types, "Should extract MedianCollector"

    # Verify nothing is left that shouldn't be
    assert '#include' not in s4, "Includes should be removed from source"
    assert '#define SERIAL_OUT' not in s4, "Defines should be removed from source"

    print("✓ test_full_preprocessing_order passed")


def test_include_not_in_function_body():
    """Test that includes don't end up inside function bodies after preprocessing."""
    cli = ArduinoCLI()

    # This was the actual bug - includes ending up inside class methods
    source = '''
template<typename T, int N>
class MedianCollector {
public:
    T median() const {
        T sorted[N];
        return sorted[N/2];
    }
};

#include <EEPROM.h>

void setup() {}
void loop() {}
'''

    includes, s1 = cli._extract_and_relocate_includes(source)
    type_defs, s2 = cli._extract_and_remove_type_definitions(s1)

    # Includes should be extracted
    assert len(includes) == 1
    assert 'EEPROM.h' in includes[0]

    # Type definitions should be extracted
    assert 'MedianCollector' in type_defs
    assert 'T median()' in type_defs

    # The remaining source should not have includes
    assert '#include' not in s2

    print("✓ test_include_not_in_function_body passed")


if __name__ == '__main__':
    print("Testing include and define relocation...\n")

    test_extract_includes()
    test_extract_defines()
    test_extract_multiline_define()
    test_extract_template_class()
    test_extract_global_constants()
    test_full_preprocessing_order()
    test_include_not_in_function_body()

    print("\n✅ All tests passed!")
