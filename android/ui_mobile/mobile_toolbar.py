"""Touch-friendly toolbar placeholders for the Android editor."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton


class MobileToolbar(QWidget):
    """Simplified toolbar with mobile-friendly affordances."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        for label in ("Copy", "Paste", "Undo", "Redo"):
            button = QPushButton(label)
            button.setObjectName(f"mobileToolbar{label}")
            layout.addWidget(button)
