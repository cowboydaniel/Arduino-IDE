# Phase 4 Debugging Features - Integration Guide

This document describes the debugging features implemented in Phase 4 and how to integrate them into the main application.

## Overview

Phase 4 implements comprehensive debugging capabilities:

1. **Remote debugging over serial** - Debug protocol communication
2. **Breakpoint support** - Set/remove breakpoints in code editor
3. **Variable inspection** - Watch and inspect variables in real-time
4. **Memory profiler** - Visualize RAM, Flash, Stack, and Heap usage
5. **Execution timeline** - Track execution events chronologically

## New Components

### 1. Debug Service (`arduino_ide/services/debug_service.py`)

Core service that manages debugging sessions.

**Features:**
- GDB and serial debug protocol support
- Breakpoint management
- Variable inspection and watching
- Call stack tracking
- Memory profiling
- Execution timeline recording

**Usage:**
```python
from arduino_ide.services.debug_service import DebugService

# Create service
debug_service = DebugService()

# Connect via serial
debug_service.connect_serial_debug(port="/dev/ttyUSB0", baud_rate=115200)

# Or connect via GDB
debug_service.connect_gdb(
    gdb_path="arm-none-eabi-gdb",
    elf_file="sketch.elf",
    gdb_server="localhost:3333"
)

# Control execution
debug_service.start_debugging()
debug_service.pause_execution()
debug_service.step_over()
debug_service.continue_execution()

# Manage breakpoints
debug_service.add_breakpoint(file_path="sketch.ino", line=42)
debug_service.remove_breakpoint(breakpoint_id=1)

# Watch variables
debug_service.add_watch_variable("counter")
```

### 2. UI Components

#### Breakpoints Panel (`arduino_ide/ui/breakpoints_panel.py`)

Displays all breakpoints with enable/disable controls.

**Integration:**
```python
from arduino_ide.ui.breakpoints_panel import BreakpointsPanel

breakpoints_panel = BreakpointsPanel(debug_service)
breakpoints_panel.breakpoint_activated.connect(navigate_to_location)
```

#### Call Stack Panel (`arduino_ide/ui/call_stack_panel.py`)

Shows the call stack during debugging.

**Integration:**
```python
from arduino_ide.ui.call_stack_panel import CallStackPanel

call_stack_panel = CallStackPanel(debug_service)
call_stack_panel.location_activated.connect(navigate_to_location)
```

#### Memory Panel (`arduino_ide/ui/memory_panel.py`)

Visualizes memory usage with progress bars.

**Integration:**
```python
from arduino_ide.ui.memory_panel import MemoryPanel

memory_panel = MemoryPanel(debug_service)
memory_panel.set_auto_refresh_interval(1000)  # 1 second
```

#### Execution Timeline (`arduino_ide/ui/execution_timeline.py`)

Chronological view of execution events.

**Integration:**
```python
from arduino_ide.ui.execution_timeline import ExecutionTimelinePanel

timeline_panel = ExecutionTimelinePanel(debug_service)
```

#### Enhanced Variable Watch (`arduino_ide/ui/variable_watch.py`)

Now integrated with debug service for real-time variable inspection.

**Updated initialization:**
```python
from arduino_ide.ui.variable_watch import VariableWatch

variable_watch = VariableWatch(debug_service)
```

#### Breakpoint Gutter (`arduino_ide/ui/breakpoint_gutter.py`)

Adds breakpoint indicators to code editor.

**Integration with code editor:**
```python
from arduino_ide.ui.breakpoint_gutter import install_breakpoint_gutter

# Install into existing code editor
bp_gutter = install_breakpoint_gutter(code_editor, debug_service)

# Set file path when file is opened
bp_gutter.set_file_path(file_path)

# Connect signals
bp_gutter.breakpoint_toggled.connect(on_breakpoint_toggled)
```

#### Debug Toolbar (`arduino_ide/ui/debug_toolbar.py`)

Toolbar with debug controls (Start/Stop, Step, Pause/Continue).

**Integration:**
```python
from arduino_ide.ui.debug_toolbar import DebugToolbar

debug_toolbar = DebugToolbar(debug_service)
main_window.addToolBar(debug_toolbar)

# Connect signals
debug_toolbar.start_debug_requested.connect(start_debug_session)
debug_toolbar.stop_debug_requested.connect(stop_debug_session)
```

### 3. CLI Runner Extensions

Added debug compilation methods to `arduino_ide/services/cli_runner.py`:

```python
# Compile with debug symbols
cli_runner.run_debug_compile(
    sketch_path="sketch.ino",
    fqbn="arduino:avr:uno",
    build_path="/tmp/build"
)

# Upload debug build
cli_runner.run_debug_upload(
    sketch_path="sketch.ino",
    fqbn="arduino:avr:uno",
    port="/dev/ttyUSB0"
)
```

## Integration Steps for Main Window

### Step 1: Import Components

Add imports to `main_window.py`:

```python
from arduino_ide.services.debug_service import DebugService
from arduino_ide.ui.debug_toolbar import DebugToolbar
from arduino_ide.ui.breakpoints_panel import BreakpointsPanel
from arduino_ide.ui.call_stack_panel import CallStackPanel
from arduino_ide.ui.memory_panel import MemoryPanel
from arduino_ide.ui.execution_timeline import ExecutionTimelinePanel
from arduino_ide.ui.breakpoint_gutter import install_breakpoint_gutter
```

### Step 2: Initialize Debug Service

In `MainWindow.__init__()`:

```python
# Create debug service
self.debug_service = DebugService(self)

# Connect signals
self.debug_service.state_changed.connect(self._on_debug_state_changed)
self.debug_service.error_occurred.connect(self._on_debug_error)
self.debug_service.debug_output.connect(self._on_debug_output)
```

### Step 3: Create Debug UI Components

```python
# Debug toolbar
self.debug_toolbar = DebugToolbar(self.debug_service, self)
self.addToolBar(self.debug_toolbar)
self.debug_toolbar.start_debug_requested.connect(self._start_debug_session)
self.debug_toolbar.stop_debug_requested.connect(self._stop_debug_session)

# Debug panels (as dock widgets)
self.breakpoints_dock = QDockWidget("Breakpoints", self)
self.breakpoints_panel = BreakpointsPanel(self.debug_service)
self.breakpoints_dock.setWidget(self.breakpoints_panel)
self.addDockWidget(Qt.BottomDockWidgetArea, self.breakpoints_dock)

self.call_stack_dock = QDockWidget("Call Stack", self)
self.call_stack_panel = CallStackPanel(self.debug_service)
self.call_stack_dock.setWidget(self.call_stack_panel)
self.addDockWidget(Qt.RightDockWidgetArea, self.call_stack_dock)

self.memory_dock = QDockWidget("Memory", self)
self.memory_panel = MemoryPanel(self.debug_service)
self.memory_dock.setWidget(self.memory_panel)
self.addDockWidget(Qt.RightDockWidgetArea, self.memory_dock)

self.timeline_dock = QDockWidget("Execution Timeline", self)
self.timeline_panel = ExecutionTimelinePanel(self.debug_service)
self.timeline_dock.setWidget(self.timeline_panel)
self.addDockWidget(Qt.BottomDockWidgetArea, self.timeline_dock)

# Initially hide debug panels
self.breakpoints_dock.hide()
self.call_stack_dock.hide()
self.memory_dock.hide()
self.timeline_dock.hide()

# Update existing variable watch
self.variable_watch.set_debug_service(self.debug_service)
```

### Step 4: Install Breakpoint Gutter in Code Editor

When creating or opening a file in the code editor:

```python
# Install breakpoint gutter
bp_gutter = install_breakpoint_gutter(self.code_editor, self.debug_service)
bp_gutter.set_file_path(file_path)

# Connect navigation signal
bp_gutter.breakpoint_toggled.connect(self._on_breakpoint_toggled)
self.breakpoints_panel.breakpoint_activated.connect(self._navigate_to_location)
self.call_stack_panel.location_activated.connect(self._navigate_to_location)
```

### Step 5: Implement Debug Session Management

```python
def _start_debug_session(self):
    """Start a debugging session"""
    try:
        # Get current sketch and board
        sketch_path = self.get_current_sketch_path()
        fqbn = self.board_manager.get_selected_fqbn()
        port = self.board_manager.get_selected_port()

        if not all([sketch_path, fqbn, port]):
            self.show_error("Please select a board and port")
            return

        # Compile with debug symbols
        self.output_panel.clear()
        self.output_panel.append_text("Compiling for debugging...\n")

        self.cli_runner.run_debug_compile(
            sketch_path=sketch_path,
            fqbn=fqbn
        )

        # Wait for compilation to finish
        self.cli_runner.finished.connect(self._on_debug_compile_finished)

    except Exception as e:
        self.show_error(f"Failed to start debug session: {e}")


def _on_debug_compile_finished(self, exit_code: int):
    """Handle debug compilation finished"""
    if exit_code != 0:
        self.show_error("Debug compilation failed")
        return

    # Upload debug build
    self.output_panel.append_text("Uploading debug build...\n")

    sketch_path = self.get_current_sketch_path()
    fqbn = self.board_manager.get_selected_fqbn()
    port = self.board_manager.get_selected_port()

    self.cli_runner.run_debug_upload(
        sketch_path=sketch_path,
        fqbn=fqbn,
        port=port
    )

    self.cli_runner.finished.connect(self._on_debug_upload_finished)


def _on_debug_upload_finished(self, exit_code: int):
    """Handle debug upload finished"""
    if exit_code != 0:
        self.show_error("Debug upload failed")
        return

    # Connect debugger
    port = self.board_manager.get_selected_port()

    self.output_panel.append_text("Connecting debugger...\n")

    if self.debug_service.connect_serial_debug(port):
        # Show debug panels
        self.breakpoints_dock.show()
        self.call_stack_dock.show()
        self.memory_dock.show()
        self.timeline_dock.show()

        self.output_panel.append_text("Debugger connected. Ready to debug.\n")
    else:
        self.show_error("Failed to connect debugger")


def _stop_debug_session(self):
    """Stop debugging session"""
    self.debug_service.stop_debugging()

    # Hide debug panels
    self.breakpoints_dock.hide()
    self.call_stack_dock.hide()
    self.memory_dock.hide()
    self.timeline_dock.hide()

    self.output_panel.append_text("Debug session stopped.\n")


def _on_debug_state_changed(self, state):
    """Handle debug state changes"""
    # Update UI based on state
    pass


def _on_debug_error(self, error_msg: str):
    """Handle debug errors"""
    self.show_error(f"Debug error: {error_msg}")


def _on_debug_output(self, output: str):
    """Handle debug console output"""
    self.output_panel.append_text(output)


def _navigate_to_location(self, file_path: str, line: int):
    """Navigate to a specific file and line"""
    # Open file if not already open
    self.open_file(file_path)

    # Navigate to line
    cursor = self.code_editor.textCursor()
    cursor.movePosition(cursor.Start)
    for _ in range(line - 1):
        cursor.movePosition(cursor.Down)

    self.code_editor.setTextCursor(cursor)
    self.code_editor.centerCursor()
```

### Step 6: Add Debug Menu

Add a Debug menu to the menu bar:

```python
def _create_debug_menu(self):
    """Create debug menu"""
    debug_menu = self.menuBar().addMenu("Debug")

    # Start/Stop
    debug_menu.addAction(self.debug_toolbar.start_action)
    debug_menu.addAction(self.debug_toolbar.stop_action)
    debug_menu.addSeparator()

    # Step actions
    debug_menu.addAction(self.debug_toolbar.step_over_action)
    debug_menu.addAction(self.debug_toolbar.step_into_action)
    debug_menu.addAction(self.debug_toolbar.step_out_action)
    debug_menu.addSeparator()

    # Continue/Pause
    debug_menu.addAction(self.debug_toolbar.continue_action)
    debug_menu.addAction(self.debug_toolbar.pause_action)
    debug_menu.addSeparator()

    # Toggle breakpoint action
    toggle_bp_action = QAction("Toggle Breakpoint", self)
    toggle_bp_action.setShortcut(QKeySequence(Qt.Key_F9))
    toggle_bp_action.triggered.connect(self._toggle_breakpoint_at_cursor)
    debug_menu.addAction(toggle_bp_action)

    # View panels submenu
    view_menu = debug_menu.addMenu("Debug Panels")
    view_menu.addAction(self.breakpoints_dock.toggleViewAction())
    view_menu.addAction(self.call_stack_dock.toggleViewAction())
    view_menu.addAction(self.memory_dock.toggleViewAction())
    view_menu.addAction(self.timeline_dock.toggleViewAction())


def _toggle_breakpoint_at_cursor(self):
    """Toggle breakpoint at current cursor line"""
    if hasattr(self.code_editor, 'breakpoint_gutter'):
        cursor = self.code_editor.textCursor()
        line = cursor.blockNumber() + 1

        bp_gutter = self.code_editor.breakpoint_gutter
        bp_gutter.toggle_breakpoint(line)
```

## Debug Protocol

For Arduino debugging over serial, the sketch needs to implement a simple debug protocol:

### Arduino Side (Debug Stub)

```cpp
// Debug protocol commands
void handleDebugCommand(String cmd) {
  if (cmd == "DEBUG_INIT") {
    Serial.println("DBG:STATE:CONNECTED");
  }
  else if (cmd == "DEBUG_START") {
    Serial.println("DBG:STATE:RUNNING");
  }
  else if (cmd == "DEBUG_PAUSE") {
    Serial.println("DBG:STATE:PAUSED");
  }
  else if (cmd == "DEBUG_GET_VAR " + varName) {
    // Send variable value
    Serial.print("DBG:VARIABLE:");
    Serial.print(varName);
    Serial.print("=");
    Serial.print(varValue);
    Serial.print(" (");
    Serial.print(varType);
    Serial.println(")");
  }
  // ... more commands
}
```

## Testing

1. **Test Breakpoint UI**: Open a sketch, click in the gutter to add/remove breakpoints
2. **Test Debug Compilation**: Use Debug menu to compile with debug symbols
3. **Test Debug Session**: Start a debug session, verify panels appear
4. **Test Variable Inspection**: Add variables to watch, verify they update
5. **Test Memory Profiler**: Check memory usage displays correctly
6. **Test Timeline**: Verify execution events are recorded

## Future Enhancements

1. **Conditional Breakpoints**: Add dialog for setting breakpoint conditions
2. **Data Breakpoints**: Break when a variable changes
3. **Remote GDB**: Full GDB/MI protocol implementation
4. **Disassembly View**: Show assembly code during debugging
5. **Register View**: Display CPU registers
6. **Debug Configurations**: Save/load debug configurations per project

## Notes

- The debug protocol is currently designed for simple serial-based debugging
- Full GDB support requires OpenOCD or similar tool for hardware debugging
- Some Arduino boards may not support hardware debugging
- Memory profiling accuracy depends on board support

---

**Phase 4 Status**: ✅ All core debugging features implemented and ready for integration.
