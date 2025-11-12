#!/usr/bin/env python3
"""
Test script to verify component library loading from JSON files
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock PySide6 if not available
try:
    from PySide6.QtCore import QObject, Signal
except ImportError:
    print("PySide6 not available, using mock classes...")
    class Signal:
        def __init__(self, *args):
            pass
        def emit(self, *args):
            pass
        def connect(self, *args):
            pass

    class QObject:
        def __init__(self, parent=None):
            pass

    sys.modules['PySide6'] = type(sys)('PySide6')
    sys.modules['PySide6.QtCore'] = type(sys)('PySide6.QtCore')
    sys.modules['PySide6.QtCore'].QObject = QObject
    sys.modules['PySide6.QtCore'].Signal = Signal

from arduino_ide.services.circuit_service import CircuitService, ComponentType

def main():
    print("=" * 70)
    print("TESTING COMPONENT LIBRARY LOADING FROM JSON FILES")
    print("=" * 70)

    # Initialize service
    print("\nInitializing Circuit Service...")
    service = CircuitService()

    # Get all components
    all_components = service.get_all_component_definitions()
    print(f"\n✓ Total Components Loaded: {len(all_components)}")

    if len(all_components) == 0:
        print("\n✗ ERROR: No components were loaded!")
        print("  Check that component_library folder exists and contains JSON files")
        return 1

    # Count by type
    print("\n" + "=" * 70)
    print("COMPONENTS BY TYPE")
    print("=" * 70)

    type_counts = {}
    for comp in all_components:
        comp_type = comp.component_type
        if comp_type not in type_counts:
            type_counts[comp_type] = []
        type_counts[comp_type].append(comp)

    for comp_type in sorted(type_counts.keys(), key=lambda x: x.value):
        count = len(type_counts[comp_type])
        print(f"{comp_type.value:20s}: {count:3d} component(s)")

    print("\n" + "=" * 70)
    print("MOTOR SUBTYPE VALIDATION")
    print("=" * 70)

    motor_components = service.get_components_by_type(ComponentType.MOTOR)
    servo_components = service.get_components_by_type(ComponentType.SERVO)

    expected_dc = 6 * 6 * 3
    expected_steppers = 3 * 4 * 3
    expected_servos = 6 * 5

    actual_dc = len([c for c in motor_components if c.id.startswith("motor_dc_")])
    actual_steppers = len([c for c in motor_components if c.id.startswith("motor_stepper_")])
    actual_servos = len([c for c in servo_components if c.id.startswith("servo_")])

    motor_checks = [
        ("DC Motors", actual_dc, expected_dc),
        ("Stepper Motors", actual_steppers, expected_steppers),
        ("Servo Motors", actual_servos, expected_servos),
    ]

    motor_validation_passed = True
    for label, actual, expected in motor_checks:
        if actual == expected:
            print(f"✓ {label}: {actual} component definitions found (expected {expected})")
        else:
            print(f"✗ {label}: {actual} component definitions found (expected {expected})")
            motor_validation_passed = False

    if not motor_validation_passed:
        print("\n✗ ERROR: Motor component library validation failed.\n")
        return 1

    # Show detailed examples
    print("\n" + "=" * 70)
    print("EXAMPLE COMPONENTS")
    print("=" * 70)

    for comp_type in sorted(type_counts.keys(), key=lambda x: x.value):
        comps = type_counts[comp_type]
        print(f"\n{comp_type.value.upper()}:")
        for comp in comps[:3]:  # Show first 3
            print(f"  • {comp.name}")
            print(f"    ID: {comp.id}")
            print(f"    Pins: {len(comp.pins)}")
            print(f"    Size: {comp.width}x{comp.height}")
            print(f"    Description: {comp.description[:60]}..." if len(comp.description) > 60 else f"    Description: {comp.description}")
        if len(comps) > 3:
            print(f"  ... and {len(comps) - 3} more")

    # Test specific components
    print("\n" + "=" * 70)
    print("TESTING SPECIFIC COMPONENTS")
    print("=" * 70)

    test_ids = [
        "arduino_uno",
        "led_red_5mm_standard",
        "resistor_220_1div4w_5pct",
        "pushbutton_tactile_6x6mm_black",
        "sensor_temp_dht22_precision",
        "sensor_motion_hc_sr04_v1",
        "button_tactile_6x6mm_surface_mount_black_160gf_spst",
        "button_momentary_16mm_panel_panel_mount_red_220gf_spdt",
        "button_toggle_miniature_panel_mount_blue_1_8ncm_dpdt",
        "sensor_temp_dht22_high_precision",
        "ic_timer_555_dip8"
    ]

    for test_id in test_ids:
        comp = service.get_component_definition(test_id)
        if comp:
            print(f"\n✓ Found: {comp.name}")
            print(f"  Type: {comp.component_type.value}")
            print(f"  Pins: {', '.join([f'{p.label}({p.pin_type.value})' for p in comp.pins])}")
        else:
            print(f"\n✗ NOT FOUND: {test_id}")

    # Validate sample coverage for each sensor subtype family
    print("\n" + "=" * 70)
    print("SENSOR SUBTYPE COVERAGE")
    print("=" * 70)

    sensor_samples = {
        "Temperature Accuracy Classes": [
            "sensor_temp_ds18b20_standard",
            "sensor_temp_ds18b20_precision",
            "sensor_temp_ds18b20_industrial"
        ],
        "Motion Sensor Versions": [
            "sensor_motion_hc_sr04_v1",
            "sensor_motion_hc_sr04_v2",
            "sensor_motion_hc_sr04_industrial"
        ],
        "Light Sensor Sensitivities": [
            "sensor_light_bh1750_low",
            "sensor_light_bh1750_medium",
            "sensor_light_bh1750_high",
            "sensor_light_bh1750_ultra"
        ],
        "Gas Sensor Sensitivities": [
            "sensor_gas_mq135_standard",
            "sensor_gas_mq135_high"
        ]
    }

    for category, ids in sensor_samples.items():
        print(f"\n{category}:")
        for comp_id in ids:
            comp = service.get_component_definition(comp_id)
            if comp:
                print(f"  ✓ Loaded {comp.name} [{comp.id}]")
            else:
                print(f"  ✗ Missing {comp_id}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print(f"\n✓ Successfully loaded {len(all_components)} components from JSON files!")
    print("✓ Component library system is working correctly!\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
