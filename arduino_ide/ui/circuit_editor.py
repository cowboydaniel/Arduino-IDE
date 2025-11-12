"""
Circuit Editor
KiCAD-inspired circuit editor with advanced tooling
"""

from __future__ import annotations

import copy
import logging
import math
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt, QLineF, QObject, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QFont,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QToolBox,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from arduino_ide.services.circuit_service import (
    CircuitService,
    ComponentDefinition,
    ComponentInstance,
    Connection,
    Pin,
    PinType,
    Sheet,
)

logger = logging.getLogger(__name__)


class ToolMode(Enum):
    """Interaction modes for the workspace"""

    SELECT = auto()
    WIRE = auto()
    BUS = auto()
    NET_LABEL = auto()
    POWER_SYMBOL = auto()
    JUNCTION = auto()
    SHEET_PIN = auto()
    MEASURE = auto()


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
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor("#00C853") if self._hovered else self.pin_color
        painter.setPen(QPen(color, 1.6))

        start, end = self._orientation_line()
        painter.drawLine(start, end)

        if self.pin.decoration == "clock":
            arc_rect = QRectF(end.x() - 6, end.y() - 6, 12, 12)
            path = QPainterPath()
            path.arcMoveTo(arc_rect, 0)
            path.arcTo(arc_rect, 0, 270)
            painter.drawPath(path)
        elif self.pin.decoration == "dot":
            painter.setBrush(color)
            painter.drawEllipse(end, 2.5, 2.5)
        elif self.pin.decoration == "triangle":
            triangle = QPolygonF([end, end + QPointF(-8, -5), end + QPointF(-8, 5)])
            painter.setBrush(color)
            painter.drawPolygon(triangle)

    def _orientation_line(self) -> Tuple[QPointF, QPointF]:
        length = max(10.0, self.pin.length)
        if self.pin.orientation == "right":
            return QPointF(0, 0), QPointF(length, 0)
        if self.pin.orientation == "up":
            return QPointF(0, 0), QPointF(0, -length)
        if self.pin.orientation == "down":
            return QPointF(0, 0), QPointF(0, length)
        return QPointF(-length, 0), QPointF(0, 0)

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
        if not graphics:
            graphics = [
                {
                    "type": "rect",
                    "rect": [0, 0, self._width, self._height],
                    "pen": "#333333",
                    "width": 2,
                    "fill": "#FAFAFA",
                }
            ]

        self._graphics_cache.clear()
        overall_rect = QRectF()
        for shape in graphics:
            pen = QPen(QColor(shape.get("pen", "#333333")), float(shape.get("width", 1.5)))
            pen.setJoinStyle(Qt.MiterJoin)
            brush_color = shape.get("fill")
            brush = Qt.NoBrush if not brush_color else QColor(brush_color)
            path = QPainterPath()
            shape_type = shape.get("type", "rect")
            if shape_type == "rect":
                rect = QRectF(*shape.get("rect", [0, 0, self._width, self._height]))
                path.addRect(rect)
            elif shape_type == "polygon":
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

            self._graphics_cache.append({"pen": pen, "brush": brush, "path": path})
            if overall_rect.isNull():
                overall_rect = path.boundingRect()
            else:
                overall_rect = overall_rect.united(path.boundingRect())

        if overall_rect.isNull():
            overall_rect = QRectF(0, 0, self._width, self._height)
        self._bounding_rect = overall_rect.adjusted(-6, -6, 6, 6)

        self._rebuild_pins(graphics)

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
            color = self._pin_color(pin.pin_type)
            pin_item = PinGraphicsItem(pin, color, self)
            pin_item.setPos(pin.position[0], pin.position[1])
            self.pin_items[pin.id] = pin_item

        bounds = self.boundingRect()
        self.label_item.setPos(bounds.center().x() - self.label_item.boundingRect().width() / 2, bounds.top() - 14)

    def _pin_color(self, pin_type: PinType) -> QColor:
        mapping = {
            PinType.POWER: QColor("#F4511E"),
            PinType.GROUND: QColor("#5D4037"),
            PinType.ANALOG: QColor("#00838F"),
            PinType.PWM: QColor("#6A1B9A"),
            PinType.SPI: QColor("#283593"),
            PinType.I2C: QColor("#2E7D32"),
            PinType.SERIAL: QColor("#C62828"),
        }
        return mapping.get(pin_type, QColor("#424242"))

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
        path = QPainterPath(start_pos)
        mid = QPointF(start_pos.x(), end_pos.y())
        if abs(start_pos.x() - end_pos.x()) < abs(start_pos.y() - end_pos.y()):
            mid = QPointF(end_pos.x(), start_pos.y())
        path.lineTo(mid)
        path.lineTo(end_pos)
        self.setPath(path)
        color = QColor(connection.wire_color)
        width = 3 if connection.connection_type == "bus" else 2
        pen = QPen(color, width)
        if connection.connection_type == "bus":
            pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)
        self.setZValue(-1)


class ComponentLibraryWidget(QWidget):
    """Dockable widget exposing the symbol library"""

    component_selected = Signal(str)

    def __init__(self, service: CircuitService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        title = QLabel("Symbol Chooser")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)
        self.toolbox = QToolBox()
        layout.addWidget(self.toolbox)
        self._populate()

    def _populate(self):
        self.toolbox.clear()
        grouped: Dict[str, List[ComponentDefinition]] = {}
        for comp in self.service.get_all_component_definitions():
            grouped.setdefault(comp.component_type.value, []).append(comp)
        for comp_type, comps in sorted(grouped.items()):
            category_widget = QWidget()
            cat_layout = QVBoxLayout(category_widget)
            for comp_def in comps:
                button = QPushButton(comp_def.name)
                button.setToolTip(comp_def.description)
                button.clicked.connect(lambda checked=False, cid=comp_def.id: self.component_selected.emit(cid))
                cat_layout.addWidget(button)
            cat_layout.addStretch()
            self.toolbox.addItem(category_widget, comp_type.replace("_", " ").title())


class PropertyInspectorWidget(QWidget):
    """Inspector for the currently selected symbol"""

    def __init__(self, service: CircuitService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = service
        self._current_component: Optional[str] = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        title = QLabel("Property Inspector")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)
        self.form = QFormLayout()
        self.ref_input = QLineEdit()
        self.ref_input.editingFinished.connect(self._on_reference_changed)
        self.value_input = QLineEdit()
        self.value_input.editingFinished.connect(self._on_value_changed)
        self.unit_combo = QComboBox()
        self.unit_combo.currentTextChanged.connect(self._on_unit_changed)
        self.form.addRow("Reference", self.ref_input)
        self.form.addRow("Value", self.value_input)
        self.form.addRow("Unit", self.unit_combo)
        layout.addLayout(self.form)
        self.hint_label = QLabel("Select a component to edit its properties.")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)
        layout.addStretch()

    def display_component(self, component_id: Optional[str]):
        self._current_component = component_id
        if not component_id:
            self.ref_input.clear()
            self.value_input.clear()
            self.unit_combo.clear()
            self.hint_label.setText("Select a component to edit its properties.")
            return

        comp = self.service.get_component_instance(component_id)
        if not comp:
            return
        comp_def = self.service.get_component_definition(comp.definition_id)
        if not comp_def:
            return
        self.hint_label.setText(f"Editing {comp_def.name} ({component_id})")
        self.ref_input.setText(comp.properties.get("reference", component_id))
        self.value_input.setText(comp.properties.get("value", ""))
        self.unit_combo.blockSignals(True)
        self.unit_combo.clear()
        if comp_def.units:
            for unit in comp_def.units:
                unit_id = unit.get("id", "unit")
                self.unit_combo.addItem(unit.get("name", unit_id), unit_id)
            current_unit = comp.properties.get("unit")
            if current_unit:
                index = self.unit_combo.findData(current_unit)
                if index >= 0:
                    self.unit_combo.setCurrentIndex(index)
        else:
            self.unit_combo.addItem("Standard", "default")
        self.unit_combo.blockSignals(False)

    def _on_reference_changed(self):
        if not self._current_component:
            return
        self.service.update_component_properties(
            self._current_component,
            {"reference": self.ref_input.text().strip()},
        )

    def _on_value_changed(self):
        if not self._current_component:
            return
        self.service.update_component_properties(
            self._current_component,
            {"value": self.value_input.text().strip()},
        )

    def _on_unit_changed(self, unit_id: str):
        if not self._current_component or not unit_id:
            return
        self.service.update_component_properties(self._current_component, {"unit": unit_id})


class MessagePanelWidget(QWidget):
    """Messages, ERC and DRC style feedback"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        title = QLabel("Messages & ERC")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.erc_list = QListWidget()
        self.tabs.addTab(self.log_view, "Messages")
        self.tabs.addTab(self.erc_list, "ERC")

    def append_message(self, text: str):
        self.log_view.appendPlainText(text)

    def show_erc_results(self, errors: List[str]):
        self.erc_list.clear()
        if not errors:
            self.erc_list.addItem(QListWidgetItem("No ERC violations."))
            return
        for error in errors:
            item = QListWidgetItem(error)
            item.setForeground(QColor("#C62828"))
            self.erc_list.addItem(item)


class SheetNavigatorWidget(QWidget):
    """Hierarchical sheet browser"""

    def __init__(self, service: CircuitService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        title = QLabel("Sheet Navigator")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree)
        button_row = QHBoxLayout()
        self.new_btn = QPushButton("New")
        self.open_btn = QPushButton("Open")
        self.embed_btn = QPushButton("Embed")
        self.new_btn.clicked.connect(self._create_sheet)
        self.open_btn.clicked.connect(self._open_sheet)
        self.embed_btn.clicked.connect(self._embed_sheet)
        button_row.addWidget(self.new_btn)
        button_row.addWidget(self.open_btn)
        button_row.addWidget(self.embed_btn)
        layout.addLayout(button_row)
        self.service.sheets_changed.connect(self.refresh)
        self.service.active_sheet_changed.connect(self._highlight_active)
        self.refresh()

    def refresh(self):
        self.tree.clear()
        sheets = self.service.get_sheets()
        items: Dict[str, QTreeWidgetItem] = {}
        for sheet in sheets:
            item = QTreeWidgetItem([sheet.name])
            item.setData(0, Qt.UserRole, sheet.sheet_id)
            items[sheet.sheet_id] = item
            if sheet.parent_id and sheet.parent_id in items:
                items[sheet.parent_id].addChild(item)
            else:
                self.tree.addTopLevelItem(item)
        self._highlight_active(self.service.get_active_sheet_id())
        self.tree.expandAll()

    def _on_selection_changed(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        sheet_id = selected[0].data(0, Qt.UserRole)
        if sheet_id:
            self.service.set_active_sheet(sheet_id)

    def _highlight_active(self, sheet_id: str):
        self.tree.blockSignals(True)
        def visit(item: QTreeWidgetItem):
            item.setSelected(item.data(0, Qt.UserRole) == sheet_id)
            for i in range(item.childCount()):
                visit(item.child(i))

        for idx in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(idx))
        self.tree.blockSignals(False)

    def _create_sheet(self):
        name, ok = QInputDialog.getText(self, "New Sheet", "Sheet name:")
        if not ok or not name:
            return
        sheet = self.service.create_sheet(name)
        self.service.set_active_sheet(sheet.sheet_id)

    def _open_sheet(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Sheet", str(Path.home()))
        if not file_path:
            return
        sheet = self.service.open_sheet(file_path)
        self.service.set_active_sheet(sheet.sheet_id)

    def _embed_sheet(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Embed Sheet", str(Path.home()))
        if not file_path:
            return
        sheet = self.service.embed_sheet(file_path)
        self.service.set_active_sheet(sheet.sheet_id)


class CircuitWorkspaceView(QGraphicsView):
    """Central schematic canvas"""

    selection_changed = Signal(object)
    status_message = Signal(str)

    def __init__(self, service: CircuitService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = service
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setSceneRect(-4000, -4000, 8000, 8000)

        self.tool_mode = ToolMode.SELECT
        self._snap_enabled = True
        self._grid_size = 20
        self.component_items: Dict[str, ComponentGraphicsItem] = {}
        self.connection_items: Dict[str, ConnectionGraphicsItem] = {}
        self._connection_lookup: Dict[str, Connection] = {}
        self._annotations: List[Dict] = []
        self._annotation_items: List[QGraphicsItem] = []
        self._history: List[Dict] = []
        self._redo_history: List[Dict] = []
        self._is_restoring_state = False
        self._is_panning = False
        self._pan_start = QPointF()
        self._connection_mode = False
        self._connection_start_component: Optional[str] = None
        self._connection_start_pin: Optional[str] = None
        self._connection_start_pos: Optional[QPointF] = None
        self._rubber_band_line: Optional[QGraphicsPathItem] = None
        self._measurement_start: Optional[QPointF] = None
        self._suspend_scene_refresh = False

        self.scene.selectionChanged.connect(self._on_selection_changed)
        self.service.circuit_changed.connect(self._on_service_changed)
        self.service.active_sheet_changed.connect(lambda _: self._refresh_scene())

        self._history.append(self._capture_snapshot())
        self._refresh_scene()

    # ------------------------------------------------------------------
    # Scene / state management
    # ------------------------------------------------------------------
    def _capture_snapshot(self) -> Dict:
        snapshot = self.service.export_circuit_state()
        snapshot["annotations"] = copy.deepcopy(self._annotations)
        return snapshot

    def _restore_snapshot(self, snapshot: Dict):
        self._is_restoring_state = True
        self.service.load_circuit_state(snapshot)
        self._annotations = copy.deepcopy(snapshot.get("annotations", []))
        self._is_restoring_state = False
        self._refresh_scene()

    def _on_service_changed(self):
        if self._suspend_scene_refresh:
            self._suspend_scene_refresh = False
        else:
            self._refresh_scene()
        if self._is_restoring_state:
            return
        self._history.append(self._capture_snapshot())
        if len(self._history) > 50:
            self._history.pop(0)
        self._redo_history.clear()

    def _refresh_scene(self):
        self.scene.clear()
        self.component_items.clear()
        self.connection_items.clear()
        self._connection_lookup.clear()
        self._annotation_items.clear()
        active_sheet = self.service.get_active_sheet_id()
        for comp in self.service.get_components_for_sheet(active_sheet):
            comp_def = self.service.get_component_definition(comp.definition_id)
            if not comp_def:
                continue
            item = ComponentGraphicsItem(comp_def, comp)
            self.scene.addItem(item)
            self.component_items[comp.instance_id] = item
        for conn in self.service.get_connections_for_sheet(active_sheet):
            self._add_connection_item(conn)
        for annotation in self._annotations:
            self._create_annotation_item(annotation)

    def _add_connection_item(self, connection: Connection):
        from_item = self.component_items.get(connection.from_component)
        to_item = self.component_items.get(connection.to_component)
        if not from_item or not to_item:
            return
        start = from_item.get_pin_scene_pos(connection.from_pin)
        end = to_item.get_pin_scene_pos(connection.to_pin)
        if not start or not end:
            return
        item = ConnectionGraphicsItem(connection, start, end)
        self.scene.addItem(item)
        self.connection_items[connection.connection_id] = item
        self._connection_lookup[connection.connection_id] = connection
        return item

    def _create_wire_path(self, start: QPointF, end: QPointF) -> QPainterPath:
        path = QPainterPath(start)
        mid = QPointF(start.x(), end.y())
        if abs(start.x() - end.x()) < abs(start.y() - end.y()):
            mid = QPointF(end.x(), start.y())
        path.lineTo(mid)
        path.lineTo(end)
        return path

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------
    def set_tool_mode(self, mode: ToolMode):
        self.tool_mode = mode
        cursor = Qt.CrossCursor if mode != ToolMode.SELECT else Qt.ArrowCursor
        self.setCursor(cursor)
        self.status_message.emit(f"Tool: {mode.name.title()}")

    def set_snapping(self, enabled: bool):
        self._snap_enabled = enabled
        self.status_message.emit(f"Grid snapping {'enabled' if enabled else 'disabled'}")

    def undo(self):
        if len(self._history) <= 1:
            return
        current = self._history.pop()
        self._redo_history.append(current)
        snapshot = self._history[-1]
        self._restore_snapshot(snapshot)
        self.status_message.emit("Undo")

    def redo(self):
        if not self._redo_history:
            return
        snapshot = self._redo_history.pop()
        self._history.append(snapshot)
        self._restore_snapshot(snapshot)
        self.status_message.emit("Redo")

    def add_component_at_center(self, component_id: str):
        center = self.mapToScene(self.viewport().rect().center())
        snapped = self._snap(center)
        self.service.add_component(component_id, snapped.x(), snapped.y())

    def clear_circuit(self):
        self._annotations.clear()
        self.service.clear_circuit()
        self._refresh_scene()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def keyPressEvent(self, event):  # type: ignore[override]
        mapping = {
            Qt.Key_Escape: ToolMode.SELECT,
            Qt.Key_W: ToolMode.WIRE,
            Qt.Key_B: ToolMode.BUS,
            Qt.Key_L: ToolMode.NET_LABEL,
            Qt.Key_P: ToolMode.POWER_SYMBOL,
            Qt.Key_J: ToolMode.JUNCTION,
            Qt.Key_S: ToolMode.SHEET_PIN,
            Qt.Key_M: ToolMode.MEASURE,
        }
        if event.key() in mapping:
            self.set_tool_mode(mapping[event.key()])
            event.accept()
            return
        if event.matches(QKeySequence.Undo):
            self.undo()
            event.accept()
            return
        if event.matches(QKeySequence.Redo):
            self.redo()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):  # type: ignore[override]
        scene_pos = self.mapToScene(event.pos())
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.ShiftModifier):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton and self.tool_mode != ToolMode.SELECT and self.tool_mode not in (ToolMode.WIRE, ToolMode.BUS):
            handled = self._handle_annotation_tool(scene_pos)
            if handled:
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if self._is_panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        if self._connection_mode and self._rubber_band_line and self._connection_start_pos:
            path = QPainterPath(self._connection_start_pos)
            current = self._snap(self.mapToScene(event.pos()))
            path.lineTo(current)
            self._rubber_band_line.setPath(path)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        if self._is_panning and event.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor if self.tool_mode == ToolMode.SELECT else Qt.CrossCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Pin/connection handling
    # ------------------------------------------------------------------
    def on_pin_clicked(self, component_id: str, pin_id: str, pin_pos: QPointF):
        if self.tool_mode not in (ToolMode.WIRE, ToolMode.BUS):
            self.status_message.emit("Switch to wire/bus tool to route connections.")
            return
        if not self._connection_mode:
            self._start_connection(component_id, pin_id, pin_pos)
        else:
            self._complete_connection(component_id, pin_id)

    def _start_connection(self, component_id: str, pin_id: str, pin_pos: QPointF):
        self._connection_mode = True
        self._connection_start_component = component_id
        self._connection_start_pin = pin_id
        self._connection_start_pos = pin_pos
        self._rubber_band_line = QGraphicsPathItem()
        pen = QPen(QColor("#00C853"), 2, Qt.DashLine)
        self._rubber_band_line.setPen(pen)
        self.scene.addItem(self._rubber_band_line)
        self.status_message.emit("Select destination pin")

    def _complete_connection(self, component_id: str, pin_id: str):
        if component_id == self._connection_start_component and pin_id == self._connection_start_pin:
            self._cancel_connection()
            return
        connection_type = "bus" if self.tool_mode == ToolMode.BUS else "wire"
        self.service.add_connection(
            self._connection_start_component,
            self._connection_start_pin,
            component_id,
            pin_id,
            wire_color="#263238" if connection_type == "bus" else "#424242",
            connection_type=connection_type,
        )
        self._cancel_connection()

    def _cancel_connection(self):
        if self._rubber_band_line:
            self.scene.removeItem(self._rubber_band_line)
            self._rubber_band_line = None
        self._connection_mode = False
        self._connection_start_component = None
        self._connection_start_pin = None
        self._connection_start_pos = None
        self.status_message.emit("Connection cancelled")

    def on_component_moved(self, component_id: str, pos: QPointF):
        self._suspend_scene_refresh = True
        self.service.move_component(component_id, pos.x(), pos.y())
        self._update_component_connections(component_id)

    def _update_component_connections(self, component_id: str):
        for conn_id, connection in self._connection_lookup.items():
            if connection.from_component != component_id and connection.to_component != component_id:
                continue
            item = self.connection_items.get(conn_id)
            if not item:
                continue
            from_item = self.component_items.get(connection.from_component)
            to_item = self.component_items.get(connection.to_component)
            if not from_item or not to_item:
                continue
            start = from_item.get_pin_scene_pos(connection.from_pin)
            end = to_item.get_pin_scene_pos(connection.to_pin)
            if not start or not end:
                continue
            item.setPath(self._create_wire_path(start, end))

    # ------------------------------------------------------------------
    # Selection & annotations
    # ------------------------------------------------------------------
    def _on_selection_changed(self):
        selected_items = [item for item in self.scene.selectedItems() if isinstance(item, ComponentGraphicsItem)]
        if selected_items:
            comp_id = selected_items[0].comp_instance.instance_id
        else:
            comp_id = None
        self.selection_changed.emit(comp_id)

    def _handle_annotation_tool(self, pos: QPointF) -> bool:
        snapped = self._snap(pos)
        if self.tool_mode == ToolMode.NET_LABEL:
            text, ok = QInputDialog.getText(self, "Net Label", "Net name:")
            if ok and text:
                data = {"type": "net_label", "text": text, "pos": (snapped.x(), snapped.y())}
                self._annotations.append(data)
                self._create_annotation_item(data)
                self._record_manual_change()
                return True
        elif self.tool_mode == ToolMode.POWER_SYMBOL:
            text, ok = QInputDialog.getText(self, "Power Symbol", "Symbol name:", text="VCC")
            if ok and text:
                data = {"type": "power", "text": text, "pos": (snapped.x(), snapped.y())}
                self._annotations.append(data)
                self._create_annotation_item(data)
                self._record_manual_change()
                return True
        elif self.tool_mode == ToolMode.JUNCTION:
            data = {"type": "junction", "pos": (snapped.x(), snapped.y())}
            self._annotations.append(data)
            self._create_annotation_item(data)
            self._record_manual_change()
            return True
        elif self.tool_mode == ToolMode.SHEET_PIN:
            text, ok = QInputDialog.getText(self, "Sheet Pin", "Pin label:")
            if ok and text:
                data = {"type": "sheet_pin", "text": text, "pos": (snapped.x(), snapped.y())}
                self._annotations.append(data)
                self._create_annotation_item(data)
                self._record_manual_change()
                return True
        elif self.tool_mode == ToolMode.MEASURE:
            if not self._measurement_start:
                self._measurement_start = snapped
                self.status_message.emit("Select measurement end point")
            else:
                dx = snapped.x() - self._measurement_start.x()
                dy = snapped.y() - self._measurement_start.y()
                dist = math.hypot(dx, dy)
                label = f"{dist:.1f} mm"
                data = {
                    "type": "measurement",
                    "text": label,
                    "pos": (self._measurement_start.x(), self._measurement_start.y()),
                    "target": (snapped.x(), snapped.y()),
                }
                self._annotations.append(data)
                self._create_annotation_item(data)
                self._measurement_start = None
                self._record_manual_change()
            return True
        return False

    def _create_annotation_item(self, data: Dict):
        annotation_type = data.get("type")
        pos = QPointF(data.get("pos", (0, 0))[0], data.get("pos", (0, 0))[1])
        if annotation_type == "net_label":
            item = QGraphicsTextItem(data.get("text", "NET"))
            item.setDefaultTextColor(QColor("#0277BD"))
            item.setFont(QFont("Monospace", 9))
            item.setPos(pos)
            self.scene.addItem(item)
            self._annotation_items.append(item)
        elif annotation_type == "power":
            text_item = QGraphicsTextItem(data.get("text", "VCC"))
            text_item.setDefaultTextColor(QColor("#FF6F00"))
            text_item.setFont(QFont("Monospace", 9, QFont.Bold))
            text_item.setPos(pos)
            triangle = QGraphicsPathItem()
            path = QPainterPath(pos)
            path.moveTo(pos)
            path.lineTo(pos + QPointF(10, 12))
            path.lineTo(pos + QPointF(-10, 12))
            path.closeSubpath()
            triangle.setPath(path)
            triangle.setBrush(QColor("#FF6F00"))
            triangle.setPen(QPen(Qt.NoPen))
            self.scene.addItem(triangle)
            self.scene.addItem(text_item)
            self._annotation_items.extend([triangle, text_item])
        elif annotation_type == "junction":
            item = QGraphicsPathItem()
            path = QPainterPath()
            path.addEllipse(pos, 4, 4)
            item.setPath(path)
            item.setBrush(QColor("#1B5E20"))
            item.setPen(QPen(Qt.NoPen))
            self.scene.addItem(item)
            self._annotation_items.append(item)
        elif annotation_type == "sheet_pin":
            item = QGraphicsTextItem(data.get("text", "PIN"))
            item.setDefaultTextColor(QColor("#4E342E"))
            item.setFont(QFont("Monospace", 9))
            item.setPos(pos)
            rect = QGraphicsPathItem()
            path = QPainterPath()
            path.addRect(QRectF(pos.x() - 10, pos.y() - 6, 20, 12))
            rect.setPath(path)
            rect.setPen(QPen(QColor("#4E342E"), 1.2))
            self.scene.addItem(rect)
            self.scene.addItem(item)
            self._annotation_items.extend([rect, item])
        elif annotation_type == "measurement":
            text_item = QGraphicsTextItem(data.get("text", ""))
            text_item.setDefaultTextColor(QColor("#D81B60"))
            text_item.setFont(QFont("Monospace", 9))
            text_item.setPos(pos)
            target = data.get("target", (pos.x(), pos.y()))
            path = QPainterPath(QPointF(pos.x(), pos.y()))
            path.lineTo(QPointF(target[0], target[1]))
            line_item = QGraphicsPathItem()
            line_item.setPath(path)
            line_item.setPen(QPen(QColor("#D81B60"), 1, Qt.DashLine))
            self.scene.addItem(line_item)
            self.scene.addItem(text_item)
            self._annotation_items.extend([line_item, text_item])

    def _record_manual_change(self):
        snapshot = self._capture_snapshot()
        self._history.append(snapshot)
        if len(self._history) > 50:
            self._history.pop(0)
        self._redo_history.clear()

    def _snap(self, pos: QPointF) -> QPointF:
        if not self._snap_enabled:
            return pos
        grid = self._grid_size
        x = round(pos.x() / grid) * grid
        y = round(pos.y() / grid) * grid
        return QPointF(x, y)


class CircuitEditor(QWidget):
    """Circuit editor widget that hosts the workspace"""

    circuit_validated = Signal(bool, list)

    def __init__(self, service: Optional[CircuitService] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.service = service or CircuitService()
        self.workspace = CircuitWorkspaceView(self.service, self)
        self.workspace.status_message.connect(self._set_status)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("padding: 4px; background-color: #F5F5F5;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._build_toolbar())
        layout.addWidget(self.workspace)
        layout.addWidget(self._status_label)

        self.service.circuit_validated.connect(self._on_circuit_validated)
        logger.info("Circuit editor initialized")

    def _build_toolbar(self) -> QHBoxLayout:
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._on_new_clicked)
        self.load_btn = QPushButton("Load")
        self.save_btn = QPushButton("Save")
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.clicked.connect(self._on_validate_clicked)
        self.export_connections_btn = QPushButton("Export Nets")
        self.export_connections_btn.clicked.connect(self._on_export_connections)
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.clicked.connect(self.workspace.undo)
        self.redo_btn = QPushButton("Redo")
        self.redo_btn.clicked.connect(self.workspace.redo)

        toolbar.addWidget(self.new_btn)
        toolbar.addWidget(self.load_btn)
        toolbar.addWidget(self.save_btn)
        toolbar.addWidget(self.undo_btn)
        toolbar.addWidget(self.redo_btn)
        toolbar.addStretch()

        self.tool_buttons = QButtonGroup(self)
        for mode, label in [
            (ToolMode.SELECT, "Select (Esc)"),
            (ToolMode.WIRE, "Wire (W)"),
            (ToolMode.BUS, "Bus (B)"),
            (ToolMode.NET_LABEL, "Net Label (L)"),
            (ToolMode.POWER_SYMBOL, "Power (P)"),
            (ToolMode.JUNCTION, "Junction (J)"),
            (ToolMode.SHEET_PIN, "Sheet Pin (S)"),
            (ToolMode.MEASURE, "Measure (M)"),
        ]:
            btn = QToolButton()
            btn.setText(label)
            btn.setCheckable(True)
            if mode == ToolMode.SELECT:
                btn.setChecked(True)
            self.tool_buttons.addButton(btn, mode.value)
            btn.clicked.connect(lambda checked=False, m=mode: self.workspace.set_tool_mode(m))
            toolbar.addWidget(btn)

        self.snap_checkbox = QCheckBox("Snap")
        self.snap_checkbox.setChecked(True)
        self.snap_checkbox.stateChanged.connect(lambda state: self.workspace.set_snapping(state == Qt.Checked))
        toolbar.addWidget(self.snap_checkbox)
        toolbar.addWidget(self.validate_btn)
        toolbar.addWidget(self.export_connections_btn)
        return toolbar

    # ------------------------------------------------------------------
    # UI actions
    # ------------------------------------------------------------------
    @Slot()
    def _on_new_clicked(self):
        if QMessageBox.question(self, "New Circuit", "Clear current circuit?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.workspace.clear_circuit()
            self._set_status("Circuit cleared")

    @Slot()
    def _on_validate_clicked(self):
        is_valid, errors = self.service.validate_circuit()
        if is_valid:
            QMessageBox.information(self, "Circuit Valid", "No ERC violations found.")
        else:
            QMessageBox.warning(self, "ERC Violations", "\n".join(errors))

    @Slot()
    def _on_export_connections(self):
        connection_list = self.service.generate_connection_list()
        QMessageBox.information(self, "Connection List", connection_list)

    @Slot(bool, list)
    def _on_circuit_validated(self, is_valid: bool, errors: List[str]):
        self.circuit_validated.emit(is_valid, errors)

    def _set_status(self, text: str):
        self._status_label.setText(text)

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------
    def save_circuit_to_file(self, file_path: str) -> bool:
        return self.service.save_circuit(file_path)

    def load_circuit_from_file(self, file_path: str) -> bool:
        return self.service.load_circuit(file_path)


class CircuitDesignerWindow(QMainWindow):
    """Standalone window hosting docks and the circuit editor"""

    def __init__(self, service: Optional[CircuitService] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.service = service or CircuitService()
        self.setWindowTitle("Arduino Circuit Designer")
        self.resize(1400, 900)
        self.circuit_editor = CircuitEditor(self.service, self)
        self.setCentralWidget(self.circuit_editor)
        self._current_file: Optional[str] = None
        self._build_docks()
        self._create_menus()
        self.circuit_editor.load_btn.clicked.connect(self._on_load_clicked)
        self.circuit_editor.save_btn.clicked.connect(self._on_save_clicked)
        logger.info("Circuit Designer window initialized")

    def _build_docks(self):
        # Symbol chooser
        self.symbol_widget = ComponentLibraryWidget(self.service)
        self.symbol_widget.component_selected.connect(self.circuit_editor.workspace.add_component_at_center)
        symbol_dock = QDockWidget("Symbols", self)
        symbol_dock.setWidget(self.symbol_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, symbol_dock)

        # Sheet navigator
        self.sheet_widget = SheetNavigatorWidget(self.service)
        sheet_dock = QDockWidget("Sheets", self)
        sheet_dock.setWidget(self.sheet_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, sheet_dock)
        self.tabifyDockWidget(symbol_dock, sheet_dock)

        # Property inspector
        self.property_widget = PropertyInspectorWidget(self.service)
        prop_dock = QDockWidget("Inspector", self)
        prop_dock.setWidget(self.property_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, prop_dock)

        # Message panel
        self.message_widget = MessagePanelWidget()
        message_dock = QDockWidget("Messages", self)
        message_dock.setWidget(self.message_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, message_dock)

        self.circuit_editor.workspace.selection_changed.connect(self.property_widget.display_component)
        self.circuit_editor.workspace.status_message.connect(self.message_widget.append_message)
        self.circuit_editor.circuit_validated.connect(self._on_circuit_validated)

    def _create_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        new_action = QAction("&New Circuit", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.circuit_editor._on_new_clicked)
        file_menu.addAction(new_action)
        load_action = QAction("&Open Circuit...", self)
        load_action.setShortcut(QKeySequence.Open)
        load_action.triggered.connect(self._on_load_clicked)
        file_menu.addAction(load_action)
        save_action = QAction("&Save Circuit", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._on_save_clicked)
        file_menu.addAction(save_action)
        save_as_action = QAction("Save Circuit &As...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self._on_save_as_clicked)
        file_menu.addAction(save_as_action)
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        circuit_menu = menubar.addMenu("&Circuit")
        validate_action = QAction("&Validate Circuit", self)
        validate_action.triggered.connect(self.circuit_editor._on_validate_clicked)
        circuit_menu.addAction(validate_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _on_load_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Circuit", str(Path.home()), "Circuit Files (*.json)")
        if not file_path:
            return
        if self.circuit_editor.load_circuit_from_file(file_path):
            self._current_file = file_path
            self.statusBar().showMessage(f"Loaded {file_path}", 4000)
            self.setWindowTitle(f"Arduino Circuit Designer - {Path(file_path).name}")

    def _on_save_clicked(self):
        if not hasattr(self, "_current_file"):
            self._current_file = None
        if not self._current_file:
            self._on_save_as_clicked()
            return
        if self.circuit_editor.save_circuit_to_file(self._current_file):
            self.statusBar().showMessage(f"Saved {self._current_file}", 4000)

    def _on_save_as_clicked(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Circuit", str(Path.home()), "Circuit Files (*.json)")
        if not file_path:
            return
        if self.circuit_editor.save_circuit_to_file(file_path):
            self._current_file = file_path
            self.statusBar().showMessage(f"Saved {file_path}", 4000)
            self.setWindowTitle(f"Arduino Circuit Designer - {Path(file_path).name}")

    def _show_about_dialog(self):
        QMessageBox.information(
            self,
            "About Arduino Circuit Designer",
            """<h3>Arduino Circuit Designer</h3>
            <p>KiCAD-inspired schematic environment with symbol docks, ERC feedback, and hierarchical sheets.</p>""",
        )

    def _on_circuit_validated(self, is_valid: bool, errors: List[str]):
        if is_valid:
            self.message_widget.append_message("ERC: No violations detected")
        else:
            self.message_widget.append_message(f"ERC: {len(errors)} violation(s)")
        self.message_widget.show_erc_results(errors)
