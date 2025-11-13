"""
SCH_EDIT_FRAME - Main Schematic Editor Window
Based on KiCad's sch_edit_frame.cpp/h - matches KiCad's visual appearance
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QStatusBar,
    QDockWidget,
    QLabel,
    QWidget,
    QVBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QSplitter,
    QFrame,
)

from arduino_ide.eeschema.schematic import Schematic
from arduino_ide.eeschema.widgets.sch_graphics_items import (
    ComponentGraphicsItem,
    ConnectionGraphicsItem,
)

logger = logging.getLogger(__name__)


class KiCadGridView(QGraphicsView):
    """
    Canvas with KiCad-style grid rendering
    Default grid: 50 mil (1.27mm) with dots
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # KiCad default settings
        self.grid_size = 50  # 50 mil = 1.27mm in internal units (assume 1 unit = 0.0254mm)
        self.grid_style = "dots"  # dots, lines, or crosses
        self.grid_visible = True
        self.grid_color = QColor(132, 132, 132)  # KiCad default grid color
        self.background_color = QColor(255, 255, 255)  # White background (light theme)

        # Canvas setup
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        # Set scene
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-10000, -10000, 20000, 20000)
        self.setScene(self.scene)

        # Set background
        self.setBackgroundBrush(QBrush(self.background_color))

        # Mouse tracking
        self.setMouseTracking(True)
        self._pan_active = False
        self._last_pan_point = QPointF()

        # Cursor position
        self.cursor_x = 0
        self.cursor_y = 0

    def drawBackground(self, painter: QPainter, rect):
        """Draw KiCad-style grid"""
        super().drawBackground(painter, rect)

        if not self.grid_visible:
            return

        painter.save()
        painter.setPen(QPen(self.grid_color, 1))

        # Calculate grid bounds
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)

        # Draw grid based on style
        if self.grid_style == "dots":
            # KiCad default: dots at grid points
            x = left
            while x < rect.right():
                y = top
                while y < rect.bottom():
                    painter.drawPoint(int(x), int(y))
                    y += self.grid_size
                x += self.grid_size

        elif self.grid_style == "lines":
            # Vertical lines
            x = left
            while x < rect.right():
                painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
                x += self.grid_size
            # Horizontal lines
            y = top
            while y < rect.bottom():
                painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
                y += self.grid_size

        elif self.grid_style == "crosses":
            # Small crosses at grid points
            x = left
            cross_size = 3
            while x < rect.right():
                y = top
                while y < rect.bottom():
                    painter.drawLine(int(x - cross_size), int(y), int(x + cross_size), int(y))
                    painter.drawLine(int(x), int(y - cross_size), int(x), int(y + cross_size))
                    y += self.grid_size
                x += self.grid_size

        painter.restore()

    def mouseMoveEvent(self, event):
        """Track cursor position"""
        scene_pos = self.mapToScene(event.pos())
        self.cursor_x = scene_pos.x()
        self.cursor_y = scene_pos.y()

        # Handle panning
        if self._pan_active:
            delta = self.mapToScene(event.pos()) - self._last_pan_point
            self._last_pan_point = self.mapToScene(event.pos())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MiddleButton:
            self._pan_active = True
            self._last_pan_point = self.mapToScene(event.pos())
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MiddleButton:
            self._pan_active = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """Zoom with mouse wheel"""
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)

    def set_dark_theme(self):
        """Switch to dark theme"""
        self.background_color = QColor(25, 25, 25)
        self.grid_color = QColor(80, 80, 80)
        self.setBackgroundBrush(QBrush(self.background_color))
        self.viewport().update()

    def set_light_theme(self):
        """Switch to light theme"""
        self.background_color = QColor(255, 255, 255)
        self.grid_color = QColor(132, 132, 132)
        self.setBackgroundBrush(QBrush(self.background_color))
        self.viewport().update()


class SchEditFrame(QMainWindow):
    """
    Main Schematic Editor Window - matches KiCad's sch_edit_frame
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Schematic Editor - KiCad Style")
        self.resize(1400, 900)

        # Create schematic model
        self.schematic = Schematic()

        # Create central canvas (KiCad style)
        self.canvas = KiCadGridView()
        self.setCentralWidget(self.canvas)

        # Create KiCad-style UI
        self._create_menu_bar()
        self._create_top_toolbar()
        self._create_left_toolbar()
        self._create_right_toolbar()
        self._create_status_bar()
        self._create_side_panels()

        # Status bar update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status_bar)
        self.status_timer.start(100)  # Update every 100ms

        logger.info("KiCad-style Schematic Editor initialized")

    def _create_menu_bar(self):
        """Create KiCad-style menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Schematic", self)
        new_action.setShortcut(QKeySequence.New)
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.Open)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.Save)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        import_action = QAction("&Import Schematic...", self)
        file_menu.addAction(import_action)

        export_action = QAction("&Export", self)
        file_menu.addAction(export_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut(QKeySequence.Cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(QKeySequence.Copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction("&Paste", self)
        paste_action.setShortcut(QKeySequence.Paste)
        edit_menu.addAction(paste_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.triggered.connect(lambda: self.canvas.scale(1.2, 1.2))
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(lambda: self.canvas.scale(1/1.2, 1/1.2))
        view_menu.addAction(zoom_out_action)

        zoom_fit_action = QAction("Zoom to &Fit", self)
        zoom_fit_action.setShortcut("Home")
        view_menu.addAction(zoom_fit_action)

        view_menu.addSeparator()

        grid_action = QAction("Show &Grid", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(True)
        grid_action.triggered.connect(self._toggle_grid)
        view_menu.addAction(grid_action)

        # Place menu
        place_menu = menubar.addMenu("&Place")

        place_symbol_action = QAction("&Symbol", self)
        place_symbol_action.setShortcut("A")
        place_menu.addAction(place_symbol_action)

        place_wire_action = QAction("&Wire", self)
        place_wire_action.setShortcut("W")
        place_menu.addAction(place_wire_action)

        place_bus_action = QAction("&Bus", self)
        place_bus_action.setShortcut("B")
        place_menu.addAction(place_bus_action)

        place_menu.addSeparator()

        place_power_action = QAction("&Power Symbol", self)
        place_power_action.setShortcut("P")
        place_menu.addAction(place_power_action)

        place_label_action = QAction("&Label", self)
        place_label_action.setShortcut("L")
        place_menu.addAction(place_label_action)

        # Inspect menu
        inspect_menu = menubar.addMenu("&Inspect")

        erc_action = QAction("&Electrical Rules Checker", self)
        inspect_menu.addAction(erc_action)

        netlist_action = QAction("Generate &Netlist", self)
        inspect_menu.addAction(netlist_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        annotate_action = QAction("&Annotate Schematic", self)
        tools_menu.addAction(annotate_action)

        bom_action = QAction("Generate &BOM", self)
        tools_menu.addAction(bom_action)

        # Preferences menu
        prefs_menu = menubar.addMenu("P&references")

        prefs_action = QAction("&Preferences...", self)
        prefs_menu.addAction(prefs_action)

        colors_action = QAction("&Color Theme...", self)
        prefs_menu.addAction(colors_action)

    def _create_top_toolbar(self):
        """Create KiCad-style top toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("main_toolbar")
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # File operations
        new_action = QAction("New", self)
        new_action.setToolTip("New schematic")
        toolbar.addAction(new_action)

        open_action = QAction("Open", self)
        open_action.setToolTip("Open schematic")
        toolbar.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setToolTip("Save schematic")
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # Edit operations
        undo_action = QAction("Undo", self)
        toolbar.addAction(undo_action)

        redo_action = QAction("Redo", self)
        toolbar.addAction(redo_action)

        toolbar.addSeparator()

        # Zoom controls
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(lambda: self.canvas.scale(1.2, 1.2))
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(lambda: self.canvas.scale(1/1.2, 1/1.2))
        toolbar.addAction(zoom_out_action)

        zoom_fit_action = QAction("Zoom Fit", self)
        toolbar.addAction(zoom_fit_action)

        toolbar.addSeparator()

        # Find
        find_action = QAction("Find", self)
        toolbar.addAction(find_action)

    def _create_left_toolbar(self):
        """Create KiCad-style left toolbar (display options)"""
        toolbar = QToolBar("Display Toolbar")
        toolbar.setObjectName("left_toolbar")
        self.addToolBar(Qt.LeftToolBarArea, toolbar)

        grid_action = QAction("Grid", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(True)
        grid_action.setToolTip("Show/hide grid")
        grid_action.triggered.connect(self._toggle_grid)
        toolbar.addAction(grid_action)

        units_action = QAction("Units", self)
        units_action.setToolTip("Toggle inch/mm")
        toolbar.addAction(units_action)

        cursor_action = QAction("Cursor", self)
        cursor_action.setCheckable(True)
        cursor_action.setChecked(True)
        cursor_action.setToolTip("Show full-screen cursor")
        toolbar.addAction(cursor_action)

        toolbar.addSeparator()

        properties_action = QAction("Properties", self)
        properties_action.setCheckable(True)
        properties_action.setToolTip("Show properties panel")
        toolbar.addAction(properties_action)

    def _create_right_toolbar(self):
        """Create KiCad-style right toolbar (schematic tools)"""
        toolbar = QToolBar("Tools Toolbar")
        toolbar.setObjectName("right_toolbar")
        self.addToolBar(Qt.RightToolBarArea, toolbar)

        # Selection tool
        select_action = QAction("Select", self)
        select_action.setCheckable(True)
        select_action.setChecked(True)
        select_action.setToolTip("Select items (Esc)")
        toolbar.addAction(select_action)

        toolbar.addSeparator()

        # Component placement
        symbol_action = QAction("Symbol", self)
        symbol_action.setToolTip("Add symbol (A)")
        toolbar.addAction(symbol_action)

        power_action = QAction("Power", self)
        power_action.setToolTip("Add power symbol (P)")
        toolbar.addAction(power_action)

        toolbar.addSeparator()

        # Wiring tools
        wire_action = QAction("Wire", self)
        wire_action.setToolTip("Draw wire (W)")
        toolbar.addAction(wire_action)

        bus_action = QAction("Bus", self)
        bus_action.setToolTip("Draw bus (B)")
        toolbar.addAction(bus_action)

        noconnect_action = QAction("No Connect", self)
        noconnect_action.setToolTip("Place no-connect flag")
        toolbar.addAction(noconnect_action)

        junction_action = QAction("Junction", self)
        junction_action.setToolTip("Add junction (J)")
        toolbar.addAction(junction_action)

        toolbar.addSeparator()

        # Labels
        label_action = QAction("Label", self)
        label_action.setToolTip("Add net label (L)")
        toolbar.addAction(label_action)

        global_label_action = QAction("Global Label", self)
        global_label_action.setToolTip("Add global label")
        toolbar.addAction(global_label_action)

        toolbar.addSeparator()

        # Hierarchy
        sheet_action = QAction("Sheet", self)
        sheet_action.setToolTip("Add hierarchical sheet (S)")
        toolbar.addAction(sheet_action)

        sheet_pin_action = QAction("Sheet Pin", self)
        sheet_pin_action.setToolTip("Add sheet pin")
        toolbar.addAction(sheet_pin_action)

        toolbar.addSeparator()

        # Graphics
        line_action = QAction("Line", self)
        line_action.setToolTip("Draw line")
        toolbar.addAction(line_action)

        text_action = QAction("Text", self)
        text_action.setToolTip("Add text (T)")
        toolbar.addAction(text_action)

        image_action = QAction("Image", self)
        image_action.setToolTip("Add image")
        toolbar.addAction(image_action)

        toolbar.addSeparator()

        # Delete
        delete_action = QAction("Delete", self)
        delete_action.setToolTip("Delete item (Del)")
        toolbar.addAction(delete_action)

    def _create_status_bar(self):
        """Create KiCad-style status bar showing cursor position, zoom, grid, units"""
        status = QStatusBar()
        self.setStatusBar(status)

        # Position labels (X, Y)
        self.pos_x_label = QLabel("X: 0.000")
        self.pos_y_label = QLabel("Y: 0.000")
        status.addPermanentWidget(self.pos_x_label)
        status.addPermanentWidget(self.pos_y_label)

        # Relative position (dx, dy, dist)
        self.pos_dx_label = QLabel("dx: 0.000")
        self.pos_dy_label = QLabel("dy: 0.000")
        self.pos_dist_label = QLabel("dist: 0.000")
        status.addPermanentWidget(self.pos_dx_label)
        status.addPermanentWidget(self.pos_dy_label)
        status.addPermanentWidget(self.pos_dist_label)

        # Zoom
        self.zoom_label = QLabel("Z: 1.00")
        status.addPermanentWidget(self.zoom_label)

        # Grid
        self.grid_label = QLabel("Grid: 50 mil")
        status.addPermanentWidget(self.grid_label)

        # Units
        self.units_label = QLabel("inches")
        status.addPermanentWidget(self.units_label)

    def _create_side_panels(self):
        """Create side panels (symbol browser, properties)"""
        # Symbol library browser (can be docked)
        self.symbol_dock = QDockWidget("Symbol Libraries", self)
        symbol_widget = QWidget()
        symbol_layout = QVBoxLayout(symbol_widget)
        symbol_layout.addWidget(QLabel("Symbol Browser"))
        self.symbol_dock.setWidget(symbol_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.symbol_dock)
        self.symbol_dock.hide()  # Hidden by default

        # Properties panel
        self.properties_dock = QDockWidget("Properties", self)
        props_widget = QWidget()
        props_layout = QVBoxLayout(props_widget)
        props_layout.addWidget(QLabel("Properties Panel"))
        self.properties_dock.setWidget(props_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.properties_dock)
        self.properties_dock.hide()  # Hidden by default

    def _update_status_bar(self):
        """Update status bar with current cursor position and zoom"""
        # Convert to mils (KiCad default)
        x_mils = self.canvas.cursor_x / 1.27  # Convert from internal units
        y_mils = self.canvas.cursor_y / 1.27

        self.pos_x_label.setText(f"X: {x_mils:.3f}")
        self.pos_y_label.setText(f"Y: {y_mils:.3f}")

        # Get zoom level
        zoom = self.canvas.transform().m11()
        self.zoom_label.setText(f"Z: {zoom:.2f}")

    def _toggle_grid(self):
        """Toggle grid visibility"""
        self.canvas.grid_visible = not self.canvas.grid_visible
        self.canvas.viewport().update()
