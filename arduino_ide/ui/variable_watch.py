"""
Variable watch panel for debugging
Enhanced with debug service integration for real-time variable inspection
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QPushButton, QHeaderView, QInputDialog, QTreeWidget,
    QTreeWidgetItem, QLabel, QTabWidget
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
import logging
from typing import Optional, List

try:
    from arduino_ide.services.debug_service import DebugService, Variable
except ImportError:
    DebugService = None
    Variable = None

logger = logging.getLogger(__name__)


class VariableWatch(QWidget):
    """Watch variables during debugging with debug service integration"""

    # Signals
    variable_added = Signal(str)  # variable name
    variable_removed = Signal(str)  # variable name

    def __init__(self, debug_service: Optional[DebugService] = None, parent=None):
        super().__init__(parent)

        self.debug_service = debug_service
        self._variable_rows = {}  # Maps variable name to row index

        self.init_ui()

        # Connect to debug service if provided
        if self.debug_service and DebugService:
            self.set_debug_service(self.debug_service)

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Toolbar
        toolbar = QHBoxLayout()

        self.add_btn = QPushButton("+ Add Watch")
        self.add_btn.setToolTip("Add a variable to watch")
        self.add_btn.clicked.connect(self._on_add_watch_clicked)
        toolbar.addWidget(self.add_btn)

        self.remove_btn = QPushButton("- Remove")
        self.remove_btn.setToolTip("Remove selected variable")
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        toolbar.addWidget(self.remove_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Refresh variable values")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setToolTip("Clear all watched variables")
        self.clear_btn.clicked.connect(self.clear_all)
        toolbar.addWidget(self.clear_btn)

        layout.addLayout(toolbar)

        # Tab widget for Watch and Locals
        self.tab_widget = QTabWidget()

        # Watch tab
        self.watch_widget = QWidget()
        watch_layout = QVBoxLayout(self.watch_widget)
        watch_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Variable", "Type", "Value"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)

        watch_layout.addWidget(self.table)
        self.tab_widget.addTab(self.watch_widget, "Watch")

        # Locals tab
        self.locals_widget = QWidget()
        locals_layout = QVBoxLayout(self.locals_widget)
        locals_layout.setContentsMargins(0, 0, 0, 0)

        self.locals_tree = QTreeWidget()
        self.locals_tree.setColumnCount(3)
        self.locals_tree.setHeaderLabels(["Variable", "Type", "Value"])

        locals_header = self.locals_tree.header()
        locals_header.setSectionResizeMode(0, QHeaderView.Stretch)
        locals_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        locals_header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.locals_tree.setAlternatingRowColors(True)

        locals_layout.addWidget(self.locals_tree)
        self.tab_widget.addTab(self.locals_widget, "Locals")

        layout.addWidget(self.tab_widget)

        # Status label
        self.status_label = QLabel("Connect debugger and pause execution to view variables")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)


    def set_debug_service(self, debug_service: DebugService):
        """Connect to debug service"""
        if not DebugService:
            logger.warning("Debug service not available")
            return

        self.debug_service = debug_service

        # Connect signals
        self.debug_service.variable_updated.connect(self._on_variable_updated)
        self.debug_service.variables_updated.connect(self._on_variables_updated)
        self.debug_service.state_changed.connect(self._on_debug_state_changed)

        logger.info("Variable watch connected to debug service")


    def add_variable(self, name: str, var_type: str = "unknown", value: str = "<pending>"):
        """Add a variable to watch"""
        # Check if already exists
        if name in self._variable_rows:
            logger.warning(f"Variable {name} already in watch list")
            return

        row = self.table.rowCount()
        self.table.insertRow(row)

        # Store mapping
        self._variable_rows[name] = row

        # Variable name
        name_item = QTableWidgetItem(name)
        self.table.setItem(row, 0, name_item)

        # Type
        type_item = QTableWidgetItem(var_type)
        self.table.setItem(row, 1, type_item)

        # Value
        value_item = QTableWidgetItem(str(value))
        self.table.setItem(row, 2, value_item)

        # Request value from debug service
        if self.debug_service and DebugService:
            self.debug_service.add_watch_variable(name)

        self.variable_added.emit(name)


    def update_variable(self, name: str, var_type: str = None, value: str = None):
        """Update variable value and/or type"""
        if name not in self._variable_rows:
            # Add new variable if not exists
            if value is not None:
                self.add_variable(name, var_type or "unknown", value)
            return

        row = self._variable_rows[name]

        # Update type if provided
        if var_type is not None:
            type_item = self.table.item(row, 1)
            if type_item:
                type_item.setText(var_type)

        # Update value if provided
        if value is not None:
            value_item = self.table.item(row, 2)
            if value_item:
                old_value = value_item.text()
                value_item.setText(str(value))

                # Highlight if value changed
                if old_value != str(value):
                    font = QFont()
                    font.setBold(True)
                    value_item.setFont(font)


    def remove_variable(self, name: str):
        """Remove a variable from watch list"""
        if name not in self._variable_rows:
            return

        row = self._variable_rows[name]
        self.table.removeRow(row)

        # Remove from debug service
        if self.debug_service and DebugService:
            self.debug_service.remove_watch_variable(name)

        # Update row mappings
        del self._variable_rows[name]

        # Re-index rows after the removed one
        for var_name, var_row in list(self._variable_rows.items()):
            if var_row > row:
                self._variable_rows[var_name] = var_row - 1

        self.variable_removed.emit(name)


    def clear_all(self):
        """Clear all variables"""
        # Remove all from debug service
        if self.debug_service and DebugService:
            for name in list(self._variable_rows.keys()):
                self.debug_service.remove_watch_variable(name)

        self.table.setRowCount(0)
        self._variable_rows.clear()


    def refresh_locals(self):
        """Refresh local variables from debug service"""
        if not self.debug_service or not DebugService:
            return

        local_vars = self.debug_service.get_local_variables()

        # Clear locals tree
        self.locals_tree.clear()

        if not local_vars:
            # Show empty state
            self.status_label.setText("No local variables")
            return

        # Populate locals tree
        for var in local_vars:
            self._add_variable_to_tree(var, self.locals_tree.invisibleRootItem())


    def _add_variable_to_tree(self, var: Variable, parent_item: QTreeWidgetItem):
        """Add a variable and its children to the tree"""
        if not Variable:
            return

        item = QTreeWidgetItem(parent_item)
        item.setText(0, var.name)
        item.setText(1, var.type)
        item.setText(2, var.value)

        # Add tooltip with address if available
        if var.address:
            item.setToolTip(2, f"Address: {var.address}")

        # Add children recursively
        for child_var in var.children:
            self._add_variable_to_tree(child_var, item)


    @Slot(str, object)
    def _on_variable_updated(self, name: str, variable):
        """Handle variable update from debug service"""
        if not Variable:
            return

        self.update_variable(name, variable.type, variable.value)


    @Slot(list)
    def _on_variables_updated(self, variables: List):
        """Handle bulk variable update"""
        if not Variable:
            return

        for var in variables:
            self.update_variable(var.name, var.type, var.value)

        # Also refresh locals
        self.refresh_locals()


    @Slot(object)
    def _on_debug_state_changed(self, state):
        """Handle debug state change"""
        if not DebugService:
            return

        from arduino_ide.services.debug_service import DebugState

        if state in (DebugState.IDLE, DebugState.DISCONNECTED):
            self.status_label.setText("Not debugging")
            self.locals_tree.clear()
        elif state == DebugState.RUNNING:
            self.status_label.setText("Running...")
        elif state == DebugState.PAUSED:
            self.status_label.setText("")
            self.refresh_locals()


    @Slot()
    def _on_add_watch_clicked(self):
        """Handle add watch button click"""
        # Show input dialog
        name, ok = QInputDialog.getText(
            self,
            "Add Watch Variable",
            "Variable name:"
        )

        if ok and name:
            name = name.strip()
            if name:
                self.add_variable(name)


    @Slot()
    def _on_remove_clicked(self):
        """Handle remove button click"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        # Get variable name from row
        name_item = self.table.item(current_row, 0)
        if name_item:
            var_name = name_item.text()
            self.remove_variable(var_name)


    @Slot()
    def _on_refresh_clicked(self):
        """Handle refresh button click"""
        # Request refresh from debug service
        if self.debug_service and DebugService:
            # Re-request all watched variables
            for var_name in self._variable_rows.keys():
                self.debug_service.add_watch_variable(var_name)

            # Refresh locals
            self.refresh_locals()
