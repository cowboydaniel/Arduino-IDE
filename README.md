# Arduino IDE Modern

<p align="center">
  <strong>A complete, feature-rich Arduino development environment built entirely in Python</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/Version-0.1.0-orange" alt="Version 0.1.0">
  <img src="https://img.shields.io/badge/Status-Feature%20Complete-success" alt="Status">
</p>

---

## Overview

**Arduino IDE Modern** is a professional-grade Arduino development environment that goes beyond traditional IDEs. Built with Python and PySide6 (Qt), it offers advanced features like visual programming, circuit design, real-time collaboration, debugging, CI/CD integration, and comprehensive plugin support.

This is NOT the official Arduino IDE, but rather a modern alternative designed for hobbyists, educators, and professional embedded developers who want powerful tools with an extensible architecture.

### Key Highlights

- **32,801+ lines** of Python code
- **2,491 electronic components** in the circuit library
- **All 6 development phases completed** (Core, Advanced Editing, Build System, Debugging, Advanced Features, Professional Tools)
- **35 UI modules** and **25 service modules** providing complete IDE functionality
- **Plugin system** for extensibility
- **Comprehensive testing** with 40+ test files

---

## Features

### Core Development Features

#### Code Editor
- Advanced syntax highlighting for Arduino C/C++
- Line numbers and current line highlighting
- Auto-indentation optimized for embedded development
- IntelliSense with clangd integration
- Code completion and smart suggestions
- Code snippets library
- Code folding
- Multi-file tabbed editing
- Find and replace functionality

#### Build System
- **Arduino CLI Integration**: Full compile and upload support
- **Library Manager**:
  - Install, update, uninstall libraries from Arduino registry
  - Version parsing and dependency resolution
  - Install from ZIP files
  - Conflict detection and duplicate management
  - Multi-mirror downloads with checksum verification
- **Board Manager**: Board detection, installation, and configuration
- Custom build configurations
- Real-time compilation output

#### Serial Communication
- Multi-device serial monitor support
- COM port auto-detection
- Configurable baud rates
- Auto-reconnect functionality
- Timestamp display
- Data logging

### Advanced Development Tools

#### Debugging
- **Full GDB/MI Protocol Support**: Professional debugging capabilities
- **Breakpoint Management**: Visual breakpoint indicators in editor gutter
- **Call Stack Panel**: Stack trace visualization and frame navigation
- **Variable Watch**: Monitor custom variables with real-time updates
- **Memory Profiler**: RAM, Flash, Stack, and Heap monitoring
- **Execution Timeline**: Event tracking and chronological logging
- **Debug Toolbar**: Step over/into/out, continue, pause controls
- Enhanced debug compilation with symbol generation

#### Visual Programming
- Block-based programming (Scratch/Blockly-style interface)
- 50+ pre-defined Arduino blocks
- Automatic code generation to Arduino C++
- Save/load block-based projects
- Perfect for education and rapid prototyping

#### Circuit Design
- Visual circuit editor with drag-and-drop components
- Comprehensive component library (2,491 components):
  - Arduino boards (Uno, Mega, Nano, etc.)
  - LEDs, resistors, capacitors, transistors
  - Integrated circuits (logic gates, op-amps, timers)
  - Sensors (temperature, motion, light, gas)
  - Motors (DC, servo, stepper)
  - Buttons, switches, potentiometers, breadboards
- Wire connections with validation
- Pin type checking
- Circuit save/load functionality

### Professional Tools

#### Version Control
- **Full Git Integration**:
  - Stage, commit, push, pull operations
  - Branch management
  - Commit history visualization
  - Visual Git panel
- Built-in GitPython support

#### Real-Time Collaboration
- Collaborative editing sessions
- Text change synchronization
- Cursor position tracking
- Built-in chat messaging
- Project sharing (public/private)
- User roles (Owner, Editor, Viewer)

#### Unit Testing Framework
- **Multiple Framework Support**: GoogleTest, Unity, AUnit
- Host-based and on-device testing
- Code coverage reporting
- Mock function system
- JUnit XML export for CI integration

#### CI/CD Integration
- **Multi-Platform Support**:
  - GitHub Actions
  - GitLab CI
  - Jenkins
  - Travis CI
  - CircleCI
  - Azure Pipelines
- Automatic pipeline configuration generation
- Build status monitoring
- Pipeline triggering from IDE

#### Performance Analysis
- **Performance Profiler**:
  - Function-level execution time profiling
  - Bottleneck detection
  - Optimization suggestions
  - Profile comparison
- **Power Consumption Analyzer**:
  - Real-time current measurement (INA219/INA260 support)
  - Sleep mode analysis
  - Battery life estimation
  - Power optimization suggestions
- **Hardware-in-Loop (HIL) Testing**:
  - Automated hardware test execution
  - Test fixture management
  - Signal generation and capture
  - Multi-board test support

#### Plugin System
- Extensible plugin architecture
- Plugin discovery and loading
- Comprehensive Plugin API
- Install from ZIP
- Example plugin included
- Supported plugin types: Tool, Editor, Compiler, Library, Theme

### User Experience

#### Themes
- Three built-in themes:
  - Dark theme
  - Light theme
  - High contrast theme
- Theme persistence across sessions
- Plugin support for custom themes

#### Workspace
- Dockable panels for flexible layouts
- Project explorer with file tree navigation
- Board information panel
- Console panel for build output
- Variable watch panel
- Status bar with real-time information
- Window state persistence
- Keyboard shortcuts for common operations

---

## Technology Stack

### Core Technologies
- **Python 3.9+**: Primary development language
- **PySide6 (Qt 6.7.2)**: Cross-platform GUI framework
- **pyserial (3.5)**: Serial communication with Arduino boards
- **pygments (2.18.0)**: Syntax highlighting engine

### Key Dependencies
- **pyqtgraph (0.13.7)**: Data visualization and plotting
- **GitPython (3.1.43)**: Git version control integration
- **requests (2.32.3)**: HTTP requests for package/library management
- **jedi (0.19.1)**: Code intelligence and completion
- **packaging (24.1)**: Version parsing and dependency management

---

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- Git (for version control features)
- Arduino CLI (included in repository)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/cowboydaniel/Arduino-IDE.git
cd Arduino-IDE

# Install dependencies
pip install -r requirements.txt

# Run the IDE
python run.py
```

### Alternative Installation Methods

#### Using pip (Development Mode)
```bash
pip install -e .
```

After installation, launch the IDE with:
```bash
arduino-ide
```

#### Using Python Module
```bash
python -m arduino_ide.main
```

---

## Project Structure

```
Arduino-IDE/
├── arduino_ide/              # Main application package
│   ├── ui/                   # User interface components (35 modules)
│   │   ├── main_window.py    # Central application window
│   │   ├── code_editor.py    # Advanced code editor
│   │   ├── serial_monitor.py # Serial communication
│   │   ├── debug_toolbar.py  # Debug controls
│   │   ├── circuit_editor.py # Circuit designer
│   │   └── ...               # 30+ more UI components
│   │
│   ├── services/             # Business logic layer (25 modules)
│   │   ├── board_manager.py  # Board management
│   │   ├── library_manager.py # Library operations
│   │   ├── debug_service.py  # Debugging engine
│   │   ├── git_service.py    # Version control
│   │   └── ...               # 21+ more services
│   │
│   ├── models/               # Data models
│   ├── component_library/    # 2,491 electronic components (JSON)
│   ├── resources/            # Templates and snippets
│   ├── cores/                # Arduino core definitions
│   ├── data/                 # API reference data
│   ├── utils/                # Utility functions
│   ├── main.py               # Application entry point
│   └── config.py             # Configuration constants
│
├── tests/                    # Test suite (40+ test files)
├── scripts/                  # Utility scripts
├── docs/                     # Documentation
├── examples/                 # Example projects
├── example_plugin/           # Example plugin implementation
├── arduino-cli               # Arduino CLI binary
├── run.py                    # Quick start script
├── setup.py                  # Package installation
├── requirements.txt          # Python dependencies
└── pytest.ini                # Test configuration
```

---

## Usage

### Creating a New Sketch

1. Launch the IDE
2. Create a new file or use a template from the templates menu
3. Write your Arduino code with IntelliSense support
4. Select your board from the board panel
5. Click "Verify" to compile or "Upload" to flash to board

### Using the Library Manager

1. Open **Tools → Library Manager**
2. Search for libraries by name or keyword
3. Click "Install" to add libraries to your project
4. Manage versions and dependencies automatically

### Debugging Your Code

1. Set breakpoints by clicking in the editor gutter
2. Click the debug button or press F5
3. Use debug toolbar to step through code
4. Monitor variables in the watch panel
5. View memory usage in the memory profiler

### Designing Circuits

1. Open **Tools → Circuit Editor**
2. Drag components from the library onto the canvas
3. Connect components with wires
4. Validate connections
5. Save your circuit design

### Visual Programming

1. Open **Tools → Visual Programming**
2. Drag blocks from the palette
3. Connect blocks to create logic
4. Click "Generate Code" to convert to Arduino C++
5. Upload generated code to board

### Collaborating on Projects

1. Open **Tools → Collaboration Panel**
2. Create a new session or join existing one
3. Share the session code with collaborators
4. Edit code together in real-time
5. Use built-in chat for communication

### Creating Plugins

1. Create a new directory for your plugin
2. Add a `plugin.json` manifest file
3. Create your plugin class inheriting from `Plugin`
4. Implement lifecycle methods and event handlers
5. Place in the plugins directory and restart IDE

See `example_plugin/` for a complete working example.

---

## Testing

The project includes comprehensive test coverage with 40+ test files.

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_board_manager_fixes.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=arduino_ide
```

### Test Categories

- Unit tests for services and components
- Integration tests for library/board management
- Feature tests for specific functionality
- Component library validation tests

---

## Documentation

Comprehensive documentation is available in the repository:

### User Guides
- **[QUICKSTART.md](QUICKSTART.md)**: Installation and first steps
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: Contribution guidelines

### Technical Documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System architecture and design patterns
- **[ROADMAP.md](ROADMAP.md)**: Development phases and feature status
- **[CHANGELOG.md](CHANGELOG.md)**: Version history

### Feature Documentation
- **[BOARD_DISCOVERY_IMPLEMENTATION.md](BOARD_DISCOVERY_IMPLEMENTATION.md)**: Board detection
- **[INTELLISENSE_IMPROVEMENTS.md](INTELLISENSE_IMPROVEMENTS.md)**: Code completion
- **[DEBUGGING_INTEGRATION.md](DEBUGGING_INTEGRATION.md)**: Debug system integration
- **[PHASE5_INTEGRATION.md](PHASE5_INTEGRATION.md)**: Visual programming, circuits, Git, collaboration, plugins
- **[PHASE6_INTEGRATION.md](PHASE6_INTEGRATION.md)**: Testing, CI/CD, profiling, power analysis

### Component Library
- **[component_library/README.md](arduino_ide/component_library/README.md)**: Component file format

---

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/cowboydaniel/Arduino-IDE.git
cd Arduino-IDE

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development tools (optional)
pip install black pylint mypy pytest pytest-cov
```

### Code Quality

The project follows Python best practices:

```bash
# Format code
black arduino_ide/

# Lint code
pylint arduino_ide/

# Type checking
mypy arduino_ide/

# Run tests
pytest
```

### Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and code quality checks
5. Submit a pull request

---

## Architecture

### Design Patterns

- **Model-View-Controller (MVC)**: Clean separation of concerns
- **Observer Pattern**: Qt signals/slots for event handling
- **Singleton Pattern**: Configuration and service managers
- **Factory Pattern**: Component creation
- **Strategy Pattern**: Pluggable compilation and upload strategies

### Data Flow

```
User Input → UI Components → Services → Models → Arduino CLI/Hardware
```

### Plugin Architecture

```
Plugin Manifest (JSON) → Plugin Loader → Plugin Lifecycle → Event Handlers → IDE Integration
```

---

## Statistics

- **117 Python files**
- **32,801+ lines of Python code**
- **2,493 JSON component definitions**
- **22 Markdown documentation files**
- **40+ test files**
- **35 UI modules**
- **25 service modules**

---

## Requirements

### System Requirements

- **Operating System**: Windows, macOS, Linux
- **Python**: 3.9 or higher
- **RAM**: 2 GB minimum, 4 GB recommended
- **Disk Space**: 500 MB for application and dependencies

### Python Dependencies

See [requirements.txt](requirements.txt) for complete list:

- PySide6 >= 6.7.2
- pyserial >= 3.5
- pygments >= 2.18.0
- pyqtgraph >= 0.13.7
- GitPython >= 3.1.43
- requests >= 2.32.3
- jedi >= 0.19.1
- packaging >= 24.1

---

## Roadmap

### Phase 1: Core Features ✅ COMPLETED
- Code editor, serial monitor, themes, project explorer

### Phase 2: Advanced Editing ✅ COMPLETED
- IntelliSense, snippets, multi-file support, find/replace

### Phase 3: Build System ✅ COMPLETED
- Arduino CLI integration, library manager, board manager

### Phase 4: Debugging ✅ COMPLETED
- GDB/MI support, breakpoints, call stack, memory profiler

### Phase 5: Advanced Features ✅ COMPLETED
- Visual programming, circuit design, Git, collaboration, plugins

### Phase 6: Professional Tools ✅ COMPLETED
- Unit testing, CI/CD, performance profiling, power analysis, HIL testing

### Future Enhancements
- Language Server Protocol (LSP) for enhanced IntelliSense
- Web-based IDE version
- Microservices architecture for enterprise deployment
- AI-powered code completion and optimization
- Cloud compilation service

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Arduino**: For the Arduino platform and Arduino CLI
- **Qt/PySide**: For the excellent cross-platform GUI framework
- **Python Community**: For the rich ecosystem of libraries
- **Contributors**: Everyone who has contributed to this project

---

## Support

### Getting Help

- Check the [documentation](docs/)
- Review [existing issues](https://github.com/cowboydaniel/Arduino-IDE/issues)
- Create a new issue for bugs or feature requests

### Community

- Contribute code or documentation
- Report bugs and suggest features
- Share your projects built with Arduino IDE Modern

---

## Screenshots

### Code Editor with IntelliSense
Advanced code editing with syntax highlighting, auto-completion, and error detection.

### Visual Programming
Block-based programming interface for beginners and rapid prototyping.

### Circuit Designer
Drag-and-drop circuit design with extensive component library.

### Debug Interface
Professional debugging with breakpoints, call stack, and memory profiling.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

### Version 0.1.0 (Current)
- Initial release
- All 6 development phases completed
- 32,801+ lines of Python code
- 2,491 electronic components
- Comprehensive testing and documentation

---

## Contact

For questions, suggestions, or collaboration opportunities:

- **Repository**: https://github.com/cowboydaniel/Arduino-IDE
- **Issues**: https://github.com/cowboydaniel/Arduino-IDE/issues

---

<p align="center">
  Made with ❤️ for the Arduino and embedded development community
</p>
