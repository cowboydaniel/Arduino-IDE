"""Minimal placeholder touch editor for Phase 0 packaging.

The real editor is implemented in the desktop package; this module ensures the
Android asset bundle contains a touch-aware wrapper that can evolve in later
phases without changing the Gradle plumbing.
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class TouchEditor(QWidget):
    """Stub touch editor used to validate the Android deployment pipeline."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        placeholder = QLabel(
            "Touch editor placeholder. Phase 1+ replaces this with the full UI."
        )
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)
