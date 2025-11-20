#!/usr/bin/env bash
set -euo pipefail

# Build clangd for Android devices. This script intentionally relies only on the
# Android SDK/NDK toolchains that ship with Android Studio so CI can reuse the
# same environment. The resulting binary is placed under android/runtime/clangd
# where the Kotlin runtime copies it into the app sandbox at startup.

ROOT_DIR=$(cd "$(dirname "$0")/../../.." && pwd)
RUNTIME_DIR="$ROOT_DIR/android/runtime/clangd"
LLVM_PROJECT_DIR=${LLVM_PROJECT_DIR:-"$ROOT_DIR/llvm-project"}

if [[ ! -d "$LLVM_PROJECT_DIR" ]]; then
  echo "\nError: LLVM sources not found. Set LLVM_PROJECT_DIR or clone https://github.com/llvm/llvm-project next to this repo." >&2
  exit 1
fi

if [[ -z "${ANDROID_NDK_HOME:-}" ]]; then
  echo "\nError: ANDROID_NDK_HOME must point to NDK r26b (or newer)." >&2
  exit 1
fi

BUILD_DIR=${BUILD_DIR:-"$LLVM_PROJECT_DIR/build-android"}
mkdir -p "$BUILD_DIR"

cmake -G Ninja \
  -S "$LLVM_PROJECT_DIR/llvm" \
  -B "$BUILD_DIR" \
  -DLLVM_ENABLE_PROJECTS="clang;clang-tools-extra" \
  -DLLVM_TARGETS_TO_BUILD="AArch64;ARM" \
  -DLLVM_ENABLE_PIC=ON \
  -DCMAKE_BUILD_TYPE=MinSizeRel \
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI="arm64-v8a" \
  -DANDROID_PLATFORM=android-24

ninja -C "$BUILD_DIR" clangd

STRIP_BIN="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip"
"$STRIP_BIN" "$BUILD_DIR/bin/clangd" -o "$RUNTIME_DIR/clangd"
chmod +x "$RUNTIME_DIR/clangd"

echo "\nclangd staged at $RUNTIME_DIR/clangd"
