# Building Arduino IDE Modern for Android

This guide provides detailed instructions for building the Android APK from source.

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04 LTS or later (recommended), or other Linux distribution
- **RAM**: 8 GB minimum, 16 GB recommended
- **Storage**: 20 GB free space for Android SDK, NDK, and build artifacts
- **CPU**: 64-bit processor (x86_64)

### Required Build Tools

Before building, install the following dependencies:

```bash
# Update package list
sudo apt update

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install autotools (REQUIRED for libffi compilation)
sudo apt install -y autoconf automake libtool pkg-config

# Install build essentials
sudo apt install -y build-essential git wget unzip openjdk-11-jdk

# Install 32-bit libraries (for Android build tools)
sudo apt install -y libc6:i386 libncurses5:i386 libstdc++6:i386 lib32z1 libbz2-1.0:i386

# Install additional libraries
sudo apt install -y zlib1g-dev libssl-dev libffi-dev
```

### Install Buildozer

Buildozer is the build system for creating Android APKs from Python applications:

```bash
# Install buildozer
pip3 install --user buildozer

# Install Cython (required by buildozer)
pip3 install --user cython

# Add ~/.local/bin to PATH if not already added
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
source ~/.bashrc
```

## Quick Build Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/cowboydaniel/Arduino-IDE.git
cd Arduino-IDE/android
```

### 2. Build the APK

```bash
# Debug build (faster, for testing)
buildozer android debug

# Release build (optimized, for distribution)
buildozer android release
```

The first build will take 30-60 minutes as it downloads:
- Android SDK (~1 GB)
- Android NDK (~1 GB)
- Python-for-android toolchain
- All Python dependencies
- Compiles native libraries (including libffi)

Subsequent builds are much faster (5-10 minutes).

### 3. Install to Device

```bash
# Connect Android device via USB with USB debugging enabled
# Then deploy and run
buildozer android deploy run
```

## Build Process Explained

### What Buildozer Does

1. **Downloads Android Tools**:
   - Android SDK (Software Development Kit)
   - Android NDK r25b (Native Development Kit)
   - Apache Ant (build system)

2. **Prepares Python-for-Android**:
   - Clones python-for-android repository
   - Applies custom recipes from `p4a-recipes/`
   - Compiles Python for ARM architecture

3. **Builds Native Libraries**:
   - Compiles libffi (Foreign Function Interface)
   - Builds SDL2 (graphics library)
   - Compiles other native dependencies

4. **Packages the APK**:
   - Bundles Python code and dependencies
   - Includes PySide6 (Qt for Android)
   - Creates APK with proper Android manifest
   - Signs APK (debug or release)

### Custom Recipes

This project includes custom python-for-android recipes in `p4a-recipes/`:

- **libffi**: Patched to work with modern autotools versions

The custom recipes are automatically used by buildozer via the `p4a.local_recipes` setting in `buildozer.spec`.

## Troubleshooting Build Issues

### autoreconf: not found

**Error**:
```
autogen.sh: exec: autoreconf: not found
```

**Solution**:
```bash
sudo apt install -y autoconf automake libtool
```

This is required for building libffi from source.

### Build Fails with "No space left on device"

**Solution**:
- Ensure you have at least 20 GB free space
- Clean previous builds: `buildozer android clean`
- Remove cached downloads: `rm -rf ~/.buildozer`

### Java Version Issues

**Error**:
```
java.lang.UnsupportedClassVersionError
```

**Solution**:
```bash
# Install Java 11 (required for current Android build tools)
sudo apt install -y openjdk-11-jdk

# Set Java 11 as default
sudo update-alternatives --config java
```

### Build is Very Slow

**Tips to Speed Up**:
- Use `--verbose` flag to see what's happening: `buildozer -v android debug`
- Enable parallel builds in `buildozer.spec`:
  ```ini
  [app]
  android.gradle_dependencies =

  [buildozer]
  android.accept_sdk_license = True
  ```
- Use a build server with more RAM/CPU cores

### USB Device Not Detected

**Solution**:
```bash
# Add udev rules for Android devices
sudo apt install -y android-sdk-platform-tools-common

# Or manually add your device
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="YOUR_VENDOR_ID", MODE="0666", GROUP="plugdev"' | sudo tee /etc/udev/rules.d/51-android.rules
sudo udevadm control --reload-rules
```

## Build Configuration

### buildozer.spec Options

The `buildozer.spec` file controls the build process. Key settings:

```ini
[app]
# Application info
title = Arduino IDE Modern - Android
package.name = arduinoidemodern
package.domain = org.arduino.ide
version = 0.1.0

# Python requirements
requirements = python3, PySide6

# Android API levels
android.api = 34          # Target SDK (Android 14)
android.minapi = 24       # Minimum SDK (Android 7.0)

# Architectures to build
android.archs = arm64-v8a, armeabi-v7a

# Permissions
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,REQUEST_INSTALL_PACKAGES

[buildozer]
# Build settings
log_level = 2             # 0=error, 1=warning, 2=info, 3=debug
warn_on_root = 0          # Allow building as root

# Custom recipes
p4a.local_recipes = ./p4a-recipes
```

## Advanced Build Options

### Building for Specific Architecture

```bash
# Build only for 64-bit ARM (smaller APK, modern devices only)
buildozer android debug android.archs=arm64-v8a

# Build only for 32-bit ARM (older devices)
buildozer android debug android.archs=armeabi-v7a
```

### Clean Builds

```bash
# Clean build artifacts (keeps Android SDK/NDK)
buildozer android clean

# Clean everything including downloads
rm -rf .buildozer ~/.buildozer
```

### Increasing Build Verbosity

```bash
# See detailed build output
buildozer -v android debug

# Maximum verbosity (for debugging build issues)
buildozer -vv android debug
```

## Release Build Process

### 1. Create Signing Key

```bash
# Generate a keystore for signing release APKs
keytool -genkey -v -keystore my-release-key.keystore \
  -alias arduino-ide -keyalg RSA -keysize 2048 -validity 10000
```

### 2. Configure Buildozer

Add to `buildozer.spec`:

```ini
[app]
android.release_artifact = apk

[buildozer]
# Don't sign with debug key
android.skip_update = False
```

### 3. Build and Sign

```bash
# Build release APK
buildozer android release

# Sign the APK
jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \
  -keystore my-release-key.keystore \
  bin/arduinoidemodern-*-release-unsigned.apk arduino-ide

# Align the APK (required by Google Play)
zipalign -v 4 bin/arduinoidemodern-*-release-unsigned.apk \
  bin/arduinoidemodern-release.apk
```

## Distribution

### Google Play Store

Requirements:
- Release APK signed with release key
- App Bundle (AAB) format recommended
- Privacy policy
- App screenshots and description

### F-Droid

Arduino IDE Modern is open source and can be distributed via F-Droid:
1. Submit app metadata to F-Droid repository
2. F-Droid builds from source automatically
3. Users install via F-Droid app

### Direct APK Distribution

- Host APK on GitHub Releases
- Users download and install manually
- Requires "Install from Unknown Sources" enabled

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/android-build.yml`:

```yaml
name: Android Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        sudo apt update
        sudo apt install -y autoconf automake libtool
        pip install buildozer cython

    - name: Build APK
      run: |
        cd android
        buildozer android debug

    - name: Upload APK
      uses: actions/upload-artifact@v3
      with:
        name: app-debug
        path: android/bin/*.apk
```

## Build Performance Tips

### Use ccache for Faster Rebuilds

```bash
# Install ccache
sudo apt install -y ccache

# Configure buildozer to use ccache
export USE_CCACHE=1
export NDK_CCACHE=ccache

buildozer android debug
```

### Reduce APK Size

1. **Build for one architecture**:
   ```bash
   buildozer android release android.archs=arm64-v8a
   ```

2. **Enable ProGuard** (code optimization):
   Add to `buildozer.spec`:
   ```ini
   android.add_gradle_repositories = google(), mavenCentral()
   android.gradle_dependencies =
   ```

3. **Strip debug symbols**:
   ```bash
   # Automatically done in release builds
   buildozer android release
   ```

## Getting Help

If you encounter build issues:

1. **Check build log**: Look for error messages in the verbose output
2. **Search issues**: Check [GitHub Issues](https://github.com/cowboydaniel/Arduino-IDE/issues)
3. **Ask for help**: Create a new issue with:
   - Operating system and version
   - Full build log (use `-vv` flag)
   - Error messages
   - Steps to reproduce

## References

- [Buildozer Documentation](https://buildozer.readthedocs.io/)
- [Python-for-Android Documentation](https://python-for-android.readthedocs.io/)
- [Android Developer Guide](https://developer.android.com/)
- [PySide6 for Android](https://doc.qt.io/qtforpython/)

---

**Happy Building! 🔨📱**
