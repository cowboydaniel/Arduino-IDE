# Library Duplicate Detection

The Arduino IDE library manager now includes comprehensive duplicate detection functionality to help identify and resolve duplicate library installations.

## Overview

Duplicate library installations can occur when:
- The same library is installed multiple times in different directories
- Multiple versions of the same library are installed concurrently
- Manual installations conflict with package manager installations
- Libraries are installed with non-standard directory names

These duplicates can cause:
- Compilation errors due to ambiguous includes
- Unexpected behavior when the wrong version is used
- Wasted disk space
- Difficulty managing library updates

## Features

### 1. Detect Duplicate Installations

Scan your libraries directory to find all duplicate installations:

```python
from arduino_ide.services.library_manager import LibraryManager

manager = LibraryManager()
duplicates = manager.detect_duplicate_installations()

# Returns: Dict[str, List[Dict[str, str]]]
# {
#     "LibraryName": [
#         {"name": "LibraryName", "version": "1.0.0", "path": "/path/1", "source": "managed"},
#         {"name": "LibraryName", "version": "2.0.0", "path": "/path/2", "source": "manual"}
#     ]
# }
```

Each installation includes:
- `name`: Original library name
- `version`: Installed version
- `path`: Full path to the installation directory
- `source`: Either "managed" (installed by package manager) or "manual" (manually installed)

### 2. Find Multiple Versions

Identify libraries with multiple versions installed:

```python
multiple_versions = manager.find_multiple_versions()

# Returns: Dict[str, List[str]]
# {"LibraryName": ["1.0.0", "1.5.0", "2.0.0"]}
```

Versions are automatically sorted using semantic versioning when possible.

### 3. Get Human-Readable Summary

Get a formatted summary of all duplicates:

```python
summary = manager.get_duplicate_summary()
print(summary)
```

Example output:
```
Duplicate library installations detected:

Library: WiFi
  ⚠ Multiple versions installed:
    Version 1.0.0:
      - /home/user/.arduino-ide-modern/libraries/WiFi-1.0 (manual)
    Version 2.0.0:
      - /home/user/.arduino-ide-modern/libraries/WiFi (managed)

Recommendations:
  - Remove duplicate installations to avoid conflicts
  - Keep only one version of each library
  - Use the library manager for installations to avoid manual duplicates
```

### 4. Resolve Duplicates

Automatically resolve duplicates by removing unwanted copies:

```python
# Dry run - see what would be done
result = manager.resolve_duplicates(
    library_name="WiFi",
    dry_run=True
)

# Actually remove duplicates
result = manager.resolve_duplicates(
    library_name="WiFi",
    dry_run=False
)

# Keep specific version
result = manager.resolve_duplicates(
    library_name="WiFi",
    keep_version="2.0.0",
    dry_run=False
)

# Keep specific path
result = manager.resolve_duplicates(
    library_name="WiFi",
    keep_path="/home/user/.arduino-ide-modern/libraries/WiFi",
    dry_run=False
)
```

Resolution strategy:
1. If `keep_path` is specified, that installation is kept
2. If `keep_version` is specified, that version is kept (prefers managed over manual)
3. Otherwise, the latest version is kept (prefers managed over manual)

The result includes:
```python
{
    "kept": {"name": "WiFi", "version": "2.0.0", "path": "/path", "source": "managed"},
    "removed": [
        {"name": "WiFi", "version": "1.0.0", "path": "/old/path", "source": "manual"}
    ],
    "errors": []
}
```

## Installation Workflow Integration

The library manager now automatically checks for duplicates before installation and emits warnings:

```python
# When installing a library that already has duplicates
manager.install_library("WiFi", "2.0.0")

# Output:
# Warning: WiFi has 2 existing installation(s). Installing will create another copy.
#   Existing: v1.0.0 at /path/1 (manual)
#   Existing: v1.5.0 at /path/2 (managed)
# Installing WiFi v2.0.0...
```

## Example Usage

See `examples/detect_library_duplicates.py` for a complete example:

```bash
python examples/detect_library_duplicates.py
```

## API Reference

### `detect_duplicate_installations() -> Dict[str, List[Dict[str, str]]]`

Scans the libraries directory and returns all duplicate installations.

**Returns:** Dictionary mapping library names to lists of installation details.

### `find_multiple_versions() -> Dict[str, List[str]]`

Finds libraries with multiple versions installed (excludes same-version duplicates).

**Returns:** Dictionary mapping library names to sorted version lists.

### `get_duplicate_summary() -> str`

Generates a human-readable summary of all duplicate installations.

**Returns:** Formatted string with duplicate information and recommendations.

### `resolve_duplicates(library_name, keep_version=None, keep_path=None, dry_run=True) -> Dict`

Resolves duplicate installations by removing unwanted copies.

**Parameters:**
- `library_name` (str): Name of the library to resolve
- `keep_version` (str, optional): Specific version to keep
- `keep_path` (str, optional): Specific path to keep (takes precedence)
- `dry_run` (bool): If True, only reports what would be done (default: True)

**Returns:** Dictionary with `kept`, `removed`, and `errors` keys.

## Best Practices

1. **Regular Scanning**: Periodically scan for duplicates using `detect_duplicate_installations()`
2. **Dry Run First**: Always use `dry_run=True` first to preview changes
3. **Prefer Managed**: Keep managed installations when possible for easier updates
4. **Latest Versions**: Generally prefer keeping the latest version unless you have specific requirements
5. **Backup First**: Consider backing up your libraries directory before resolving duplicates

## Troubleshooting

### Case-Insensitive Matching

Library names are matched case-insensitively, so "servo", "Servo", and "SERVO" are considered the same library.

### Managed vs Manual Detection

A library is considered "managed" if:
- It's tracked in `installed_libraries.json`
- The installed version matches the tracked version
- It's installed in a directory with the standard naming convention (directory name = library name)

All other installations are considered "manual".

### Missing library.properties

Directories without a `library.properties` file are ignored during duplicate detection.

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_library_duplicate_detection.py -v
```

This includes 18 tests covering:
- Duplicate detection (same library, multiple locations)
- Multiple version detection
- Case-insensitive matching
- Resolution strategies (dry-run, actual removal)
- Preference for managed installations
- Error handling
