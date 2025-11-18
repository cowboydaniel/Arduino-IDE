"""Gesture helpers for the mobile UI surface."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class GestureHandler(QObject):
    """Emits signals for common mobile gestures so widgets can subscribe."""

    pinch = Signal(float)
    swipe = Signal(str)

    def emit_pinch(self, scale: float) -> None:
        self.pinch.emit(scale)

    def emit_swipe(self, direction: str) -> None:
        self.swipe.emit(direction)
