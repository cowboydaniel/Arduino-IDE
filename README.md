# Arduino IDE Modern

A modern, professional Arduino development environment built with PySide6 that addresses the limitations of the traditional Arduino IDE while remaining accessible to beginners.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.7+-green.svg)

## 🎯 Core Philosophy

- **Progressive Disclosure**: Simple by default, powerful when needed
- **Beginner-friendly but not limiting**: Professional tools without compromising accessibility
- **Hardware-first thinking**: The IDE understands you're working with physical devices

## ✨ Key Features

### 1. Intelligent Code Editor
- **Syntax highlighting** for Arduino C/C++ with hardware-aware coloring
- **Line numbers** and current line highlighting
- **Auto-indentation** that understands C/C++ block structure
- **Inline suggestions** with helpful tips and best practices:
  - Use `LED_BUILTIN` instead of hardcoded pin 13
  - Reminder to open Serial Monitor when using Serial
  - Suggest named constants for pin numbers
  - Recommend `millis()` instead of long `delay()` calls
  - Detect missing `pinMode()` declarations
  - And many more helpful hints!
- **IntelliSense** support (coming soon with Language Server Protocol integration)
- **Code snippets library** for common Arduino patterns

### 2. Advanced Serial Monitor
- **Multi-device support**: Monitor multiple Arduinos simultaneously
- **Auto-detection** of available COM ports
- **Multiple baud rates**: 300 to 250000 baud
- **Color-coded messages**: Errors in red, success in green
- **Auto-scroll** with manual override
- **Send commands** with history

### 3. Professional UI/UX
- **Tabbed editor**: Work on multiple files simultaneously
- **Dockable panels**: Customize your workspace
- **Multiple themes**:
  - Dark mode (VS Code-inspired)
  - Light mode (clean and professional)
  - High contrast mode (accessibility-focused)
- **Project explorer**: Navigate your files with ease
- **Board information panel**: Quick access to board specs

### 4. Debugging Suite
- **Variable watch**: Monitor variables in real-time
- **Breakpoint support** (coming soon)
- **Memory profiler** (coming soon)
- **Logic analyzer integration** (planned)

### 5. Enhanced Package Manager 🆕
- **Smart caching**: Incremental index updates save 90%+ bandwidth
- **Multi-mirror downloads**: Automatic fallback to ensure reliability
- **Resume capability**: Interrupted downloads continue automatically
- **Dependency resolution**: Automatic installation of required libraries
- **Offline mode**: Full functionality with cached packages
- **Background updates**: Non-blocking update checking with notifications
- **CLI tools**: Full arduino-cli compatible command-line interface
- **Rich metadata**: Community ratings, download stats, compatibility info

[📖 Read the Package Manager Documentation](docs/PACKAGE_MANAGER_REDESIGN.md)

### 6. Build & Upload System
- **One-click verify/compile**
- **Direct upload to board**
- **Console output** with error highlighting
- **Build progress** tracking

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/Arduino-IDE.git
cd Arduino-IDE
```

2. **Create a virtual environment** (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

### Running the IDE

```bash
python -m arduino_ide.main
```

Or use the entry point:
```bash
python setup.py install
arduino-ide
```

## 📚 Project Structure

```
Arduino-IDE/
├── arduino_ide/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── ui/                     # User interface components
│   │   ├── main_window.py      # Main application window
│   │   ├── code_editor.py      # Code editor with syntax highlighting
│   │   ├── serial_monitor.py   # Serial communication interface
│   │   ├── board_panel.py      # Board information display
│   │   ├── project_explorer.py # File navigation
│   │   ├── console_panel.py    # Build output console
│   │   └── variable_watch.py   # Debugging variable watch
│   ├── services/               # Business logic services
│   │   └── theme_manager.py    # Theme management system
│   ├── models/                 # Data models
│   ├── utils/                  # Utility functions
│   └── resources/              # Icons, themes, templates
│       ├── icons/
│       ├── themes/
│       ├── snippets/
│       └── templates/
├── requirements.txt            # Python dependencies
├── setup.py                    # Package setup
├── .gitignore
└── README.md
```

## 🎨 Themes

The IDE supports three built-in themes:

1. **Dark Theme** (default)
   - VS Code-inspired color scheme
   - Reduced eye strain for long coding sessions
   - Syntax highlighting optimized for dark backgrounds

2. **Light Theme**
   - Clean, professional appearance
   - High contrast for bright environments
   - Traditional IDE feel

3. **High Contrast Theme**
   - Maximum accessibility
   - Black background with yellow text
   - 2px borders for clarity
   - WCAG AAA compliant

Change themes from: **View → Theme**

## 🔧 Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New File | Ctrl+N |
| Open File | Ctrl+O |
| Save File | Ctrl+S |
| Find | Ctrl+F |
| Verify/Compile | Ctrl+R |
| Upload | Ctrl+U |
| Serial Monitor | Ctrl+Shift+M |
| Start Debugging | F5 |
| Toggle Breakpoint | F9 |
| Help | F1 |

## 🔌 Supported Boards

Currently configured for common Arduino boards:

- Arduino Uno
- Arduino Mega 2560
- Arduino Nano
- Arduino Leonardo
- Arduino Micro
- Arduino Uno R4 WiFi
- Arduino Uno R4 Minima
- ESP32 Dev Module
- ESP8266 NodeMCU

More boards can be easily added through configuration.

## 🛠️ Development

### Adding New Features

The architecture uses a modular approach:

1. **UI Components** (`arduino_ide/ui/`): All visual widgets
2. **Services** (`arduino_ide/services/`): Business logic and hardware interaction
3. **Models** (`arduino_ide/models/`): Data structures
4. **Utils** (`arduino_ide/utils/`): Helper functions

### Running Tests

```bash
# TODO: Add test suite
pytest tests/
```

### Building for Distribution

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --name="Arduino IDE Modern" \
            --windowed \
            --onefile \
            arduino_ide/main.py
```

## 🗺️ Roadmap

### Phase 1: Core Features ✅ (Current)
- [x] Basic code editor with syntax highlighting
- [x] Serial monitor
- [x] Theme system
- [x] Project explorer
- [x] Board selection

### Phase 2: Advanced Editing (In Progress)
- [ ] IntelliSense with clangd integration
- [ ] Code snippets library
- [ ] Multi-file project support
- [ ] Find and replace
- [ ] Code folding

### Phase 3: Build System
- [ ] Arduino CLI integration
- [ ] PlatformIO backend support
- [ ] Library manager
- [ ] Board manager
- [ ] Custom build configurations

### Phase 4: Debugging
- [ ] Remote debugging over serial
- [ ] Breakpoint support
- [ ] Variable inspection
- [ ] Memory profiler
- [ ] Execution timeline

### Phase 5: Advanced Features
- [ ] Visual programming mode (block-based)
- [ ] Circuit view with diagrams
- [ ] Git integration
- [ ] Collaborative features
- [ ] Plugin system

### Phase 6: Professional Tools
- [ ] Unit testing framework
- [ ] CI/CD integration
- [ ] Performance profiler
- [ ] Power consumption analyzer
- [ ] Hardware-in-loop testing

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Document all public functions and classes
- Add comments for complex logic

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Arduino Team**: For the original Arduino IDE and ecosystem
- **Qt/PySide**: For the excellent GUI framework
- **VS Code**: For design inspiration
- **Pygments**: For syntax highlighting support

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/Arduino-IDE/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/Arduino-IDE/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/Arduino-IDE/wiki)

## 🌟 Screenshots

### Dark Theme
*Code editor with Arduino syntax highlighting and multi-panel layout*

### Serial Monitor
*Real-time communication with Arduino boards, supporting multiple devices*

### Theme Switching
*Three built-in themes for different preferences and accessibility needs*

---

**Built with ❤️ for the Arduino community**
