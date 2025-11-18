from __future__ import annotations

import datetime
from typing import List, Optional, Tuple, Union

from PySide6 import QtCore, QtWidgets

from services_mobile.bluetooth_service import BluetoothDevice, BluetoothSerialSession, BluetoothService
from services_mobile.usb_service import SerialSession, USBDevice, USBService
from services_mobile.wifi_service import WiFiBoard, WiFiSerialSession, WiFiService


class SerialMonitorWidget(QtWidgets.QWidget):
    """Serial monitor with OTG device management and touch-friendly controls."""

    line_received = QtCore.Signal(str)
    connection_changed = QtCore.Signal(bool)

    def __init__(
        self,
        usb_service: USBService,
        bluetooth_service: Optional[BluetoothService] = None,
        wifi_service: Optional[WiFiService] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.usb_service = usb_service
        self.bluetooth_service = bluetooth_service
        self.wifi_service = wifi_service
        self.devices: List[USBDevice] = []
        self.bt_devices: List[BluetoothDevice] = []
        self.wifi_devices: List[WiFiBoard] = []
        self.session: Optional[Union[SerialSession, BluetoothSerialSession, WiFiSerialSession]] = None

        self.transport_combo = QtWidgets.QComboBox()
        self.transport_combo.addItem("USB", "usb")
        if self.bluetooth_service:
            self.transport_combo.addItem("Bluetooth", "bluetooth")
        if self.wifi_service:
            self.transport_combo.addItem("WiFi", "wifi")
        self.transport_combo.currentIndexChanged.connect(self.refresh_devices)

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
        controls.addWidget(QtWidgets.QLabel("Transport:"))
        controls.addWidget(self.transport_combo)
        controls.addWidget(QtWidgets.QLabel("Device:"))
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
        transport = self.transport_combo.currentData()
        self.device_combo.clear()

        if transport == "usb":
            self.devices = self.usb_service.detect_devices()
            for dev in self.devices:
                label = f"{dev.description} ({dev.port})"
                if dev.vid and dev.pid:
                    label += f" [{dev.vid}:{dev.pid}]"
                self.device_combo.addItem(label, dev)
            if not self.devices:
                self.device_combo.addItem("No USB devices detected", None)
            self.status_label.setText("USB list updated")

        elif transport == "bluetooth" and self.bluetooth_service:
            self.bt_devices = self.bluetooth_service.discover_devices()
            for dev in self.bt_devices:
                label = f"{dev.name} ({dev.address})"
                if dev.rssi is not None:
                    label += f" RSSI {dev.rssi}dBm"
                if dev.is_ble:
                    label += " [BLE]"
                self.device_combo.addItem(label, dev)
            if not self.bt_devices:
                self.device_combo.addItem("No Bluetooth devices detected", None)
            self.status_label.setText("Bluetooth scan complete")

        elif transport == "wifi" and self.wifi_service:
            self.wifi_devices = self.wifi_service.discover_boards()
            for dev in self.wifi_devices:
                label = f"{dev.name} ({dev.host}:{dev.port})"
                if dev.fqbn_hint:
                    label += f" [{dev.fqbn_hint}]"
                self.device_combo.addItem(label, dev)
            if not self.wifi_devices:
                self.device_combo.addItem("No WiFi boards discovered", None)
            self.status_label.setText("WiFi discovery finished")

    def current_connection(self) -> Tuple[str, Optional[object]]:
        return self.transport_combo.currentData(), self.device_combo.currentData()

    def current_device(self) -> Optional[USBDevice]:
        transport, device = self.current_connection()
        if transport == "usb" and isinstance(device, USBDevice):
            return device
        return None

    def _toggle_connection(self, checked: bool) -> None:
        if checked:
            self._connect()
        else:
            self._disconnect()

    def _connect(self) -> None:
        transport, device = self.current_connection()
        if transport == "usb":
            if not isinstance(device, USBDevice):
                self.status_label.setText("Select a USB device before connecting")
                self.connect_button.setChecked(False)
                return
            baud = self.baud_combo.currentData()
            self.session = self.usb_service.start_serial_session(device, int(baud))
            self.status_label.setText(f"Connecting to {device.port}…")
        elif transport == "bluetooth":
            if not self.bluetooth_service or not isinstance(device, BluetoothDevice):
                self.status_label.setText("Select a Bluetooth device before connecting")
                self.connect_button.setChecked(False)
                return
            baud = self.baud_combo.currentData()
            self.session = self.bluetooth_service.start_serial_session(device, int(baud))
            self.status_label.setText(f"Connecting to {device.name}…")
        elif transport == "wifi":
            if not self.wifi_service or not isinstance(device, WiFiBoard):
                self.status_label.setText("Select a WiFi board before connecting")
                self.connect_button.setChecked(False)
                return
            self.session = self.wifi_service.start_serial_session(device)
            self.status_label.setText(f"Connecting to {device.host}…")
        else:
            self.status_label.setText("Unsupported transport")
            self.connect_button.setChecked(False)
            return

        assert self.session is not None
        self.session.line_received.connect(self._handle_line)
        self.session.status.connect(self._update_status)
        self.session.error.connect(self._handle_error)
        self.connection_changed.emit(True)
        self.connect_button.setText("Disconnect")

    def _disconnect(self) -> None:
        transport, device = self.current_connection()
        if transport == "usb" and isinstance(device, USBDevice):
            self.usb_service.stop_serial_session(device)
        elif transport == "bluetooth" and isinstance(device, BluetoothDevice) and self.bluetooth_service:
            self.bluetooth_service.stop_serial_session(device)
        elif transport == "wifi" and isinstance(device, WiFiBoard) and self.wifi_service:
            self.wifi_service.stop_serial_session(device)
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
