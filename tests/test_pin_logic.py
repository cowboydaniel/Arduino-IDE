#!/usr/bin/env python3
"""
Test script to verify pin generation logic
"""

from arduino_ide.models.board import DEFAULT_BOARDS

def test_pin_generation():
    """Test that pins are generated correctly for each board"""

    print("Testing pin generation for all default boards:\n")

    for board in DEFAULT_BOARDS:
        print(f"Board: {board.name}")
        print(f"  Architecture: {board.architecture}")
        print(f"  Digital pins: {board.specs.digital_pins}")
        print(f"  Analog pins: {board.specs.analog_pins}")

        # Generate pins like the widget does
        digital_pins = [f'D{i}' for i in range(board.specs.digital_pins)]
        analog_pins = [f'A{i}' for i in range(board.specs.analog_pins)]
        all_pins = digital_pins + analog_pins

        print(f"  Total pins: {len(all_pins)}")
        print(f"  Digital: {', '.join(digital_pins[:5])}{'...' if len(digital_pins) > 5 else ''}")
        print(f"  Analog: {', '.join(analog_pins)}")
        print()

if __name__ == "__main__":
    test_pin_generation()
