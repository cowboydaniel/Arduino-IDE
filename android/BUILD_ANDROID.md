# Building Arduino IDE Modern for Android

Phase 0 delivers a ready-to-import Android Studio project that does **not**
require running `pyside6-android-deploy` or other generation commands. Everything
needed to sync and assemble the debug APK is committed under `android/`.

## Prerequisites

- Android Studio Flamingo (or newer) with Android SDK Platform 34
- Android NDK r26b installed via the SDK Manager
- Python 3.11 available on your PATH for PySide6 tooling
- OpenJDK 17 (bundled with Android Studio works)

## Project layout

- `android/android-studio/` — Gradle project to open directly in Android Studio
- `android/runtime/` — Bundled Qt/PySide6 runtime placeholders used by Gradle
- `arduino-cli` — Prebuilt Arduino CLI binary staged into the APK
- `main.py` and `arduino_ide/` — Python sources copied into the APK assets

## Quick start (Android Studio)

1. Open **File → Open…** and choose `android/android-studio`.
2. Allow Android Studio to use the checked-in Gradle wrapper. On first run the
   wrapper downloads its own JAR based on `gradle/wrapper/gradle-wrapper.properties`
   so we don't commit binary artifacts (requires Python 3 and network access).
3. Press **Sync Project with Gradle Files** — no additional generation steps are
   required.
4. Select the **debug** build variant and click **Run ▶** to install on a device
   or emulator.

## Command line build

From the repository root you can assemble the debug APK entirely with the
committed wrapper:

```bash
cd android/android-studio
./gradlew assembleDebug
```

The Gradle tasks will stage Python sources, the bundled runtime artifacts, and
the Arduino CLI into `app/src/main/assets` automatically.

The wrapper script auto-downloads `gradle/wrapper/gradle-wrapper.jar` if it is
not present so binary files remain out of version control.

## Updating runtime assets

The placeholders under `android/runtime` can be replaced with real PySide6/Qt
Android deployment outputs. Drop the generated `pyside6-android-deploy` output
into `android/runtime` and rebuild — the Gradle sync task will pick up the new
files without extra configuration.
