# Mobile clangd runtime

This folder is reserved for a mobile-friendly clangd bundle. The Android build
*requires* a real binary here: Gradle will refuse to assemble the APK if the
`clangd` file is missing, and `ClangdRuntimeBridge` copies the packaged asset
into the app sandbox before launching the language server over JNI, gRPC, or
stdio.

## Building

You must produce a mobile-friendly build from an LLVM checkout that sits next to
this repository:

```bash
# ANDROID_NDK_HOME must point at NDK r26b+ from the Android SDK Manager
./android/runtime/clangd/build-clangd-android.sh
```

The helper script configures the NDK toolchain for `arm64-v8a`, compiles clangd
with Ninja, strips symbols, and drops the result into this folder so the APK can
pick it up. Gradle will package this asset into the APK unchanged and the
runtime will refuse to start if the binary is absent. See `android/BUILD_ANDROID.md`
for more context and manual steps if you prefer to drive the build yourself.

## JNI or gRPC shim

A thin shim (checked into `android/android-studio/app/src/main/java/...`) can
load the packaged binary through JNI or expose it through gRPC for testability.
Our `LanguageServerTransport` abstraction accepts either strategy, so teams can
swap implementations without touching UI code.
