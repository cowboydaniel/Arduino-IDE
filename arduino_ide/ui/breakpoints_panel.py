"""
Breakpoints Panel
Displays and manages code breakpoints for debugging
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QPushButton, QMenu,
                               QCheckBox, QLineEdit, QLabel)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon, QAction, QContextMenuEvent
import logging
from typing import Optional, List

from arduino_ide.services.debug_service import DebugService, Breakpoint, BreakpointType


logger = logging.getLogger(__name__)


class BreakpointsPanel(QWidget):
    """
    Panel for managing debugging breakpoints
    Shows breakpoint list with enable/disable, conditions, and hit counts
    """

    # Signals
    breakpoint_activated = Signal(str, int)  # file_path, line - user wants to navigate to breakpoint
    breakpoint_removed = Signal(int)  # breakpoint_id

    def __init__(self, debug_service: Optional[DebugService] = None, parent=None):
        super().__init__(parent)

        self.debug_service = debug_service

        # UI setup
        self._setup_ui()
        self._setup_connections()

        # Connect to debug service if provided
        if self.debug_service:
            self.set_debug_service(self.debug_service)

        logger.info("Breakpoints panel initialized")


    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Toolbar
        toolbar_layout = QHBoxLayout()

        self.remove_all_btn = QPushButton("Remove All")
        self.remove_all_btn.setToolTip("Remove all breakpoints")

        self.disable_all_btn = QPushButton("Disable All")
        self.disable_all_btn.setToolTip("Disable all breakpoints")

        self.enable_all_btn = QPushButton("Enable All")
        self.enable_all_btn.setToolTip("Enable all breakpoints")

        toolbar_layout.addWidget(self.remove_all_btn)
        toolbar_layout.addWidget(self.disable_all_btn)
        toolbar_layout.addWidget(self.enable_all_btn)
        toolbar_layout.addStretch()

        layout.addLayout(toolbar_layout)

        # Breakpoints table
        self.breakpoints_table = QTableWidget()
        self.breakpoints_table.setColumnCount(5)
        self.breakpoints_table.setHorizontalHeaderLabels([
            "Enabled", "File", "Line", "Condition", "Hits"
        ])

        # Configure table
        header = self.breakpoints_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Enabled checkbox
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # File
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Line
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Condition
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Hits

        self.breakpoints_table.verticalHeader().setVisible(False)
        self.breakpoints_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.breakpoints_table.setSelectionMode(QTableWidget.SingleSelection)
        self.breakpoints_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.breakpoints_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.breakpoints_table.setAlternatingRowColors(True)

        layout.addWidget(self.breakpoints_table)

        # Status label
        self.status_label = QLabel("No breakpoints")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.status_label)


    def _setup_connections(self):
        """Setup signal connections"""
        self.remove_all_btn.clicked.connect(self._on_remove_all)
        self.disable_all_btn.clicked.connect(self._on_disable_all)
        self.enable_all_btn.clicked.connect(self._on_enable_all)

        self.breakpoints_table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.breakpoints_table.customContextMenuRequested.connect(self._show_context_menu)


    def set_debug_service(self, debug_service: DebugService):
        """Connect to debug service"""
        self.debug_service = debug_service

        # Connect signals
        self.debug_service.breakpoint_added.connect(self._on_breakpoint_added)
        self.debug_service.breakpoint_removed.connect(self._on_breakpoint_removed)
        self.debug_service.breakpoint_updated.connect(self._on_breakpoint_updated)
        self.debug_service.breakpoint_hit.connect(self._on_breakpoint_hit)

        # Initial refresh
        self.refresh_breakpoints()


    def refresh_breakpoints(self):
        """Refresh the breakpoints table"""
        if not self.debug_service:
            return

        # Clear table
        self.breakpoints_table.setRowCount(0)

        # Get all breakpoints
        breakpoints = self.debug_service.get_breakpoints()

        if not breakpoints:
            self.status_label.setText("No breakpoints")
            self.status_label.setVisible(True)
            return

        self.status_label.setVisible(False)

        # Populate table
        for row, bp in enumerate(breakpoints):
            self.breakpoints_table.insertRow(row)

            # Store breakpoint ID in row data
            self.breakpoints_table.setItem(row, 0, QTableWidgetItem())
            self.breakpoints_table.item(row, 0).setData(Qt.UserRole, bp.id)

            # Enabled checkbox
            enabled_widget = QWidget()
            enabled_layout = QHBoxLayout(enabled_widget)
            enabled_layout.setContentsMargins(0, 0, 0, 0)
            enabled_layout.setAlignment(Qt.AlignCenter)

            enabled_cb = QCheckBox()
            enabled_cb.setChecked(bp.enabled)
            enabled_cb.stateChanged.connect(
                lambda state, bp_id=bp.id: self._on_breakpoint_toggled(bp_id, state)
            )

            enabled_layout.addWidget(enabled_cb)
            self.breakpoints_table.setCellWidget(row, 0, enabled_widget)

            # File (just filename, not full path)
            import os
            filename = os.path.basename(bp.file_path)
            file_item = QTableWidgetItem(filename)
            file_item.setToolTip(bp.file_path)
            self.breakpoints_table.setItem(row, 1, file_item)

            # Line number
            line_item = QTableWidgetItem(str(bp.line))
            line_item.setTextAlignment(Qt.AlignCenter)
            self.breakpoints_table.setItem(row, 2, line_item)

            # Condition
            condition_text = bp.condition if bp.condition else ""
            condition_item = QTableWidgetItem(condition_text)
            condition_item.setToolTip(condition_text)
            self.breakpoints_table.setItem(row, 3, condition_item)

            # Hit count
            hits_item = QTableWidgetItem(str(bp.hit_count))
            hits_item.setTextAlignment(Qt.AlignCenter)
            self.breakpoints_table.setItem(row, 4, hits_item)

        # Update status
        self.status_label.setText(f"{len(breakpoints)} breakpoint(s)")


    @Slot(Breakpoint)
    def _on_breakpoint_added(self, breakpoint: Breakpoint):
        """Handle breakpoint added"""
        self.refresh_breakpoints()


    @Slot(int)
    def _on_breakpoint_removed(self, breakpoint_id: int):
        """Handle breakpoint removed"""
        self.refresh_breakpoints()


    @Slot(Breakpoint)
    def _on_breakpoint_updated(self, breakpoint: Breakpoint):
        """Handle breakpoint updated"""
        self.refresh_breakpoints()


    @Slot(Breakpoint, str, int)
    def _on_breakpoint_hit(self, breakpoint: Breakpoint, file_path: str, line: int):
        """Handle breakpoint hit - highlight the row"""
        # Find row with this breakpoint
        for row in range(self.breakpoints_table.rowCount()):
            item = self.breakpoints_table.item(row, 0)
            if item and item.data(Qt.UserRole) == breakpoint.id:
                # Highlight row (you could change background color)
                self.breakpoints_table.selectRow(row)
                break

        # Refresh to update hit count
        self.refresh_breakpoints()


    @Slot(int, int)
    def _on_breakpoint_toggled(self, breakpoint_id: int, state: int):
        """Handle breakpoint enable/disable toggle"""
        if self.debug_service:
            self.debug_service.toggle_breakpoint(breakpoint_id)


    @Slot(int, int)
    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle cell double click - navigate to breakpoint location"""
        if not self.debug_service:
            return

        # Get breakpoint ID from row
        item = self.breakpoints_table.item(row, 0)
        if not item:
            return

        breakpoint_id = item.data(Qt.UserRole)
        breakpoints = self.debug_service.get_breakpoints()

        for bp in breakpoints:
            if bp.id == breakpoint_id:
                # Emit signal to navigate to this location
                self.breakpoint_activated.emit(bp.file_path, bp.line)
                break


    def _show_context_menu(self, pos):
        """Show context menu for breakpoint actions"""
        if self.breakpoints_table.rowCount() == 0:
            return

        # Get current row
        current_row = self.breakpoints_table.currentRow()
        if current_row < 0:
            return

        # Get breakpoint ID
        item = self.breakpoints_table.item(current_row, 0)
        if not item:
            return

        breakpoint_id = item.data(Qt.UserRole)

        # Create context menu
        menu = QMenu(self)

        go_to_action = QAction("Go to Location", self)
        go_to_action.triggered.connect(lambda: self._on_go_to_breakpoint(breakpoint_id))

        enable_action = QAction("Enable", self)
        enable_action.triggered.connect(lambda: self._on_toggle_breakpoint(breakpoint_id, True))

        disable_action = QAction("Disable", self)
        disable_action.triggered.connect(lambda: self._on_toggle_breakpoint(breakpoint_id, False))

        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self._on_remove_breakpoint(breakpoint_id))

        menu.addAction(go_to_action)
        menu.addSeparator()
        menu.addAction(enable_action)
        menu.addAction(disable_action)
        menu.addSeparator()
        menu.addAction(remove_action)

        # Show menu
        menu.exec_(self.breakpoints_table.viewport().mapToGlobal(pos))


    def _on_go_to_breakpoint(self, breakpoint_id: int):
        """Navigate to breakpoint location"""
        if not self.debug_service:
            return

        breakpoints = self.debug_service.get_breakpoints()
        for bp in breakpoints:
            if bp.id == breakpoint_id:
                self.breakpoint_activated.emit(bp.file_path, bp.line)
                break


    def _on_toggle_breakpoint(self, breakpoint_id: int, enabled: bool):
        """Enable or disable a breakpoint"""
        if self.debug_service:
            # Get current state
            breakpoints = self.debug_service.get_breakpoints()
            for bp in breakpoints:
                if bp.id == breakpoint_id:
                    if bp.enabled != enabled:
                        self.debug_service.toggle_breakpoint(breakpoint_id)
                    break


    def _on_remove_breakpoint(self, breakpoint_id: int):
        """Remove a breakpoint"""
        if self.debug_service:
            self.debug_service.remove_breakpoint(breakpoint_id)
            self.breakpoint_removed.emit(breakpoint_id)


    def _on_remove_all(self):
        """Remove all breakpoints"""
        if not self.debug_service:
            return

        breakpoints = self.debug_service.get_breakpoints()
        for bp in breakpoints:
            self.debug_service.remove_breakpoint(bp.id)


    def _on_disable_all(self):
        """Disable all breakpoints"""
        if not self.debug_service:
            return

        breakpoints = self.debug_service.get_breakpoints()
        for bp in breakpoints:
            if bp.enabled:
                self.debug_service.toggle_breakpoint(bp.id)


    def _on_enable_all(self):
        """Enable all breakpoints"""
        if not self.debug_service:
            return

        breakpoints = self.debug_service.get_breakpoints()
        for bp in breakpoints:
            if not bp.enabled:
                self.debug_service.toggle_breakpoint(bp.id)


    def clear(self):
        """Clear all breakpoints"""
        self._on_remove_all()
