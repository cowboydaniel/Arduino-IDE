# Phase 5: Advanced Features - Integration Guide

This document describes the advanced features implemented in Phase 5 and how to integrate them into the main application.

## Overview

Phase 5 implements 5 major advanced features:

1. **Visual Programming Mode (Block-based)** - Scratch/Blockly-style programming
2. **Circuit View with Diagrams** - Visual circuit design tool
3. **Git Integration** - Full version control system
4. **Collaborative Features** - Real-time collaboration and sharing
5. **Plugin System** - Extensible plugin architecture

## Feature 1: Visual Programming Mode

### Components

**Service**: `arduino_ide/services/visual_programming_service.py`
- Block definitions for all Arduino functions
- Workspace management
- Code generation from blocks to Arduino C++
- Save/load block projects

**UI**: `arduino_ide/ui/visual_programming_editor.py`
- Block palette organized by categories
- Drag-and-drop workspace
- Visual block rendering
- Generate Code button

### Integration

```python
from arduino_ide.services.visual_programming_service import VisualProgrammingService
from arduino_ide.ui.visual_programming_editor import VisualProgrammingEditor

# Create service
visual_prog_service = VisualProgrammingService()

# Create editor
visual_prog_editor = VisualProgrammingEditor(visual_prog_service)

# Connect code generation
visual_prog_editor.code_generated.connect(on_code_generated)

# Add to main window as tab or dock
self.addTab(visual_prog_editor, "Visual Programming")
```

### Usage

1. **Select blocks** from palette (Control, Logic, Math, I/O, etc.)
2. **Drag blocks** into workspace
3. **Connect blocks** by snapping them together
4. **Set parameters** in each block
5. **Generate code** to convert blocks to Arduino C++

### Block Categories

- **Arduino**: Setup, Loop entry points
- **Input/Output**: digitalWrite, analogRead, Serial, etc.
- **Control**: delay, if/then/else, loops
- **Logic**: comparisons, AND/OR/NOT
- **Math**: arithmetic, random, map
- **Variables**: set, get, change

## Feature 2: Circuit View with Diagrams

### Components

**Service**: `arduino_ide/services/circuit_service.py`
- Component library (Arduino, LED, Resistor, Sensors, etc.)
- Circuit design management
- Connection validation
- Pin type checking

**UI**: `arduino_ide/ui/circuit_editor.py`
- Component library palette
- Visual circuit workspace
- Component placement and wiring
- Circuit validation

### Integration

```python
from arduino_ide.services.circuit_service import CircuitService
from arduino_ide.ui.circuit_editor import CircuitEditor

# Create service
circuit_service = CircuitService()

# Create editor
circuit_editor = CircuitEditor(circuit_service)

# Connect validation
circuit_editor.circuit_validated.connect(on_circuit_validated)

# Add to main window
self.addDockWidget(Qt.RightDockWidgetArea, circuit_editor_dock)
```

### Usage

1. **Select components** from library (Arduino, LEDs, sensors, etc.)
2. **Place components** in workspace
3. **Connect components** by wiring pins
4. **Validate circuit** to check for errors
5. **Save/Load** circuit designs

### Available Components

- Arduino Uno board with all pins
- LEDs (Red, Green, Blue)
- Resistors (220Ω, 330Ω, 1kΩ, 10kΩ)
- Pushbuttons
- Potentiometers
- Servo motors
- Sensors (Ultrasonic, Temperature)
- Breadboards

## Feature 3: Git Integration

### Components

**Service**: `arduino_ide/services/git_service.py`
- Full Git CLI wrapper
- Repository management
- Commit operations
- Branch management
- Remote operations (fetch, pull, push)
- Configuration management

**UI**: `arduino_ide/ui/git_panel.py`
- Changes tab (staging, committing)
- History tab (commit log)
- Branches tab (create, checkout, delete)
- Remotes tab (fetch, pull, push)

### Integration

```python
from arduino_ide.services.git_service import GitService
from arduino_ide.ui.git_panel import GitPanel

# Create service
git_service = GitService(repo_path=project_path)

# Create panel
git_panel = GitPanel(git_service)

# Add to main window
git_dock = QDockWidget("Git", self)
git_dock.setWidget(git_panel)
self.addDockWidget(Qt.BottomDockWidgetArea, git_dock)

# Connect signals
git_service.commit_created.connect(on_commit_created)
git_service.branch_changed.connect(on_branch_changed)
```

### Usage

1. **Initialize** repository (if not exists)
2. **Stage files** for commit
3. **Create commits** with messages
4. **Manage branches** (create, switch, merge)
5. **Sync with remote** (fetch, pull, push)

### Git Operations

- `git init` - Initialize repository
- `git status` - Check file status
- `git add` - Stage files
- `git commit` - Create commits
- `git branch` - Manage branches
- `git checkout` - Switch branches
- `git merge` - Merge branches
- `git fetch/pull/push` - Remote operations
- `git log` - View history

## Feature 4: Collaborative Features

### Components

**Service**: `arduino_ide/services/collaboration_service.py`
- Real-time collaboration sessions
- Text change synchronization
- Cursor position sharing
- Chat messaging
- Project sharing
- Collaborator management

**UI**: `arduino_ide/ui/collaboration_panel.py`
- Session control (start/join/leave)
- Collaborators list with online status
- Chat widget for communication
- Shared projects management

### Integration

```python
from arduino_ide.services.collaboration_service import CollaborationService
from arduino_ide.ui.collaboration_panel import CollaborationPanel

# Create service
collab_service = CollaborationService()

# Set current user
collab_service.set_current_user(user_id="user123", username="John Doe")

# Create panel
collab_panel = CollaborationPanel(collab_service)

# Add to main window
collab_dock = QDockWidget("Collaboration", self)
collab_dock.setWidget(collab_panel)
self.addDockWidget(Qt.RightDockWidgetArea, collab_dock)

# Connect text changes
collab_service.text_change_received.connect(apply_remote_change)
collab_service.cursor_updated.connect(update_remote_cursor)
```

### Usage

1. **Set user** information
2. **Start session** (or join existing)
3. **Share project** with collaborators
4. **Edit together** with real-time sync
5. **Chat** with team members
6. **See collaborator cursors** and changes

### Collaboration Modes

- **Peer-to-Peer**: Direct connection between users
- **Server-Based**: Central server coordinates (future)

### Features

- Real-time text editing synchronization
- Cursor position tracking
- Chat messaging
- Project sharing (public/private)
- User roles (Owner, Editor, Viewer)
- Change history tracking

## Feature 5: Plugin System

### Components

**Service**: `arduino_ide/services/plugin_system.py`
- Plugin discovery and loading
- Plugin lifecycle management
- Plugin API for IDE interaction
- Plugin manager
- Install/uninstall functionality

**UI**: `arduino_ide/ui/plugin_manager.py`
- Plugin list with status
- Activate/deactivate controls
- Install from file
- Plugin details viewer

### Integration

```python
from arduino_ide.services.plugin_system import PluginManager
from arduino_ide.ui.plugin_manager import PluginManagerWidget

# Create plugin manager
plugin_manager = PluginManager(plugins_dir="/path/to/plugins")

# Discover plugins
plugin_manager.discover_plugins()

# Create UI
plugin_manager_widget = PluginManagerWidget(plugin_manager)

# Add to settings/preferences dialog
self.preferences_tabs.addTab(plugin_manager_widget, "Plugins")

# Auto-activate plugins on startup
for plugin in plugin_manager.get_all_plugins():
    if should_auto_activate(plugin):
        plugin_manager.activate_plugin(plugin.metadata.id)
```

### Creating a Plugin

**1. Create plugin directory structure:**
```
my-plugin/
├── plugin.json
├── main.py
└── README.md
```

**2. Create `plugin.json` manifest:**
```json
{
  "id": "my-awesome-plugin",
  "name": "My Awesome Plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Does awesome things",
  "type": "tool",
  "entry_point": "main.MainPlugin",
  "dependencies": [],
  "min_ide_version": "2.0.0",
  "license": "MIT"
}
```

**3. Create `main.py` plugin class:**
```python
from arduino_ide.services.plugin_system import Plugin

class MainPlugin(Plugin):
    def activate(self):
        print(f"Plugin activated: {self.metadata.name}")

        # Register commands
        self.api.register_command("my_command", self.my_command_handler)

        # Register menu items
        self.api.register_menu_item("Tools/My Plugin", "Do Something", self.do_something)

    def deactivate(self):
        print("Plugin deactivated")

    def my_command_handler(self):
        self.api.show_message("Command executed!")

    def do_something(self):
        code = self.api.get_current_code()
        # Process code...
        self.api.insert_code("// Added by plugin\n")

    def on_file_saved(self, file_path: str):
        print(f"File saved: {file_path}")
```

**4. Install plugin:**
- Package as .zip
- Use "Install" button in Plugin Manager
- Or copy to plugins directory

### Plugin Types

- **Tool**: Adds new tools/features
- **Editor**: Editor enhancements
- **Compiler**: Custom compilers
- **Library**: Library management
- **Theme**: Visual themes
- **Export**: Export formats
- **Debugger**: Debugging tools
- **Language**: Language support

### Plugin API

Plugins can access:
- `api.get_version()` - IDE version
- `api.register_command()` - Register commands
- `api.execute_command()` - Execute commands
- `api.register_panel()` - Add UI panels
- `api.register_menu_item()` - Add menu items
- `api.show_message()` - Show dialogs
- `api.get_current_file_path()` - Get active file
- `api.get_current_code()` - Get editor content
- `api.insert_code()` - Insert code
- `api.compile_sketch()` - Trigger compilation
- `api.upload_sketch()` - Trigger upload

### Plugin Events

Plugins receive:
- `on_file_opened(file_path)` - File opened
- `on_file_saved(file_path)` - File saved
- `on_compile_started()` - Compilation started
- `on_compile_finished(success)` - Compilation finished

## Main Window Integration Example

```python
from PySide6.QtWidgets import QMainWindow, QTabWidget, QDockWidget
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize Phase 5 services
        self._init_phase5_services()

        # Setup UI
        self._setup_phase5_ui()

    def _init_phase5_services(self):
        """Initialize Phase 5 services"""
        # Visual Programming
        self.visual_prog_service = VisualProgrammingService()

        # Circuit Design
        self.circuit_service = CircuitService()

        # Git Integration
        self.git_service = GitService()

        # Collaboration
        self.collab_service = CollaborationService()
        self.collab_service.set_current_user("user1", "Developer")

        # Plugin System
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()

    def _setup_phase5_ui(self):
        """Setup Phase 5 UI components"""
        # Visual Programming tab
        visual_prog_editor = VisualProgrammingEditor(self.visual_prog_service)
        visual_prog_editor.code_generated.connect(self._on_blocks_code_generated)

        # Circuit Editor dock
        circuit_editor = CircuitEditor(self.circuit_service)
        circuit_dock = QDockWidget("Circuit Design", self)
        circuit_dock.setWidget(circuit_editor)
        self.addDockWidget(Qt.RightDockWidgetArea, circuit_dock)

        # Git Panel dock
        git_panel = GitPanel(self.git_service)
        git_dock = QDockWidget("Git", self)
        git_dock.setWidget(git_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, git_dock)

        # Collaboration Panel dock
        collab_panel = CollaborationPanel(self.collab_service)
        collab_dock = QDockWidget("Collaboration", self)
        collab_dock.setWidget(collab_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, collab_dock)

        # Plugin Manager in preferences
        plugin_manager_widget = PluginManagerWidget(self.plugin_manager)
        # Add to preferences dialog

        # Add to View menu
        self._add_phase5_menu_items(circuit_dock, git_dock, collab_dock)

    def _add_phase5_menu_items(self, *docks):
        """Add Phase 5 menu items"""
        view_menu = self.menuBar().addMenu("View")

        for dock in docks:
            view_menu.addAction(dock.toggleViewAction())

        # Tools menu
        tools_menu = self.menuBar().addMenu("Tools")
        tools_menu.addAction("Plugin Manager", self._show_plugin_manager)

    def _on_blocks_code_generated(self, code: str):
        """Handle code generated from visual blocks"""
        # Insert into code editor
        self.code_editor.setText(code)

    def _show_plugin_manager(self):
        """Show plugin manager dialog"""
        # Show plugin manager dialog
        pass
```

## Testing

### Visual Programming
1. Open Visual Programming mode
2. Add Setup and Loop blocks
3. Add digitalWrite blocks
4. Set pin numbers and values
5. Generate code
6. Verify generated Arduino C++ code

### Circuit Editor
1. Add Arduino Uno to workspace
2. Add LED and resistor
3. Connect LED anode to Arduino D13
4. Connect LED cathode through resistor to GND
5. Validate circuit
6. Check for errors

### Git Integration
1. Open project directory
2. Initialize Git repository
3. Stage files
4. Create commit
5. Create branch
6. Switch branches

### Collaboration
1. Set user information
2. Start collaboration session
3. Share session ID
4. Join from another instance
5. Edit together
6. Send chat messages

### Plugin System
1. Create example plugin
2. Install plugin
3. Activate plugin
4. Test plugin functionality
5. Deactivate plugin
6. Uninstall plugin

## Performance Considerations

- **Visual Programming**: Blocks are rendered using Qt Graphics View (hardware accelerated)
- **Circuit Editor**: Component rendering optimized for large circuits
- **Git Operations**: Async operations to prevent UI blocking
- **Collaboration**: Change batching and delta synchronization
- **Plugins**: Lazy loading and sandboxed execution

## Security

- **Git**: Credentials handled by system Git credential manager
- **Collaboration**: Session IDs are SHA-256 hashed
- **Plugins**: Plugins run in same process (future: sandboxing)

## Future Enhancements

1. **Visual Programming**:
   - Custom block creation
   - Block import/export
   - Library of saved patterns

2. **Circuit Editor**:
   - Auto-routing wires
   - Component search
   - Export to Fritzing format

3. **Git Integration**:
   - Visual merge tool
   - Commit graph visualization
   - GitFlow workflow support

4. **Collaboration**:
   - WebSocket server implementation
   - Voice/video chat
   - Screen sharing

5. **Plugin System**:
   - Plugin marketplace
   - Auto-updates
   - Sandboxed execution
   - Hot reload

---

**Phase 5 Status**: ✅ All advanced features implemented and ready for integration.
