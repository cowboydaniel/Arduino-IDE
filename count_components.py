#!/usr/bin/env python3
"""
Calculate the number of components that will be generated
"""

def count_components():
    """Count total components based on the generation logic"""

    counts = {}

    # Arduino boards
    counts["Arduino Boards"] = 1

    # LEDs
    led_colors = 14  # Red, Green, Blue, Yellow, White, Orange, Pink, Purple, Cyan, Amber, Infrared, UV, Cool White, Warm White
    led_sizes = 6    # 3mm, 5mm, 10mm, SMD0603, SMD0805, SMD1206
    led_types = 5    # Standard, High-Brightness, Super-Bright, RGB, Bi-Color
    counts["LEDs"] = led_colors * led_sizes * led_types

    # Resistors (E24 series)
    e24_values = 24  # E24 series
    multipliers = 7  # 1, 10, 100, 1K, 10K, 100K, 1M
    wattages = 6     # 1/8W, 1/4W, 1/2W, 1W, 2W, 5W
    tolerances = 3   # 1%, 5%, 10%
    counts["Resistors"] = multipliers * e24_values * wattages * tolerances

    # Capacitors
    cap_types = 5    # Ceramic, Electrolytic, Tantalum, Film, Polyester
    cap_voltages = 8 # 6.3V, 10V, 16V, 25V, 35V, 50V, 100V, 250V
    cap_values_pf = 6   # 6 values
    cap_values_nf = 9   # 9 values
    cap_values_uf = 13  # 13 values
    counts["Capacitors"] = cap_types * cap_voltages * (cap_values_pf + cap_values_nf + cap_values_uf)

    # BJT Transistors
    bjt_models = 13  # 2N2222, 2N3904, etc.
    bjt_packages = 3 # TO-92, TO-220, SOT-23
    counts["BJT Transistors"] = bjt_models * bjt_packages

    # MOSFET Transistors
    mosfet_models = 10    # IRF520, IRF540, etc.
    mosfet_packages = 3   # TO-220, TO-92, SOT-23
    power_ratings = 4     # 30W, 50W, 75W, 100W
    counts["MOSFET Transistors"] = mosfet_models * mosfet_packages * power_ratings

    # Logic ICs
    logic_families = 5   # 74HC, 74HCT, 74LS, 74ALS, CD4000
    logic_types = 28     # 00, 02, 04, 08, etc.
    counts["Logic ICs"] = logic_families * logic_types

    # Op-Amps
    opamp_models = 20  # LM358, LM324, etc.
    opamp_packages = 3 # DIP-8, SOIC-8, DIP-14
    counts["Op-Amps"] = opamp_models * opamp_packages

    # Timers
    timer_models = 7   # 555, 556, 7555, etc.
    timer_packages = 3 # DIP-8, SOIC-8, DIP-14
    counts["Timers"] = timer_models * timer_packages

    # Microcontrollers
    mcus = 11        # ATmega328P, ATmega2560, etc.
    mcu_packages = 3 # DIP, TQFP, QFN
    counts["Microcontrollers"] = mcus * mcu_packages

    # Temperature Sensors
    temp_sensors = 15  # LM35, LM335, DS18B20, etc.
    accuracies = 3     # Standard, High-Precision, Industrial
    counts["Temperature Sensors"] = temp_sensors * accuracies

    # Motion/Distance Sensors
    motion_sensors = 9 # HC-SR04, HC-SR501, etc.
    versions = 3       # v1.0, v2.0, v3.0
    counts["Motion Sensors"] = motion_sensors * versions

    # Light Sensors
    light_sensors = 6  # LDR, BH1750, etc.
    sensitivities = 4  # Low, Medium, High, Ultra-High
    counts["Light Sensors"] = light_sensors * sensitivities

    # Gas Sensors
    gas_sensors = 9       # MQ-2, MQ-3, etc.
    gas_sensitivities = 2 # Standard, High-Sensitivity
    counts["Gas Sensors"] = gas_sensors * gas_sensitivities

    # DC Motors
    dc_voltages = 6  # 3V, 5V, 6V, 9V, 12V, 24V
    dc_rpms = 6      # 100RPM, 200RPM, etc.
    dc_torques = 3   # Low, Medium, High
    counts["DC Motors"] = dc_voltages * dc_rpms * dc_torques

    # Servo Motors
    servo_types = 6  # SG90, MG90S, etc.
    servo_torques = 5 # 2kg-cm, 5kg-cm, etc.
    counts["Servo Motors"] = servo_types * servo_torques

    # Stepper Motors
    stepper_types = 3   # 28BYJ-48, NEMA17, NEMA23
    stepper_steps = 4   # 200, 400, 1000, 2000
    stepper_voltages = 3 # 5V, 12V, 24V
    counts["Stepper Motors"] = stepper_types * stepper_steps * stepper_voltages

    # Buttons & Switches
    button_types = 4  # Tactile, Momentary, Latching, Toggle
    button_sizes = 3  # 6x6mm, 12x12mm, 6x3mm
    button_colors = 6 # Black, Red, Blue, Green, Yellow, White
    counts["Buttons"] = button_types * button_sizes * button_colors

    # Potentiometers
    pot_values = 8    # 1K, 5K, 10K, etc.
    pot_types = 3     # Linear, Logarithmic, Anti-Log
    pot_mounting = 2  # PCB, Panel
    counts["Potentiometers"] = pot_values * pot_types * pot_mounting

    # Breadboards
    bb_sizes = 4     # Mini, Half, Full, Large
    bb_colors = 6    # White, Red, Blue, Green, Black, Clear
    bb_qualities = 2 # Standard, Premium
    counts["Breadboards"] = bb_sizes * bb_colors * bb_qualities

    return counts

def main():
    print("=" * 60)
    print("CIRCUIT COMPONENT LIBRARY - COMPONENT COUNT")
    print("=" * 60)

    counts = count_components()

    total = 0
    for category, count in counts.items():
        print(f"{category:30s}: {count:5,d}")
        total += count

    print("=" * 60)
    print(f"{'TOTAL COMPONENTS':30s}: {total:5,d}")
    print("=" * 60)

    if total >= 5000:
        print(f"\n✓ SUCCESS! Generated {total:,} components (target: 5,000+)")
    else:
        print(f"\n✗ WARNING: Only {total:,} components (target: 5,000+)")

if __name__ == "__main__":
    main()
