"""
Variable watch panel for debugging
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QPushButton, QHeaderView
)
from PySide6.QtCore import Qt


class VariableWatch(QWidget):
    """Watch variables during debugging"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        add_btn = QPushButton("+ Add Watch")
        toolbar.addWidget(add_btn)

        remove_btn = QPushButton("- Remove")
        toolbar.addWidget(remove_btn)

        toolbar.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Variable", "Type", "Value"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        # Add example data
        self.add_variable("counter", "int", "42")
        self.add_variable("ledState", "bool", "HIGH")
        self.add_variable("temperature", "float", "23.5")

        layout.addWidget(self.table)

    def add_variable(self, name, var_type, value):
        """Add a variable to watch"""
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(name))
        self.table.setItem(row, 1, QTableWidgetItem(var_type))
        self.table.setItem(row, 2, QTableWidgetItem(str(value)))

    def update_variable(self, name, value):
        """Update variable value"""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == name:
                self.table.setItem(row, 2, QTableWidgetItem(str(value)))
                break

    def clear_all(self):
        """Clear all variables"""
        self.table.setRowCount(0)
