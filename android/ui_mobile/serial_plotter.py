from __future__ import annotations

from collections import deque
import re
from typing import Deque

from PySide6 import QtWidgets
import pyqtgraph as pg


class SerialPlotterWidget(QtWidgets.QWidget):
    """Real-time serial plotter optimized for touch interactions."""

    def __init__(self, max_points: int = 500, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.max_points = max_points
        self.values: Deque[float] = deque(maxlen=max_points)
        self.x_axis: Deque[int] = deque(maxlen=max_points)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("left", "Value")
        self.plot_widget.setLabel("bottom", "Sample")
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color=(120, 200, 255), width=2))
        self.plot_widget.setClipToView(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.plot_widget)

    def append_line(self, line: str) -> None:
        match = re.search(r"-?\d+(?:\.\d+)?", line)
        if not match:
            return
        value = float(match.group(0))
        next_index = self.x_axis[-1] + 1 if self.x_axis else 0
        self.values.append(value)
        self.x_axis.append(next_index)
        self.curve.setData(list(self.x_axis), list(self.values))


__all__ = ["SerialPlotterWidget"]
