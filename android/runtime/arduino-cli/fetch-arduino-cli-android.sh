#!/usr/bin/env bash
set -euo pipefail

# Downloads the official arduino-cli ARM64 Linux binary for use on Android.
# The binary is a statically-linked Go executable that runs natively on
# arm64-v8a Android devices. It is placed under android/runtime/arduino-cli/
# where the Gradle build packages it as an APK asset and the Kotlin runtime
# extracts it into the app sandbox at first launch.

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
RUNTIME_DIR="$SCRIPT_DIR"

# arduino-cli version to download
VERSION="${ARDUINO_CLI_VERSION:-1.1.3}"

ARCHIVE="arduino-cli_${VERSION}_Linux_ARM64.tar.gz"
URL="https://github.com/arduino/arduino-cli/releases/download/v${VERSION}/${ARCHIVE}"

echo "Downloading arduino-cli ${VERSION} for Linux ARM64..."
curl -fSL "$URL" -o "$RUNTIME_DIR/$ARCHIVE"

echo "Extracting..."
tar -xzf "$RUNTIME_DIR/$ARCHIVE" -C "$RUNTIME_DIR" arduino-cli
rm -f "$RUNTIME_DIR/$ARCHIVE"

chmod +x "$RUNTIME_DIR/arduino-cli"

# Verify the binary is an ARM64 ELF
if file "$RUNTIME_DIR/arduino-cli" | grep -q "aarch64"; then
    echo "arduino-cli staged at $RUNTIME_DIR/arduino-cli"
else
    echo "Warning: binary may not be ARM64. Check with 'file $RUNTIME_DIR/arduino-cli'" >&2
fi
