"""
Schematic Graphics Items - Qt Graphics items for schematic objects
Based on KiCad's widget structure
"""

import logging
from typing import Dict, List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsTextItem,
)

from arduino_ide.models.circuit_domain import (
    ComponentDefinition,
    ComponentInstance,
    Connection,
    Pin,
    PinType,
)
from arduino_ide.eeschema.sch_painter import SchematicPainter

logger = logging.getLogger(__name__)


class PinGraphicsItem(QGraphicsItem):
    """Graphics representation of a schematic pin"""

    def __init__(self, pin: Pin, color: QColor, parent: Optional[QGraphicsItem] = None):
        super().__init__(parent)
        self.pin = pin
        self.pin_color = color
        self._hovered = False
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CrossCursor)
        self.setZValue(2)

    def boundingRect(self) -> QRectF:  # type: ignore[override]
        length = max(10.0, self.pin.length)
        if self.pin.orientation in ("up", "down"):
            return QRectF(-6, -length - 6, 12, length + 12)
        return QRectF(-length - 6, -6, length + 12, 12)

    def paint(self, painter: QPainter, option, widget=None):  # type: ignore[override]
        SchematicPainter.draw_pin(painter, self.pin, QPointF(0, 0), self._hovered)

    def hoverEnterEvent(self, event):  # type: ignore[override]
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):  # type: ignore[override]
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            parent = self.parentItem()
            if parent and hasattr(parent, "comp_instance"):
                view = self.scene().views()[0]
                if hasattr(view, "on_pin_clicked"):
                    view.on_pin_clicked(
                        parent.comp_instance.instance_id,
                        self.pin.id,
                        self.scenePos(),
                    )
            event.accept()
        else:
            super().mousePressEvent(event)


class ComponentGraphicsItem(QGraphicsItem):
    """KiCAD style symbol rendering"""

    def __init__(
        self,
        comp_def: ComponentDefinition,
        comp_instance: ComponentInstance,
        parent: Optional[QGraphicsItem] = None,
    ):
        super().__init__(parent)
        self.comp_def = comp_def
        self.comp_instance = comp_instance
        self._resolved_pins: List[Pin] = list(comp_def.pins)
        self._width = comp_def.width
        self._height = comp_def.height
        self._graphics_cache: List[Dict] = []
        self.pin_items: Dict[str, PinGraphicsItem] = {}
        self.label_item = QGraphicsTextItem(comp_def.name, self)
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        self.label_item.setFont(font)
        self.label_item.setDefaultTextColor(Qt.black)

        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self._rebuild_graphics()
        self.setPos(comp_instance.x, comp_instance.y)
        self.setRotation(comp_instance.rotation)

    def boundingRect(self) -> QRectF:  # type: ignore[override]
        return self._bounding_rect

    def paint(self, painter: QPainter, option, widget=None):  # type: ignore[override]
        painter.setRenderHint(QPainter.Antialiasing)
        for entry in self._graphics_cache:
            painter.setPen(entry["pen"])
            painter.setBrush(entry.get("brush", Qt.NoBrush))
            painter.drawPath(entry["path"])

    def _rebuild_graphics(self):
        self.prepareGeometryChange()
        graphics = self._resolve_graphics()

        self._graphics_cache.clear()
        overall_rect = QRectF()

        for shape in (graphics or []):
            pen = QPen(QColor(shape.get("pen", "#333333")), float(shape.get("width", 1.5)))
            pen.setJoinStyle(Qt.MiterJoin)
            brush_color = shape.get("fill")
            brush = Qt.NoBrush if not brush_color else QColor(brush_color)
            path = self._create_shape_path(shape)

            self._graphics_cache.append({"pen": pen, "brush": brush, "path": path})
            if overall_rect.isNull():
                overall_rect = path.boundingRect()
            else:
                overall_rect = overall_rect.united(path.boundingRect())

        if overall_rect.isNull():
            overall_rect = QRectF(0, 0, self._width, self._height)
        self._bounding_rect = overall_rect.adjusted(-6, -6, 6, 6)

        self._rebuild_pins(graphics or [])

    def _create_shape_path(self, shape: Dict) -> QPainterPath:
        """Create QPainterPath from shape definition"""
        path = QPainterPath()
        shape_type = shape.get("type", "rect")

        if shape_type == "rect":
            rect = QRectF(*shape.get("rect", [0, 0, self._width, self._height]))
            path.addRect(rect)
        elif shape_type == "polygon":
            from PySide6.QtGui import QPolygonF
            points = [QPointF(p[0], p[1]) for p in shape.get("points", [])]
            if points:
                path.addPolygon(QPolygonF(points))
        elif shape_type == "arc":
            rect = QRectF(*shape.get("rect", [0, 0, self._width, self._height]))
            start = float(shape.get("start", 0))
            span = float(shape.get("span", 90))
            path.arcMoveTo(rect, start)
            path.arcTo(rect, start, span)
        elif shape_type == "circle":
            cx, cy = shape.get("center", [0, 0])
            radius = float(shape.get("radius", 10))
            path.addEllipse(QPointF(cx, cy), radius, radius)

        return path

    def _resolve_graphics(self) -> List[Dict]:
        unit_id = self.comp_instance.properties.get("unit")
        if not self.comp_def.units:
            self._resolved_pins = list(self.comp_def.pins)
            return self.comp_def.graphics

        if unit_id:
            for unit in self.comp_def.units:
                if unit.get("id") == unit_id:
                    self._apply_unit_override(unit)
                    return unit.get("graphics", self.comp_def.graphics)

        default_unit = self.comp_def.units[0]
        self.comp_instance.properties["unit"] = default_unit.get("id", "unit_1")
        self._apply_unit_override(default_unit)
        return default_unit.get("graphics", self.comp_def.graphics)

    def _apply_unit_override(self, unit_def: Dict):
        self._width = unit_def.get("width", self.comp_def.width)
        self._height = unit_def.get("height", self.comp_def.height)
        if unit_def.get("pins"):
            pins: List[Pin] = []
            for pin_data in unit_def["pins"]:
                try:
                    pin_type = PinType(pin_data.get("pin_type", PinType.DIGITAL.value))
                except ValueError:
                    pin_type = PinType.DIGITAL
                pins.append(
                    Pin(
                        id=pin_data["id"],
                        label=pin_data.get("label", pin_data["id"]),
                        pin_type=pin_type,
                        position=(pin_data.get("position", [0, 0])[0], pin_data.get("position", [0, 0])[1]),
                        length=float(pin_data.get("length", 20)),
                        orientation=pin_data.get("orientation", "left"),
                        decoration=pin_data.get("decoration", "line"),
                    )
                )
            self._resolved_pins = pins
        else:
            self._resolved_pins = list(self.comp_def.pins)

    def _rebuild_pins(self, graphics: List[Dict]):
        for pin_item in list(self.pin_items.values()):
            pin_item.setParentItem(None)
            pin_item.scene().removeItem(pin_item) if pin_item.scene() else None
        self.pin_items.clear()

        for pin in self._resolved_pins:
            color = SchematicPainter.get_pin_color(pin.pin_type)
            pin_item = PinGraphicsItem(pin, color, self)
            pin_item.setPos(pin.position[0], pin.position[1])
            self.pin_items[pin.id] = pin_item

        bounds = self.boundingRect()
        self.label_item.setPos(bounds.center().x() - self.label_item.boundingRect().width() / 2, bounds.top() - 14)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):  # type: ignore[override]
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            view = self.scene().views()[0]
            if hasattr(view, "on_component_moved"):
                view.on_component_moved(self.comp_instance.instance_id, self.pos())
        return super().itemChange(change, value)

    def get_pin_scene_pos(self, pin_id: str) -> Optional[QPointF]:
        if pin_id not in self.pin_items:
            return None
        return self.pin_items[pin_id].scenePos()


class ConnectionGraphicsItem(QGraphicsPathItem):
    """Orthogonal wire/bus rendering"""

    def __init__(self, connection: Connection, start_pos: QPointF, end_pos: QPointF, parent=None):
        super().__init__(parent)
        self.connection = connection
        path = SchematicPainter.create_wire_path(start_pos, end_pos)
        self.setPath(path)
        color = QColor(connection.wire_color)
        width = 3 if connection.connection_type == "bus" else 2
        pen = QPen(color, width)
        if connection.connection_type == "bus":
            pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)
        self.setZValue(-1)
