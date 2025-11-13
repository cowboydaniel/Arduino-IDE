# KiCad Component Libraries

This directory contains the complete KiCad symbol library that can be used with the Arduino IDE examples and reference hardware projects. Libraries are provided in the KiCad 6+ file formats and can be imported into a KiCad project via the symbol and footprint library managers.

## Contents

This directory includes all 222+ official KiCad symbol libraries, including:
- Microcontrollers (MCU_*)
- Analog components (Amplifier_*, Analog_*)
- Digital logic (74xx, 4xxx)
- Power management (Battery_Management, Regulator_*)
- Sensors (Sensor_*)
- Communication interfaces (Interface_*)
- And many more component categories

Each library is stored as a `.kicad_sym` file containing schematic symbols for that component category.

## Source and licensing

The symbol libraries are from the official [KiCad symbols repository](https://gitlab.com/kicad/libraries/kicad-symbols). They are distributed under the [Creative Commons Attribution-ShareAlike 4.0 International (CC-BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/) license. See `LICENSE.md` in this directory for full redistribution terms.

## Usage

1. Open KiCad and load your project.
2. In the **Symbol Library Manager**, add the path to this folder.
3. The symbols will appear organized by their library names (e.g., `MCU_ST_STM32`, `Amplifier_Operational`, `Sensor_Temperature`, etc.).

