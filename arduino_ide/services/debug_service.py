"""
Debug Service for Arduino IDE Modern
Handles remote debugging over serial, GDB protocol, breakpoints, and variable inspection
"""

import re
import logging
from typing import Optional, Dict, List, Set, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtCore import QObject, Signal, QProcess, QTimer
import serial
import serial.tools.list_ports


logger = logging.getLogger(__name__)


class DebugState(Enum):
    """Current state of the debugger"""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RUNNING = "running"
    PAUSED = "paused"
    STEPPING = "stepping"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class BreakpointType(Enum):
    """Type of breakpoint"""
    LINE = "line"
    FUNCTION = "function"
    CONDITIONAL = "conditional"


@dataclass
class Breakpoint:
    """Represents a code breakpoint"""
    id: int
    file_path: str
    line: int
    enabled: bool = True
    breakpoint_type: BreakpointType = BreakpointType.LINE
    condition: Optional[str] = None
    hit_count: int = 0

    def __hash__(self):
        return hash((self.file_path, self.line))


@dataclass
class Variable:
    """Represents a variable in debug context"""
    name: str
    value: str
    type: str
    scope: str = "local"
    children: List['Variable'] = field(default_factory=list)
    address: Optional[str] = None

    def __repr__(self):
        return f"Variable(name={self.name}, value={self.value}, type={self.type})"


@dataclass
class StackFrame:
    """Represents a call stack frame"""
    level: int
    function: str
    file_path: Optional[str] = None
    line: Optional[int] = None
    address: Optional[str] = None

    def __repr__(self):
        return f"StackFrame(level={self.level}, func={self.function}, {self.file_path}:{self.line})"


@dataclass
class MemoryRegion:
    """Represents a memory region"""
    name: str
    start_address: int
    size: int
    used: int
    free: int

    @property
    def usage_percent(self) -> float:
        return (self.used / self.size * 100) if self.size > 0 else 0.0


@dataclass
class ExecutionEvent:
    """Represents an execution timeline event"""
    timestamp: float
    event_type: str  # 'breakpoint', 'step', 'pause', 'resume', 'function_call', 'function_return'
    location: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class DebugService(QObject):
    """
    Service for managing Arduino debugging sessions
    Supports remote debugging over serial with GDB/MI protocol
    """

    # Signals for debug events
    state_changed = Signal(DebugState)
    breakpoint_hit = Signal(Breakpoint, str, int)  # breakpoint, file, line
    breakpoint_added = Signal(Breakpoint)
    breakpoint_removed = Signal(int)  # breakpoint id
    breakpoint_updated = Signal(Breakpoint)

    variable_updated = Signal(str, Variable)  # name, variable
    variables_updated = Signal(list)  # List[Variable]

    stack_trace_updated = Signal(list)  # List[StackFrame]

    memory_updated = Signal(dict)  # Dict of memory regions

    execution_event = Signal(ExecutionEvent)

    debug_output = Signal(str)  # Debug console output
    error_occurred = Signal(str)  # Error messages


    def __init__(self, parent=None):
        super().__init__(parent)

        self._state = DebugState.IDLE
        self._gdb_process: Optional[QProcess] = None
        self._serial_connection: Optional[serial.Serial] = None

        # Breakpoint management
        self._breakpoints: Dict[int, Breakpoint] = {}
        self._next_breakpoint_id = 1
        self._breakpoint_locations: Dict[Tuple[str, int], int] = {}  # (file, line) -> id

        # Variable tracking
        self._watched_variables: Dict[str, Variable] = {}
        self._local_variables: Dict[str, Variable] = {}

        # Stack trace
        self._call_stack: List[StackFrame] = []
        self._current_frame: Optional[StackFrame] = None

        # Memory tracking
        self._memory_regions: Dict[str, MemoryRegion] = {}

        # Execution timeline
        self._execution_timeline: List[ExecutionEvent] = []
        self._timeline_max_events = 1000

        # GDB communication
        self._gdb_output_buffer = ""
        self._gdb_command_queue: List[str] = []
        self._pending_response = False

        # Polling timer for serial debugging
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll_serial_debug)
        self._poll_interval = 100  # ms

        # Current execution location
        self._current_file: Optional[str] = None
        self._current_line: Optional[int] = None

        logger.info("Debug service initialized")


    @property
    def state(self) -> DebugState:
        """Get current debug state"""
        return self._state


    def _set_state(self, new_state: DebugState):
        """Update debug state and emit signal"""
        if new_state != self._state:
            logger.info(f"Debug state: {self._state.value} -> {new_state.value}")
            self._state = new_state
            self.state_changed.emit(new_state)


    # ==================== Connection Management ====================

    def connect_serial_debug(self, port: str, baud_rate: int = 115200) -> bool:
        """
        Connect to Arduino for serial debugging
        Uses custom debug protocol over serial
        """
        try:
            self._set_state(DebugState.CONNECTING)

            # Close existing connection
            if self._serial_connection and self._serial_connection.is_open:
                self._serial_connection.close()

            # Open serial connection
            self._serial_connection = serial.Serial(
                port=port,
                baudrate=baud_rate,
                timeout=0.1,
                write_timeout=1.0
            )

            logger.info(f"Serial debug connected: {port} @ {baud_rate}")

            # Send initialization handshake
            self._send_debug_command("DEBUG_INIT")

            # Start polling for debug data
            self._poll_timer.start(self._poll_interval)

            self._set_state(DebugState.CONNECTED)
            self.debug_output.emit(f"Connected to {port} for debugging")

            return True

        except Exception as e:
            logger.error(f"Serial debug connection failed: {e}")
            self.error_occurred.emit(f"Failed to connect: {str(e)}")
            self._set_state(DebugState.ERROR)
            return False


    def connect_gdb(self, gdb_path: str, elf_file: str, gdb_server: str = "localhost:3333") -> bool:
        """
        Connect to Arduino using GDB (via OpenOCD or similar)
        """
        try:
            self._set_state(DebugState.CONNECTING)

            if self._gdb_process:
                self._gdb_process.kill()
                self._gdb_process = None

            self._gdb_process = QProcess(self)
            self._gdb_process.readyReadStandardOutput.connect(self._on_gdb_output)
            self._gdb_process.readyReadStandardError.connect(self._on_gdb_error)
            self._gdb_process.finished.connect(self._on_gdb_finished)

            # Start GDB with MI interface
            args = [
                "-q",  # Quiet mode
                "-interpreter=mi",  # Machine interface
                elf_file
            ]

            self._gdb_process.start(gdb_path, args)

            if not self._gdb_process.waitForStarted(3000):
                raise Exception("GDB process failed to start")

            logger.info(f"GDB started: {gdb_path}")

            # Connect to GDB server
            self._send_gdb_command(f"target remote {gdb_server}")

            self._set_state(DebugState.CONNECTED)
            self.debug_output.emit(f"GDB connected to {gdb_server}")

            return True

        except Exception as e:
            logger.error(f"GDB connection failed: {e}")
            self.error_occurred.emit(f"Failed to connect GDB: {str(e)}")
            self._set_state(DebugState.ERROR)
            return False


    def disconnect(self):
        """Disconnect from debugging session"""
        try:
            # Stop polling
            self._poll_timer.stop()

            # Close serial connection
            if self._serial_connection and self._serial_connection.is_open:
                self._send_debug_command("DEBUG_EXIT")
                self._serial_connection.close()
                self._serial_connection = None

            # Terminate GDB
            if self._gdb_process:
                self._send_gdb_command("quit")
                self._gdb_process.waitForFinished(1000)
                self._gdb_process.kill()
                self._gdb_process = None

            # Clear state
            self._call_stack.clear()
            self._current_frame = None
            self._current_file = None
            self._current_line = None

            self._set_state(DebugState.DISCONNECTED)
            self.debug_output.emit("Debug session disconnected")

            logger.info("Debug session disconnected")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")


    # ==================== Breakpoint Management ====================

    def add_breakpoint(self, file_path: str, line: int, condition: Optional[str] = None) -> Optional[Breakpoint]:
        """Add a breakpoint at the specified location"""
        try:
            # Check if breakpoint already exists
            location_key = (file_path, line)
            if location_key in self._breakpoint_locations:
                existing_id = self._breakpoint_locations[location_key]
                logger.warning(f"Breakpoint already exists at {file_path}:{line}")
                return self._breakpoints[existing_id]

            # Create new breakpoint
            bp_id = self._next_breakpoint_id
            self._next_breakpoint_id += 1

            bp_type = BreakpointType.CONDITIONAL if condition else BreakpointType.LINE
            breakpoint = Breakpoint(
                id=bp_id,
                file_path=file_path,
                line=line,
                enabled=True,
                breakpoint_type=bp_type,
                condition=condition
            )

            # Store breakpoint
            self._breakpoints[bp_id] = breakpoint
            self._breakpoint_locations[location_key] = bp_id

            # Send to debugger if connected
            if self._state in (DebugState.CONNECTED, DebugState.PAUSED, DebugState.RUNNING):
                self._sync_breakpoint_to_debugger(breakpoint)

            self.breakpoint_added.emit(breakpoint)
            logger.info(f"Breakpoint added: {file_path}:{line} (id={bp_id})")

            return breakpoint

        except Exception as e:
            logger.error(f"Failed to add breakpoint: {e}")
            self.error_occurred.emit(f"Failed to add breakpoint: {str(e)}")
            return None


    def remove_breakpoint(self, breakpoint_id: int) -> bool:
        """Remove a breakpoint by ID"""
        try:
            if breakpoint_id not in self._breakpoints:
                logger.warning(f"Breakpoint {breakpoint_id} not found")
                return False

            breakpoint = self._breakpoints[breakpoint_id]

            # Remove from tracking
            location_key = (breakpoint.file_path, breakpoint.line)
            del self._breakpoints[breakpoint_id]
            del self._breakpoint_locations[location_key]

            # Send to debugger if connected
            if self._state in (DebugState.CONNECTED, DebugState.PAUSED, DebugState.RUNNING):
                self._remove_breakpoint_from_debugger(breakpoint)

            self.breakpoint_removed.emit(breakpoint_id)
            logger.info(f"Breakpoint removed: {breakpoint_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to remove breakpoint: {e}")
            return False


    def toggle_breakpoint(self, breakpoint_id: int) -> bool:
        """Enable or disable a breakpoint"""
        try:
            if breakpoint_id not in self._breakpoints:
                return False

            breakpoint = self._breakpoints[breakpoint_id]
            breakpoint.enabled = not breakpoint.enabled

            # Update in debugger if connected
            if self._state in (DebugState.CONNECTED, DebugState.PAUSED, DebugState.RUNNING):
                if breakpoint.enabled:
                    self._sync_breakpoint_to_debugger(breakpoint)
                else:
                    self._remove_breakpoint_from_debugger(breakpoint)

            self.breakpoint_updated.emit(breakpoint)
            logger.info(f"Breakpoint {breakpoint_id} {'enabled' if breakpoint.enabled else 'disabled'}")

            return True

        except Exception as e:
            logger.error(f"Failed to toggle breakpoint: {e}")
            return False


    def get_breakpoints(self, file_path: Optional[str] = None) -> List[Breakpoint]:
        """Get all breakpoints, optionally filtered by file"""
        if file_path:
            return [bp for bp in self._breakpoints.values() if bp.file_path == file_path]
        return list(self._breakpoints.values())


    def get_breakpoint_at_line(self, file_path: str, line: int) -> Optional[Breakpoint]:
        """Get breakpoint at specific location"""
        location_key = (file_path, line)
        bp_id = self._breakpoint_locations.get(location_key)
        return self._breakpoints.get(bp_id) if bp_id else None


    # ==================== Execution Control ====================

    def start_debugging(self) -> bool:
        """Start or resume debugging execution"""
        try:
            if self._state == DebugState.CONNECTED:
                # Initial start
                self._send_debug_command("DEBUG_START")
                self._set_state(DebugState.RUNNING)
                self._add_execution_event("resume", "Debug session started")
                return True

            elif self._state == DebugState.PAUSED:
                # Resume from pause
                return self.continue_execution()

            else:
                logger.warning(f"Cannot start debugging from state: {self._state}")
                return False

        except Exception as e:
            logger.error(f"Failed to start debugging: {e}")
            return False


    def continue_execution(self) -> bool:
        """Continue execution after pause/breakpoint"""
        try:
            if self._state != DebugState.PAUSED:
                logger.warning("Not paused, cannot continue")
                return False

            self._send_debug_command("DEBUG_CONTINUE")
            self._set_state(DebugState.RUNNING)
            self._add_execution_event("resume", "Execution continued")

            return True

        except Exception as e:
            logger.error(f"Failed to continue: {e}")
            return False


    def pause_execution(self) -> bool:
        """Pause execution"""
        try:
            if self._state != DebugState.RUNNING:
                logger.warning("Not running, cannot pause")
                return False

            self._send_debug_command("DEBUG_PAUSE")
            self._set_state(DebugState.PAUSED)
            self._add_execution_event("pause", "Execution paused")

            # Update state
            self._refresh_debug_state()

            return True

        except Exception as e:
            logger.error(f"Failed to pause: {e}")
            return False


    def step_over(self) -> bool:
        """Step over current line"""
        try:
            if self._state != DebugState.PAUSED:
                logger.warning("Not paused, cannot step")
                return False

            self._send_debug_command("DEBUG_STEP_OVER")
            self._set_state(DebugState.STEPPING)
            self._add_execution_event("step", "Step over")

            return True

        except Exception as e:
            logger.error(f"Failed to step over: {e}")
            return False


    def step_into(self) -> bool:
        """Step into function call"""
        try:
            if self._state != DebugState.PAUSED:
                logger.warning("Not paused, cannot step")
                return False

            self._send_debug_command("DEBUG_STEP_INTO")
            self._set_state(DebugState.STEPPING)
            self._add_execution_event("step", "Step into")

            return True

        except Exception as e:
            logger.error(f"Failed to step into: {e}")
            return False


    def step_out(self) -> bool:
        """Step out of current function"""
        try:
            if self._state != DebugState.PAUSED:
                logger.warning("Not paused, cannot step")
                return False

            self._send_debug_command("DEBUG_STEP_OUT")
            self._set_state(DebugState.STEPPING)
            self._add_execution_event("step", "Step out")

            return True

        except Exception as e:
            logger.error(f"Failed to step out: {e}")
            return False


    def stop_debugging(self) -> bool:
        """Stop debugging session"""
        try:
            self._send_debug_command("DEBUG_STOP")
            self.disconnect()
            return True

        except Exception as e:
            logger.error(f"Failed to stop debugging: {e}")
            return False


    # ==================== Variable Inspection ====================

    def add_watch_variable(self, variable_name: str) -> bool:
        """Add a variable to watch list"""
        try:
            if variable_name in self._watched_variables:
                logger.warning(f"Variable {variable_name} already watched")
                return False

            # Request variable value
            self._send_debug_command(f"DEBUG_GET_VAR {variable_name}")

            # Create placeholder
            var = Variable(name=variable_name, value="<pending>", type="unknown")
            self._watched_variables[variable_name] = var

            logger.info(f"Added watch variable: {variable_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to add watch variable: {e}")
            return False


    def remove_watch_variable(self, variable_name: str) -> bool:
        """Remove a variable from watch list"""
        if variable_name in self._watched_variables:
            del self._watched_variables[variable_name]
            logger.info(f"Removed watch variable: {variable_name}")
            return True
        return False


    def get_watched_variables(self) -> List[Variable]:
        """Get all watched variables"""
        return list(self._watched_variables.values())


    def get_local_variables(self) -> List[Variable]:
        """Get local variables in current scope"""
        return list(self._local_variables.values())


    def evaluate_expression(self, expression: str) -> Optional[str]:
        """Evaluate an expression in current context"""
        try:
            self._send_debug_command(f"DEBUG_EVAL {expression}")
            # Result will come asynchronously
            return None
        except Exception as e:
            logger.error(f"Failed to evaluate expression: {e}")
            return None


    # ==================== Stack Trace ====================

    def get_call_stack(self) -> List[StackFrame]:
        """Get current call stack"""
        return self._call_stack.copy()


    def set_current_frame(self, frame_level: int) -> bool:
        """Set active stack frame for variable inspection"""
        try:
            if 0 <= frame_level < len(self._call_stack):
                self._current_frame = self._call_stack[frame_level]
                self._send_debug_command(f"DEBUG_SELECT_FRAME {frame_level}")
                self._refresh_local_variables()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to set frame: {e}")
            return False


    # ==================== Memory Profiling ====================

    def get_memory_info(self) -> Dict[str, MemoryRegion]:
        """Get memory region information"""
        return self._memory_regions.copy()


    def refresh_memory_info(self):
        """Request updated memory information"""
        self._send_debug_command("DEBUG_MEMORY_INFO")


    # ==================== Execution Timeline ====================

    def get_execution_timeline(self) -> List[ExecutionEvent]:
        """Get execution timeline events"""
        return self._execution_timeline.copy()


    def clear_execution_timeline(self):
        """Clear execution timeline"""
        self._execution_timeline.clear()
        logger.info("Execution timeline cleared")


    def _add_execution_event(self, event_type: str, location: Optional[str] = None, data: Optional[Dict] = None):
        """Add event to execution timeline"""
        import time

        event = ExecutionEvent(
            timestamp=time.time(),
            event_type=event_type,
            location=location,
            data=data
        )

        self._execution_timeline.append(event)

        # Limit timeline size
        if len(self._execution_timeline) > self._timeline_max_events:
            self._execution_timeline.pop(0)

        self.execution_event.emit(event)


    # ==================== Debug Protocol Communication ====================

    def _send_debug_command(self, command: str):
        """Send debug command over serial"""
        try:
            if self._serial_connection and self._serial_connection.is_open:
                cmd_bytes = f"{command}\n".encode('utf-8')
                self._serial_connection.write(cmd_bytes)
                logger.debug(f"Debug command sent: {command}")
            elif self._gdb_process:
                self._send_gdb_command(command)
        except Exception as e:
            logger.error(f"Failed to send debug command: {e}")


    def _send_gdb_command(self, command: str):
        """Send GDB command"""
        try:
            if self._gdb_process and self._gdb_process.state() == QProcess.Running:
                cmd = f"{command}\n"
                self._gdb_process.write(cmd.encode('utf-8'))
                logger.debug(f"GDB command: {command}")
        except Exception as e:
            logger.error(f"Failed to send GDB command: {e}")


    def _poll_serial_debug(self):
        """Poll serial connection for debug data"""
        try:
            if not self._serial_connection or not self._serial_connection.is_open:
                return

            # Read available data
            if self._serial_connection.in_waiting > 0:
                data = self._serial_connection.read(self._serial_connection.in_waiting)
                self._process_debug_data(data.decode('utf-8', errors='ignore'))

        except Exception as e:
            logger.error(f"Error polling serial debug: {e}")


    def _process_debug_data(self, data: str):
        """Process incoming debug data"""
        try:
            lines = data.strip().split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                self.debug_output.emit(line)

                # Parse debug messages
                if line.startswith("DBG:"):
                    self._parse_debug_message(line[4:])

        except Exception as e:
            logger.error(f"Error processing debug data: {e}")


    def _parse_debug_message(self, message: str):
        """Parse structured debug messages"""
        try:
            parts = message.split(':', 1)
            if len(parts) < 2:
                return

            msg_type = parts[0].strip()
            msg_data = parts[1].strip()

            if msg_type == "BREAKPOINT":
                self._handle_breakpoint_hit(msg_data)
            elif msg_type == "VARIABLE":
                self._handle_variable_update(msg_data)
            elif msg_type == "STACK":
                self._handle_stack_update(msg_data)
            elif msg_type == "MEMORY":
                self._handle_memory_update(msg_data)
            elif msg_type == "STATE":
                self._handle_state_change(msg_data)

        except Exception as e:
            logger.error(f"Error parsing debug message: {e}")


    def _handle_breakpoint_hit(self, data: str):
        """Handle breakpoint hit event"""
        try:
            # Parse: "file:line"
            parts = data.split(':')
            if len(parts) >= 2:
                file_path = parts[0]
                line = int(parts[1])

                self._current_file = file_path
                self._current_line = line

                # Find breakpoint
                bp = self.get_breakpoint_at_line(file_path, line)

                if bp:
                    bp.hit_count += 1
                    self.breakpoint_hit.emit(bp, file_path, line)
                    self._add_execution_event("breakpoint", f"{file_path}:{line}")

                self._set_state(DebugState.PAUSED)
                self._refresh_debug_state()

        except Exception as e:
            logger.error(f"Error handling breakpoint hit: {e}")


    def _handle_variable_update(self, data: str):
        """Handle variable value update"""
        try:
            # Parse: "name=value (type)"
            match = re.match(r'(\w+)\s*=\s*(.+?)\s*\((\w+)\)', data)
            if match:
                name = match.group(1)
                value = match.group(2)
                var_type = match.group(3)

                var = Variable(name=name, value=value, type=var_type)

                if name in self._watched_variables:
                    self._watched_variables[name] = var
                    self.variable_updated.emit(name, var)

                self._local_variables[name] = var

        except Exception as e:
            logger.error(f"Error handling variable update: {e}")


    def _handle_stack_update(self, data: str):
        """Handle stack trace update"""
        try:
            # Parse stack frames
            self._call_stack.clear()

            frames = data.split(';')
            for i, frame_data in enumerate(frames):
                if not frame_data:
                    continue

                # Parse: "function@file:line"
                parts = frame_data.split('@')
                function = parts[0]

                file_path = None
                line = None

                if len(parts) > 1:
                    loc_parts = parts[1].split(':')
                    file_path = loc_parts[0]
                    if len(loc_parts) > 1:
                        line = int(loc_parts[1])

                frame = StackFrame(
                    level=i,
                    function=function,
                    file_path=file_path,
                    line=line
                )
                self._call_stack.append(frame)

            if self._call_stack:
                self._current_frame = self._call_stack[0]

            self.stack_trace_updated.emit(self._call_stack)

        except Exception as e:
            logger.error(f"Error handling stack update: {e}")


    def _handle_memory_update(self, data: str):
        """Handle memory information update"""
        try:
            # Parse: "SRAM:2048:512;FLASH:32768:16384"
            regions = data.split(';')

            for region_data in regions:
                parts = region_data.split(':')
                if len(parts) >= 3:
                    name = parts[0]
                    size = int(parts[1])
                    used = int(parts[2])

                    region = MemoryRegion(
                        name=name,
                        start_address=0,
                        size=size,
                        used=used,
                        free=size - used
                    )
                    self._memory_regions[name] = region

            self.memory_updated.emit(self._memory_regions)

        except Exception as e:
            logger.error(f"Error handling memory update: {e}")


    def _handle_state_change(self, data: str):
        """Handle debugger state change"""
        try:
            if data == "RUNNING":
                self._set_state(DebugState.RUNNING)
            elif data == "PAUSED":
                self._set_state(DebugState.PAUSED)
            elif data == "STOPPED":
                self._set_state(DebugState.IDLE)
        except Exception as e:
            logger.error(f"Error handling state change: {e}")


    def _refresh_debug_state(self):
        """Refresh all debug state (variables, stack, memory)"""
        self._send_debug_command("DEBUG_GET_STACK")
        self._send_debug_command("DEBUG_GET_LOCALS")
        self.refresh_memory_info()


    def _refresh_local_variables(self):
        """Refresh local variables in current frame"""
        self._send_debug_command("DEBUG_GET_LOCALS")


    def _sync_breakpoint_to_debugger(self, breakpoint: Breakpoint):
        """Sync breakpoint to debugger"""
        cmd = f"DEBUG_SET_BREAKPOINT {breakpoint.file_path}:{breakpoint.line}"
        if breakpoint.condition:
            cmd += f" IF {breakpoint.condition}"
        self._send_debug_command(cmd)


    def _remove_breakpoint_from_debugger(self, breakpoint: Breakpoint):
        """Remove breakpoint from debugger"""
        cmd = f"DEBUG_CLEAR_BREAKPOINT {breakpoint.file_path}:{breakpoint.line}"
        self._send_debug_command(cmd)


    # ==================== GDB Process Handlers ====================

    def _on_gdb_output(self):
        """Handle GDB stdout"""
        if not self._gdb_process:
            return

        data = self._gdb_process.readAllStandardOutput().data().decode('utf-8')
        self._gdb_output_buffer += data

        # Process complete lines
        while '\n' in self._gdb_output_buffer:
            line, self._gdb_output_buffer = self._gdb_output_buffer.split('\n', 1)
            self._process_gdb_output(line)


    def _on_gdb_error(self):
        """Handle GDB stderr"""
        if not self._gdb_process:
            return

        data = self._gdb_process.readAllStandardError().data().decode('utf-8')
        logger.warning(f"GDB error: {data}")
        self.debug_output.emit(f"GDB: {data}")


    def _on_gdb_finished(self, exit_code: int):
        """Handle GDB process exit"""
        logger.info(f"GDB process finished with code {exit_code}")
        self._set_state(DebugState.DISCONNECTED)
        self._gdb_process = None


    def _process_gdb_output(self, line: str):
        """Process GDB/MI output"""
        # Parse GDB Machine Interface output
        # This is a simplified parser - full GDB/MI parsing is complex

        self.debug_output.emit(line)

        # Look for specific patterns
        if line.startswith("*stopped"):
            self._set_state(DebugState.PAUSED)
            self._refresh_debug_state()
        elif line.startswith("*running"):
            self._set_state(DebugState.RUNNING)
        elif "breakpoint-hit" in line:
            # Parse breakpoint hit
            pass


    # ==================== Cleanup ====================

    def cleanup(self):
        """Cleanup debug service resources"""
        try:
            self.disconnect()
            logger.info("Debug service cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
