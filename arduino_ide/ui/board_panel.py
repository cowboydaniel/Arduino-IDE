"""
Board information and selection panel
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox,
    QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt
from arduino_ide.ui.pin_usage_widget import PinUsageWidget


class BoardPanel(QWidget):
    """Panel showing board information and configuration"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Board selection
        board_group = QGroupBox("Board")
        board_layout = QFormLayout()

        self.board_combo = QComboBox()
        self.board_combo.addItems([
            "Arduino Uno",
            "Arduino Mega 2560",
            "Arduino Nano",
            "Arduino Leonardo",
            "Arduino Micro",
            "Arduino Uno R4 WiFi",
            "Arduino Uno R4 Minima",
            "ESP32 Dev Module",
            "ESP8266 NodeMCU",
        ])
        board_layout.addRow("Type:", self.board_combo)

        self.port_label = QLabel("Not connected")
        board_layout.addRow("Port:", self.port_label)

        board_group.setLayout(board_layout)
        layout.addWidget(board_group)

        # Board info
        info_group = QGroupBox("Information")
        info_layout = QFormLayout()

        self.cpu_label = QLabel("ATmega328P")
        info_layout.addRow("CPU:", self.cpu_label)

        self.flash_label = QLabel("32 KB")
        info_layout.addRow("Flash:", self.flash_label)

        self.ram_label = QLabel("2 KB")
        info_layout.addRow("RAM:", self.ram_label)

        self.clock_label = QLabel("16 MHz")
        info_layout.addRow("Clock:", self.clock_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Pin usage overview
        self.pin_usage_widget = PinUsageWidget()
        layout.addWidget(self.pin_usage_widget)

        layout.addStretch()

    def update_board_info(self, board):
        """Update board information based on selected board.

        Dynamically extracts board specifications from the Board object,
        allowing it to work with any board from the Arduino ecosystem.

        Args:
            board: Board object from arduino_ide.models.board (required)
        """
        # Default values
        cpu = "Unknown"
        flash = "Unknown"
        ram = "Unknown"
        clock = "Unknown"

        # Extract specs from Board object
        if board and hasattr(board, 'specs'):
            specs = board.specs
            cpu = specs.cpu if specs.cpu else "Unknown"
            flash = specs.flash if specs.flash else "Unknown"
            ram = specs.ram if specs.ram else "Unknown"
            clock = specs.clock if specs.clock else "Unknown"

        # Update labels
        self.cpu_label.setText(cpu)
        self.flash_label.setText(flash)
        self.ram_label.setText(ram)
        self.clock_label.setText(clock)

    def set_port(self, port):
        """Set connected port"""
        self.port_label.setText(port)

    def set_board(self, board):
        """Set the current board

        Args:
            board: Board object from arduino_ide.models.board
        """
        self.pin_usage_widget.set_board(board)

    def update_pin_usage(self, code_text):
        """Update pin usage overview from code

        Args:
            code_text: Arduino sketch code as string
        """
        self.pin_usage_widget.update_from_code(code_text)
