# Board Discovery Implementation

## Overview

This implementation provides **generalized board support** for the Arduino IDE by integrating with the **Arduino boards platform framework**. Instead of hardcoding board definitions, the IDE now dynamically discovers boards from installed platform packages by parsing `boards.txt` files.

## Architecture

### Arduino Platform Framework

The Arduino ecosystem uses a standardized platform specification:

- **Package Index**: JSON file at https://downloads.arduino.cc/packages/package_index.json containing metadata for all available platforms
- **Platform Packages**: Compressed archives (`.tar.bz2`, `.tar.gz`, `.zip`) containing board definitions
- **boards.txt**: Configuration file defining board properties (name, FQBN, specs, etc.)
- **platform.txt**: Build system configuration for the platform

### Directory Structure

Installed platforms are stored in: `~/.arduino-ide-modern/packages/`

```
packages/
  arduino/              # Package name
    avr/                # Architecture
      1.8.6/            # Version
        boards.txt      # Board definitions
        platform.txt    # Build configuration
        ...
    samd/
      1.8.13/
        boards.txt
        ...
  esp32/
    esp32/
      2.0.9/
        boards.txt
        ...
```

## Implementation Components

### 1. BoardsTxtParser (`arduino_ide/services/boards_txt_parser.py`)

Parses Arduino `boards.txt` files following the Arduino platform specification.

**Key features:**
- Extracts board IDs, names, and FQBNs
- Parses board specifications (CPU, clock, flash, RAM)
- Handles Arduino properties file format
- Creates Board objects with full metadata

### 2. BoardPackageVersion Model Updates

Added `architecture` field to store platform architecture (e.g., "avr", "esp32"):

```python
@dataclass
class BoardPackageVersion:
    version: str
    url: str
    size: int
    checksum: str
    release_date: datetime
    architecture: str = ""  # NEW: Platform architecture
    ...
```

### 3. BoardManager Enhancements

#### Board Discovery (`_discover_boards_from_installed_platforms()`)

Scans the packages directory and discovers boards:

1. Iterates through installed platform directories
2. Finds `boards.txt` files
3. Parses each `boards.txt` to extract board definitions
4. Returns list of Board objects

#### Platform Installation (`install_package()`)

Enhanced to handle Arduino platform structure:

- Accepts platform IDs: `"arduino:avr"`, `"esp32:esp32"`
- Extracts architecture from package version data
- Installs to correct path: `packages/name/architecture/version/`
- Supports `.tar.bz2`, `.tar.gz`, and `.zip` archives

#### Platform Uninstallation (`uninstall_package()`)

Updated to handle new directory structure and clean up empty directories.

### 4. arduino-cli Wrapper Updates

- Ensures package index is loaded before installation
- Calls `board_manager.install_package()` with platform ID
- Board list now discovers from installed platforms via `get_all_boards()`

## Usage

### Installing a Platform

```bash
# Install Arduino AVR Boards (Uno, Mega, Nano, etc.)
python3 arduino-cli core install arduino:avr

# Install ESP32 boards
python3 arduino-cli core install esp32:esp32
```

### Discovering Boards

```python
from arduino_ide.services.board_manager import BoardManager

bm = BoardManager()

# Get all boards from installed platforms
boards = bm.get_all_boards()

for board in boards:
    print(f"{board.name}: {board.fqbn}")
    print(f"  CPU: {board.specs.cpu}")
    print(f"  Flash: {board.specs.flash}")
```

### IDE Integration

The main window now uses `get_boards_from_cli()` which:

1. Calls arduino-cli wrapper with `board list --format json`
2. Wrapper calls `get_all_boards()`
3. `get_all_boards()` scans installed platforms
4. Parses `boards.txt` files
5. Returns discovered boards

No hardcoded boards needed!

## Testing

### Test Package Index Download

```bash
python3 test_package_index.py
```

This verifies:
- Connection to Arduino package index
- JSON parsing
- Package structure

### Test Board Discovery

```bash
python3 test_board_discovery.py
```

This demonstrates:
- Package index update
- Platform availability check
- Board discovery from installed platforms
- Complete workflow

### Manual Testing

1. **Update package index:**
   ```bash
   python3 -c "from arduino_ide.services.board_manager import BoardManager; \
               bm = BoardManager(); \
               bm.update_index(force=True); \
               print(f'Packages: {len(bm.board_index.packages)}')"
   ```

2. **Install Arduino AVR:**
   ```bash
   python3 arduino-cli core install arduino:avr
   ```

3. **List discovered boards:**
   ```bash
   python3 arduino-cli board list
   ```

4. **Run IDE:**
   ```bash
   python3 run.py
   ```

   The board selector should show all boards from installed platforms.

## Benefits

### Before (Hardcoded)

- ❌ Only 8 boards supported (Uno, Mega, Nano, etc.)
- ❌ Required code changes to add new boards
- ❌ No support for third-party platforms
- ❌ Couldn't support newer board revisions

### After (Generalized)

- ✅ Supports entire Arduino ecosystem
- ✅ No code changes needed for new boards
- ✅ Full support for third-party platforms (ESP32, STM32, RP2040, etc.)
- ✅ Automatic support for board updates
- ✅ Follows Arduino official platform specification
- ✅ Compatible with arduino-cli workflow

## Troubleshooting

### No boards showing in IDE

1. Check if any platforms are installed:
   ```bash
   ls -la ~/.arduino-ide-modern/packages/
   ```

2. Install Arduino AVR if empty:
   ```bash
   python3 arduino-cli core install arduino:avr
   ```

3. Verify boards.txt exists:
   ```bash
   find ~/.arduino-ide-modern/packages/ -name "boards.txt"
   ```

### Package index download fails

- Check network connectivity
- Try manual download:
  ```bash
  curl -I https://downloads.arduino.cc/packages/package_index.json
  ```
- Check firewall/proxy settings

### Boards not discovered after install

1. Check extraction completed:
   ```bash
   ls -la ~/.arduino-ide-modern/packages/arduino/avr/*/
   ```

2. Verify boards.txt is readable:
   ```bash
   cat ~/.arduino-ide-modern/packages/arduino/avr/*/boards.txt | head
   ```

3. Test parser directly:
   ```python
   from pathlib import Path
   from arduino_ide.services.boards_txt_parser import BoardsTxtParser

   boards_txt = Path("~/.arduino-ide-modern/packages/arduino/avr/1.8.6/boards.txt").expanduser()
   boards = BoardsTxtParser.parse_boards_txt(boards_txt, "arduino", "avr")
   print(f"Found {len(boards)} boards")
   ```

## Future Enhancements

- **Platform search**: `arduino-cli core search <query>`
- **Platform updates**: Detect and install platform updates
- **Dependency resolution**: Auto-install required tools
- **Platform metadata**: Show platform descriptions in UI
- **Board images**: Display board photos in IDE
- **Platform categories**: Organize by official/partner/community

## References

- [Arduino Platform Specification](https://arduino.github.io/arduino-cli/latest/platform-specification/)
- [arduino-cli Documentation](https://arduino.github.io/arduino-cli/latest/)
- [Arduino Package Index](https://downloads.arduino.cc/packages/package_index.json)
