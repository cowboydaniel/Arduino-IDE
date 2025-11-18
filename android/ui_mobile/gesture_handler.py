from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from .touch_editor import TouchEditor


class GestureHandler(QtCore.QObject):
    """Handles pinch gestures for touch-friendly font scaling."""

    def __init__(self, editor: TouchEditor) -> None:
        super().__init__(editor)
        self.editor = editor
        self.editor.grabGesture(QtCore.Qt.PinchGesture)
        self.base_font_size = editor.font().pointSizeF()

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:  # noqa: N802
        if event.type() == QtCore.QEvent.Gesture and isinstance(event, QtGui.QGestureEvent):
            pinch = event.gesture(QtCore.Qt.PinchGesture)
            if pinch:
                self.handle_pinch(pinch)
                return True
        return super().eventFilter(obj, event)

    def handle_pinch(self, pinch: QtGui.QPinchGesture) -> None:
        factor = pinch.scaleFactor()
        delta = factor - 1
        font = self.editor.font()
        new_size = max(10.0, min(28.0, self.base_font_size + delta * 6))
        font.setPointSizeF(new_size)
        self.editor.setFont(font)

        if pinch.state() == QtCore.Qt.GestureFinished:
            self.base_font_size = new_size


__all__ = ["GestureHandler"]
