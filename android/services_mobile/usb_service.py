"""USB OTG service placeholder for the Android build."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class UsbDevice:
    vendor_id: int
    product_id: int
    description: str


class UsbService:
    """Stub OTG handler that records device attachments."""

    def __init__(self) -> None:
        self._seen: list[UsbDevice] = []

    def on_device_attached(self, device: UsbDevice) -> None:
        self._seen.append(device)

    def iter_devices(self) -> Iterable[UsbDevice]:
        return tuple(self._seen)
