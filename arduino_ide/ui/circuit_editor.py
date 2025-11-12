"""
Circuit Editor
Visual circuit design interface with component library and wiring
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QPushButton, QGraphicsView, QGraphicsScene,
                               QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem,
                               QGraphicsRectItem, QGraphicsTextItem, QListWidget,
                               QListWidgetItem, QLabel, QMessageBox, QGroupBox,
                               QScrollArea, QToolBox, QMainWindow, QFileDialog)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QLineF, Slot
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPainterPath, QPolygonF, QAction, QKeySequence
import logging
from typing import Optional, Dict, List
from pathlib import Path

from arduino_ide.services.circuit_service import CircuitService
from arduino_ide.models.circuit_domain import (
    ComponentDefinition,
    ComponentInstance,
    Connection,
    ComponentType,
    ElectricalRuleDiagnostic,
    PinType,
    Pin,
)

logger = logging.getLogger(__name__)


class PinGraphicsItem(QGraphicsEllipseItem):
    """Graphics item representing a clickable pin"""

    def __init__(self, pin: Pin, pin_color: QColor, parent=None):
        super().__init__(-3, -3, 6, 6, parent)

        self.pin = pin
        self.setBrush(QBrush(pin_color))
        self.setPen(QPen(Qt.black, 1))
        self.setZValue(2)  # Above component

        # Make clickable
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setAcceptHoverEvents(True)

        self._is_hovered = False


    def hoverEnterEvent(self, event):
        """Highlight pin on hover"""
        self._is_hovered = True
        self.setPen(QPen(QColor("#00FF00"), 2))  # Green highlight
        self.setZValue(3)
        super().hoverEnterEvent(event)


    def hoverLeaveEvent(self, event):
        """Remove highlight on hover leave"""
        self._is_hovered = False
        self.setPen(QPen(Qt.black, 1))
        self.setZValue(2)
        super().hoverLeaveEvent(event)


    def mousePressEvent(self, event):
        """Handle pin click"""
        if event.button() == Qt.LeftButton:
            # Get parent component and notify workspace
            component_item = self.parentItem()
            if component_item and hasattr(component_item, 'comp_instance'):
                scene = self.scene()
                if scene and hasattr(scene.views()[0], 'on_pin_clicked'):
                    scene.views()[0].on_pin_clicked(
                        component_item.comp_instance.instance_id,
                        self.pin.id,
                        self.scenePos()
                    )
            event.accept()
        else:
            super().mousePressEvent(event)


class ComponentGraphicsItem(QGraphicsRectItem):
    """Graphics item representing a circuit component"""

    def __init__(self, comp_def: ComponentDefinition, comp_instance: ComponentInstance, parent=None):
        super().__init__(parent)

        self.comp_def = comp_def
        self.comp_instance = comp_instance

        # Setup appearance
        self.setRect(0, 0, comp_def.width, comp_def.height)
        self.setPos(comp_instance.x, comp_instance.y)

        # Set color based on type
        color = self._get_component_color()
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor("#333333"), 2))

        # Make draggable
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

        # Add label
        self.label = QGraphicsTextItem(self)
        display_label = comp_instance.annotation or comp_def.name
        self.label.setPlainText(display_label)
        self.label.setDefaultTextColor(Qt.black)
        font = QFont()
        font.setBold(True)
        font.setPointSize(8)
        self.label.setFont(font)

        # Center label
        label_width = self.label.boundingRect().width()
        self.label.setPos((comp_def.width - label_width) / 2, comp_def.height / 2 - 10)

        # Draw pins
        self.pin_items = {}
        for pin in comp_def.pins:
            # Create clickable pin item
            pin_item = PinGraphicsItem(pin, self._get_pin_color(pin.pin_type), self)
            pin_item.setPos(pin.position[0], pin.position[1])

            # Add pin label
            pin_label = QGraphicsTextItem(self)
            pin_label.setPlainText(pin.label)
            pin_label.setDefaultTextColor(Qt.black)
            pin_font = QFont()
            pin_font.setPointSize(6)
            pin_label.setFont(pin_font)
            pin_label.setPos(pin.position[0] - 10, pin.position[1] - 15)

            self.pin_items[pin.id] = (pin_item, pin_label)


    def _get_component_color(self) -> QColor:
        """Get color for component type"""
        color_map = {
            ComponentType.ARDUINO_BOARD: QColor("#4A90E2"),
            ComponentType.LED: QColor("#E74C3C"),
            ComponentType.RESISTOR: QColor("#F39C12"),
            ComponentType.BUTTON: QColor("#95A5A6"),
            ComponentType.POTENTIOMETER: QColor("#3498DB"),
            ComponentType.SERVO: QColor("#9B59B6"),
            ComponentType.SENSOR: QColor("#1ABC9C"),
            ComponentType.BREADBOARD: QColor("#ECF0F1"),
        }
        return color_map.get(self.comp_def.component_type, QColor("#BDC3C7"))


    def _get_pin_color(self, pin_type: PinType) -> QColor:
        """Get color for pin type"""
        color_map = {
            PinType.DIGITAL: QColor("#3498DB"),
            PinType.ANALOG: QColor("#E67E22"),
            PinType.PWM: QColor("#9B59B6"),
            PinType.POWER: QColor("#E74C3C"),
            PinType.GROUND: QColor("#000000"),
            PinType.I2C: QColor("#1abc9c"),
            PinType.SPI: QColor("#8e44ad"),
            PinType.SERIAL: QColor("#2c3e50"),
        }
        return color_map.get(pin_type, QColor("#95A5A6"))


    def itemChange(self, change, value):
        """Handle item changes"""
        if change == QGraphicsItem.ItemPositionChange:
            new_pos = value
            self.comp_instance.x = new_pos.x()
            self.comp_instance.y = new_pos.y()

            # Update connected wires
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                if hasattr(view, '_update_component_connections'):
                    view._update_component_connections(self.comp_instance.instance_id)

        return super().itemChange(change, value)


    def get_pin_scene_pos(self, pin_id: str) -> Optional[QPointF]:
        """Get the scene position of a pin"""
        if pin_id in self.pin_items:
            pin_item, _ = self.pin_items[pin_id]
            return pin_item.scenePos()
        return None


class ConnectionGraphicsItem(QGraphicsLineItem):
    """Graphics item representing a wire connection"""

    def __init__(self, connection: Connection, start_pos: QPointF, end_pos: QPointF, parent=None):
        super().__init__(parent)

        self.connection = connection

        self.setLine(QLineF(start_pos, end_pos))
        self.setPen(QPen(QColor(connection.wire_color), 3))
        self.setZValue(-1)


class ComponentLibraryWidget(QWidget):
    """Widget displaying available components"""

    component_selected = Signal(str)  # component_id

    def __init__(self, service: CircuitService, parent=None):
        super().__init__(parent)

        self.service = service

        self._setup_ui()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title = QLabel("Component Library")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)

        # Toolbox with component categories
        self.toolbox = QToolBox()

        # Group by component type
        type_groups = {}
        for comp_def in self.service.get_all_component_definitions():
            if comp_def.component_type not in type_groups:
                type_groups[comp_def.component_type] = []
            type_groups[comp_def.component_type].append(comp_def)

        # Add each category
        for comp_type, components in sorted(type_groups.items(), key=lambda x: x[0].value):
            category_widget = self._create_category_widget(components)
            self.toolbox.addItem(category_widget, comp_type.value.replace("_", " ").title())

        layout.addWidget(self.toolbox)


    def _create_category_widget(self, components: List[ComponentDefinition]) -> QWidget:
        """Create widget for a component category"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)

        for comp_def in components:
            comp_button = QPushButton(comp_def.name)
            comp_button.setToolTip(comp_def.description)
            comp_button.clicked.connect(lambda checked, cid=comp_def.id: self.component_selected.emit(cid))

            layout.addWidget(comp_button)

        layout.addStretch()
        return widget


class CircuitWorkspaceView(QGraphicsView):
    """Graphics view for circuit design workspace"""

    def __init__(self, service: CircuitService, parent=None):
        super().__init__(parent)

        self.service = service
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Component and connection items
        self.component_items: Dict[str, ComponentGraphicsItem] = {}
        self.connection_items: Dict[str, ConnectionGraphicsItem] = {}

        # Setup view
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)  # Allow component dragging
        self.setSceneRect(-2000, -2000, 4000, 4000)

        # Grid background
        self.setBackgroundBrush(QBrush(QColor("#FFFFFF")))

        # Enable panning with middle mouse button
        self._is_panning = False
        self._pan_start_pos = None

        # Connection mode state
        self._connection_mode = False
        self._connection_start_component = None
        self._connection_start_pin = None
        self._connection_start_pos = None
        self._rubber_band_line = None

        # Connect to service
        self.service.component_added.connect(self._on_component_added)
        self.service.component_removed.connect(self._on_component_removed)
        self.service.connection_added.connect(self._on_connection_added)
        self.service.connection_removed.connect(self._on_connection_removed)

        logger.info("Circuit workspace view initialized")


    @Slot(str)
    def _on_component_added(self, instance_id: str):
        """Handle component added"""
        components = self.service.get_circuit_components()
        comp_instance = next((c for c in components if c.instance_id == instance_id), None)

        if not comp_instance:
            return

        comp_def = self.service.get_component_definition(comp_instance.definition_id)
        if not comp_def:
            return

        # Create graphics item
        item = ComponentGraphicsItem(comp_def, comp_instance)
        self.scene.addItem(item)
        self.component_items[instance_id] = item

        logger.debug(f"Added component to circuit: {instance_id}")


    @Slot(str)
    def _on_component_removed(self, instance_id: str):
        """Handle component removed"""
        if instance_id in self.component_items:
            item = self.component_items[instance_id]
            self.scene.removeItem(item)
            del self.component_items[instance_id]

            logger.debug(f"Removed component from circuit: {instance_id}")


    @Slot(str)
    def _on_connection_added(self, connection_id: str):
        """Handle connection added"""
        connections = self.service.get_circuit_connections()
        connection = next((c for c in connections if c.connection_id == connection_id), None)

        if not connection:
            return

        # Get component items
        from_comp_item = self.component_items.get(connection.from_component)
        to_comp_item = self.component_items.get(connection.to_component)

        if not from_comp_item or not to_comp_item:
            return

        # Get actual pin positions
        from_pos = from_comp_item.get_pin_scene_pos(connection.from_pin)
        to_pos = to_comp_item.get_pin_scene_pos(connection.to_pin)

        if not from_pos or not to_pos:
            logger.warning(f"Could not find pin positions for connection {connection_id}")
            return

        # Create connection line
        conn_item = ConnectionGraphicsItem(connection, from_pos, to_pos)
        self.scene.addItem(conn_item)
        self.connection_items[connection_id] = conn_item

        logger.debug(f"Added connection to circuit: {connection_id}")


    @Slot(str)
    def _on_connection_removed(self, connection_id: str):
        """Handle connection removed"""
        if connection_id in self.connection_items:
            item = self.connection_items[connection_id]
            self.scene.removeItem(item)
            del self.connection_items[connection_id]

            logger.debug(f"Removed connection from circuit: {connection_id}")


    def on_pin_clicked(self, component_id: str, pin_id: str, pin_pos: QPointF):
        """Handle pin click - start or complete connection"""
        if not self._connection_mode:
            # Start connection mode
            self._start_connection(component_id, pin_id, pin_pos)
        else:
            # Complete connection
            self._complete_connection(component_id, pin_id)


    def _start_connection(self, component_id: str, pin_id: str, pin_pos: QPointF):
        """Start connection mode"""
        self._connection_mode = True
        self._connection_start_component = component_id
        self._connection_start_pin = pin_id
        self._connection_start_pos = pin_pos

        # Create rubber band line
        self._rubber_band_line = QGraphicsLineItem()
        self._rubber_band_line.setPen(QPen(QColor("#00FF00"), 2, Qt.DashLine))
        self._rubber_band_line.setZValue(-0.5)
        self._rubber_band_line.setLine(QLineF(pin_pos, pin_pos))
        self.scene.addItem(self._rubber_band_line)

        # Change cursor
        self.setCursor(Qt.CrossCursor)

        logger.debug(f"Started connection from {component_id}:{pin_id}")


    def _complete_connection(self, to_component_id: str, to_pin_id: str):
        """Complete connection to target pin"""
        # Don't allow connection to same pin
        if (self._connection_start_component == to_component_id and
            self._connection_start_pin == to_pin_id):
            self._cancel_connection()
            return

        # Create connection in service
        try:
            self.service.add_connection(
                self._connection_start_component,
                self._connection_start_pin,
                to_component_id,
                to_pin_id,
                "#000000"  # Black wire by default
            )
            logger.debug(f"Connected {self._connection_start_component}:{self._connection_start_pin} to {to_component_id}:{to_pin_id}")
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")

        # Clean up connection mode
        self._cancel_connection()


    def _cancel_connection(self):
        """Cancel connection mode"""
        if self._rubber_band_line:
            self.scene.removeItem(self._rubber_band_line)
            self._rubber_band_line = None

        self._connection_mode = False
        self._connection_start_component = None
        self._connection_start_pin = None
        self._connection_start_pos = None
        self.setCursor(Qt.ArrowCursor)

        logger.debug("Cancelled connection mode")


    def _update_component_connections(self, component_id: str):
        """Update all connections for a component when it moves"""
        connections = self.service.get_circuit_connections()

        for connection in connections:
            # Check if this component is involved in this connection
            if connection.from_component == component_id or connection.to_component == component_id:
                conn_item = self.connection_items.get(connection.connection_id)
                if conn_item:
                    # Get updated pin positions
                    from_comp_item = self.component_items.get(connection.from_component)
                    to_comp_item = self.component_items.get(connection.to_component)

                    if from_comp_item and to_comp_item:
                        from_pos = from_comp_item.get_pin_scene_pos(connection.from_pin)
                        to_pos = to_comp_item.get_pin_scene_pos(connection.to_pin)

                        if from_pos and to_pos:
                            conn_item.setLine(QLineF(from_pos, to_pos))


    def add_component_at_center(self, component_id: str):
        """Add a component at the center of the view"""
        center = self.mapToScene(self.viewport().rect().center())
        self.service.add_component(component_id, center.x(), center.y())


    def clear_circuit(self):
        """Clear all components and connections"""
        self.service.clear_circuit()
        self.scene.clear()
        self.component_items.clear()
        self.connection_items.clear()


    def mousePressEvent(self, event):
        """Handle mouse press - enable panning with middle button or Ctrl+left"""
        # Right-click cancels connection mode
        if event.button() == Qt.RightButton and self._connection_mode:
            self._cancel_connection()
            event.accept()
            return

        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier):
            self._is_panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        """Handle mouse move - pan the view if panning is active or update rubber band"""
        if self._is_panning and self._pan_start_pos:
            delta = event.pos() - self._pan_start_pos
            self._pan_start_pos = event.pos()

            # Pan by adjusting scrollbars
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        elif self._connection_mode and self._rubber_band_line and self._connection_start_pos:
            # Update rubber band line to follow mouse
            mouse_pos = self.mapToScene(event.pos())
            self._rubber_band_line.setLine(QLineF(self._connection_start_pos, mouse_pos))
            event.accept()
        else:
            super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        """Handle mouse release - stop panning"""
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and self._is_panning):
            self._is_panning = False
            self._pan_start_pos = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


    def wheelEvent(self, event):
        """Handle mouse wheel - zoom in/out"""
        if event.modifiers() & Qt.ControlModifier:
            # Zoom with Ctrl+Wheel
            zoom_factor = 1.15
            if event.angleDelta().y() > 0:
                self.scale(zoom_factor, zoom_factor)
            else:
                self.scale(1 / zoom_factor, 1 / zoom_factor)
            event.accept()
        else:
            # Normal scrolling
            super().wheelEvent(event)


    def keyPressEvent(self, event):
        """Handle key press - ESC cancels connection mode"""
        if event.key() == Qt.Key_Escape and self._connection_mode:
            self._cancel_connection()
            event.accept()
        else:
            super().keyPressEvent(event)


    def drawBackground(self, painter, rect):
        """Draw grid background"""
        super().drawBackground(painter, rect)

        # Draw grid
        grid_size = 10
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        painter.setPen(QPen(QColor("#E0E0E0"), 0.5, Qt.DotLine))

        # Vertical lines
        x = left
        while x < rect.right():
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            x += grid_size

        # Horizontal lines
        y = top
        while y < rect.bottom():
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            y += grid_size


class CircuitEditor(QWidget):
    """
    Main circuit editor widget
    Combines component library and circuit workspace
    """

    circuit_validated = Signal(bool, list)  # is_valid, errors

    def __init__(self, service: Optional[CircuitService] = None, parent=None):
        super().__init__(parent)

        self.service = service or CircuitService()

        self._setup_ui()
        self._setup_connections()

        logger.info("Circuit editor initialized")


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()

        self.new_btn = QPushButton("New")
        self.new_btn.setToolTip("Clear circuit")

        self.load_btn = QPushButton("Load")
        self.load_btn.setToolTip("Load circuit from file")

        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("Save circuit to file")

        self.validate_btn = QPushButton("Validate")
        self.validate_btn.setToolTip("Validate circuit connections")
        self.validate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        self.export_connections_btn = QPushButton("Export Connections")
        self.export_connections_btn.setToolTip("Export connection list")

        toolbar.addWidget(self.new_btn)
        toolbar.addWidget(self.load_btn)
        toolbar.addWidget(self.save_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.validate_btn)
        toolbar.addWidget(self.export_connections_btn)

        layout.addLayout(toolbar)

        # Main content - splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left: Component library
        self.library = ComponentLibraryWidget(self.service)
        self.library.setMaximumWidth(250)
        splitter.addWidget(self.library)

        # Right: Circuit workspace
        self.workspace = CircuitWorkspaceView(self.service)
        splitter.addWidget(self.workspace)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 5px; background-color: #F0F0F0;")
        layout.addWidget(self.status_label)


    def _setup_connections(self):
        """Setup signal connections"""
        self.new_btn.clicked.connect(self._on_new_clicked)
        self.validate_btn.clicked.connect(self._on_validate_clicked)
        self.export_connections_btn.clicked.connect(self._on_export_connections)

        self.library.component_selected.connect(self._on_component_selected)

        self.service.circuit_changed.connect(self._on_circuit_changed)
        self.service.circuit_validated.connect(self._on_circuit_validated)


    @Slot()
    def _on_new_clicked(self):
        """Handle new circuit"""
        reply = QMessageBox.question(
            self,
            "New Circuit",
            "Clear current circuit?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.workspace.clear_circuit()
            self.status_label.setText("Circuit cleared")


    @Slot(str)
    def _on_component_selected(self, component_id: str):
        """Handle component selected from library"""
        self.workspace.add_component_at_center(component_id)
        comp_def = self.service.get_component_definition(component_id)
        self.status_label.setText(f"Added: {comp_def.name}")


    @Slot()
    def _on_circuit_changed(self):
        """Handle circuit change"""
        component_count = len(self.service.get_circuit_components())
        connection_count = len(self.service.get_circuit_connections())
        self.status_label.setText(f"Components: {component_count}, Connections: {connection_count}")


    @Slot()
    def _on_validate_clicked(self):
        """Handle validate button"""
        is_valid, diagnostics = self.service.validate_circuit()

        if is_valid:
            QMessageBox.information(
                self,
                "Circuit Valid",
                "Circuit validation passed! No errors found."
            )
        else:
            error_text = "\n".join(
                self._format_diagnostic(diag)
                for diag in diagnostics
            )
            QMessageBox.warning(
                self,
                "Circuit Validation Failed",
                f"Found {len(diagnostics)} issue(s):\n\n{error_text}"
            )


    def _format_diagnostic(self, diag: ElectricalRuleDiagnostic) -> str:
        context = []
        if diag.related_net:
            context.append(f"net {diag.related_net}")
        if diag.related_component:
            context.append(f"component {diag.related_component}")
        context_text = f" ({', '.join(context)})" if context else ""
        return f"• {diag.severity.upper()} {diag.code}: {diag.message}{context_text}"


    @Slot(bool, list)
    def _on_circuit_validated(self, is_valid: bool, errors: List[dict]):
        """Handle circuit validated"""
        self.circuit_validated.emit(is_valid, errors)


    @Slot()
    def _on_export_connections(self):
        """Export connection list"""
        connection_list = self.service.generate_connection_list()

        QMessageBox.information(
            self,
            "Connection List",
            connection_list
        )


    def save_circuit_to_file(self, file_path: str) -> bool:
        """Save circuit to file"""
        return self.service.save_circuit(file_path)


    def load_circuit_from_file(self, file_path: str) -> bool:
        """Load circuit from file"""
        return self.service.load_circuit(file_path)


class CircuitDesignerWindow(QMainWindow):
    """
    Standalone window for Circuit Designer
    Can be opened from main IDE or run independently
    """

    def __init__(self, service: Optional[CircuitService] = None, parent=None):
        super().__init__(parent)

        self.service = service or CircuitService()
        self.current_file = None

        self.setWindowTitle("Arduino Circuit Designer")
        self.resize(1200, 800)

        # Create circuit editor as central widget
        self.circuit_editor = CircuitEditor(self.service, self)
        self.setCentralWidget(self.circuit_editor)

        # Connect load/save buttons to file dialogs
        self.circuit_editor.load_btn.clicked.connect(self._on_load_clicked)
        self.circuit_editor.save_btn.clicked.connect(self._on_save_clicked)

        # Create menus
        self._create_menus()

        logger.info("Circuit Designer window initialized")

    def _create_menus(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File Menu
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

        file_menu.addSeparator()

        close_action = QAction("&Close", self)
        close_action.setShortcut(QKeySequence.Close)
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

        # Circuit Menu
        circuit_menu = menubar.addMenu("&Circuit")

        validate_action = QAction("&Validate Circuit", self)
        validate_action.setShortcut(Qt.CTRL | Qt.Key_V)
        validate_action.triggered.connect(self.circuit_editor._on_validate_clicked)
        circuit_menu.addAction(validate_action)

        export_action = QAction("&Export Connections", self)
        export_action.setShortcut(Qt.CTRL | Qt.Key_E)
        export_action.triggered.connect(self.circuit_editor._on_export_connections)
        circuit_menu.addAction(export_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    @Slot()
    def _on_load_clicked(self):
        """Handle load circuit"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Circuit",
            str(Path.home()),
            "Circuit Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        if self.circuit_editor.load_circuit_from_file(file_path):
            self.current_file = file_path
            self.setWindowTitle(f"Arduino Circuit Designer - {Path(file_path).name}")
            QMessageBox.information(
                self,
                "Circuit Loaded",
                f"Successfully loaded circuit from {Path(file_path).name}"
            )
        else:
            QMessageBox.critical(
                self,
                "Load Failed",
                f"Failed to load circuit from {Path(file_path).name}"
            )

    @Slot()
    def _on_save_clicked(self):
        """Handle save circuit"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._on_save_as_clicked()

    @Slot()
    def _on_save_as_clicked(self):
        """Handle save circuit as"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Circuit As",
            str(Path.home() / "circuit.json"),
            "Circuit Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        self._save_to_file(file_path)

    def _save_to_file(self, file_path: str):
        """Save circuit to file"""
        if self.circuit_editor.save_circuit_to_file(file_path):
            self.current_file = file_path
            self.setWindowTitle(f"Arduino Circuit Designer - {Path(file_path).name}")
            QMessageBox.information(
                self,
                "Circuit Saved",
                f"Successfully saved circuit to {Path(file_path).name}"
            )
        else:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save circuit to {Path(file_path).name}"
            )

    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Arduino Circuit Designer",
            """<h3>Arduino Circuit Designer</h3>
            <p>Visual circuit design tool for Arduino projects</p>
            <p><b>Features:</b></p>
            <ul>
            <li>Drag-and-drop component placement</li>
            <li>Visual wire connections</li>
            <li>Circuit validation</li>
            <li>100+ electronic components</li>
            <li>Save/load circuits</li>
            </ul>
            <p><b>Controls:</b></p>
            <ul>
            <li>Left-click and drag component: Move component</li>
            <li>Left-click pin: Start wire connection (click another pin to complete)</li>
            <li>Right-click or ESC: Cancel wire connection</li>
            <li>Middle-click and drag or Ctrl+Left-drag: Pan view</li>
            <li>Ctrl+Mouse wheel: Zoom in/out</li>
            <li>Mouse wheel: Scroll vertically</li>
            </ul>
            <p>Part of Arduino IDE Modern</p>"""
        )
