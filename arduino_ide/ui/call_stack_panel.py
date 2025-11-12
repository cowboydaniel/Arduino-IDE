"""
Call Stack Panel
Displays the call stack during debugging with navigation
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                               QHeaderView, QLabel)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
import logging
from typing import Optional, List

from arduino_ide.services.debug_service import DebugService, StackFrame


logger = logging.getLogger(__name__)


class CallStackPanel(QWidget):
    """
    Panel for displaying and navigating the call stack during debugging
    Shows stack frames with function name, file, and line number
    """

    # Signals
    frame_activated = Signal(int)  # frame_level - user wants to inspect this frame
    location_activated = Signal(str, int)  # file_path, line - user wants to navigate to location

    def __init__(self, debug_service: Optional[DebugService] = None, parent=None):
        super().__init__(parent)

        self.debug_service = debug_service
        self._current_frame_level = 0

        # UI setup
        self._setup_ui()
        self._setup_connections()

        # Connect to debug service if provided
        if self.debug_service:
            self.set_debug_service(self.debug_service)

        logger.info("Call stack panel initialized")


    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Call stack table
        self.stack_table = QTableWidget()
        self.stack_table.setColumnCount(4)
        self.stack_table.setHorizontalHeaderLabels([
            "Level", "Function", "File", "Line"
        ])

        # Configure table
        header = self.stack_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Level
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Function
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # File
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Line

        self.stack_table.verticalHeader().setVisible(False)
        self.stack_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stack_table.setSelectionMode(QTableWidget.SingleSelection)
        self.stack_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stack_table.setAlternatingRowColors(True)

        layout.addWidget(self.stack_table)

        # Status label
        self.status_label = QLabel("No call stack (not debugging)")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)


    def _setup_connections(self):
        """Setup signal connections"""
        self.stack_table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.stack_table.currentCellChanged.connect(self._on_current_cell_changed)


    def set_debug_service(self, debug_service: DebugService):
        """Connect to debug service"""
        self.debug_service = debug_service

        # Connect signals
        self.debug_service.stack_trace_updated.connect(self._on_stack_trace_updated)
        self.debug_service.state_changed.connect(self._on_debug_state_changed)

        # Initial refresh
        self.refresh_stack()


    def refresh_stack(self):
        """Refresh the call stack display"""
        if not self.debug_service:
            self._show_empty_state("No debug service")
            return

        # Get call stack
        call_stack = self.debug_service.get_call_stack()

        if not call_stack:
            self._show_empty_state("No call stack")
            return

        # Hide status label
        self.status_label.setVisible(False)

        # Clear table
        self.stack_table.setRowCount(0)

        # Populate table
        for row, frame in enumerate(call_stack):
            self.stack_table.insertRow(row)

            # Level
            level_item = QTableWidgetItem(str(frame.level))
            level_item.setTextAlignment(Qt.AlignCenter)
            level_item.setData(Qt.UserRole, frame.level)  # Store frame level

            # Highlight current frame (level 0)
            if frame.level == self._current_frame_level:
                font = QFont()
                font.setBold(True)
                level_item.setFont(font)

            self.stack_table.setItem(row, 0, level_item)

            # Function
            function_item = QTableWidgetItem(frame.function)
            if frame.level == self._current_frame_level:
                font = QFont()
                font.setBold(True)
                function_item.setFont(font)
            self.stack_table.setItem(row, 1, function_item)

            # File (just filename)
            if frame.file_path:
                import os
                filename = os.path.basename(frame.file_path)
                file_item = QTableWidgetItem(filename)
                file_item.setToolTip(frame.file_path)

                if frame.level == self._current_frame_level:
                    font = QFont()
                    font.setBold(True)
                    file_item.setFont(font)
            else:
                file_item = QTableWidgetItem("(unknown)")
                file_item.setForeground(Qt.gray)

            self.stack_table.setItem(row, 2, file_item)

            # Line
            if frame.line is not None:
                line_item = QTableWidgetItem(str(frame.line))
                line_item.setTextAlignment(Qt.AlignCenter)

                if frame.level == self._current_frame_level:
                    font = QFont()
                    font.setBold(True)
                    line_item.setFont(font)
            else:
                line_item = QTableWidgetItem("--")
                line_item.setTextAlignment(Qt.AlignCenter)
                line_item.setForeground(Qt.gray)

            self.stack_table.setItem(row, 3, line_item)

        # Select current frame
        if self._current_frame_level < self.stack_table.rowCount():
            self.stack_table.selectRow(self._current_frame_level)


    def _show_empty_state(self, message: str):
        """Show empty state with message"""
        self.stack_table.setRowCount(0)
        self.status_label.setText(message)
        self.status_label.setVisible(True)


    @Slot(list)
    def _on_stack_trace_updated(self, stack_frames: List[StackFrame]):
        """Handle stack trace update from debug service"""
        self._current_frame_level = 0  # Reset to top of stack
        self.refresh_stack()


    @Slot(object)
    def _on_debug_state_changed(self, state):
        """Handle debug state change"""
        from arduino_ide.services.debug_service import DebugState

        if state in (DebugState.IDLE, DebugState.DISCONNECTED):
            self._show_empty_state("Not debugging")
        elif state == DebugState.RUNNING:
            self._show_empty_state("Running...")
        elif state == DebugState.PAUSED:
            # Stack will be updated via stack_trace_updated signal
            pass


    @Slot(int, int)
    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle cell double click - navigate to frame location"""
        if row < 0 or row >= self.stack_table.rowCount():
            return

        # Get frame level from row
        level_item = self.stack_table.item(row, 0)
        if not level_item:
            return

        frame_level = level_item.data(Qt.UserRole)

        # Get frame info
        if not self.debug_service:
            return

        call_stack = self.debug_service.get_call_stack()
        if frame_level >= len(call_stack):
            return

        frame = call_stack[frame_level]

        # Navigate to location if available
        if frame.file_path and frame.line is not None:
            self.location_activated.emit(frame.file_path, frame.line)


    @Slot(int, int, int, int)
    def _on_current_cell_changed(self, currentRow: int, currentColumn: int,
                                  previousRow: int, previousColumn: int):
        """Handle current cell change - update active frame"""
        if currentRow < 0 or currentRow >= self.stack_table.rowCount():
            return

        # Get frame level from row
        level_item = self.stack_table.item(currentRow, 0)
        if not level_item:
            return

        frame_level = level_item.data(Qt.UserRole)

        # Update current frame in debug service
        if self.debug_service:
            self.debug_service.set_current_frame(frame_level)
            self._current_frame_level = frame_level

            # Emit signal for other components
            self.frame_activated.emit(frame_level)

            # Refresh to update bold formatting
            self.refresh_stack()


    def clear(self):
        """Clear the call stack display"""
        self._show_empty_state("No call stack")
        self._current_frame_level = 0
