# KiCad Component Libraries

This directory contains KiCad component libraries that can be used with the Arduino IDE examples and reference hardware projects. Libraries are provided in the KiCad 6+ file formats and can be imported into a KiCad project via the symbol and footprint library managers.

## Contents

- `Reference.kicad_sym` – Subset of the KiCad "Reference" symbol library with generic passive components (resistor, capacitor, inductor) that ship with the official KiCad distribution.

## Source and licensing

The `Reference.kicad_sym` definitions are reproduced from the official [KiCad symbol library](https://gitlab.com/kicad/libraries/kicad-symbols) as released in KiCad 7.0.8. They are distributed under the [Creative Commons Attribution-ShareAlike 4.0 International (CC-BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/) license, matching the upstream repository. See `LICENSE` in this directory for redistribution terms.

## Usage

1. Open KiCad and load your project.
2. In the **Symbol Library Manager**, add the path to this folder.
3. The new symbols will appear under the `Reference` library prefix.

