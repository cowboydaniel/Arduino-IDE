# Real-time Status Display

The Real-time Status Display is a powerful feature in Arduino IDE Modern that allows you to monitor live variable values and memory usage from your Arduino board in real-time.

## Features

### 📊 Live Variable Monitoring
- Display any variable value in real-time
- Trend indicators (▲ increasing, ▼ decreasing)
- Graph visualization support (click the 📊 button)
- Automatic history tracking (last 100 values)

### 💾 Memory Usage Visualization
- **RAM Usage**: Visual progress bar with percentage
- **Flash Usage**: Visual progress bar with percentage
- Color-coded warnings (Green < 50%, Yellow < 75%, Red ≥ 75%)

### 🎮 Controls
- **⏸ Pause/Resume**: Freeze or resume real-time updates
- **🗑 Clear**: Remove all monitored variables
- **Connection Status**: Shows if connected to serial monitor

## How to Use

### 1. Open the Status Display

**Method 1: Via Menu**
- Go to `Tools` → `Real-time Status`
- Or use keyboard shortcut: `Ctrl+Shift+S`

**Method 2: Via Toolbar**
- Click the `⚡ Status` button in the main toolbar

### 2. Send Data from Arduino

The Real-time Status Display receives data through the Serial Monitor. Your Arduino sketch needs to send specially formatted messages.

#### Variable Updates

Format: `VAR:name=value`

```cpp
Serial.println("VAR:counter=42");
Serial.println("VAR:ledState=HIGH");
Serial.println("VAR:temp=23.5°C");
```

#### Memory Updates

Format: `MEM:RAM=percentage,FLASH=percentage`

```cpp
Serial.println("MEM:RAM=45,FLASH=32");
```

### 3. Complete Example

See `examples/RealTimeStatus.ino` for a complete working example:

```cpp
void setup() {
  Serial.begin(9600);
}

void loop() {
  // Send variable update
  Serial.print("VAR:counter=");
  Serial.println(counter);

  // Send memory update
  Serial.print("MEM:RAM=");
  Serial.print(ramPercent);
  Serial.print(",FLASH=");
  Serial.println(flashPercent);

  delay(1000);
}
```

## Protocol Reference

### Variable Update Protocol

**Format:** `VAR:variable_name=value`

| Component | Description | Example |
|-----------|-------------|---------|
| `VAR:` | Prefix indicating variable update | Required |
| `variable_name` | Name of the variable | `counter`, `temp`, `ledState` |
| `=` | Separator | Required |
| `value` | Current value (can include units) | `42`, `23.5°C`, `HIGH` |

**Examples:**
```
VAR:counter=42
VAR:ledState=HIGH
VAR:temp=23.5°C
VAR:humidity=65%
VAR:distance=150cm
```

### Memory Update Protocol

**Format:** `MEM:RAM=percent,FLASH=percent`

| Component | Description | Example |
|-----------|-------------|---------|
| `MEM:` | Prefix indicating memory update | Required |
| `RAM=` | RAM usage percentage | `RAM=45` |
| `,` | Separator | Required |
| `FLASH=` | Flash usage percentage | `FLASH=32` |

**Examples:**
```
MEM:RAM=45,FLASH=32
MEM:RAM=60,FLASH=28
```

## Visual Representation

```
┌──────────────────────┐
│ ⚡ Real-time Status   │
├──────────────────────┤
│ Live Values          │
├──────────────────────┤
│ counter: 42 [📊]     │
│ ledState: HIGH       │
│ temp: 23.5°C ▲       │
│ humidity: 65% ▼      │
│                      │
│ Memory Usage         │
│ RAM:  ████░░ 45%     │
│ Flash: ███░░░ 32%    │
│                      │
│ Connection           │
│ 🟢 Connected         │
│ Last update: 14:23:45│
│                      │
│ [⏸ Pause] [🗑 Clear] │
└──────────────────────┘
```

## Advanced Features

### Trend Detection

The status display automatically detects trends by comparing consecutive values:
- **▲** (Green): Value increased
- **▼** (Red): Value decreased
- No indicator: Value unchanged or non-numeric

### Graph Visualization

Click the 📊 button next to any variable to view its historical graph (future feature).

### Auto-parsing

The system automatically:
- Extracts numeric values for trend detection
- Preserves units (°C, %, cm, etc.)
- Maintains formatting

## Tips and Best Practices

### 1. Update Frequency
- Recommended: 1-2 updates per second
- Avoid: Continuous updates in tight loops
- Use delays or timers for periodic updates

```cpp
// Good
if (millis() - lastUpdate >= 1000) {
  sendStatusUpdate();
  lastUpdate = millis();
}

// Avoid
void loop() {
  sendStatusUpdate(); // Too frequent!
}
```

### 2. Variable Naming
- Use descriptive names: `temperature`, not `t`
- CamelCase or snake_case: `ledState` or `led_state`
- Keep names short for better display: < 15 characters

### 3. Units
- Include units for clarity: `23.5°C`, `150cm`, `65%`
- Be consistent with formatting
- Use standard abbreviations

### 4. Memory Calculation

For accurate RAM usage:

```cpp
int getFreeRam() {
  extern int __heap_start, *__brkval;
  int v;
  return (int) &v - (__brkval == 0 ?
         (int) &__heap_start : (int) __brkval);
}

void sendMemoryUpdate() {
  int freeRam = getFreeRam();
  int totalRam = 2048; // Arduino Uno
  int ramPercent = 100 - (freeRam * 100 / totalRam);

  Serial.print("MEM:RAM=");
  Serial.print(ramPercent);
  Serial.println(",FLASH=35"); // Flash % from build output
}
```

## Troubleshooting

### Variables Not Showing
1. Ensure Serial Monitor is connected
2. Check baud rate matches (9600 recommended)
3. Verify message format: `VAR:name=value`
4. Check for typos in prefix

### Values Not Updating
1. Click "Resume" if paused
2. Check Arduino is sending data (view Serial Monitor)
3. Verify update frequency in Arduino code
4. Check USB connection

### Memory Bars Not Updating
1. Verify format: `MEM:RAM=X,FLASH=Y`
2. Ensure percentages are 0-100
3. Check for commas between RAM and FLASH

## Integration with Existing Code

The Real-time Status Display works alongside your normal serial output:

```cpp
void loop() {
  // Normal serial output
  Serial.println("Sensor reading: 512");

  // Status display update (parsed separately)
  Serial.println("VAR:sensor=512");

  // Both appear in Serial Monitor
  // Only VAR: message updates Status Display
}
```

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Toggle Status Display | `Ctrl+Shift+S` |
| Toggle Serial Monitor | `Ctrl+Shift+M` |

## Related Features

- **Serial Monitor**: View all serial output
- **Variable Watch**: Debug-time variable inspection
- **Board Panel**: View board specifications
- **Pin Usage**: Track pin assignments

## Examples

The `examples/` folder contains:
- `RealTimeStatus.ino`: Complete working example
- Shows all features
- Includes helper functions
- Ready to upload and test

## Future Enhancements

Planned features:
- 📊 Live graphing of variable history
- 📁 Export data to CSV
- ⚠️ Custom alerts/thresholds
- 🎨 Customizable colors
- 📊 Multiple graph windows
- 🔔 Sound notifications

## Contributing

Found a bug or have a feature request? Please open an issue on GitHub!

---

**Arduino IDE Modern** | Real-time Status Display v1.0
