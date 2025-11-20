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
- `android/runtime/clangd` — Staging area for a mobile-friendly clangd binary used by the Kotlin LSP client

## Quick start (Android Studio)

1. Open **File → Open…** and choose `android/android-studio`.
2. Allow Android Studio to use the checked-in Gradle wrapper. On first run the
   wrapper downloads its own JAR based on `gradle/wrapper/gradle-wrapper.properties`
   so we don't commit binary artifacts.
3. Press **Sync Project with Gradle Files** — no additional generation steps are
   required.
4. Select the **debug** build variant and click **Run ▶** to install on a device
   or emulator.

### Packaging clangd for Android (required)

The Android app will not start language services unless a real clangd binary is
packaged. Run the checked-in helper script to stage it before assembling:

```bash
# From the repository root with ANDROID_NDK_HOME pointing at NDK r26b+
./android/runtime/clangd/build-clangd-android.sh
```

Under the hood the script configures CMake for `arm64-v8a`, builds clangd from
`clang-tools-extra`, strips symbols, and copies the binary into
`android/runtime/clangd`. Android Studio packages that file as an asset and the
Kotlin runtime marks it executable inside the sandbox via `ClangdRuntimeBridge`.
Gradle tasks that produce APKs will fail fast if `android/runtime/clangd/clangd`
is missing or empty so you never ship a placeholder.

Teams that prefer a manual flow can follow the same steps:

1. Configure CMake with `-DLLVM_ENABLE_PROJECTS=clang;clang-tools-extra` and set
   `-DLLVM_TARGETS_TO_BUILD=AArch64;ARM` using the Android toolchain file.
2. Build clangd with `ninja clangd` and strip symbols via `llvm-strip`.
3. Drop the resulting `clangd` binary into `android/runtime/clangd`.

`LanguageServerClient` consumes either a JNI-based stdio bridge or a gRPC shim
implementing `LanguageServerTransport`, so UI code remains transport-agnostic.

## Command line build

From the repository root you can assemble the debug APK entirely with the
committed wrapper:

```bash
cd android/android-studio
./gradlew assembleDebug
```

The wrapper script auto-downloads `gradle/wrapper/gradle-wrapper.jar` if it is
not present so binary files remain out of version control.
