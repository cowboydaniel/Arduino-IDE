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

    def update_board_info(self, board_type):
        """Update board information based on selected board"""
        # Board specifications database
        board_specs = {
            "Arduino Uno": {
                "cpu": "ATmega328P",
                "flash": "32 KB",
                "ram": "2 KB",
                "clock": "16 MHz"
            },
            "Arduino Mega 2560": {
                "cpu": "ATmega2560",
                "flash": "256 KB",
                "ram": "8 KB",
                "clock": "16 MHz"
            },
            "Arduino Nano": {
                "cpu": "ATmega328P",
                "flash": "32 KB",
                "ram": "2 KB",
                "clock": "16 MHz"
            },
            "Arduino Leonardo": {
                "cpu": "ATmega32u4",
                "flash": "32 KB",
                "ram": "2.5 KB",
                "clock": "16 MHz"
            },
            "Arduino Pro Mini": {
                "cpu": "ATmega328P",
                "flash": "32 KB",
                "ram": "2 KB",
                "clock": "8/16 MHz"
            },
            "ESP32 Dev Module": {
                "cpu": "ESP32 Dual-Core",
                "flash": "4 MB",
                "ram": "520 KB",
                "clock": "240 MHz"
            },
            "ESP8266 NodeMCU": {
                "cpu": "ESP8266",
                "flash": "4 MB",
                "ram": "80 KB",
                "clock": "80/160 MHz"
            },
            "Arduino Due": {
                "cpu": "AT91SAM3X8E",
                "flash": "512 KB",
                "ram": "96 KB",
                "clock": "84 MHz"
            }
        }

        # Get specs for the board or use defaults
        specs = board_specs.get(board_type, {
            "cpu": "Unknown",
            "flash": "Unknown",
            "ram": "Unknown",
            "clock": "Unknown"
        })

        # Update labels
        self.cpu_label.setText(specs["cpu"])
        self.flash_label.setText(specs["flash"])
        self.ram_label.setText(specs["ram"])
        self.clock_label.setText(specs["clock"])

    def set_port(self, port):
        """Set connected port"""
        self.port_label.setText(port)

    def update_pin_usage(self, code_text):
        """Update pin usage overview from code

        Args:
            code_text: Arduino sketch code as string
        """
        self.pin_usage_widget.update_from_code(code_text)
