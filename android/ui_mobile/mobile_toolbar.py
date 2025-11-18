from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class KeyboardToolbar(QtWidgets.QToolBar):
    """Touch-friendly toolbar offering quick access to coding symbols."""

    symbol_pressed = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__("Keyboard Toolbar", parent)
        self.setMovable(False)
        self.setOrientation(QtCore.Qt.Horizontal)
        self.setIconSize(self.iconSize() * 1.2)
        self._populate_buttons()

    def _populate_buttons(self) -> None:
        symbols = ["{}", "[]", "()", "<>", "=", ";", ",", ".", "&&", "||", "!", "#"]
        for symbol in symbols:
            action = self.addAction(symbol)
            action.triggered.connect(lambda _checked=False, value=symbol: self.symbol_pressed.emit(value))


__all__ = ["KeyboardToolbar"]
