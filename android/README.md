# Arduino IDE Modern - Android Edition

<p align="center">
  <strong>Full-featured Arduino development environment for Android devices</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Android-green" alt="Android">
  <img src="https://img.shields.io/badge/Min%20SDK-API%2024%20(Android%207.0)-blue" alt="Min SDK 24">
  <img src="https://img.shields.io/badge/Target%20SDK-API%2034%20(Android%2014)-blue" alt="Target SDK 34">
  <img src="https://img.shields.io/badge/Status-In%20Development-yellow" alt="Status">
</p>

---

## Overview

**Arduino IDE Modern for Android** brings the complete power of the desktop Arduino development environment to mobile devices. Built using Python and Qt for Android (PySide6), this port enables developers to write, compile, and upload Arduino code directly from smartphones and tablets.

Whether you're prototyping on the go, teaching Arduino in classrooms without computers, or debugging projects in the field, Arduino IDE Modern for Android provides a professional-grade development experience optimized for touchscreen interfaces.

### Current Status

- ✅ **Phase 1: Android Foundation & Basic Editor** – Initial PySide6-based Android shell with touch-friendly editor, syntax highlighting, file management, tabbed editing, keyboard toolbar, and theme support.
- ✅ **Phase 2: Arduino Build System Integration** – Integrated Arduino CLI-powered verification with board selection, core installation, library management, build console, and clickable compiler errors.

### Why Android?

- **Portability**: Develop anywhere with just your phone or tablet
- **USB OTG Support**: Direct connection to Arduino boards via USB cable
- **Bluetooth Integration**: Wireless programming and monitoring
- **Education**: Lower barrier to entry for students without computers
- **Field Work**: Debug and modify code directly at deployment sites
- **Cost Effective**: Leverage existing mobile hardware

---

## Features

### Core Mobile-Optimized Features

#### Touch-Optimized Code Editor
- **Gesture-based navigation**: Pinch to zoom, swipe between files
- **Floating keyboard toolbar**: Quick access to common symbols and brackets
- **Haptic feedback**: Tactile response for selections and actions
- **Split-screen support**: View code and documentation side-by-side
- **Dark mode optimization**: OLED-friendly themes for battery savings
- Syntax highlighting for Arduino C/C++
- IntelliSense with touch-friendly popups
- Code snippets library with categorized templates
- Multi-file tabbed editing
- Virtual cursor navigation for precise editing

#### Mobile Build System
- **Arduino CLI integration** (ARM64 native binary)
- **Incremental compilation**: Cache compiled objects for faster builds
- **Background compilation**: Continue working while code compiles
- **Build notifications**: Android notifications for compilation results
- Library manager with offline caching
- Board manager with auto-detection via USB OTG
- Low-memory mode for older devices

#### USB OTG Serial Communication
- **Direct USB connection** to Arduino boards
- **Auto-reconnect**: Handle Android USB permission dialogs gracefully
- **Multiple device support**: Connect to several boards simultaneously
- Configurable baud rates (300 to 2000000)
- Serial monitor with scrolling buffer
- Serial plotter with touch-zoom and pan
- Data logging to device storage
- CSV export for analysis

#### Bluetooth Serial Support
- **Bluetooth Classic** (SPP profile) for HC-05/HC-06 modules
- **Bluetooth Low Energy (BLE)** for ESP32, Arduino Nano 33 BLE
- Device pairing and management
- Automatic reconnection
- Concurrent USB and Bluetooth connections

### Android-Specific Features

#### Native Integration
- **Share functionality**: Share sketches via email, cloud storage, messaging
- **Intent handling**: Open .ino files from file managers
- **Document provider**: Access sketches from Google Drive, Dropbox
- **Scoped storage**: Android 11+ storage compliance
- **Background service**: Continue uploads in background
- **Quick Settings tile**: Quick access to serial monitor
- **Widget support**: Home screen widgets for quick actions

#### Power Management
- **Battery optimization**: Adaptive refresh rates and background throttling
- **Doze mode compatibility**: Maintain serial connections during idle
- **Wake lock management**: Prevent sleep during uploads
- **Low-power serial monitoring**: Reduced sampling rates for battery savings

#### Cloud & Sync
- **Google Drive integration**: Automatic sketch backup and sync
- **GitHub mobile**: Commit and push directly from Android
- **Cloud compilation**: Offload heavy builds to cloud servers (optional)
- **Cross-device sync**: Continue work from desktop to mobile seamlessly

### Adapted Desktop Features

All major desktop features adapted for mobile:

- **Visual Programming**: Touch-friendly block editor with drag-and-drop
- **Circuit Designer**: Mobile-optimized schematic capture with component library
- **Debugging**: GDB/MI support via USB or WiFi debugging
- **Version Control**: Git integration with visual diff viewer
- **Collaboration**: Real-time multi-user editing sessions
- **Plugin System**: Installable extensions via APK or Python packages
- **Code Quality**: Real-time analysis and suggestions
- **Examples Library**: 100+ pre-loaded Arduino examples

---

## System Requirements

### Minimum Requirements
- **Android Version**: 7.0 (Nougat, API 24) or higher
- **RAM**: 2 GB minimum
- **Storage**: 500 MB free space
- **CPU**: ARM64 (AArch64) processor
- **USB OTG** support (for direct board connection)

### Recommended Requirements
- **Android Version**: 11.0 or higher
- **RAM**: 4 GB or more
- **Storage**: 1 GB free space
- **Screen Size**: 7" tablet or larger for optimal experience
- **Bluetooth**: 4.0 or higher for BLE support

### Tested Devices
- Samsung Galaxy Tab series (S7+, S8, S9)
- Google Pixel phones (6, 7, 8 series)
- OnePlus devices (9, 10, 11 series)
- Xiaomi tablets (Pad 5, Pad 6)
- Amazon Fire tablets (HD 10, HD 8 with Google Play)

---

## Installation

### Google Play Store (Recommended)
```
Coming Soon - Currently in Beta Testing
```

### APK Direct Download
1. Download the latest APK from [Releases](https://github.com/cowboydaniel/Arduino-IDE/releases)
2. Enable "Install from Unknown Sources" in Android settings
3. Open the APK file and follow installation prompts
4. Grant required permissions (Storage, USB, Bluetooth)

### Building from Source
```bash
# Install Buildozer (on Linux desktop or Termux)
pip install buildozer

# Clone the repository
git clone https://github.com/cowboydaniel/Arduino-IDE.git
cd Arduino-IDE/android

# Build APK
buildozer android debug

# Install to connected device
buildozer android deploy run
```

See [BUILD_ANDROID.md](BUILD_ANDROID.md) for detailed build instructions.

---

## Quick Start Guide

### First Launch Setup

1. **Grant Permissions**: Accept storage and USB access permissions
2. **Download Core Files**: First launch downloads Arduino CLI and core libraries (~100 MB)
3. **USB OTG Setup**: Connect Arduino board via USB OTG adapter
4. **Grant USB Permission**: Accept Android USB device permission dialog
5. **Select Board**: Choose your Arduino board from detected devices
6. **Start Coding**: Open an example or create a new sketch

### Connecting Your Arduino Board

#### Via USB OTG Cable
1. Connect USB OTG adapter to Android device
2. Connect Arduino board to OTG adapter
3. Accept USB permission dialog
4. Board appears in board selector

#### Via Bluetooth (Classic)
1. Pair Bluetooth module in Android Bluetooth settings
2. Open Serial Monitor in app
3. Select paired device from Bluetooth devices list
4. Connect and start monitoring

#### Via WiFi (ESP32/ESP8266)
1. Connect Arduino board to same WiFi network
2. Enable WiFi debugging in app settings
3. Enter board IP address
4. Connect for OTA uploads and debugging

### Creating Your First Sketch

1. Tap **New** or select **File → New Sketch**
2. Write your Arduino code using the touch keyboard
3. Tap **Verify** to compile (builds in background)
4. Tap **Upload** to flash to connected board
5. Open **Serial Monitor** to view output

---

## Mobile UI Design

### Layout Modes

#### Phone Mode (Portrait)
- **Single panel view**: Code editor fills screen
- **Bottom navigation**: Quick access to Monitor, Plotter, Console
- **Floating action button**: Upload, Verify actions
- **Slide-out menu**: File browser, settings, tools

#### Phone Mode (Landscape)
- **Split view**: Code editor (70%) + output panel (30%)
- **Toolbar**: Top toolbar with common actions
- **Tabs**: Horizontal tab bar for open files

#### Tablet Mode
- **Multi-panel layout**: Editor, file tree, output console
- **Dockable panels**: Drag to rearrange
- **Full toolbar**: Desktop-like toolbar experience
- **Picture-in-Picture**: Serial monitor as floating window

### Touch Gestures

- **Pinch zoom**: Adjust code font size
- **Two-finger swipe**: Switch between open files
- **Long press**: Context menu (cut, copy, paste, refactor)
- **Double tap**: Select word or symbol
- **Three-finger swipe**: Undo/redo
- **Edge swipe**: Open file browser drawer

---

## Hardware Support

### Supported Arduino Boards

All boards supported by Arduino CLI:
- Arduino Uno, Mega, Nano, Micro
- Arduino Leonardo, Due, Zero
- Arduino MKR series (WiFi, WAN, GSM, NB, Vidor)
- Arduino Nano 33 (IoT, BLE, Sense)
- ESP8266, ESP32 (all variants)
- STM32 boards
- Teensy boards (via USB OTG)
- Third-party Arduino-compatible boards

### USB OTG Compatibility

**Supported USB Chipsets**:
- CH340/CH341 (most common Arduino clones)
- CP2102/CP2104 (Silicon Labs)
- FTDI FT232 (original Arduino boards)
- PL2303 (Prolific)

**Required**: USB OTG adapter or USB-C to USB-A adapter

### Bluetooth Modules

**Bluetooth Classic (SPP)**:
- HC-05, HC-06 modules
- RN-42 Bluetooth modules

**Bluetooth Low Energy (BLE)**:
- HM-10, HM-11 modules
- Arduino Nano 33 BLE built-in
- ESP32 built-in BLE

---

## Storage & File Management

### Sketch Storage Locations

- **Internal Storage**: `/storage/emulated/0/Arduino/`
- **SD Card**: `/storage/[SD-ID]/Arduino/` (if available)
- **App Private Storage**: `/data/data/com.arduino.ide/files/`
- **Cloud Storage**: Google Drive, Dropbox integration

### Library Management

- **Auto-download**: Libraries downloaded on-demand
- **Offline cache**: Previously used libraries stored locally
- **Manual install**: Import ZIP libraries from Downloads folder
- **Cloud sync**: Sync custom libraries across devices

### File Import/Export

- **Import sketches**: From .ino, .zip, GitHub repositories
- **Export sketches**: Share as .zip, upload to cloud, Git push
- **Backup/Restore**: Automatic cloud backup (optional)

---

## Performance Optimization

### Memory Management

- **Adaptive memory limits**: Adjust based on device RAM
- **Lazy loading**: Load components only when needed
- **Library pruning**: Download only required library versions
- **Cache management**: Automatic cleanup of build artifacts

### Battery Life

- **Adaptive refresh**: Lower screen refresh during idle
- **Background throttling**: Reduce CPU usage when backgrounded
- **Serial sampling**: Adjustable polling rates for serial monitor
- **WiFi optimization**: Disconnect when not needed

### Build Performance

- **Incremental builds**: Rebuild only changed files
- **Parallel compilation**: Multi-core support where available
- **Cloud offload**: Optional cloud compilation for heavy projects
- **Build cache**: Persistent object file caching

---

## Known Limitations

### Android Platform Constraints

- **No GDB native debugging**: Full GDB debugging not available (WiFi debugging possible)
- **Limited multi-tasking**: Background builds may pause on older devices
- **USB reliability**: Some devices have USB OTG power issues
- **Storage access**: Scoped storage limits on Android 11+

### Performance Limitations

- **Large sketches**: Projects >5000 lines may be slower to navigate
- **Heavy libraries**: Large libraries (e.g., TFT_eSPI) slow compilation
- **Code completion**: IntelliSense slower than desktop on mid-range devices

### Workarounds

- Use **cloud compilation** for heavy builds
- Enable **low-memory mode** in settings for older devices
- Use **external keyboard** for extensive coding sessions
- **Split work**: Heavy refactoring on desktop, quick fixes on mobile

---

## Permissions Explained

### Required Permissions

- **Storage (READ/WRITE)**: Access Arduino sketches and libraries
- **USB Access**: Communicate with Arduino boards via USB OTG
- **Bluetooth**: Connect to Bluetooth serial modules
- **Internet**: Download libraries, Arduino cores, and updates
- **Foreground Service**: Keep uploads running in background
- **Wake Lock**: Prevent sleep during board uploads

### Optional Permissions

- **Camera**: Scan QR codes for WiFi board connection
- **Location**: Required for Bluetooth scanning on Android 12+
- **Notifications**: Show compilation and upload status
- **Install Packages**: Install plugin APKs

All permissions are requested at runtime with clear explanations.

---

## FAQ

### General Questions

**Q: Can I really develop Arduino projects on my phone?**
A: Yes! All core functionality works, including code editing, compilation, and uploading. The experience is optimized for mobile with touch gestures and mobile-friendly UI.

**Q: Do I need internet connection?**
A: Internet required for first-time setup to download Arduino CLI and cores. After setup, offline development is fully supported. Cloud features require internet.

**Q: Is this the official Arduino IDE?**
A: No, this is an independent modern alternative. It's compatible with all Arduino boards and libraries but offers additional features.

### Hardware Questions

**Q: My device doesn't have USB OTG. Can I still use this?**
A: Yes! Use Bluetooth serial modules or WiFi-enabled boards (ESP32/ESP8266) for wireless programming.

**Q: Does it work with Arduino clones?**
A: Yes! Supports all USB serial chipsets including CH340, CP2102, FTDI, and PL2303.

**Q: Can I power Arduino from my phone's USB port?**
A: Depends on your device's USB OTG power output. Most phones provide 5V at 500mA, enough for small Arduino boards. Use external power for larger projects.

### App Questions

**Q: Why is the app size so large?**
A: The app bundles Python runtime, Qt framework, and Arduino CLI. Total size ~150-200 MB to ensure offline functionality.

**Q: Does it drain battery quickly?**
A: Normal editing uses minimal battery. Active serial monitoring or compilation increases usage. Enable battery saver mode in app settings.

**Q: Can I use external keyboard?**
A: Yes! Bluetooth and USB keyboards fully supported with keyboard shortcuts.

---

## Roadmap

### Version 1.0 (Current Development)
- ✅ Core code editor and compilation
- ✅ USB OTG serial support
- ✅ Bluetooth serial support
- ✅ Library and board management
- ⏳ Google Play Store release
- ⏳ Cloud storage integration

### Version 1.1 (Planned)
- WiFi debugging and OTA uploads
- Enhanced tablet UI
- Plugin system for Android
- Code completion improvements
- Custom keyboard layouts

### Version 2.0 (Future)
- ChromeOS support
- Samsung DeX optimization
- Peer-to-peer collaboration
- AI code assistant
- AR circuit visualization

---

## Contributing

We welcome contributions to the Android port! Areas where help is needed:

- **UI/UX improvements** for mobile experience
- **Device compatibility testing** on various Android devices
- **Performance optimization** for low-end devices
- **Documentation** and tutorials
- **Translation** to multiple languages

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

## Technical Architecture

### Technology Stack

- **Python 3.11**: Core application logic (via python-for-android)
- **PySide6**: Qt 6 framework for Android
- **Kivy**: Alternative UI framework for some components
- **Arduino CLI ARM64**: Native ARM compilation binary
- **Buildozer**: Build system for creating APK

### App Structure

```
android/
├── buildozer.spec          # Build configuration
├── main.py                 # Android application entry point
├── ui_mobile/              # Mobile-optimized UI components
│   ├── touch_editor.py     # Touch-friendly code editor
│   ├── mobile_toolbar.py   # Compact toolbar for phones
│   └── gesture_handler.py  # Touch gesture recognition
├── services_mobile/        # Android-specific services
│   ├── usb_service.py      # USB OTG communication
│   ├── bluetooth_service.py # BLE and Classic Bluetooth
│   └── storage_service.py  # Scoped storage handling
├── res/                    # Android resources
│   ├── drawable/           # Icons and images
│   ├── values/             # Strings and styles
│   └── xml/                # Android manifests
└── libs/                   # Native libraries
    ├── arm64-v8a/          # 64-bit ARM binaries
    └── armeabi-v7a/        # 32-bit ARM binaries (legacy)
```

---

## License

This project is licensed under the MIT License, same as the desktop version. See [LICENSE](../LICENSE) for details.

---

## Support & Community

### Getting Help

- **Documentation**: Check [docs/android/](../docs/android/)
- **GitHub Issues**: [Report bugs or request features](https://github.com/cowboydaniel/Arduino-IDE/issues)
- **Discussions**: [Community forum](https://github.com/cowboydaniel/Arduino-IDE/discussions)

### Social Media

- Follow development updates
- Share your mobile Arduino projects
- Connect with other mobile makers

---

## Acknowledgments

- **Arduino Team**: For the Arduino platform and Arduino CLI
- **Qt for Android**: For excellent cross-platform mobile framework
- **python-for-android**: For enabling Python apps on Android
- **Kivy Community**: For mobile UI components
- **Beta Testers**: Everyone testing on their Android devices

---

<p align="center">
  <strong>Build Arduino projects anywhere, anytime! 🚀📱</strong>
</p>

<p align="center">
  Made with ❤️ for the mobile maker community
</p>
