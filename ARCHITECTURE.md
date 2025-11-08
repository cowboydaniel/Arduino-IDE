# Architecture Documentation

## Overview

Arduino IDE Modern is built using a modular, layered architecture that separates concerns and allows for easy extensibility.

## Technology Stack

- **Language**: Python 3.9+
- **GUI Framework**: PySide6 (Qt for Python)
- **Serial Communication**: pyserial
- **Syntax Highlighting**: Pygments (custom highlighter)
- **Version Control**: GitPython
- **Data Visualization**: pyqtgraph

## Architecture Layers

### 1. Presentation Layer (UI)

**Location**: `arduino_ide/ui/`

Responsible for all user interface components using PySide6 widgets.

#### Components:

- **MainWindow** (`main_window.py`)
  - Central application window
  - Menu bar, toolbars, status bar
  - Dock widget management
  - Tab management for multiple files
  - Window state persistence

- **CodeEditor** (`code_editor.py`)
  - QPlainTextEdit-based editor
  - Custom syntax highlighter for Arduino C/C++
  - Line number display
  - Current line highlighting
  - Auto-indentation
  - Future: Language Server Protocol client

- **SerialMonitor** (`serial_monitor.py`)
  - Multi-device serial communication
  - Auto-detection of COM ports
  - Configurable baud rates
  - Real-time data display
  - Send/receive functionality
  - Color-coded messages

- **BoardPanel** (`board_panel.py`)
  - Board type selection
  - Hardware specifications display
  - Port status
  - Pinout diagram viewer (planned)

- **ProjectExplorer** (`project_explorer.py`)
  - File tree navigation
  - Project structure display
  - File operations (planned)
  - Git integration indicators (planned)

- **ConsolePanel** (`console_panel.py`)
  - Build output display
  - Error and warning highlighting
  - Clickable error messages (planned)

- **VariableWatch** (`variable_watch.py`)
  - Debug variable monitoring
  - Real-time value updates
  - Type information display

### 2. Service Layer

**Location**: `arduino_ide/services/`

Contains business logic and hardware interaction services.

#### Services:

- **ThemeManager** (`theme_manager.py`)
  - Theme application and switching
  - Three built-in themes:
    - Dark (VS Code-inspired)
    - Light (professional)
    - High Contrast (accessibility)
  - Custom theme support (planned)
  - Theme persistence

- **BoardManager** (planned)
  - Board detection and configuration
  - Board package installation
  - Toolchain management
  - Board definitions

- **CompilerService** (planned)
  - Arduino CLI integration
  - PlatformIO backend support
  - Build system abstraction
  - Error parsing and highlighting

- **LibraryManager** (planned)
  - Library search and installation
  - Dependency resolution
  - Version management
  - Local library development

- **DebugService** (planned)
  - Remote debugging protocol
  - Breakpoint management
  - Variable inspection
  - Memory profiling

- **GitService** (planned)
  - Repository operations
  - Commit and push
  - Branch management
  - Diff visualization

### 3. Data Layer (Models)

**Location**: `arduino_ide/models/`

Data structures and business entities.

#### Models (planned):

- **Project**
  - Project metadata
  - File structure
  - Build configuration
  - Dependencies

- **Board**
  - Board specifications
  - Pin definitions
  - Memory layout
  - Upload parameters

- **Library**
  - Library metadata
  - Dependencies
  - Examples
  - Documentation

- **Sketch**
  - Source files
  - Include paths
  - Preprocessor definitions

### 4. Utility Layer

**Location**: `arduino_ide/utils/`

Helper functions and shared utilities.

#### Utilities (planned):

- **FileUtils**: File operations and path handling
- **ConfigManager**: Application settings
- **Logger**: Logging and debugging
- **Validators**: Input validation
- **Parsers**: Code parsing utilities

## Design Patterns

### 1. Model-View-Controller (MVC)
- **Model**: Data structures in `models/`
- **View**: UI components in `ui/`
- **Controller**: Services in `services/`

### 2. Singleton Pattern
- `ThemeManager`: Single instance for application-wide theme
- `ConfigManager` (planned): Global configuration
- `PluginManager` (planned): Plugin registry

### 3. Observer Pattern
- Qt's signal/slot mechanism for event handling
- UI updates on data changes
- Real-time serial monitor updates

### 4. Factory Pattern (planned)
- Board factory for creating board instances
- Editor factory for different file types
- Theme factory for custom themes

### 5. Strategy Pattern (planned)
- Compiler strategy (Arduino CLI vs PlatformIO)
- Upload strategy (serial, WiFi, bootloader)
- Parser strategy (C++, Python, Assembly)

## Data Flow

### 1. Application Startup

```
main.py
  ↓
QApplication initialization
  ↓
MainWindow creation
  ↓
UI component initialization
  ↓
Theme application
  ↓
State restoration
  ↓
Event loop
```

### 2. File Editing

```
User types in CodeEditor
  ↓
QPlainTextEdit processes input
  ↓
Syntax highlighter updates
  ↓
Auto-indentation (if applicable)
  ↓
Modified flag set
  ↓
UI updated
```

### 3. Serial Communication

```
User clicks Connect
  ↓
SerialMonitor.toggle_connection()
  ↓
serial.Serial() connection
  ↓
QTimer starts (50ms interval)
  ↓
read_serial_data() called
  ↓
Data displayed in QTextEdit
  ↓
data_received signal emitted
```

### 4. Code Compilation (planned)

```
User clicks Verify
  ↓
MainWindow.verify_sketch()
  ↓
CompilerService.compile()
  ↓
Arduino CLI invocation
  ↓
Output parsing
  ↓
Console display
  ↓
Status update
```

## Extension Points

### 1. Plugin System (planned)

```python
class Plugin:
    def activate(self):
        """Called when plugin is loaded"""
        pass

    def deactivate(self):
        """Called when plugin is unloaded"""
        pass

    def get_ui_extensions(self):
        """Return UI components to add"""
        pass
```

### 2. Custom Themes

```python
class CustomTheme:
    def get_stylesheet(self) -> str:
        """Return QSS stylesheet"""
        pass

    def get_syntax_colors(self) -> dict:
        """Return syntax highlighting colors"""
        pass
```

### 3. Custom Board Support

```python
class BoardDefinition:
    name: str
    cpu: str
    flash: str
    ram: str
    upload_protocol: str
    build_flags: List[str]
```

## Security Considerations

1. **Code Execution**
   - Sandboxed compilation
   - User permission for external tools
   - Validation of upload commands

2. **Serial Communication**
   - Permission checks for COM port access
   - Buffer overflow protection
   - Timeout handling

3. **File Operations**
   - Path traversal prevention
   - Permission validation
   - Safe temporary file handling

4. **Network Features** (planned)
   - HTTPS for remote features
   - Certificate validation
   - Secure credential storage

## Performance Optimizations

1. **Lazy Loading**
   - Load UI components on demand
   - Defer heavy initialization
   - Background service startup

2. **Caching**
   - Syntax highlighting cache
   - File system cache
   - Board definition cache

3. **Asynchronous Operations**
   - Non-blocking file I/O
   - Background compilation
   - Threaded serial communication

4. **Memory Management**
   - Proper widget cleanup
   - Signal/slot disconnection
   - Resource disposal

## Testing Strategy

### 1. Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Focus on business logic

### 2. Integration Tests
- Test component interactions
- Real serial communication tests
- File system operations

### 3. UI Tests
- Automated UI interaction
- Screenshot comparisons
- Accessibility validation

### 4. Performance Tests
- Large file handling
- Memory leak detection
- Responsiveness benchmarks

## Deployment

### 1. Package Installation
```bash
pip install arduino-ide-modern
```

### 2. Standalone Executable
- PyInstaller for Windows/Linux/macOS
- Single-file distribution
- Embedded Python runtime

### 3. Docker Container (planned)
- Isolated environment
- Reproducible builds
- Cloud IDE support

## Future Architecture Enhancements

1. **Language Server Protocol**
   - clangd integration for C/C++
   - Real-time diagnostics
   - Advanced refactoring

2. **Web-based IDE** (long-term)
   - Browser-based interface
   - WebSocket serial communication
   - Cloud compilation

3. **Microservices** (enterprise)
   - Separate compilation service
   - Board management service
   - Collaboration service

4. **AI Integration**
   - Code completion with ML
   - Bug detection
   - Optimization suggestions

---

This architecture is designed to be:
- **Modular**: Easy to extend and modify
- **Testable**: Components can be tested independently
- **Maintainable**: Clear separation of concerns
- **Scalable**: Ready for future enhancements
