from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PySide6 import QtCore

from .build_service import ArduinoCLI


@dataclass(eq=True, frozen=True)
class BluetoothDevice:
    """Represents a Bluetooth peripheral that can provide serial data."""

    name: str
    address: str
    rssi: Optional[int] = None
    is_ble: bool = False


class BluetoothSerialSession(QtCore.QObject):
    """Maintains a simulated Bluetooth serial session with RX/TX support."""

    line_received = QtCore.Signal(str)
    status = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, device: BluetoothDevice, baud_rate: int = 115200) -> None:
        super().__init__()
        self.device = device
        self.baud_rate = baud_rate
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def connected(self) -> bool:
        return self._running

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        transport = "BLE" if self.device.is_ble else "Bluetooth"
        self.status.emit(f"Connected to {self.device.name} via {transport} @ {self.baud_rate} baud")

    def _read_loop(self) -> None:  # pragma: no cover - hardware dependent
        """Simulate incoming data from the Bluetooth module."""

        while self._running:
            payload = random.choice(
                [
                    "\n",
                    "OK",
                    "READY",
                    "RSSI=-70",
                    "Ping",
                    "RX Notification",
                ]
            )
            self.line_received.emit(payload)
            time.sleep(1.2)
        self.status.emit("Bluetooth session ended")

    def write_line(self, text: str) -> None:
        if not self.connected:
            self.error.emit("Cannot send data: Bluetooth link is closed.")
            return
        self.line_received.emit(f"[tx] {text}")

    def close(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.25)
        self.status.emit("Disconnected")


class BluetoothService(QtCore.QObject):
    """Handles Bluetooth Classic and BLE discovery, pairing, and serial sessions."""

    devices_changed = QtCore.Signal(list)

    def __init__(self, cli: Optional[ArduinoCLI] = None) -> None:
        super().__init__()
        self.cli = cli or ArduinoCLI()
        self._paired: set[str] = set()
        self._sessions: dict[str, BluetoothSerialSession] = {}

    def discover_devices(self) -> List[BluetoothDevice]:
        """Scan for Bluetooth Classic and BLE devices.

        In this offline environment the scan is simulated with deterministic devices.
        """

        simulated = [
            BluetoothDevice("HC-05", "00:11:22:33:44:55", rssi=-60, is_ble=False),
            BluetoothDevice("ESP32-BLE", "aa:bb:cc:dd:ee:ff", rssi=-72, is_ble=True),
        ]
        self.devices_changed.emit(simulated)
        return simulated

    def pair(self, device: BluetoothDevice) -> bool:
        self._paired.add(device.address)
        return True

    def is_paired(self, device: BluetoothDevice) -> bool:
        return device.address in self._paired

    def start_serial_session(self, device: BluetoothDevice, baud_rate: int = 115200) -> BluetoothSerialSession:
        if not self.is_paired(device):
            self.pair(device)
        session = BluetoothSerialSession(device, baud_rate)
        session.start()
        self._sessions[device.address] = session
        return session

    def stop_serial_session(self, device: BluetoothDevice) -> None:
        session = self._sessions.pop(device.address, None)
        if session:
            session.close()

    def upload_sketch(self, sketch_path: Path, fqbn: str, device: BluetoothDevice) -> str:
        """Simulate Bluetooth-based upload by delegating to Arduino CLI when present."""

        if not sketch_path.exists():
            return f"Sketch {sketch_path} does not exist"

        if self.cli.available:
            command = ["upload", "--fqbn", fqbn, str(sketch_path.parent)]
            result = self.cli.run(command, cwd=sketch_path.parent)
            return result.stdout + result.stderr

        steps = [
            f"Starting OTA over Bluetooth to {device.name} ({device.address})",
            "Negotiating SPP/BLE link...",
            "Transferring binary...",
            "Upload complete (simulated)",
        ]
        return "\n".join(steps)


__all__ = ["BluetoothDevice", "BluetoothService", "BluetoothSerialSession"]
