#!/usr/bin/env python3
"""
Test library index parsing to identify version issues
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from arduino_ide.models.library import Library, LibraryIndex

# Sample Arduino library index entry (based on actual Arduino index structure)
# The Arduino library index actually uses a FLAT structure where each entry
# is a single version, not a nested versions array

SAMPLE_INDEX_FLAT = {
    "libraries": [
        {
            "name": "DHT sensor library",
            "version": "1.4.4",
            "author": "Adafruit",
            "maintainer": "Adafruit <info@adafruit.com>",
            "sentence": "Arduino library for DHT11, DHT22, etc Temp & Humidity Sensors",
            "paragraph": "Arduino library for DHT11, DHT22, etc Temp & Humidity Sensors",
            "website": "https://github.com/adafruit/DHT-sensor-library",
            "category": "Sensors",
            "architectures": ["*"],
            "types": ["Contributed"],
            "repository": "https://github.com/adafruit/DHT-sensor-library.git",
            "url": "https://downloads.arduino.cc/libraries/github.com/adafruit/DHT_sensor_library-1.4.4.zip",
            "archiveFileName": "DHT_sensor_library-1.4.4.zip",
            "size": 25423,
            "checksum": "SHA-256:db3dad0f8e0945dc7b8db3d1d72cd1e3edb5ee66e4eed1de4b87d47d90f55f0a"
        },
        {
            "name": "DHT sensor library",
            "version": "1.4.3",
            "author": "Adafruit",
            "maintainer": "Adafruit <info@adafruit.com>",
            "sentence": "Arduino library for DHT11, DHT22, etc Temp & Humidity Sensors",
            "paragraph": "Arduino library for DHT11, DHT22, etc Temp & Humidity Sensors",
            "website": "https://github.com/adafruit/DHT-sensor-library",
            "category": "Sensors",
            "architectures": ["*"],
            "types": ["Contributed"],
            "repository": "https://github.com/adafruit/DHT-sensor-library.git",
            "url": "https://downloads.arduino.cc/libraries/github.com/adafruit/DHT_sensor_library-1.4.3.zip",
            "archiveFileName": "DHT_sensor_library-1.4.3.zip",
            "size": 25123,
            "checksum": "SHA-256:abc123def456"
        }
    ]
}

# New Arduino library index format (nested versions)
SAMPLE_INDEX_NESTED = {
    "libraries": [
        {
            "name": "DHT sensor library",
            "author": "Adafruit",
            "maintainer": "Adafruit <info@adafruit.com>",
            "sentence": "Arduino library for DHT11, DHT22, etc Temp & Humidity Sensors",
            "paragraph": "Arduino library for DHT11, DHT22, etc Temp & Humidity Sensors",
            "website": "https://github.com/adafruit/DHT-sensor-library",
            "category": "Sensors",
            "architectures": ["*"],
            "types": ["Contributed"],
            "repository": "https://github.com/adafruit/DHT-sensor-library.git",
            "versions": [
                {
                    "version": "1.4.4",
                    "url": "https://downloads.arduino.cc/libraries/github.com/adafruit/DHT_sensor_library-1.4.4.zip",
                    "archiveFileName": "DHT_sensor_library-1.4.4.zip",
                    "size": 25423,
                    "checksum": "SHA-256:db3dad0f8e0945dc7b8db3d1d72cd1e3edb5ee66e4eed1de4b87d47d90f55f0a",
                    "releaseDate": "2023-01-15T10:30:00Z"
                },
                {
                    "version": "1.4.3",
                    "url": "https://downloads.arduino.cc/libraries/github.com/adafruit/DHT_sensor_library-1.4.3.zip",
                    "archiveFileName": "DHT_sensor_library-1.4.3.zip",
                    "size": 25123,
                    "checksum": "SHA-256:abc123def456",
                    "releaseDate": "2022-12-01T10:30:00Z"
                }
            ]
        }
    ]
}

def test_nested_format():
    """Test parsing nested versions format"""
    print("\n" + "="*60)
    print("Testing NESTED format (versions as array)")
    print("="*60)

    lib_data = SAMPLE_INDEX_NESTED["libraries"][0]
    library = Library.from_arduino_index(lib_data)

    print(f"Library name: {library.name}")
    print(f"Author: {library.author}")
    print(f"Category: {library.category}")
    print(f"Number of versions: {len(library.versions)}")
    print(f"Latest version: {library.latest_version}")

    if library.latest_version:
        print("✅ NESTED format works correctly!")
        return True
    else:
        print("❌ NESTED format FAILED - latest_version is None!")
        return False

def test_flat_format():
    """Test parsing flat format (each entry is one version)"""
    print("\n" + "="*60)
    print("Testing FLAT format (one entry per version)")
    print("="*60)

    lib_data = SAMPLE_INDEX_FLAT["libraries"][0]
    print(f"\nParsing entry: {lib_data['name']} v{lib_data['version']}")
    print(f"Has 'versions' key: {'versions' in lib_data}")

    library = Library.from_arduino_index(lib_data)

    print(f"\nLibrary name: {library.name}")
    print(f"Author: {library.author}")
    print(f"Category: {library.category}")
    print(f"Number of versions: {len(library.versions)}")
    print(f"Latest version: {library.latest_version}")

    if library.latest_version:
        print("✅ FLAT format works!")
        return True
    else:
        print("❌ FLAT format FAILED - latest_version is None!")
        print("   This is the issue! Arduino library index uses FLAT format,")
        print("   but the parser expects NESTED format.")
        return False

if __name__ == "__main__":
    nested_works = test_nested_format()
    flat_works = test_flat_format()

    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    print(f"Nested format: {'✅ Works' if nested_works else '❌ Failed'}")
    print(f"Flat format: {'✅ Works' if flat_works else '❌ Failed'}")

    if not flat_works:
        print("\n⚠️  ISSUE IDENTIFIED:")
        print("The Arduino library index uses a FLAT structure where each")
        print("library entry represents a single version. Multiple entries")
        print("can have the same library name but different versions.")
        print("\nThe current parser expects a NESTED structure with a")
        print("'versions' array, which causes it to find 0 versions and")
        print("set latest_version to None, resulting in 'N/A' in the UI.")
