from __future__ import annotations

import datetime
from typing import List, Optional

from PySide6 import QtCore, QtWidgets

from services_mobile.usb_service import SerialSession, USBDevice, USBService


class SerialMonitorWidget(QtWidgets.QWidget):
    """Serial monitor with OTG device management and touch-friendly controls."""

    line_received = QtCore.Signal(str)
    connection_changed = QtCore.Signal(bool)

    def __init__(self, usb_service: USBService, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.usb_service = usb_service
        self.devices: List[USBDevice] = []
        self.session: Optional[SerialSession] = None

        self.device_combo = QtWidgets.QComboBox()
        self.refresh_button = QtWidgets.QToolButton(text="Refresh")
        self.refresh_button.clicked.connect(self.refresh_devices)

        self.baud_combo = QtWidgets.QComboBox()
        for baud in [9600, 19200, 38400, 57600, 115200, 230400, 460800]:
            self.baud_combo.addItem(str(baud), baud)
        self.baud_combo.setCurrentText("115200")

        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.setCheckable(True)
        self.connect_button.clicked.connect(self._toggle_connection)

        self.status_label = QtWidgets.QLabel("Disconnected")

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Serial output will appear here…")

        self.input_field = QtWidgets.QLineEdit()
        self.input_field.setPlaceholderText("Type data to send…")
        self.input_field.returnPressed.connect(self._send_line)
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self._send_line)

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("USB Device:"))
        controls.addWidget(self.device_combo, 1)
        controls.addWidget(self.refresh_button)
        controls.addWidget(QtWidgets.QLabel("Baud:"))
        controls.addWidget(self.baud_combo)
        controls.addWidget(self.connect_button)

        input_row = QtWidgets.QHBoxLayout()
        input_row.addWidget(self.input_field, 1)
        input_row.addWidget(self.send_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log, 1)
        layout.addLayout(input_row)

        self.refresh_devices()

    def refresh_devices(self) -> None:
        self.devices = self.usb_service.detect_devices()
        self.device_combo.clear()
        for dev in self.devices:
            label = f"{dev.description} ({dev.port})"
            if dev.vid and dev.pid:
                label += f" [{dev.vid}:{dev.pid}]"
            self.device_combo.addItem(label, dev)
        if not self.devices:
            self.device_combo.addItem("No USB devices detected", None)
        self.status_label.setText("USB list updated")

    def current_device(self) -> Optional[USBDevice]:
        data = self.device_combo.currentData()
        if isinstance(data, USBDevice):
            return data
        return None

    def _toggle_connection(self, checked: bool) -> None:
        if checked:
            self._connect()
        else:
            self._disconnect()

    def _connect(self) -> None:
        device = self.current_device()
        if not device:
            self.status_label.setText("Select a USB device before connecting")
            self.connect_button.setChecked(False)
            return

        baud = self.baud_combo.currentData()
        self.session = self.usb_service.start_serial_session(device, int(baud))
        self.session.line_received.connect(self._handle_line)
        self.session.status.connect(self._update_status)
        self.session.error.connect(self._handle_error)
        self.connection_changed.emit(True)
        self.connect_button.setText("Disconnect")
        self.status_label.setText(f"Connecting to {device.port}…")

    def _disconnect(self) -> None:
        device = self.current_device()
        if device:
            self.usb_service.stop_serial_session(device)
        if self.session:
            try:
                self.session.deleteLater()
            except Exception:
                pass
        self.session = None
        self.connection_changed.emit(False)
        self.connect_button.setText("Connect")
        self.connect_button.setChecked(False)
        self.status_label.setText("Disconnected")

    def _handle_line(self, line: str) -> None:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.appendPlainText(f"[{timestamp}] {line}")
        self.line_received.emit(line)

    def _handle_error(self, message: str) -> None:
        self.log.appendPlainText(f"[ERROR] {message}")
        self.status_label.setText(message)
        self.connect_button.setChecked(False)

    def _update_status(self, status: str) -> None:
        self.status_label.setText(status)

    def _send_line(self) -> None:
        if not self.session or not self.session.connected:
            self.status_label.setText("Not connected")
            return
        text = self.input_field.text().strip()
        if not text:
            return
        self.session.write_line(text)
        self.input_field.clear()


__all__ = ["SerialMonitorWidget"]
