# Arduino Core Files

## Deprecated Minimal Core

The files in the `arduino/` subdirectory are a **minimal stub implementation** and are **deprecated**.

They are kept for reference only and are **no longer used** for compilation.

## Current Implementation

The Arduino IDE now automatically downloads the **official Arduino AVR core** from:
https://github.com/arduino/ArduinoCore-avr

This happens automatically on first compilation and provides:
- Full Arduino API compatibility
- All standard Arduino functions (random(), randomSeed(), etc.)
- Complete pin definitions (A0-A5, LED_BUILTIN, etc.)
- All Arduino libraries and utilities
- Regular updates from the official Arduino project

The official core is installed to `~/.arduino-ide/cores/arduino-avr/` and used
for all compilations.

## For Developers

If you need to:
1. **Use a different core version**: Modify `CORE_VERSION` in `arduino_ide/services/core_manager.py`
2. **Force re-download**: Delete `~/.arduino-ide/cores/arduino-avr/`
3. **Use local core**: Set a custom path when initializing `CoreManager`

The core is managed by the `CoreManager` class in `arduino_ide/services/core_manager.py`.
