#!/usr/bin/env python3
"""
Test loading flat Arduino library index structure
"""

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from arduino_ide.services.library_manager import LibraryManager

# Sample flat index (like real Arduino index)
FLAT_INDEX = {
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
            "checksum": "SHA-256:abc123"
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
            "checksum": "SHA-256:def456"
        },
        {
            "name": "Servo",
            "version": "1.2.0",
            "author": "Michael Margolis, Arduino",
            "maintainer": "Arduino <info@arduino.cc>",
            "sentence": "Allows Arduino boards to control a variety of servo motors.",
            "paragraph": "This library can control a great number of servos.",
            "website": "https://github.com/arduino-libraries/Servo",
            "category": "Device Control",
            "architectures": ["*"],
            "types": ["Arduino"],
            "repository": "https://github.com/arduino-libraries/Servo.git",
            "url": "https://downloads.arduino.cc/libraries/github.com/arduino-libraries/Servo-1.2.0.zip",
            "archiveFileName": "Servo-1.2.0.zip",
            "size": 15234,
            "checksum": "SHA-256:servo123"
        },
        {
            "name": "Servo",
            "version": "1.1.8",
            "author": "Michael Margolis, Arduino",
            "maintainer": "Arduino <info@arduino.cc>",
            "sentence": "Allows Arduino boards to control a variety of servo motors.",
            "paragraph": "This library can control a great number of servos.",
            "website": "https://github.com/arduino-libraries/Servo",
            "category": "Device Control",
            "architectures": ["*"],
            "types": ["Arduino"],
            "repository": "https://github.com/arduino-libraries/Servo.git",
            "url": "https://downloads.arduino.cc/libraries/github.com/arduino-libraries/Servo-1.1.8.zip",
            "archiveFileName": "Servo-1.1.8.zip",
            "size": 14987,
            "checksum": "SHA-256:servo456"
        }
    ],
    "last_updated": "2024-01-01T00:00:00Z"
}

def test_flat_index_loading():
    """Test that library manager can load flat index structure"""
    print("Testing Flat Arduino Library Index Loading")
    print("=" * 60)

    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Override home directory
        import arduino_ide.services.library_manager
        original_home = Path.home
        Path.home = lambda: tmp_path

        try:
            # Create library manager
            lib_manager = LibraryManager()

            # Write flat index to cache
            lib_manager.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(lib_manager.index_file, 'w') as f:
                json.dump(FLAT_INDEX, f)

            # Reload index
            lib_manager._load_library_index()

            # Check results
            print(f"\n✅ Index loaded successfully")
            print(f"Total libraries: {len(lib_manager.library_index.libraries)}")

            for lib in lib_manager.library_index.libraries:
                print(f"\nLibrary: {lib.name}")
                print(f"  Author: {lib.author}")
                print(f"  Category: {lib.category}")
                print(f"  Versions: {len(lib.versions)}")
                print(f"  Latest version: {lib.latest_version}")

                if lib.latest_version:
                    print(f"  ✅ Has latest_version!")
                else:
                    print(f"  ❌ Missing latest_version!")
                    return False

                # List all versions
                for v in lib.versions:
                    print(f"    - v{v.version} ({v.size_human_readable()})")

            # Verify correct aggregation
            dht_lib = lib_manager.get_library("DHT sensor library")
            servo_lib = lib_manager.get_library("Servo")

            if not dht_lib:
                print("\n❌ DHT library not found!")
                return False

            if not servo_lib:
                print("\n❌ Servo library not found!")
                return False

            print(f"\n📊 Verification:")
            print(f"  DHT library has {len(dht_lib.versions)} versions (expected 2)")
            print(f"  Servo library has {len(servo_lib.versions)} versions (expected 2)")

            if len(dht_lib.versions) != 2:
                print(f"  ❌ DHT library version count wrong!")
                return False

            if len(servo_lib.versions) != 2:
                print(f"  ❌ Servo library version count wrong!")
                return False

            print("\n✅ ALL TESTS PASSED!")
            print("   Flat index structure is now properly supported.")
            print("   Libraries will show correct version numbers instead of 'N/A'.")
            return True

        finally:
            Path.home = original_home

if __name__ == "__main__":
    try:
        success = test_flat_index_loading()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
