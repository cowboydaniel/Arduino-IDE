"""
Schematic Painter - Rendering engine for schematic objects
Based on KiCad's sch_painter.cpp/h structure
"""

import logging
from typing import Dict, List, Optional

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtCore import Qt

from arduino_ide.models.circuit_domain import (
    ComponentDefinition,
    Pin,
    PinType,
)

logger = logging.getLogger(__name__)


class SchematicPainter:
    """
    Rendering engine for schematic elements.
    Corresponds to KiCad's SCH_PAINTER class.
    """

    # Color scheme matching KiCad
    COLORS = {
        "component_body": QColor("#333333"),
        "component_fill": QColor("#FAFAFA"),
        "pin_default": QColor("#424242"),
        "pin_power": QColor("#F4511E"),
        "pin_ground": QColor("#5D4037"),
        "pin_analog": QColor("#00838F"),
        "pin_pwm": QColor("#6A1B9A"),
        "pin_spi": QColor("#283593"),
        "pin_i2c": QColor("#2E7D32"),
        "pin_serial": QColor("#C62828"),
        "pin_hover": QColor("#00C853"),
        "wire": QColor("#424242"),
        "bus": QColor("#263238"),
        "net_label": QColor("#0277BD"),
        "power_symbol": QColor("#FF6F00"),
        "junction": QColor("#1B5E20"),
        "sheet_pin": QColor("#4E342E"),
        "measurement": QColor("#D81B60"),
    }

    @staticmethod
    def get_pin_color(pin_type: PinType) -> QColor:
        """Get color for pin based on type"""
        mapping = {
            PinType.POWER: SchematicPainter.COLORS["pin_power"],
            PinType.GROUND: SchematicPainter.COLORS["pin_ground"],
            PinType.ANALOG: SchematicPainter.COLORS["pin_analog"],
            PinType.PWM: SchematicPainter.COLORS["pin_pwm"],
            PinType.SPI: SchematicPainter.COLORS["pin_spi"],
            PinType.I2C: SchematicPainter.COLORS["pin_i2c"],
            PinType.SERIAL: SchematicPainter.COLORS["pin_serial"],
        }
        return mapping.get(pin_type, SchematicPainter.COLORS["pin_default"])

    @staticmethod
    def draw_pin(painter: QPainter, pin: Pin, pos: QPointF, hovered: bool = False):
        """Draw a schematic pin"""
        painter.setRenderHint(QPainter.Antialiasing)
        color = SchematicPainter.COLORS["pin_hover"] if hovered else SchematicPainter.get_pin_color(pin.pin_type)
        painter.setPen(QPen(color, 1.6))

        start, end = SchematicPainter._get_pin_line(pin, pos)
        painter.drawLine(start, end)

        # Draw pin decoration
        if pin.decoration == "clock":
            arc_rect = QRectF(end.x() - 6, end.y() - 6, 12, 12)
            path = QPainterPath()
            path.arcMoveTo(arc_rect, 0)
            path.arcTo(arc_rect, 0, 270)
            painter.drawPath(path)
        elif pin.decoration == "dot":
            painter.setBrush(color)
            painter.drawEllipse(end, 2.5, 2.5)
        elif pin.decoration == "triangle":
            triangle = QPolygonF([end, end + QPointF(-8, -5), end + QPointF(-8, 5)])
            painter.setBrush(color)
            painter.drawPolygon(triangle)

    @staticmethod
    def _get_pin_line(pin: Pin, base_pos: QPointF) -> tuple:
        """Get pin line coordinates based on orientation"""
        length = max(10.0, pin.length)
        pin_pos = QPointF(pin.position[0], pin.position[1])
        start = base_pos + pin_pos

        if pin.orientation == "right":
            return start, start + QPointF(length, 0)
        elif pin.orientation == "up":
            return start, start + QPointF(0, -length)
        elif pin.orientation == "down":
            return start, start + QPointF(0, length)
        else:  # left
            return start + QPointF(-length, 0), start

    @staticmethod
    def draw_component_body(
        painter: QPainter,
        graphics: List[Dict],
        width: float,
        height: float,
    ):
        """Draw component body from graphics primitives"""
        painter.setRenderHint(QPainter.Antialiasing)

        if not graphics:
            # Default rectangle if no graphics defined
            graphics = [
                {
                    "type": "rect",
                    "rect": [0, 0, width, height],
                    "pen": "#333333",
                    "width": 2,
                    "fill": "#FAFAFA",
                }
            ]

        for shape in graphics:
            pen_color = shape.get("pen", "#333333")
            pen_width = float(shape.get("width", 1.5))
            pen = QPen(QColor(pen_color), pen_width)
            pen.setJoinStyle(Qt.MiterJoin)
            painter.setPen(pen)

            fill_color = shape.get("fill")
            if fill_color:
                painter.setBrush(QColor(fill_color))
            else:
                painter.setBrush(Qt.NoBrush)

            shape_type = shape.get("type", "rect")

            if shape_type == "rect":
                rect = QRectF(*shape.get("rect", [0, 0, width, height]))
                painter.drawRect(rect)

            elif shape_type == "polygon":
                points = [QPointF(p[0], p[1]) for p in shape.get("points", [])]
                if points:
                    painter.drawPolygon(QPolygonF(points))

            elif shape_type == "arc":
                rect = QRectF(*shape.get("rect", [0, 0, width, height]))
                start = float(shape.get("start", 0))
                span = float(shape.get("span", 90))
                painter.drawArc(rect, int(start * 16), int(span * 16))

            elif shape_type == "circle":
                cx, cy = shape.get("center", [0, 0])
                radius = float(shape.get("radius", 10))
                painter.drawEllipse(QPointF(cx, cy), radius, radius)

    @staticmethod
    def create_wire_path(start: QPointF, end: QPointF) -> QPainterPath:
        """Create orthogonal wire routing path"""
        path = QPainterPath(start)
        mid = QPointF(start.x(), end.y())
        if abs(start.x() - end.x()) < abs(start.y() - end.y()):
            mid = QPointF(end.x(), start.y())
        path.lineTo(mid)
        path.lineTo(end)
        return path

    @staticmethod
    def draw_wire(painter: QPainter, start: QPointF, end: QPointF, is_bus: bool = False):
        """Draw wire or bus"""
        painter.setRenderHint(QPainter.Antialiasing)
        color = SchematicPainter.COLORS["bus"] if is_bus else SchematicPainter.COLORS["wire"]
        width = 3 if is_bus else 2
        pen = QPen(color, width)
        if is_bus:
            pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        path = SchematicPainter.create_wire_path(start, end)
        painter.drawPath(path)

    @staticmethod
    def draw_junction(painter: QPainter, pos: QPointF):
        """Draw junction dot"""
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(SchematicPainter.COLORS["junction"])
        painter.setPen(QPen(Qt.NoPen))
        painter.drawEllipse(pos, 4, 4)

    @staticmethod
    def draw_net_label(painter: QPainter, pos: QPointF, text: str):
        """Draw net label"""
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(SchematicPainter.COLORS["net_label"])
        painter.drawText(pos, text)

    @staticmethod
    def draw_power_symbol(painter: QPainter, pos: QPointF, text: str):
        """Draw power symbol"""
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw triangle
        path = QPainterPath(pos)
        path.lineTo(pos + QPointF(10, 12))
        path.lineTo(pos + QPointF(-10, 12))
        path.closeSubpath()

        painter.setBrush(SchematicPainter.COLORS["power_symbol"])
        painter.setPen(QPen(Qt.NoPen))
        painter.drawPath(path)

        # Draw text
        painter.setPen(SchematicPainter.COLORS["power_symbol"])
        painter.drawText(pos + QPointF(-10, -5), text)
