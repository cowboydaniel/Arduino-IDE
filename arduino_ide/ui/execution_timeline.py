"""
Execution Timeline Panel
Displays a timeline of execution events during debugging
Shows breakpoints, steps, pauses, function calls, etc.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QPushButton, QLabel,
                               QCheckBox, QSpinBox)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QBrush
import logging
from typing import Optional, List
from datetime import datetime

from arduino_ide.services.debug_service import DebugService, ExecutionEvent


logger = logging.getLogger(__name__)


class ExecutionTimelinePanel(QWidget):
    """
    Panel for displaying execution timeline during debugging
    Shows chronological list of execution events with timestamps
    """

    # Signals
    event_activated = Signal(ExecutionEvent)  # User wants to inspect this event

    def __init__(self, debug_service: Optional[DebugService] = None, parent=None):
        super().__init__(parent)

        self.debug_service = debug_service

        # Event type colors
        self.event_colors = {
            'breakpoint': QColor(220, 50, 50),      # Red
            'step': QColor(50, 150, 220),           # Blue
            'pause': QColor(220, 150, 50),          # Orange
            'resume': QColor(50, 220, 50),          # Green
            'function_call': QColor(150, 100, 220), # Purple
            'function_return': QColor(150, 150, 150) # Gray
        }

        # Auto-scroll setting
        self.auto_scroll_enabled = True

        # UI setup
        self._setup_ui()
        self._setup_connections()

        # Connect to debug service if provided
        if self.debug_service:
            self.set_debug_service(self.debug_service)

        logger.info("Execution timeline panel initialized")


    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Toolbar
        toolbar_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Clear execution timeline")

        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.setToolTip("Automatically scroll to newest events")

        # Max events spinner
        max_events_label = QLabel("Max events:")
        self.max_events_spin = QSpinBox()
        self.max_events_spin.setMinimum(100)
        self.max_events_spin.setMaximum(10000)
        self.max_events_spin.setValue(1000)
        self.max_events_spin.setSingleStep(100)
        self.max_events_spin.setToolTip("Maximum number of events to keep")

        toolbar_layout.addWidget(self.clear_btn)
        toolbar_layout.addWidget(self.auto_scroll_cb)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(max_events_label)
        toolbar_layout.addWidget(self.max_events_spin)

        layout.addLayout(toolbar_layout)

        # Timeline table
        self.timeline_table = QTableWidget()
        self.timeline_table.setColumnCount(4)
        self.timeline_table.setHorizontalHeaderLabels([
            "Time", "Event Type", "Location", "Details"
        ])

        # Configure table
        header = self.timeline_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Time
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Event Type
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Location
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Details

        self.timeline_table.verticalHeader().setVisible(False)
        self.timeline_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.timeline_table.setSelectionMode(QTableWidget.SingleSelection)
        self.timeline_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.timeline_table.setAlternatingRowColors(True)

        layout.addWidget(self.timeline_table)

        # Status label
        self.status_label = QLabel("No execution events")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)


    def _setup_connections(self):
        """Setup signal connections"""
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.auto_scroll_cb.stateChanged.connect(self._on_auto_scroll_toggled)
        self.timeline_table.cellDoubleClicked.connect(self._on_cell_double_clicked)


    def set_debug_service(self, debug_service: DebugService):
        """Connect to debug service"""
        self.debug_service = debug_service

        # Connect signals
        self.debug_service.execution_event.connect(self._on_execution_event)
        self.debug_service.state_changed.connect(self._on_debug_state_changed)

        # Initial load
        self.refresh_timeline()


    def refresh_timeline(self):
        """Refresh the entire timeline from debug service"""
        if not self.debug_service:
            return

        # Clear table
        self.timeline_table.setRowCount(0)

        # Get all events
        events = self.debug_service.get_execution_timeline()

        if not events:
            self.status_label.setText("No execution events")
            self.status_label.setVisible(True)
            return

        self.status_label.setVisible(False)

        # Add all events
        for event in events:
            self._add_event_to_table(event)

        # Auto-scroll to bottom
        if self.auto_scroll_enabled:
            self.timeline_table.scrollToBottom()


    def _add_event_to_table(self, event: ExecutionEvent):
        """Add a single event to the timeline table"""
        row = self.timeline_table.rowCount()
        self.timeline_table.insertRow(row)

        # Format timestamp
        timestamp = datetime.fromtimestamp(event.timestamp)
        time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds

        # Time
        time_item = QTableWidgetItem(time_str)
        time_item.setData(Qt.UserRole, event)  # Store event object
        self.timeline_table.setItem(row, 0, time_item)

        # Event Type
        event_type_item = QTableWidgetItem(event.event_type)

        # Color code by event type
        if event.event_type in self.event_colors:
            color = self.event_colors[event.event_type]
            event_type_item.setForeground(QBrush(color))

        self.timeline_table.setItem(row, 1, event_type_item)

        # Location
        location_text = event.location if event.location else ""
        location_item = QTableWidgetItem(location_text)
        self.timeline_table.setItem(row, 2, location_item)

        # Details
        details_text = ""
        if event.data:
            # Format data dict as string
            details_text = ", ".join(f"{k}={v}" for k, v in event.data.items())

        details_item = QTableWidgetItem(details_text)
        details_item.setToolTip(details_text)
        self.timeline_table.setItem(row, 3, details_item)


    @Slot(ExecutionEvent)
    def _on_execution_event(self, event: ExecutionEvent):
        """Handle new execution event from debug service"""
        # Hide status label if visible
        if self.status_label.isVisible():
            self.status_label.setVisible(False)

        # Add event to table
        self._add_event_to_table(event)

        # Auto-scroll to bottom
        if self.auto_scroll_enabled:
            self.timeline_table.scrollToBottom()

        # Limit table size
        max_events = self.max_events_spin.value()
        while self.timeline_table.rowCount() > max_events:
            self.timeline_table.removeRow(0)


    @Slot(object)
    def _on_debug_state_changed(self, state):
        """Handle debug state change"""
        from arduino_ide.services.debug_service import DebugState

        if state in (DebugState.IDLE, DebugState.DISCONNECTED):
            # Don't clear timeline, just show status
            pass


    @Slot()
    def _on_clear_clicked(self):
        """Handle clear button click"""
        if self.debug_service:
            self.debug_service.clear_execution_timeline()

        self.timeline_table.setRowCount(0)
        self.status_label.setText("Timeline cleared")
        self.status_label.setVisible(True)


    @Slot(int)
    def _on_auto_scroll_toggled(self, state: int):
        """Handle auto-scroll toggle"""
        self.auto_scroll_enabled = (state == Qt.Checked)
        logger.debug(f"Timeline auto-scroll: {self.auto_scroll_enabled}")


    @Slot(int, int)
    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle cell double click"""
        if row < 0 or row >= self.timeline_table.rowCount():
            return

        # Get event from row
        time_item = self.timeline_table.item(row, 0)
        if not time_item:
            return

        event = time_item.data(Qt.UserRole)
        if event:
            self.event_activated.emit(event)


    def clear(self):
        """Clear the timeline"""
        self._on_clear_clicked()


    def get_event_statistics(self) -> dict:
        """Get statistics about events in timeline"""
        if not self.debug_service:
            return {}

        events = self.debug_service.get_execution_timeline()

        stats = {
            'total_events': len(events),
            'event_types': {}
        }

        for event in events:
            event_type = event.event_type
            stats['event_types'][event_type] = stats['event_types'].get(event_type, 0) + 1

        return stats


    def export_timeline(self, file_path: str):
        """Export timeline to CSV file"""
        try:
            if not self.debug_service:
                return False

            events = self.debug_service.get_execution_timeline()

            with open(file_path, 'w') as f:
                # Write header
                f.write("Timestamp,Event Type,Location,Data\n")

                # Write events
                for event in events:
                    timestamp = datetime.fromtimestamp(event.timestamp).isoformat()
                    location = event.location if event.location else ""
                    data = str(event.data) if event.data else ""

                    # Escape commas and quotes
                    location = location.replace('"', '""')
                    data = data.replace('"', '""')

                    f.write(f'"{timestamp}","{event.event_type}","{location}","{data}"\n')

            logger.info(f"Timeline exported to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export timeline: {e}")
            return False
