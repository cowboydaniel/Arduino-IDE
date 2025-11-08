# Real-time Memory Status Display

The Real-time Memory Status Display provides instant feedback on program storage (Flash) and dynamic memory (RAM) usage as you write your Arduino code. No compilation needed - see memory estimates update live!

## Features

### 📊 Live Memory Analysis
- **Program Storage (Flash)**: Shows estimated compiled code size
- **Dynamic Memory (RAM)**: Shows estimated variable and stack usage
- **Board-Specific**: Automatically adjusts limits based on selected board
- **Color-Coded Warnings**: Visual feedback when memory usage is high
  - 🟢 Green: < 50% (safe)
  - 🟡 Yellow: 50-75% (caution)
  - 🟠 Orange: 75-90% (warning)
  - 🔴 Red: ≥ 90% (critical)

### ⚡ Real-time Updates
Updates instantly as you type, analyzing:
- Function definitions and complexity
- Variable declarations (global and local estimates)
- Array sizes
- String literals
- Library usage (Serial, Wire, SPI, Servo, LCD, etc.)
- Lines of code

## How to Use

### 1. Open the Status Display

**Method 1: Via Toolbar**
- Click the `⚡ Status` button in the main toolbar

**Method 2: Via Menu**
- Go to `Tools` → `Real-time Status`
- Keyboard shortcut: `Ctrl+Shift+S`

### 2. Write Code

As you type, the memory bars update automatically:

```cpp
void setup() {
  Serial.begin(9600);  // Flash increases (Serial library)
}

void loop() {
  int myVar = 42;      // RAM estimate increases
}
```

### 3. Select Different Boards

Memory limits change based on the selected board:
- Arduino Uno: 32 KB Flash, 2 KB RAM
- Arduino Mega 2560: 256 KB Flash, 8 KB RAM
- ESP32: 4 MB Flash, 520 KB RAM
- And more...

## Visual Layout

```
┌────────────────────────────┐
│ ⚡ Real-time Memory Usage  │
│ Updates live as you write  │
├────────────────────────────┤
│ Program Storage (Flash)    │
│ ████████░░░░░░░░░░ 35%    │
│ 3.2 KB / 32.0 KB          │
│                            │
│ Dynamic Memory (RAM)       │
│ ███████░░░░░░░░░░░ 28%    │
│ 574 bytes / 2.0 KB        │
│                            │
│ Board Information          │
│ Board: Arduino Uno         │
│                            │
│ 💡 These are estimates     │
│ based on code analysis.    │
│ Compile to see actual      │
│ memory usage.              │
└────────────────────────────┘
```

## Memory Estimation Details

### Flash (Program Storage) Estimation

The analyzer calculates Flash usage based on:

1. **Base Arduino Runtime**: ~1500 bytes
2. **Functions**: ~150 bytes per function
3. **String Literals**: Actual byte count
4. **Code Complexity**: ~15 bytes per line of code
5. **Libraries**:
   - Serial: +1000 bytes
   - Wire (I2C): +1500 bytes
   - SPI: +800 bytes
   - Servo: +1200 bytes
   - LCD: +2000 bytes

**Example:**
```cpp
// Function adds ~150 bytes
void blinkLED() {
  digitalWrite(13, HIGH);  // ~30 bytes (2 LOC × 15)
  delay(1000);
}

void setup() {
  Serial.begin(9600);  // +1000 bytes (Serial library)
  pinMode(13, OUTPUT);
}  // Another function: +150 bytes
```

### RAM (Dynamic Memory) Estimation

The analyzer calculates RAM usage based on:

1. **Base Runtime**: ~200 bytes (stack + Arduino overhead)
2. **Variables by Type**:
   - `int`: 2 bytes
   - `long`, `float`, `double`: 4 bytes
   - `char`, `byte`, `bool`: 1 byte
3. **Arrays**: Size × type size
4. **String Buffers**: Declared size
5. **Stack Estimate**: ~32 bytes per function
6. **Serial Buffers**: +128 bytes if Serial is used

**Example:**
```cpp
int counter = 0;           // +2 bytes
float temperature = 23.5;  // +4 bytes
char message[50];          // +50 bytes
byte data[100];            // +100 bytes

void setup() {
  Serial.begin(9600);      // +128 bytes (buffers)
}                          // +32 bytes (stack)
```

## Supported Boards

The status display automatically adjusts for these boards:

| Board | Flash | RAM |
|-------|-------|-----|
| Arduino Uno | 32 KB | 2 KB |
| Arduino Nano | 32 KB | 2 KB |
| Arduino Leonardo | 32 KB | 2.5 KB |
| Arduino Mega 2560 | 256 KB | 8 KB |
| Arduino Uno R4 WiFi | 256 KB | 32 KB |
| Arduino Uno R4 Minima | 256 KB | 32 KB |
| Arduino Due | 512 KB | 96 KB |
| ESP32 Dev Module | 4 MB | 520 KB |
| ESP8266 NodeMCU | 4 MB | 80 KB |

## Tips for Managing Memory

### Reducing Flash Usage

1. **Remove unused libraries**: Only include what you need
2. **Use `const` or `PROGMEM`**: Store constants in Flash instead of RAM
3. **Optimize string usage**: Combine similar strings
4. **Simplify functions**: Break complex logic into smaller pieces

```cpp
// Before: String in RAM
char message[] = "Hello, World!";  // Uses RAM

// After: String in Flash
const char message[] PROGMEM = "Hello, World!";  // Stays in Flash
```

### Reducing RAM Usage

1. **Use local variables**: Instead of globals when possible
2. **Minimize buffer sizes**: Only allocate what you need
3. **Use smaller data types**: `byte` instead of `int` when values < 256
4. **Reuse buffers**: Use the same buffer for multiple purposes

```cpp
// Before: Wastes RAM
int ledPin = 13;        // 2 bytes, but value is < 256
char buffer1[100];      // 100 bytes
char buffer2[100];      // 100 bytes

// After: Optimized
byte ledPin = 13;       // 1 byte
char buffer[100];       // 100 bytes (reused)
```

## Understanding the Estimates

### Why Estimates May Differ from Actual

The real-time analyzer provides **estimates** based on static code analysis. Actual compiled memory usage may differ because:

1. **Compiler Optimizations**: The compiler may optimize away unused code
2. **Inline Functions**: Small functions may be inlined
3. **Library Internals**: Actual library sizes vary by implementation
4. **Link-time Optimization**: Dead code elimination
5. **Debug vs Release**: Debug builds include extra information

### When to Trust the Estimates

- ✅ **Good for trends**: See how changes affect memory
- ✅ **Early warnings**: Catch potential memory issues early
- ✅ **Relative comparisons**: Compare different implementations
- ✅ **Learning tool**: Understand what uses memory

### When to Compile

Always compile before final deployment to see:
- Actual memory usage
- Exact available memory
- Compiler warnings about memory
- Optimized code size

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Toggle Status Display | `Ctrl+Shift+S` |
| Toggle Serial Monitor | `Ctrl+Shift+M` |
| Verify/Compile | `Ctrl+R` |
| Upload | `Ctrl+U` |

## Example Use Cases

### 1. Optimizing Memory Usage

```cpp
// Version 1: Check memory usage
int sensors[10];          // Status shows RAM usage
float values[10];

// Version 2: Optimize
byte sensors[10];         // Watch RAM decrease
int values[10];           // Enough precision for most cases
```

### 2. Choosing Between Libraries

```cpp
// Test A: Basic implementation
#include <LiquidCrystal.h>  // Check Flash usage

// Test B: Lighter library
#include <TinyLCD.h>         // Compare Flash usage
```

### 3. Before Adding Features

Check current memory usage before adding new features to ensure you have enough space.

## Troubleshooting

### Status Not Updating
- Ensure the Status Display panel is visible
- Check that you're editing an `.ino` file
- Try switching to a different tab and back

### Incorrect Estimates
- Remember these are estimates, not exact values
- Compile for actual measurements
- Some advanced C++ features may not be analyzed correctly

### Board Not Recognized
- Select board from the Board dropdown in toolbar
- Status will update automatically
- Default is Arduino Uno if board unknown

## Integration with Other Features

The Status Display works alongside:
- **Pin Usage Panel**: See which pins are used
- **Board Panel**: View board specifications
- **Console**: See compilation messages
- **Serial Monitor**: Monitor runtime behavior

## Future Enhancements

Planned features:
- 📊 Historical memory usage graphs
- ⚠️ Customizable warning thresholds
- 💾 Export memory reports
- 🎯 Memory optimization suggestions
- 🔍 Detailed breakdown by function/variable

## Contributing

Found a bug or want to improve the memory estimation algorithm? Contributions welcome!

---

**Arduino IDE Modern** | Real-time Memory Status Display v2.0
