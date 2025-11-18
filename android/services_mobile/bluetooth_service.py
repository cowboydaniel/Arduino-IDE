"""Bluetooth service placeholder for Android builds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class BluetoothDevice:
    name: str
    address: str


class BluetoothService:
    """Simple registry of discovered Bluetooth devices."""

    def __init__(self) -> None:
        self._devices: list[BluetoothDevice] = []

    def add_device(self, device: BluetoothDevice) -> None:
        if device not in self._devices:
            self._devices.append(device)

    def iter_devices(self) -> Iterable[BluetoothDevice]:
        return tuple(self._devices)
