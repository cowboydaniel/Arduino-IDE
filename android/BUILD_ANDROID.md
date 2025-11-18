# Building Arduino IDE Modern for Android (Qt for Python pipeline)

This guide explains how to produce signed Android artifacts from source using the Qt for Python/Gradle toolchain instead of Buildozer or python-for-android.

## Prerequisites

### System requirements

- **Operating system**: Ubuntu 22.04 LTS or later (other modern Linux distros work with equivalent packages)
- **RAM**: 8 GB minimum, 16 GB recommended
- **Storage**: 20 GB free space for Android SDK/NDK, Qt, and build outputs
- **CPU**: 64-bit processor (x86_64)

### Base packages

Install common build utilities and Java (Gradle and the Android tools require Java 17):

```bash
sudo apt update
sudo apt install -y build-essential git wget unzip python3 python3-venv \
  openjdk-17-jdk ninja-build zlib1g-dev libssl-dev
```

### Android SDK/NDK

1. Download Google's command line tools and install to `~/Android/Sdk`:

   ```bash
   mkdir -p "$HOME/Android" && cd "$HOME/Android"
   wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
   unzip commandlinetools-linux-*_latest.zip
   mv cmdline-tools "$HOME/Android/cmdline-tools"
   mkdir -p "$HOME/Android/Sdk/cmdline-tools/latest"
   mv "$HOME/Android/cmdline-tools"/* "$HOME/Android/Sdk/cmdline-tools/latest"
   ```

2. Install required SDK components (adjust the platform version to match the current target SDK in the project):

   ```bash
   export ANDROID_SDK_ROOT="$HOME/Android/Sdk"
   yes | "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" \
     "platform-tools" \
     "platforms;android-34" \
     "build-tools;34.0.0" \
     "cmake;3.22.1" \
     "ndk;26.1.10909125"
   export ANDROID_NDK_ROOT="$ANDROID_SDK_ROOT/ndk/26.1.10909125"
   ```

### Qt for Android (matching PySide6)

Arduino IDE Modern uses PySide6 6.7.2. Install the corresponding Qt for Android packages with `aqtinstall`:

```bash
python3 -m pip install --user aqtinstall
# Install the desktop host tools (required by androiddeployqt)
python3 -m aqt install-qt linux desktop 6.7.2 gcc_64 --outputdir "$HOME/Qt"
# Install Android libraries for each architecture you plan to ship
python3 -m aqt install-qt linux android 6.7.2 android_arm64_v8a --outputdir "$HOME/Qt"
python3 -m aqt install-qt linux android 6.7.2 android_armv7 --outputdir "$HOME/Qt"  # optional 32-bit
```

Set helpful environment variables (add to `~/.bashrc` for convenience):

```bash
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export ANDROID_SDK_ROOT="$HOME/Android/Sdk"
export ANDROID_NDK_ROOT="$ANDROID_SDK_ROOT/ndk/26.1.10909125"
export QT_HOST_PATH="$HOME/Qt/6.7.2/gcc_64"
export QT_ANDROID_ARM64="$HOME/Qt/6.7.2/android_arm64_v8a"
export QT_ANDROID_ARMV7="$HOME/Qt/6.7.2/android_armv7"
export PATH="$JAVA_HOME/bin:$ANDROID_SDK_ROOT/platform-tools:$PATH"
```

## Quick build

```bash
cd Arduino-IDE/android
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt

# Initialize deployment settings file if it does not exist
pyside6-android-deploy --init android-deploy.json \
  --name "Arduino IDE Modern" \
  --package org.arduino.ide \
  --main main.py

# Build an unsigned debug APK for both 32-bit and 64-bit ARM
pyside6-android-deploy --config android-deploy.json \
  --android-platform android-34 \
  --architectures arm64-v8a,armeabi-v7a \
  --qt-dir "$QT_ANDROID_ARM64" \
  --no-makefile \
  --verbose
```

The deploy command generates a Gradle project under `android/build/` and produces debug artifacts in `android/build/android-build/build/outputs/apk/debug/`.

## Configuring `android-deploy.json`

`pyside6-android-deploy --init` creates a JSON configuration file you can edit to customize packaging. Key fields:

- `mainScript`: Entry point (`main.py` in this project).
- `packageName` and `applicationName`: Android identifier and display name.
- `androidSdk` / `ndk`: Paths to your SDK/NDK.
- `qmake` and `qt`: Set to `$QT_HOST_PATH/bin/qmake` and the Qt for Android directory for the target ABI.
- `androidPlatform`: API level to target (e.g., `android-34`).
- `architectures`: Comma-separated list such as `arm64-v8a,armeabi-v7a`.
- `androidExtraResources`: Add icons, XML resources, and native libraries.

Regenerate the Gradle project after edits by re-running `pyside6-android-deploy --config android-deploy.json`.

## Targeting architectures

- **Modern devices**: Build only `arm64-v8a` for a smaller APK:
  ```bash
  pyside6-android-deploy --config android-deploy.json --architectures arm64-v8a --qt-dir "$QT_ANDROID_ARM64"
  ```
- **Legacy support**: Include `armeabi-v7a` by adding it to `architectures` and install the matching Qt package. Expect a larger APK/AAB.

## Signing and release builds

1. **Create a keystore** (one-time):
   ```bash
   keytool -genkey -v -keystore my-release-key.keystore \
     -alias arduino-ide -keyalg RSA -keysize 2048 -validity 10000
   ```

2. **Provide signing info to Gradle**. After running the deploy command, create `android/build/gradle.properties` (or `~/.gradle/gradle.properties`) with:
   ```properties
   releaseStoreFile=/absolute/path/to/my-release-key.keystore
   releaseStorePassword=YOUR_STORE_PASSWORD
   releaseKeyAlias=arduino-ide
   releaseKeyPassword=YOUR_KEY_PASSWORD
   ```

3. **Assemble signed artifacts**:
   ```bash
   cd android/build/android-build
   ./gradlew assembleRelease   # produces APK
   ./gradlew bundleRelease     # produces AAB for Play Store
   ```

Release outputs are located under `android/build/android-build/app/build/outputs/`.

## Cleaning builds

- Remove generated Gradle projects and artifacts:
  ```bash
  rm -rf android/build
  ```
- Clear Python environment:
  ```bash
  rm -rf android/.venv
  ```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `sdkmanager: command not found` | SDK tools not on `PATH` | Export `ANDROID_SDK_ROOT` and add `$ANDROID_SDK_ROOT/cmdline-tools/latest/bin` to `PATH`. |
| `Could not determine Java version` | Wrong JDK installed | Use OpenJDK 17 and update `JAVA_HOME`. |
| `No toolchains found in the NDK` | `ANDROID_NDK_ROOT` points to wrong version | Reinstall the NDK listed above and export the matching path. |
| `aapt2` or `zipalign` missing | Build-tools not installed | Re-run `sdkmanager` with `"build-tools;34.0.0"`. |
| Qt version mismatch | Qt for Android version differs from PySide6 | Install Qt 6.7.2 for all target ABIs via `aqtinstall`. |
| `ModuleNotFoundError` during deployment | Virtual environment missing dependencies | Activate `.venv` and run `pip install -r ../requirements.txt`. |

For verbose output, add `--verbose` to `pyside6-android-deploy` or `--info` to Gradle commands.

## Release checklist

- [ ] Build release AAB with `./gradlew bundleRelease`.
- [ ] Verify signature: `apksigner verify --verbose app/build/outputs/apk/release/*.apk`.
- [ ] Test on target devices for each architecture built.
- [ ] Confirm versionCode/versionName in `android-deploy.json` before tagging a release.
- [ ] Attach APK/AAB to GitHub Releases or upload to the Play Console.

---

**Happy building with the new pipeline!**
