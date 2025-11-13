# Quick Start Guide

Get up and running with Arduino IDE Modern in 5 minutes!

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/Arduino-IDE.git
cd Arduino-IDE
```

### Step 2: Install Dependencies

#### Option A: Using pip directly

```bash
pip install -r requirements.txt
```

#### Option B: Using a virtual environment (recommended)

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**On Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Run the IDE

```bash
python run.py
```

Or:

```bash
python -m arduino_ide.main
```

## First Steps

### 1. Write Your First Sketch

When the IDE opens, you'll see a basic Arduino template:

```cpp
void setup() {
  Serial.begin(9600);
}

void loop() {

}
```

### 2. Connect Your Arduino

1. Plug in your Arduino board via USB
2. The IDE should auto-detect available COM ports
3. Select your board from the **Board Info** panel (right side)

### 3. Open Serial Monitor

1. Click **📡 Serial Monitor** in the toolbar (or press `Ctrl+Shift+M`)
2. Select the correct COM port
3. Choose baud rate (default: 9600)
4. Click **Connect**

### 4. Upload Code

1. Click **✓ Verify** to compile your code
2. Click **→ Upload** to flash to your Arduino
3. Watch the console for progress

## Built-in Libraries Ready to Use

On first launch the IDE automatically installs the same set of bundled
libraries that ship with the classic Arduino 1.8 IDE (Servo, Wire, SD,
Ethernet, LiquidCrystal, and many more). They are copied into the managed
libraries folder (`~/.arduino-ide-modern/libraries`) so sketches can include
headers like `#include <Servo.h>` immediately—no manual downloads required.

## Features to Explore

### Themes

Try different themes from **View → Theme**:
- **Dark** - Easy on the eyes for long coding sessions
- **Light** - Clean and professional
- **High Contrast** - Maximum accessibility

### Multiple Files

Click **+ New** to open multiple sketches in tabs.

### Project Explorer

Use the **Project Explorer** (left panel) to:
- Browse project files
- Organize your code
- Manage libraries

### Serial Monitor Features

- **Send commands**: Type in the input box and press Enter
- **Auto-scroll**: Toggle to keep latest data visible
- **Color coding**: Errors in red, success in green
- **Clear output**: Click Clear to reset

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New File | `Ctrl+N` |
| Open | `Ctrl+O` |
| Save | `Ctrl+S` |
| Verify | `Ctrl+R` |
| Upload | `Ctrl+U` |
| Serial Monitor | `Ctrl+Shift+M` |
| Find | `Ctrl+F` |

## Example Projects

### Blink LED

```cpp
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(1000);
  digitalWrite(LED_BUILTIN, LOW);
  delay(1000);
}
```

### Read Sensor

```cpp
void setup() {
  Serial.begin(9600);
}

void loop() {
  int value = analogRead(A0);
  Serial.print("Sensor: ");
  Serial.println(value);
  delay(500);
}
```

### Button Input

```cpp
const int BUTTON_PIN = 2;
const int LED_PIN = 13;

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  int buttonState = digitalRead(BUTTON_PIN);
  digitalWrite(LED_PIN, !buttonState);  // Inverted due to pullup
}
```

## Troubleshooting

### COM Port Not Found

- **Check connection**: Ensure Arduino is plugged in
- **Drivers**: Install Arduino USB drivers
- **Refresh**: Click the refresh button (🔄) next to port selection

### Serial Monitor Not Connecting

- **Close other programs**: Arduino IDE, PuTTY, etc. may be using the port
- **Check baud rate**: Must match your code (`Serial.begin()`)
- **Permissions**: On Linux, add yourself to `dialout` group:
  ```bash
  sudo usermod -a -G dialout $USER
  # Then log out and back in
  ```

### Code Won't Compile

- **Check syntax**: Look for missing semicolons, brackets
- **Library missing**: Install required libraries
- **Console output**: Read error messages in the console panel

### UI Issues

- **Reset layout**: Close and reopen the IDE
- **Theme problems**: Switch to a different theme
- **Qt issues**: Ensure PySide6 is properly installed:
  ```bash
  pip install --upgrade PySide6
  ```

## Next Steps

1. **Explore Templates**: Check `arduino_ide/resources/templates/` for example sketches
2. **Read Documentation**: See [README.md](README.md) for full feature list
3. **Join Community**: Open discussions on GitHub
4. **Contribute**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **GitHub Discussions**: Ask questions and share projects
- **Documentation**: Check the Wiki for detailed guides

---

**Happy Making! 🎉**
