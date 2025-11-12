#!/usr/bin/env python3
"""Generate brushed DC, servo, and stepper motor component definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "arduino_ide" / "component_library" / "motors"

DC_VOLTAGES = [
    {"id": "3v", "label": "3V", "voltage": 3, "base_no_load_current": 0.08, "base_rated_current": 0.25, "base_stall_current": 0.60},
    {"id": "5v", "label": "5V", "voltage": 5, "base_no_load_current": 0.09, "base_rated_current": 0.30, "base_stall_current": 0.90},
    {"id": "6v", "label": "6V", "voltage": 6, "base_no_load_current": 0.10, "base_rated_current": 0.35, "base_stall_current": 1.10},
    {"id": "9v", "label": "9V", "voltage": 9, "base_no_load_current": 0.12, "base_rated_current": 0.45, "base_stall_current": 1.60},
    {"id": "12v", "label": "12V", "voltage": 12, "base_no_load_current": 0.14, "base_rated_current": 0.60, "base_stall_current": 2.40},
    {"id": "24v", "label": "24V", "voltage": 24, "base_no_load_current": 0.18, "base_rated_current": 0.85, "base_stall_current": 3.20},
]

DC_RPMS = [
    {"id": "60rpm", "label": "60 RPM", "rpm": 60},
    {"id": "120rpm", "label": "120 RPM", "rpm": 120},
    {"id": "300rpm", "label": "300 RPM", "rpm": 300},
    {"id": "600rpm", "label": "600 RPM", "rpm": 600},
    {"id": "1200rpm", "label": "1,200 RPM", "rpm": 1200},
    {"id": "2400rpm", "label": "2,400 RPM", "rpm": 2400},
]

DC_TORQUE_CLASSES = [
    {"id": "light", "label": "Light Duty", "torque": "0.25 kg·cm", "current_factor": 0.8, "mechanics": "Ø24 mm can, 30 mm length, 2 mm D-shaft"},
    {"id": "medium", "label": "General Purpose", "torque": "1.20 kg·cm", "current_factor": 1.0, "mechanics": "Ø27 mm can, 35 mm length, 3 mm D-shaft"},
    {"id": "heavy", "label": "High Torque", "torque": "2.80 kg·cm", "current_factor": 1.4, "mechanics": "Ø37 mm can, 50 mm length, 4 mm keyed shaft"},
]

SERVO_MODELS = [
    {"id": "sg90", "name": "SG90 Micro Servo", "form_factor": "Micro", "dimensions": "22.8 × 12.2 × 28.5 mm", "voltage_range": "4.8-6.0V", "speed": "0.12s/60° @ 4.8V", "weight": "9g"},
    {"id": "mg90s", "name": "MG90S Metal Gear Servo", "form_factor": "Micro", "dimensions": "22.5 × 12.0 × 28.5 mm", "voltage_range": "4.8-6.0V", "speed": "0.10s/60° @ 6.0V", "weight": "13g"},
    {"id": "mg996r", "name": "MG996R High-Torque Servo", "form_factor": "Standard", "dimensions": "40.7 × 19.7 × 42.9 mm", "voltage_range": "4.8-7.2V", "speed": "0.14s/60° @ 6.0V", "weight": "55g"},
    {"id": "ds3218", "name": "DS3218 Digital Servo", "form_factor": "Large Torque", "dimensions": "40.5 × 20.0 × 40.5 mm", "voltage_range": "4.8-6.8V", "speed": "0.16s/60° @ 6.8V", "weight": "60g"},
    {"id": "hs422", "name": "HS-422 Analog Servo", "form_factor": "Standard", "dimensions": "40.6 × 19.8 × 36.6 mm", "voltage_range": "4.8-6.0V", "speed": "0.21s/60° @ 6.0V", "weight": "45g"},
    {"id": "fs5106r", "name": "FS5106R Continuous Servo", "form_factor": "Continuous", "dimensions": "40.8 × 20.1 × 39.5 mm", "voltage_range": "4.8-6.0V", "speed": "0.12s/60° @ 6.0V", "weight": "41g"},
]

SERVO_TORQUE_OPTIONS = [
    {"id": "2kg_cm", "label": "2kg-cm", "torque": "2.0 kg·cm", "stall_current": 0.65},
    {"id": "3kg_cm", "label": "3kg-cm", "torque": "3.0 kg·cm", "stall_current": 0.80},
    {"id": "5kg_cm", "label": "5kg-cm", "torque": "5.0 kg·cm", "stall_current": 1.20},
    {"id": "8kg_cm", "label": "8kg-cm", "torque": "8.0 kg·cm", "stall_current": 1.80},
    {"id": "12kg_cm", "label": "12kg-cm", "torque": "12.0 kg·cm", "stall_current": 2.50},
]

STEPPER_FAMILIES = [
    {"id": "nema11", "name": "NEMA 11 Bipolar Stepper", "frame_size": "28 mm square", "body_length": "28 mm", "holding_torque": "0.18 N·m", "control_interface": "Bipolar stepper driver (A4988/DRV8825)", "shaft": "5 mm round shaft"},
    {"id": "nema17", "name": "NEMA 17 Bipolar Stepper", "frame_size": "42 mm square", "body_length": "40 mm", "holding_torque": "0.45 N·m", "control_interface": "Bipolar stepper driver (A4988/TMC2208)", "shaft": "5 mm round shaft"},
    {"id": "nema23", "name": "NEMA 23 Bipolar Stepper", "frame_size": "57 mm square", "body_length": "56 mm", "holding_torque": "1.25 N·m", "control_interface": "Bipolar stepper driver (TB6600)", "shaft": "6.35 mm round shaft"},
]

STEPPER_STEP_COUNTS = [
    {"id": "200", "steps": 200, "step_angle": "1.8°", "max_speed_rpm": 60},
    {"id": "400", "steps": 400, "step_angle": "0.9°", "max_speed_rpm": 45},
    {"id": "1000", "steps": 1000, "step_angle": "0.36°", "max_speed_rpm": 20},
    {"id": "2000", "steps": 2000, "step_angle": "0.18°", "max_speed_rpm": 10},
]

STEPPER_VOLTAGES = [
    {"id": "5v", "label": "5V", "voltage": 5, "current_per_phase": 0.70},
    {"id": "12v", "label": "12V", "voltage": 12, "current_per_phase": 1.20},
    {"id": "24v", "label": "24V", "voltage": 24, "current_per_phase": 1.80},
]


def format_current(value: float) -> str:
    return f"{value:.2f}A"


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def write_component(component: Dict[str, object]) -> None:
    filename = OUTPUT_DIR / f"{component['id']}.json"
    with filename.open("w", encoding="utf-8") as fh:
        json.dump(component, fh, indent=2)
        fh.write("\n")


def generate_dc_motors() -> int:
    count = 0
    for voltage in DC_VOLTAGES:
        for rpm in DC_RPMS:
            for torque in DC_TORQUE_CLASSES:
                rated_current = voltage["base_rated_current"] * torque["current_factor"]
                stall_current = voltage["base_stall_current"] * torque["current_factor"]
                no_load_current = voltage["base_no_load_current"] * torque["current_factor"]

                component_id = f"motor_dc_{voltage['id']}_{rpm['id']}_{torque['id']}"
                component = {
                    "id": component_id,
                    "name": f"{torque['label']} {voltage['label']} {rpm['label']} DC Gear Motor",
                    "component_type": "motor",
                    "description": (
                        f"Brushed DC gearmotor rated for {voltage['label']} operation with a {rpm['label']} output and "
                        f"{torque['torque']} torque capability."
                    ),
                    "width": 90,
                    "height": 60,
                    "pins": [
                        {"id": "positive", "label": "+", "pin_type": "power", "position": [15, 30]},
                        {"id": "negative", "label": "-", "pin_type": "ground", "position": [75, 30]},
                    ],
                    "metadata": {
                        "motor_subtype": "Brushed DC",
                        "voltage": f"{voltage['voltage']}V nominal",
                        "speed": f"{rpm['rpm']} RPM output",
                        "torque": f"{torque['torque']} rated torque",
                        "current": f"{format_current(rated_current)} rated, {format_current(stall_current)} stall",
                        "no_load_current": format_current(no_load_current),
                        "control_interface": "Two-wire brushed motor (H-bridge/MOSFET)",
                        "step_angle": "N/A",
                        "mechanical_dimensions": torque["mechanics"],
                        "shaft_type": torque["mechanics"].split(",")[-1].strip(),
                    },
                }
                write_component(component)
                count += 1
    return count


def generate_servo_motors() -> int:
    count = 0
    for model in SERVO_MODELS:
        for torque in SERVO_TORQUE_OPTIONS:
            component_id = f"servo_{model['id']}_{torque['id']}"
            component = {
                "id": component_id,
                "name": f"{model['name']} ({torque['label']} torque)",
                "component_type": "servo",
                "description": (
                    f"{model['form_factor']} servo configured for {torque['torque']} output torque with "
                    f"{model['speed']} response."
                ),
                "width": 60,
                "height": 70,
                "pins": [
                    {"id": "vcc", "label": "VCC", "pin_type": "power", "position": [15, 0]},
                    {"id": "signal", "label": "SIG", "pin_type": "pwm", "position": [30, 0]},
                    {"id": "gnd", "label": "GND", "pin_type": "ground", "position": [45, 0]},
                ],
                "metadata": {
                    "motor_subtype": "Servo",
                    "voltage": model["voltage_range"],
                    "speed": model["speed"],
                    "torque": torque["torque"],
                    "current": f"{format_current(torque['stall_current'])} stall",
                    "control_interface": "PWM (50Hz, 1-2ms pulse)",
                    "step_angle": "N/A",
                    "mechanical_dimensions": model["dimensions"],
                    "form_factor": model["form_factor"],
                    "weight": model["weight"],
                },
            }
            write_component(component)
            count += 1
    return count


def generate_stepper_motors() -> int:
    count = 0
    for family in STEPPER_FAMILIES:
        for steps in STEPPER_STEP_COUNTS:
            for voltage in STEPPER_VOLTAGES:
                component_id = f"motor_stepper_{family['id']}_{steps['id']}step_{voltage['id']}"
                component = {
                    "id": component_id,
                    "name": f"{family['name']} {steps['steps']} step ({voltage['label']})",
                    "component_type": "motor",
                    "description": (
                        f"{family['name']} with {steps['steps']} steps per revolution and a {steps['step_angle']} step angle, "
                        f"optimized for {voltage['label']} drivers."
                    ),
                    "width": 90,
                    "height": 90,
                    "pins": [
                        {"id": "a_plus", "label": "A+", "pin_type": "power", "position": [15, 0]},
                        {"id": "a_minus", "label": "A-", "pin_type": "power", "position": [35, 0]},
                        {"id": "b_plus", "label": "B+", "pin_type": "power", "position": [55, 0]},
                        {"id": "b_minus", "label": "B-", "pin_type": "power", "position": [75, 0]},
                    ],
                    "metadata": {
                        "motor_subtype": "Stepper",
                        "voltage": f"{voltage['voltage']}V nominal",
                        "speed": f"Supports {steps['max_speed_rpm']} RPM typical",
                        "torque": f"{family['holding_torque']} holding torque",
                        "current": f"{format_current(voltage['current_per_phase'])} per phase",
                        "control_interface": family["control_interface"],
                        "step_angle": steps["step_angle"],
                        "mechanical_dimensions": f"{family['frame_size']} frame, {family['body_length']} length, {family['shaft']}",
                        "steps_per_revolution": steps["steps"],
                    },
                }
                write_component(component)
                count += 1
    return count


def main() -> None:
    ensure_output_dir()
    dc_count = generate_dc_motors()
    servo_count = generate_servo_motors()
    stepper_count = generate_stepper_motors()

    total = dc_count + servo_count + stepper_count
    print(f"Generated {dc_count} DC motors, {servo_count} servos, and {stepper_count} steppers ({total} components total).")


if __name__ == "__main__":
    main()
