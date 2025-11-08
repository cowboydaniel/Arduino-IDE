"""
Serial Monitor with multi-device support and plotting capabilities
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QLabel, QTabWidget, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QTextCursor, QFont
import serial
import serial.tools.list_ports


class SerialMonitor(QWidget):
    """Multi-device serial monitor with plotting"""

    data_received = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.serial_connections = {}
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        # Port selection
        toolbar.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        self.refresh_ports()
        toolbar.addWidget(self.port_combo)

        refresh_btn = QPushButton("🔄")
        refresh_btn.clicked.connect(self.refresh_ports)
        toolbar.addWidget(refresh_btn)

        # Baud rate
        toolbar.addWidget(QLabel("Baud:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems([
            "300", "1200", "2400", "4800", "9600", "19200",
            "38400", "57600", "74880", "115200", "230400", "250000"
        ])
        self.baud_combo.setCurrentText("9600")
        toolbar.addWidget(self.baud_combo)

        # Connect/Disconnect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        toolbar.addWidget(self.connect_btn)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_output)
        toolbar.addWidget(clear_btn)

        # Autoscroll checkbox
        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        toolbar.addWidget(self.autoscroll_check)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Output area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas, Monaco, Courier New", 10))
        layout.addWidget(self.output_text)

        # Input area
        input_layout = QHBoxLayout()

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Type command and press Enter...")
        self.input_line.returnPressed.connect(self.send_data)
        input_layout.addWidget(self.input_line)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_data)
        input_layout.addWidget(send_btn)

        layout.addLayout(input_layout)

        # Timer for reading serial data
        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self.read_serial_data)

    def refresh_ports(self):
        """Refresh available COM ports"""
        self.port_combo.clear()

        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}", port.device)

        if self.port_combo.count() == 0:
            self.port_combo.addItem("No ports found", None)

    def toggle_connection(self):
        """Connect or disconnect from serial port"""
        port_data = self.port_combo.currentData()

        if not port_data:
            self.append_output("[ERROR] No valid port selected\n", "red")
            return

        if self.connect_btn.text() == "Connect":
            try:
                baud_rate = int(self.baud_combo.currentText())

                # Open serial connection
                ser = serial.Serial(port_data, baud_rate, timeout=0.1)

                self.serial_connections[port_data] = ser

                self.connect_btn.setText("Disconnect")
                self.connect_btn.setStyleSheet("background-color: #4CAF50;")

                self.append_output(f"[CONNECTED] {port_data} @ {baud_rate} baud\n", "green")

                # Start reading timer
                self.read_timer.start(50)  # Read every 50ms

            except Exception as e:
                self.append_output(f"[ERROR] Failed to connect: {str(e)}\n", "red")

        else:
            # Disconnect
            if port_data in self.serial_connections:
                self.serial_connections[port_data].close()
                del self.serial_connections[port_data]

            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("")

            self.read_timer.stop()

            self.append_output(f"[DISCONNECTED] {port_data}\n", "orange")

    def read_serial_data(self):
        """Read data from serial port"""
        for port, ser in self.serial_connections.items():
            try:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                    self.append_output(data)
                    self.data_received.emit(data)

            except Exception as e:
                self.append_output(f"[ERROR] Read error: {str(e)}\n", "red")

    def send_data(self):
        """Send data to serial port"""
        text = self.input_line.text()

        if not text:
            return

        port_data = self.port_combo.currentData()

        if port_data in self.serial_connections:
            try:
                # Add newline if not present
                if not text.endswith('\n'):
                    text += '\n'

                self.serial_connections[port_data].write(text.encode('utf-8'))

                self.append_output(f">> {text}", "blue")
                self.input_line.clear()

            except Exception as e:
                self.append_output(f"[ERROR] Send error: {str(e)}\n", "red")
        else:
            self.append_output("[ERROR] Not connected\n", "red")

    def append_output(self, text, color=None):
        """Append text to output area"""
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.End)

        if color:
            self.output_text.setTextColor(self.get_color(color))

        self.output_text.append(text.rstrip())

        if color:
            self.output_text.setTextColor(self.get_color("white"))

        # Auto-scroll
        if self.autoscroll_check.isChecked():
            self.output_text.verticalScrollBar().setValue(
                self.output_text.verticalScrollBar().maximum()
            )

    def get_color(self, color_name):
        """Get QColor from name"""
        from PySide6.QtGui import QColor

        colors = {
            "red": QColor(255, 100, 100),
            "green": QColor(100, 255, 100),
            "blue": QColor(100, 150, 255),
            "orange": QColor(255, 165, 0),
            "white": QColor(255, 255, 255),
        }

        return colors.get(color_name, QColor(255, 255, 255))

    def clear_output(self):
        """Clear output area"""
        self.output_text.clear()

    def closeEvent(self, event):
        """Close all serial connections"""
        for ser in self.serial_connections.values():
            ser.close()

        self.serial_connections.clear()
        event.accept()
