"""
Board information and selection panel
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox,
    QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt


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

        # Pin configuration
        pins_group = QGroupBox("Pin Configuration")
        pins_layout = QVBoxLayout()

        pins_btn = QPushButton("View Pinout Diagram")
        pins_layout.addWidget(pins_btn)

        pins_group.setLayout(pins_layout)
        layout.addWidget(pins_group)

        layout.addStretch()

    def update_board_info(self, board_type):
        """Update board information based on selected board"""
        # TODO: Implement board-specific info
        pass

    def set_port(self, port):
        """Set connected port"""
        self.port_label.setText(port)
