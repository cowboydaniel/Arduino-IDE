"""
Debug Toolbar
Provides debugging controls: Start/Stop, Step Over/Into/Out, Pause/Continue
"""

from PySide6.QtWidgets import QToolBar, QWidget, QLabel, QComboBox, QHBoxLayout
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QIcon, QKeySequence
import logging
from typing import Optional

try:
    from arduino_ide.services.debug_service import DebugService, DebugState
except ImportError:
    DebugService = None
    DebugState = None

logger = logging.getLogger(__name__)


class DebugToolbar(QToolBar):
    """
    Toolbar with debugging controls
    Provides start/stop, step, pause/continue, and debug configuration selection
    """

    # Signals
    start_debug_requested = Signal()
    stop_debug_requested = Signal()
    continue_requested = Signal()
    pause_requested = Signal()
    step_over_requested = Signal()
    step_into_requested = Signal()
    step_out_requested = Signal()
    debug_config_changed = Signal(str)  # Configuration name

    def __init__(self, debug_service: Optional['DebugService'] = None, parent=None):
        super().__init__("Debug", parent)

        self.debug_service = debug_service
        self._current_state = DebugState.IDLE if DebugState else None

        self._setup_ui()
        self._setup_connections()

        # Connect to debug service if provided
        if self.debug_service and DebugService:
            self.set_debug_service(self.debug_service)

        # Initial state
        self._update_actions_state()

        logger.info("Debug toolbar initialized")


    def _setup_ui(self):
        """Setup toolbar UI"""
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(self.iconSize())  # Use default icon size

        # Debug configuration selector
        self.config_widget = QWidget()
        config_layout = QHBoxLayout(self.config_widget)
        config_layout.setContentsMargins(5, 0, 5, 0)

        config_label = QLabel("Configuration:")
        self.config_combo = QComboBox()
        self.config_combo.addItems(["Debug", "Release"])
        self.config_combo.setCurrentText("Debug")
        self.config_combo.setToolTip("Select build configuration")

        config_layout.addWidget(config_label)
        config_layout.addWidget(self.config_combo)

        self.addWidget(self.config_widget)
        self.addSeparator()

        # Start/Stop actions
        self.start_action = QAction("Start Debugging", self)
        self.start_action.setToolTip("Start debugging session (F5)")
        self.start_action.setShortcut(QKeySequence(Qt.Key_F5))
        # Would ideally set an icon here: self.start_action.setIcon(QIcon("path/to/icon"))
        self.addAction(self.start_action)

        self.stop_action = QAction("Stop Debugging", self)
        self.stop_action.setToolTip("Stop debugging session (Shift+F5)")
        self.stop_action.setShortcut(QKeySequence(Qt.SHIFT | Qt.Key_F5))
        self.stop_action.setEnabled(False)
        self.addAction(self.stop_action)

        self.addSeparator()

        # Continue/Pause actions
        self.continue_action = QAction("Continue", self)
        self.continue_action.setToolTip("Continue execution (F5)")
        self.continue_action.setEnabled(False)
        self.addAction(self.continue_action)

        self.pause_action = QAction("Pause", self)
        self.pause_action.setToolTip("Pause execution (F6)")
        self.pause_action.setShortcut(QKeySequence(Qt.Key_F6))
        self.pause_action.setEnabled(False)
        self.addAction(self.pause_action)

        self.addSeparator()

        # Step actions
        self.step_over_action = QAction("Step Over", self)
        self.step_over_action.setToolTip("Step over (F10)")
        self.step_over_action.setShortcut(QKeySequence(Qt.Key_F10))
        self.step_over_action.setEnabled(False)
        self.addAction(self.step_over_action)

        self.step_into_action = QAction("Step Into", self)
        self.step_into_action.setToolTip("Step into function (F11)")
        self.step_into_action.setShortcut(QKeySequence(Qt.Key_F11))
        self.step_into_action.setEnabled(False)
        self.addAction(self.step_into_action)

        self.step_out_action = QAction("Step Out", self)
        self.step_out_action.setToolTip("Step out of function (Shift+F11)")
        self.step_out_action.setShortcut(QKeySequence(Qt.SHIFT | Qt.Key_F11))
        self.step_out_action.setEnabled(False)
        self.addAction(self.step_out_action)

        self.addSeparator()

        # State indicator
        self.state_label = QLabel("Not debugging")
        self.state_label.setStyleSheet("padding: 0 10px; color: #888;")
        self.addWidget(self.state_label)


    def _setup_connections(self):
        """Setup signal connections"""
        # Configuration
        self.config_combo.currentTextChanged.connect(self._on_config_changed)

        # Debug control actions
        self.start_action.triggered.connect(self._on_start_debug)
        self.stop_action.triggered.connect(self._on_stop_debug)
        self.continue_action.triggered.connect(self._on_continue)
        self.pause_action.triggered.connect(self._on_pause)

        # Step actions
        self.step_over_action.triggered.connect(self._on_step_over)
        self.step_into_action.triggered.connect(self._on_step_into)
        self.step_out_action.triggered.connect(self._on_step_out)


    def set_debug_service(self, debug_service: 'DebugService'):
        """Connect to debug service"""
        if not DebugService:
            logger.warning("Debug service not available")
            return

        self.debug_service = debug_service

        # Connect to state changes
        self.debug_service.state_changed.connect(self._on_debug_state_changed)

        logger.info("Debug toolbar connected to debug service")


    @Slot(str)
    def _on_config_changed(self, config: str):
        """Handle configuration change"""
        self.debug_config_changed.emit(config)
        logger.debug(f"Debug configuration changed to: {config}")


    @Slot()
    def _on_start_debug(self):
        """Handle start debug action"""
        self.start_debug_requested.emit()

        if self.debug_service:
            # Service will handle connection and starting
            pass


    @Slot()
    def _on_stop_debug(self):
        """Handle stop debug action"""
        self.stop_debug_requested.emit()

        if self.debug_service:
            self.debug_service.stop_debugging()


    @Slot()
    def _on_continue(self):
        """Handle continue action"""
        self.continue_requested.emit()

        if self.debug_service:
            self.debug_service.continue_execution()


    @Slot()
    def _on_pause(self):
        """Handle pause action"""
        self.pause_requested.emit()

        if self.debug_service:
            self.debug_service.pause_execution()


    @Slot()
    def _on_step_over(self):
        """Handle step over action"""
        self.step_over_requested.emit()

        if self.debug_service:
            self.debug_service.step_over()


    @Slot()
    def _on_step_into(self):
        """Handle step into action"""
        self.step_into_requested.emit()

        if self.debug_service:
            self.debug_service.step_into()


    @Slot()
    def _on_step_out(self):
        """Handle step out action"""
        self.step_out_requested.emit()

        if self.debug_service:
            self.debug_service.step_out()


    @Slot(object)
    def _on_debug_state_changed(self, state):
        """Handle debug state change"""
        if not DebugState:
            return

        self._current_state = state
        self._update_actions_state()
        self._update_state_label(state)


    def _update_actions_state(self):
        """Update action enabled/disabled state based on debug state"""
        if not DebugState or not self._current_state:
            return

        state = self._current_state

        # Start/Stop actions
        self.start_action.setEnabled(state in (DebugState.IDLE, DebugState.DISCONNECTED))
        self.stop_action.setEnabled(state not in (DebugState.IDLE, DebugState.DISCONNECTED))

        # Continue/Pause actions
        self.continue_action.setEnabled(state == DebugState.PAUSED)
        self.pause_action.setEnabled(state == DebugState.RUNNING)

        # Step actions (only enabled when paused)
        stepping_enabled = (state == DebugState.PAUSED)
        self.step_over_action.setEnabled(stepping_enabled)
        self.step_into_action.setEnabled(stepping_enabled)
        self.step_out_action.setEnabled(stepping_enabled)

        # Configuration selector (only when not debugging)
        self.config_combo.setEnabled(state in (DebugState.IDLE, DebugState.DISCONNECTED))


    def _update_state_label(self, state):
        """Update state label text and color"""
        if not DebugState:
            return

        state_text = {
            DebugState.IDLE: "Not debugging",
            DebugState.CONNECTING: "Connecting...",
            DebugState.CONNECTED: "Connected",
            DebugState.RUNNING: "Running",
            DebugState.PAUSED: "Paused",
            DebugState.STEPPING: "Stepping",
            DebugState.DISCONNECTED: "Disconnected",
            DebugState.ERROR: "Error"
        }.get(state, "Unknown")

        state_color = {
            DebugState.IDLE: "#888",
            DebugState.CONNECTING: "#FFA500",
            DebugState.CONNECTED: "#4EC9B0",
            DebugState.RUNNING: "#4CAF50",
            DebugState.PAUSED: "#FFC107",
            DebugState.STEPPING: "#2196F3",
            DebugState.DISCONNECTED: "#888",
            DebugState.ERROR: "#F44336"
        }.get(state, "#888")

        self.state_label.setText(state_text)
        self.state_label.setStyleSheet(f"padding: 0 10px; color: {state_color}; font-weight: bold;")


    def get_current_configuration(self) -> str:
        """Get currently selected debug configuration"""
        return self.config_combo.currentText()


    def set_configuration(self, config: str):
        """Set debug configuration"""
        index = self.config_combo.findText(config)
        if index >= 0:
            self.config_combo.setCurrentIndex(index)
