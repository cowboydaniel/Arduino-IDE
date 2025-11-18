# Building Arduino IDE Modern for Android (Kotlin)

Phase 0 delivers a ready-to-import Android Studio project that does **not**
require any Python or Qt deployment steps. Everything needed to sync and
assemble the debug APK is committed under `android/`.

## Prerequisites

- Android Studio Flamingo (or newer) with Android SDK Platform 34
- Android NDK r26b installed via the SDK Manager
- OpenJDK 17 (bundled with Android Studio works)
- CMake and Ninja from the Android SDK (installed automatically with NDK)

## Project layout

- `android/android-studio/` — Gradle project to open directly in Android Studio
- `android/android-studio/app/src/main/java/` — Kotlin sources with the entry `MainActivity`
- `android/android-studio/app/src/main/res/` — Material 3 theming and view-binding layouts
- `arduino-cli` — Prebuilt Arduino CLI binary staged for future integration

## Quick start (Android Studio)

1. Open **File → Open…** and choose `android/android-studio`.
2. Allow Android Studio to use the checked-in Gradle wrapper. On first run the
   wrapper downloads its own JAR based on `gradle/wrapper/gradle-wrapper.properties`
   so we don't commit binary artifacts.
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

The wrapper script auto-downloads `gradle/wrapper/gradle-wrapper.jar` if it is
not present so binary files remain out of version control.
