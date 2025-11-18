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
class WiFiBoard:
    """Represents a WiFi-capable board discoverable via mDNS."""

    name: str
    host: str
    port: int = 3232
    fqbn_hint: Optional[str] = None


class WiFiSerialSession(QtCore.QObject):
    """Simulated WiFi debug session (e.g., Telnet/GDB proxy)."""

    line_received = QtCore.Signal(str)
    status = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, board: WiFiBoard) -> None:
        super().__init__()
        self.board = board
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def connected(self) -> bool:
        return self._running

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        self.status.emit(f"Connected to {self.board.name} @ {self.board.host}:{self.board.port}")

    def _read_loop(self) -> None:  # pragma: no cover - network/hardware dependent
        messages = [
            "WiFi debug stream started",
            "Heap: 182kB",
            "OTA ready",
            "mDNS: esp32.local",
        ]
        while self._running:
            self.line_received.emit(random.choice(messages))
            time.sleep(1.5)
        self.status.emit("WiFi session ended")

    def write_line(self, text: str) -> None:
        if not self.connected:
            self.error.emit("WiFi debug channel is closed.")
            return
        self.line_received.emit(f"[tx] {text}")

    def close(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.25)
        self.status.emit("Disconnected")


class WiFiService(QtCore.QObject):
    """Supports WiFi board discovery, OTA uploads, and debug streams."""

    devices_changed = QtCore.Signal(list)

    def __init__(self, cli: Optional[ArduinoCLI] = None) -> None:
        super().__init__()
        self.cli = cli or ArduinoCLI()
        self._sessions: dict[str, WiFiSerialSession] = {}

    def discover_boards(self) -> List[WiFiBoard]:
        """Discover WiFi-enabled boards via mDNS (simulated offline)."""

        simulated = [
            WiFiBoard("ESP32 OTA", "esp32.local", fqbn_hint="esp32:esp32:esp32"),
            WiFiBoard("ESP8266 OTA", "esp8266.local", port=8266, fqbn_hint="esp8266:esp8266:nodemcuv2"),
        ]
        self.devices_changed.emit(simulated)
        return simulated

    def start_serial_session(self, board: WiFiBoard) -> WiFiSerialSession:
        session = WiFiSerialSession(board)
        session.start()
        self._sessions[board.host] = session
        return session

    def stop_serial_session(self, board: WiFiBoard) -> None:
        session = self._sessions.pop(board.host, None)
        if session:
            session.close()

    def ota_upload(self, sketch_path: Path, fqbn: str, board: WiFiBoard) -> str:
        if not sketch_path.exists():
            return f"Sketch {sketch_path} does not exist"

        if self.cli.available:
            command = ["upload", "--fqbn", fqbn, "--port", f"network:{board.host}:{board.port}", str(sketch_path.parent)]
            result = self.cli.run(command, cwd=sketch_path.parent)
            return result.stdout + result.stderr

        steps = [
            f"Connecting to {board.host}:{board.port} for OTA",
            "Resolving mDNS host...",
            "Uploading binary...",
            "Rebooting board...",
            "OTA upload complete (simulated)",
        ]
        return "\n".join(steps)


__all__ = ["WiFiBoard", "WiFiService", "WiFiSerialSession"]
