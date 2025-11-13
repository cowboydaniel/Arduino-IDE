# Fix for BC256-1_0.ino Compilation Error

## Problem

Your `BC256-1_0.ino` file compiles perfectly on Arduino IDE 1.x but fails on Arduino IDE 2.x with errors like:

```
error: expected unqualified-id before 'else'
 else if(String(buf) == F("BENCH"));
```

This is a **bug in Arduino IDE 2.x's preprocessor**. It incorrectly extracts `else if` statements from inside your `loop()` function and places them at global scope in the generated `.cpp` file.

## Solution

Use the provided Python script to preprocess your `.ino` file before compiling:

### Step 1: Run the Fix Script

```bash
python3 fix_ino_for_ide2.py /path/to/BC256-1_0.ino
```

This will:
- Create a backup: `BC256-1_0.ino.backup`
- Fix the original file in-place

### Step 2: Compile with Arduino IDE 2.x

Open the fixed `BC256-1_0.ino` in Arduino IDE 2.x and compile normally.

## Alternative: Save to New File

If you want to keep the original unchanged:

```bash
python3 fix_ino_for_ide2.py BC256-1_0.ino BC256-1_0_fixed.ino
```

## What the Script Does

The script scans your `.ino` file and removes any control flow statements (`if`, `else if`, `else`, `while`, `for`, `switch`) that appear with empty semicolon bodies (`;`) at global scope. These are invalid C++ but Arduino IDE 1.x silently ignores them.

**Example of removed statements:**
```cpp
// These at global scope will be removed:
if(condition);
else if(condition);
while(false);
```

**Your function-level code is preserved:**
```cpp
void loop() {
  // These are kept - they're inside a function
  if (String(buf) == F("AUTO")) {
    // code
  }
  else if (String(buf) == F("BENCH")) {
    // code
  }
}
```

## Root Cause

Arduino IDE 2.x has a preprocessing bug where it sometimes extracts code from inside functions and places it at global scope. The official Arduino IDE 1.x preprocessor handles this differently, which is why your code compiles there.

This fix has been applied to this repository's Python-based arduino-cli, but you're using the official Arduino IDE 2.x which has its own (buggy) preprocessor written in Go.

## Long-term Solution

The proper fix needs to be applied to Arduino IDE 2.x itself. This issue has been reported to the Arduino team.

## Questions?

If you have issues with this fix, please provide:
1. The full compilation error output
2. The first 30 lines of the generated `.cpp` file from the build directory
3. Your Arduino IDE version
