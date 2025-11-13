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

- **43,116 lines** of Python code across **101 modules**
- **2,000+ KiCAD component catalog** for circuit design
- **All 6 development phases completed** (Core, Advanced Editing, Build System, Debugging, Advanced Features, Professional Tools)
- **41 UI modules** (92+ classes) and **29 service modules** providing complete IDE functionality
- **8-type plugin system** for extensibility
- **Comprehensive testing** with 40+ test files
- **Advanced debugging** with GDB/MI protocol support
- **Real-time collaboration** with operational transformation
- **Professional analysis tools**: Performance profiling, power analysis, HIL testing

---

## Features

### Core Development Features

#### Code Editor
- Advanced syntax highlighting for Arduino C/C++
- Line numbers and current line highlighting
- Auto-indentation optimized for embedded development
- IntelliSense with clangd integration
- Code completion and smart suggestions
- **Code Snippets Library**:
  - Category-based organization (Basic Structure, Digital I/O, Analog I/O, Serial Communication, etc.)
  - Cursor positioning with placeholders ($0)
  - Tab stops for parameter entry (${1:default})
  - Search and filter snippets
  - Custom snippet insertion
- Code folding
- Multi-file tabbed editing
- Find and replace with regex support
- **Breadcrumb Navigation**: Visual file path and function context indicator
- **Code Minimap**: Zoomed-out code overview for quick navigation
- **Contextual Help System**: Inline hints and context-aware suggestions
- **Smart Error Recovery**: Intelligent error detection with friendly recovery hints

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
- Data logging to files
- **Serial Plotter**: Real-time data visualization with multi-series support
- **CSV Export**: Export plotted data for external analysis
- Color-coded message types
- Send/receive functionality with terminal emulation

### Advanced Development Tools

#### Code Intelligence & Quality
- **Code Quality Panel**: Real-time code metrics and analysis
- **Inline Code Hints**: Context-aware suggestions and tips in the editor
- **Smart Error Recovery**: Compiler error analysis with friendly recovery hints
  - Semicolon and syntax error detection
  - Identifier and type mismatch suggestions
  - Memory and optimization issue detection
- **Code Suggestion Analyzer**:
  - Hardcoded pin detection
  - Magic number identification
  - Missing pinMode warnings
  - Delay optimization suggestions
  - Analog pin usage recommendations
- **Problems Panel**: Centralized error and warning tracking
  - Filter by severity (All, Errors Only, Warnings Only, Info Only)
  - Double-click to jump to code location
  - Problem count tracking
  - Clear all functionality
  - File, line number, and message display
- **Git Change Highlighting**: Visual indicators for modified code
- **Built-in API Reference**:
  - **Arduino API Reference**: Comprehensive function reference with syntax, parameters, examples, warnings, and tips
  - **C++ Language Reference**: Complete C++ data types, keywords, operators with platform-specific guidance

#### Debugging
- **Full GDB/MI Protocol Support**: Professional debugging capabilities
- **Debug Workspace Dialog**: Unified debugging interface with integrated panels
- **Breakpoint Management**: Visual breakpoint indicators in editor gutter
  - Line, function, and conditional breakpoints
  - Breakpoint hit count tracking
  - Enable/disable individual breakpoints
- **Call Stack Panel**: Stack trace visualization and frame navigation
- **Variable Watch**: Monitor custom variables with real-time updates
  - Variable type information
  - Scope tracking (local, global)
  - Address display
  - Variable hierarchy for nested structures
- **Memory Profiler**: RAM, Flash, Stack, and Heap monitoring
  - Free/used memory calculation
  - Memory region visualization
  - Fragmentation tracking
- **Execution Timeline**: Event tracking and chronological logging
  - Breakpoint events, step events, function calls/returns
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
- KiCAD-powered component catalog with **2000+ component definitions**:
  - Arduino boards (Uno, Mega, Nano, etc.)
  - LEDs, resistors, capacitors, inductors, transistors, diodes
  - Integrated circuits (logic gates, op-amps, timers, microcontrollers)
  - Sensors (temperature, motion, light, gas, humidity)
  - Motors (DC, servo, stepper)
  - Buttons, switches, potentiometers, breadboards
  - Connectors, displays, and communication modules
- Wire connections with validation
- Pin type checking (power, ground, signal, analog, digital)
- Circuit save/load functionality
- **Electrical Rules Checking (ERC)**:
  - Unconnected power/ground pin detection
  - Floating input detection
  - Conflicting driver detection
  - Connection graph analysis
- **Multi-sheet hierarchical designs**: Support for complex circuits with sub-sheets
- Component property editing and annotation

### Professional Tools

#### Version Control
- **Full Git Integration**:
  - Stage, commit, push, pull operations
  - Branch management
  - Commit history visualization
  - Visual Git panel
- Built-in GitPython support

#### Real-Time Collaboration
- Collaborative editing sessions with multiple collaboration modes:
  - Offline mode for local development
  - Peer-to-peer for direct connections
  - Server-based for centralized coordination
- **Operational Transformation**: Advanced conflict resolution for concurrent edits
- Text change synchronization with real-time updates
- Cursor position tracking and presence indicators
- Built-in chat messaging with message history
- Project sharing (public/private)
- User roles (Owner, Editor, Viewer) with permission management
- Collaborator presence tracking and last active status
- Session management and coordination

#### Unit Testing Framework
- **Multiple Framework Support**: GoogleTest, Unity, AUnit
- Host-based and on-device testing with automatic test discovery
- **15 Assertion Types**: equal, not_equal, true, false, null, not_null, greater, less, greater_or_equal, less_or_equal, near, throws, no_throw, contains, matches
- **Mock Function System**: Create and manage mock functions for unit testing
- Code coverage reporting with detailed metrics
- JUnit XML export for CI integration
- Test result aggregation and performance metrics
- Test case management with status tracking (pending, running, passed, failed, skipped, error)
- Multiple test types: unit, integration, functional, hardware

#### CI/CD Integration
- **Multi-Platform Support**:
  - GitHub Actions
  - GitLab CI
  - Jenkins
  - Travis CI
  - CircleCI
  - Azure Pipelines
- Automatic pipeline configuration generation
- Build status monitoring with real-time updates
- Pipeline triggering from IDE
- Build job management and tracking
- Artifact management and storage
- Multiple deployment environments (development, staging, production, testing)
- Build log access and analysis
- Automated testing integration in pipelines

#### Performance Analysis
- **Performance Profiler**:
  - Function-level execution time profiling
  - Call count and statistics tracking
  - CPU cycle counting
  - Self vs total time tracking
  - Bottleneck identification
  - Memory allocation tracking
  - Optimization suggestions with actionable recommendations
  - Profile comparison for before/after analysis
  - Multiple profiling modes: host-based, on-device, simulation
- **Power Consumption Analyzer**:
  - Real-time current measurement (INA219/INA260 support)
  - Voltage and power tracking (mW)
  - Energy accumulation in millijoules (mJ)
  - Session phase tracking (upload, runtime)
  - Session stage monitoring (idle, compile, upload, running, cool_down)
  - Average and peak power calculation
  - Sleep mode analysis
  - Battery life estimation based on usage patterns
  - Load profile estimation
  - Power optimization suggestions
- **Hardware-in-Loop (HIL) Testing**:
  - Automated hardware test execution
  - Test fixture management and configuration
  - **8 Signal Types**: digital, analog, PWM, serial, I2C, SPI, power, custom
  - Signal direction configuration (input, output, bidirectional)
  - Test step execution with validators
  - Signal generation and capture
  - Multi-board test coordination
  - Test result capturing and measurement
  - Automated test workflows

#### Plugin System
- Extensible plugin architecture with lifecycle management
- Plugin discovery and automatic loading
- Comprehensive Plugin API with IDE instance access
- Install from ZIP packages
- Example plugin included for reference
- **8 Supported Plugin Types**:
  - Tool (custom utilities and features)
  - Editor (code editing enhancements)
  - Compiler (custom compilation workflows)
  - Library (library management extensions)
  - Theme (visual customization)
  - Export (custom export formats)
  - Debugger (debugging tools and protocols)
  - Language (multi-language support)
- Plugin dependency resolution and version constraints
- Command and menu integration
- Panel and widget registration
- Event handler support
- Enable/disable toggles for installed plugins

#### System Utilities
- **Background Updater**: Automatic IDE update checking
- **Offline Detection**: Smart offline mode detection and handling
- **Git Diff Visualization**: Enhanced diff display for version control
- **Download Manager**: Multi-mirror downloads with checksum verification
- **Index Updater**: Automatic board and library index synchronization

#### Import/Export Features
- **Project Import**: Arduino sketch import and example loading
- **Library Installation**: ZIP library installation with validation
- **Plugin Installation**: ZIP plugin packaging and installation
- **Data Export**:
  - JUnit XML export for test results
  - CSV export for serial plotter data
  - Circuit design save/load (JSON format)
  - Block programming project save/load
- **Board Package Management**: Install boards from package repositories
- **Arduino CLI Integration**: Seamless binary distribution

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
- **Board Information Panel**: Comprehensive hardware specifications display
  - Core specs (CPU, clock, flash, RAM, voltage, digital/PWM pins)
  - Connectivity features (WiFi, Bluetooth, USB support)
  - Advanced features (ADC resolution, DAC, touch pins, RTC, sleep mode)
  - Power consumption metrics (typical and maximum)
- Console panel for build output
- Variable watch panel
- Status bar with real-time information
- Window state persistence
- Keyboard shortcuts for common operations
- **Quick Actions Panel**: Fast access to frequently used operations
- **Context Panel**: Context-aware tools for different editor modes
- **Pin Usage Panel**: Visual pin usage tracking and availability
- **Onboarding Wizard**: Guided first-time setup and feature introduction
- **Preferences Dialog**: Comprehensive application settings and configuration
- **Example Templates**: Pre-built project templates
  - Basic sketch structure
  - Button control
  - Sensor reading
  - LED patterns
  - Serial communication examples

---

## Feature Matrix

### Development Tools
| Category | Features | Count |
|----------|----------|-------|
| **Editor** | Syntax highlighting, IntelliSense, snippets, minimap, breadcrumbs, find/replace | 10+ features |
| **Code Intelligence** | Contextual help, inline hints, error recovery, code suggestions | 6+ analyzers |
| **Build System** | Arduino CLI, library manager, board manager, custom configs | 4 systems |
| **Serial Tools** | Monitor, plotter, data logging, CSV export | 4 tools |

### Advanced Features
| Category | Features | Count |
|----------|----------|-------|
| **Debugging** | GDB/MI protocol, breakpoints, call stack, memory profiler, execution timeline | 7+ panels |
| **Visual Tools** | Block programming (50+ blocks), circuit design (2000+ components), ERC validation | 3 editors |
| **Testing** | Unit tests (3 frameworks), HIL testing (8 signal types), 15 assertion types | 26+ capabilities |
| **Analysis** | Performance profiler, power analyzer, code quality metrics | 3 profilers |

### Professional Tools
| Category | Features | Count |
|----------|----------|-------|
| **Version Control** | Git integration, diff visualization, branch management | Full Git support |
| **Collaboration** | Real-time editing, operational transformation, chat, 3 user roles | 6+ features |
| **CI/CD** | 6 platform support, pipeline generation, 4 deployment environments | 10+ features |
| **Extensibility** | 8 plugin types, dependency resolution, API access | Full plugin system |

### User Experience
| Category | Features | Count |
|----------|----------|-------|
| **Interface** | 41 UI modules, dockable panels, 3 themes, onboarding wizard | 15+ panels |
| **Workflow** | Quick actions, context panel, preferences, templates | 10+ tools |
| **Import/Export** | Arduino sketches, ZIP packages, JUnit XML, CSV data | 8+ formats |

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
│   ├── ui/                   # User interface components (41 modules)
│   │   ├── main_window.py    # Central application window
│   │   ├── code_editor.py    # Advanced code editor with minimap
│   │   ├── breadcrumb_bar.py # Navigation breadcrumb
│   │   ├── code_minimap.py   # Code overview minimap
│   │   ├── serial_monitor.py # Serial communication
│   │   ├── plotter_panel.py  # Real-time data plotting
│   │   ├── debug_toolbar.py  # Debug controls
│   │   ├── debug_workspace_dialog.py # Complete debug workspace
│   │   ├── circuit_editor.py # Circuit designer with ERC
│   │   ├── visual_programming_editor.py # Block-based programming
│   │   ├── git_panel.py      # Git version control
│   │   ├── collaboration_panel.py # Real-time collaboration
│   │   ├── code_quality_panel.py # Code quality metrics
│   │   ├── unit_testing_panel.py # Unit testing interface
│   │   ├── cicd_panel.py     # CI/CD pipeline management
│   │   ├── hil_testing_dialog.py # HIL testing interface
│   │   ├── power_analyzer_dialog.py # Power analysis
│   │   ├── performance_profiler_ui.py # Performance profiling
│   │   ├── plugin_manager.py # Plugin management
│   │   ├── onboarding_wizard.py # First-time setup
│   │   └── ...               # 20+ more UI components
│   │
│   ├── services/             # Business logic layer (29 modules)
│   │   ├── board_manager.py  # Board management
│   │   ├── library_manager.py # Library operations
│   │   ├── debug_service.py  # GDB/MI debugging engine
│   │   ├── git_service.py    # Version control
│   │   ├── collaboration_service.py # Real-time collaboration
│   │   ├── circuit_service.py # Circuit design and validation
│   │   ├── visual_programming_service.py # Block programming
│   │   ├── unit_testing_service.py # Unit testing framework
│   │   ├── cicd_service.py   # CI/CD integration
│   │   ├── performance_profiler_service.py # Performance profiling
│   │   ├── power_analyzer_service.py # Power analysis
│   │   ├── hil_testing_service.py # HIL testing
│   │   ├── plugin_system.py  # Plugin architecture
│   │   ├── contextual_help_service.py # Code intelligence
│   │   ├── error_recovery.py # Smart error recovery
│   │   └── ...               # 14+ more services
│   │
│   ├── models/               # Data models and structures
│   │   ├── board.py          # Board model with specifications
│   │   ├── library.py        # Library model
│   │   ├── package.py        # Package model
│   │   └── circuit_domain.py # Circuit design models
│   │
│   ├── resources/            # Templates and resources
│   │   ├── snippets/         # Code snippets library
│   │   │   └── arduino_snippets.json # Organized snippet database
│   │   └── templates/        # Project templates (.ino files)
│   │
│   ├── cores/                # Arduino core definitions
│   │
│   ├── data/                 # Built-in reference databases
│   │   ├── arduino_api_reference.py # Arduino function reference
│   │   └── cpp_reference.py # C++ language reference
│   │
│   ├── eeschema/             # Circuit schematic infrastructure
│   │   ├── erc/              # Electrical Rules Checking engine
│   │   ├── sch_io/           # Schematic I/O (JSON, KiCAD formats)
│   │   └── connection_graph.py # Circuit connection analysis
│   │
│   ├── utils/                # Utility functions
│   ├── main.py               # Application entry point
│   └── config.py             # Configuration constants
│
├── tests/                    # Test suite (40+ test files)
├── scripts/                  # Utility scripts
├── docs/                     # Documentation (22+ files)
├── examples/                 # Example projects and templates
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

### Running Unit Tests

1. Open **Tools → Unit Testing Panel**
2. Select your testing framework (GoogleTest, Unity, or AUnit)
3. Add test cases with assertions
4. Configure test settings (host-based or on-device)
5. Run tests and view results with code coverage

### Analyzing Power Consumption

1. Open **Tools → Power Analyzer**
2. Connect INA219 or INA260 current sensor
3. Configure measurement settings
4. Upload and run your sketch
5. View real-time power metrics, energy usage, and battery life estimates

### Setting Up CI/CD

1. Open **Tools → CI/CD Panel**
2. Select your CI/CD platform (GitHub Actions, GitLab CI, etc.)
3. Configure build and deployment settings
4. Generate pipeline configuration
5. Monitor build status from within the IDE

### Using Code Quality Tools

1. View the **Code Quality Panel** for real-time metrics
2. Check the **Problem Panel** for errors and warnings
3. Hover over code for inline hints and suggestions
4. Follow smart error recovery suggestions for compiler errors
5. Review code suggestions for optimization opportunities

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
- **Factory Pattern**: Component creation and instantiation
- **Strategy Pattern**: Pluggable compilation and upload strategies
- **Command Pattern**: Menu actions and tool operations
- **State Pattern**: Debug states and session management

### Data Flow

```
User Input → UI Components → Services → Models → Arduino CLI/Hardware
                ↓              ↓          ↓
            Signals/Slots → Data Models → Persistence (QSettings/JSON)
```

### Data Persistence

- **QSettings**: Application preferences and window state
- **JSON Format**: Circuit designs, block projects, test configurations
- **File-based Projects**: Multi-file project organization
- **Settings Serialization**: Automatic state save/restore on startup
- **Git Integration**: Version control for project history

### Threading Model

- **Main Thread**: UI rendering and user interaction
- **Background Threads**: Download operations, compilation, uploads
- **QProcess**: External tool execution (Arduino CLI, Git, GDB)
- **QThread**: Background tasks and long-running operations
- **Signal/Slot Communication**: Thread-safe messaging between components

### Plugin Architecture

```
Plugin Manifest (JSON) → Plugin Loader → Plugin Discovery
                              ↓
                    Lifecycle Management (load/activate/deactivate)
                              ↓
                    Event Handlers → IDE Integration
                              ↓
                    Command/Menu Registration → UI Integration
```

### Circuit Design Architecture

```
Component Library (KiCAD) → Circuit Service → ERC Engine
                                  ↓
                        Connection Graph → Pin Validation
                                  ↓
                        Schematic I/O → JSON/KiCAD Format
```

---

## Statistics

- **101 Python files** (not counting test files)
- **43,116 lines of Python code**
- **2,000+ KiCAD component definitions** for circuit design
- **22 Markdown documentation files**
- **40+ test files** with comprehensive coverage
- **41 UI modules** with 92+ UI classes
- **29 service modules** providing comprehensive functionality
- **50+ visual programming blocks** across multiple categories
- **Comprehensive snippet library** with organized categories
- **5 project templates** for quick start
- **Arduino API Reference**: 100+ functions documented
- **C++ Language Reference**: 50+ data types, keywords, and operators
- **15 assertion types** for unit testing
- **8 signal types** for HIL testing
- **8 plugin types** supported
- **6 CI/CD platforms** integrated
- **3 built-in themes** with custom theme support

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
Drag-and-drop circuit design powered by KiCAD symbol libraries.

### Debug Interface
Professional debugging with breakpoints, call stack, and memory profiling.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

### Version 0.1.0 (Current)
- Initial release
- All 6 development phases completed
- 32,801+ lines of Python code
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
