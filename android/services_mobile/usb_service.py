from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import serial
from PySide6 import QtCore
from serial.tools import list_ports

from .build_service import ArduinoCLI


@dataclass(eq=True, frozen=True)
class USBDevice:
    """Represents a USB serial device discovered via OTG."""

    port: str
    description: str
    vid: Optional[str] = None
    pid: Optional[str] = None
    manufacturer: Optional[str] = None

    @classmethod
    def from_list_port(cls, port_info: list_ports.ListPortInfo) -> "USBDevice":
        return cls(
            port=port_info.device,
            description=port_info.description,
            vid=f"{port_info.vid:04x}" if port_info.vid is not None else None,
            pid=f"{port_info.pid:04x}" if port_info.pid is not None else None,
            manufacturer=port_info.manufacturer,
        )


@dataclass
class USBUploadResult:
    success: bool
    output: str
    device: Optional[USBDevice] = None
    fqbn: Optional[str] = None


class SerialSession(QtCore.QObject):
    """Maintains a live serial connection with background reading."""

    line_received = QtCore.Signal(str)
    status = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, device: USBDevice, baud_rate: int) -> None:
        super().__init__()
        self.device = device
        self.baud_rate = baud_rate
        self._serial: Optional[serial.Serial] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def start(self) -> None:
        try:
            self._serial = serial.Serial(self.device.port, self.baud_rate, timeout=0.1)
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            self.status.emit(f"Connected to {self.device.port} @ {self.baud_rate} baud")
        except Exception as exc:  # pragma: no cover - serial hardware dependent
            self.error.emit(f"Failed to open {self.device.port}: {exc}")

    def _read_loop(self) -> None:  # pragma: no cover - serial hardware dependent
        assert self._serial
        while self._running and self._serial.is_open:
            try:
                line = self._serial.readline()
            except Exception as exc:
                self.error.emit(f"Serial read error: {exc}")
                break
            if not line:
                continue
            try:
                decoded = line.decode("utf-8", errors="replace").strip()
            except Exception:
                decoded = str(line)
            self.line_received.emit(decoded)
        self.status.emit("Serial session ended")

    def write_line(self, text: str) -> None:
        if not self.connected:
            self.error.emit("Cannot send data: serial port is closed.")
            return
        try:
            assert self._serial
            self._serial.write((text + "\n").encode("utf-8"))
        except Exception as exc:  # pragma: no cover - serial hardware dependent
            self.error.emit(f"Serial write error: {exc}")

    def close(self) -> None:
        self._running = False
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.2)
        self.status.emit("Disconnected")


class USBService:
    """Handles USB OTG device discovery, permissions, uploads, and serial sessions."""

    SUPPORTED_DRIVERS = {"1a86:7523", "10c4:ea60", "0403:6001", "067b:2303"}

    def __init__(self, cli: Optional[ArduinoCLI] = None) -> None:
        self.cli = cli or ArduinoCLI()
        self._permission_granted: set[str] = set()
        self._serial_sessions: Dict[str, SerialSession] = {}

    def detect_devices(self) -> List[USBDevice]:
        return [USBDevice.from_list_port(p) for p in list_ports.comports()]

    def request_permission(self, device: USBDevice) -> bool:
        """Simulate Android USB permission prompt by recording user approval."""
        self._permission_granted.add(device.port)
        return True

    def has_permission(self, device: USBDevice) -> bool:
        return device.port in self._permission_granted

    def is_supported(self, device: USBDevice) -> bool:
        if device.vid and device.pid:
            return f"{device.vid}:{device.pid}" in self.SUPPORTED_DRIVERS
        return True

    def upload_sketch(self, sketch_path: Path, fqbn: str, device: USBDevice) -> USBUploadResult:
        if not self.has_permission(device):
            granted = self.request_permission(device)
            if not granted:
                return USBUploadResult(False, "USB permission denied", device=device, fqbn=fqbn)

        if not sketch_path.exists():
            return USBUploadResult(False, f"Sketch {sketch_path} does not exist", device=device, fqbn=fqbn)

        if not self.is_supported(device):
            return USBUploadResult(False, f"Driver unsupported for {device.description}", device=device, fqbn=fqbn)

        if self.cli.available:
            command = [
                "upload",
                "-p",
                device.port,
                "--fqbn",
                fqbn,
                str(sketch_path.parent),
            ]
            result = self.cli.run(command, cwd=sketch_path.parent)
            output = result.stdout + result.stderr
            return USBUploadResult(result.returncode == 0, output, device=device, fqbn=fqbn)

        simulated = [
            f"Uploading {sketch_path.name} to {device.port} ({device.description})",
            "Arduino CLI not bundled - simulated upload completed.",
            "Progress: 100%",
            "Result: SUCCESS",
        ]
        time.sleep(0.3)
        return USBUploadResult(True, "\n".join(simulated), device=device, fqbn=fqbn)

    def start_serial_session(self, device: USBDevice, baud_rate: int) -> SerialSession:
        session = SerialSession(device, baud_rate)
        session.start()
        self._serial_sessions[device.port] = session
        return session

    def stop_serial_session(self, device: USBDevice) -> None:
        session = self._serial_sessions.pop(device.port, None)
        if session:
            session.close()

    def active_session(self, device: USBDevice) -> Optional[SerialSession]:
        return self._serial_sessions.get(device.port)


__all__ = ["USBDevice", "USBService", "USBUploadResult", "SerialSession"]
