# Mobile clangd runtime

This folder is reserved for a mobile-friendly clangd bundle. The Android build
pipes the resulting binary into the APK via `ClangdRuntimeBridge`, which copies
it into the app sandbox before launching the language server over JNI, gRPC, or
stdio.

## Building

1. Install the Android NDK r26b and LLVM toolchain from the Android SDK.
2. Configure CMake with `-DLLVM_ENABLE_PROJECTS=clang;clang-tools-extra` and set
   `-DLLVM_TARGETS_TO_BUILD=AArch64;ARM` so that clangd is compiled for mobile
   ABIs.
3. Build clangd with `ninja clangd` and strip symbols via `llvm-strip` to reduce
   the APK footprint.
4. Copy the resulting `clangd` binary into this directory before running the
   Android Studio build. The Kotlin runtime will mark it executable at startup.

## JNI or gRPC shim

A thin shim (checked into `android/android-studio/app/src/main/java/...`) can
load the packaged binary through JNI or expose it through gRPC for testability.
Our `LanguageServerTransport` abstraction accepts either strategy, so teams can
swap implementations without touching UI code.
