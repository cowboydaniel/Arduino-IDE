# Building Standalone .exe

This guide explains how to package Arduino IDE Modern as a standalone Windows executable (.exe) that works on any PC without requiring Python to be installed.

## Quick Start

### On Windows

Simply double-click `build_exe.bat` in Windows Explorer.

### On Any Platform

```bash
python build_exe.py
```

## Requirements

To build the .exe, you need:

- Python 3.8 or later
- PyInstaller 6.3.0 (will be installed automatically if missing)
- All project dependencies (install with `pip install -r requirements.txt`)

## Build Process

The build script will:

1. Check for PyInstaller and install it if needed
2. Clean previous build artifacts
3. Bundle the application with all dependencies using PyInstaller
4. Create a single-file executable in the `dist/` directory

The first build may take 5-10 minutes. Subsequent builds are faster.

## Output

After a successful build, you'll find:

- `dist/Arduino-IDE.exe` - The standalone executable (approx. 100-150 MB)

This single .exe file contains:

- Python interpreter
- All Python dependencies (PySide6, pyserial, pygments, etc.)
- Application code
- Resources (snippets, templates, API references)
- Arduino cores and headers

## Distribution

The generated .exe can be distributed to any Windows PC (Windows 7 or later) without requiring:

- Python installation
- pip packages
- Any additional dependencies

Simply copy `Arduino-IDE.exe` to the target computer and run it.

## Build Options

### Custom Build

To customize the build, edit `arduino_ide.spec`:

- **Add icon**: Set `icon='path/to/icon.ico'` in the `EXE()` section
- **Enable console**: Set `console=True` to show a console window (useful for debugging)
- **One-folder mode**: Change to `onedir=True` for a directory-based distribution
- **Compression**: Adjust `upx=True/False` for UPX compression

### Manual Build

To build manually without the script:

```bash
# Install PyInstaller
pip install pyinstaller==6.3.0

# Build using the spec file
pyinstaller arduino_ide.spec --clean
```

## Troubleshooting

### Build Fails

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Clean build artifacts: Delete `build/` and `dist/` directories
- Update PyInstaller: `pip install --upgrade pyinstaller`

### .exe Doesn't Run

- Run from command line to see error messages: `Arduino-IDE.exe`
- Check Windows Defender or antivirus (may flag as false positive)
- Ensure running on Windows 7 or later

### Missing Resources

If the .exe runs but is missing snippets, templates, or other resources:

1. Check that all data files are listed in `arduino_ide.spec`
2. Verify the resource paths in the spec file are correct
3. Rebuild with `--clean` flag

## Advanced Configuration

### Reducing File Size

To reduce the .exe size:

1. Set `upx=True` in the spec file (requires UPX to be installed)
2. Use one-folder mode instead of one-file (faster startup, multiple files)
3. Exclude unnecessary dependencies in the spec file

### Adding Custom Resources

To bundle additional files:

1. Edit `arduino_ide.spec`
2. Add entries to the `datas` list:
   ```python
   datas = [
       ('path/to/source', 'destination/in/bundle'),
       # ... existing entries
   ]
   ```

## Technical Details

### How It Works

PyInstaller:

1. Analyzes the Python code to find all dependencies
2. Bundles Python interpreter, libraries, and application code
3. Creates a bootloader that extracts and runs the application
4. At runtime, extracts resources to a temporary directory (`sys._MEIPASS`)

### Resource Handling

The application code has been modified to support both:

- **Development mode**: Runs from source with `python run.py`
- **Bundled mode**: Runs from .exe with resources in `sys._MEIPASS`

Files modified for PyInstaller compatibility:

- `arduino_ide/main.py` - Handles arduino-cli path resolution
- `arduino_ide/services/snippets_manager.py` - Handles snippets resource loading

### Bundle Contents

The .exe includes:

| Component | Source | Size (approx) |
|-----------|--------|---------------|
| Python interpreter | Embedded | 10 MB |
| PySide6 (Qt) | PyPI package | 80 MB |
| Application code | Local | 5 MB |
| Resources | Local | 1 MB |
| Other dependencies | PyPI packages | 20 MB |
| **Total** | | **~115 MB** |

*Note: Actual size may vary based on Python version and dependencies.*

## See Also

- [PyInstaller Documentation](https://pyinstaller.org/)
- [PyInstaller Spec Files](https://pyinstaller.org/en/stable/spec-files.html)
- [Main README](README.md)
