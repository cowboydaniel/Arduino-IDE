"""
Visual Programming Editor
Block-based programming interface with drag-and-drop
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QScrollArea, QLabel, QPushButton, QGraphicsView,
                               QGraphicsScene, QGraphicsItem, QGraphicsRectItem,
                               QGraphicsTextItem, QToolBox, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, Slot
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPainterPath
import logging
from typing import Optional, Dict

from arduino_ide.services.visual_programming_service import (
    VisualProgrammingService, BlockDefinition, BlockInstance,
    BlockCategory, BlockType
)

logger = logging.getLogger(__name__)


class BlockGraphicsItem(QGraphicsRectItem):
    """Graphics item representing a block in the workspace"""

    def __init__(self, block_def: BlockDefinition, block_instance: BlockInstance, parent=None):
        super().__init__(parent)

        self.block_def = block_def
        self.block_instance = block_instance

        # Setup appearance
        self.setRect(0, 0, 200, 60)
        self.setPos(block_instance.x, block_instance.y)

        # Set color based on category
        color = QColor(block_def.color)
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(120), 2))

        # Make draggable
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

        # Add label
        self.label = QGraphicsTextItem(self)
        self.label.setPlainText(self._format_label())
        self.label.setDefaultTextColor(Qt.white)
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setPos(10, 20)

        # Add notches for statement blocks
        if block_def.block_type == BlockType.STATEMENT:
            self._draw_notches()


    def _format_label(self) -> str:
        """Format block label with parameter values"""
        label = self.block_def.label

        # Replace parameter placeholders with values
        for param_name, param_value in self.block_instance.parameters.items():
            placeholder = f"{{{param_name}}}"
            label = label.replace(placeholder, str(param_value))

        return label


    def _draw_notches(self):
        """Draw connection notches for statement blocks"""
        # Top notch (for connecting to previous block)
        path = QPainterPath()
        path.moveTo(50, 0)
        path.lineTo(55, -5)
        path.lineTo(65, -5)
        path.lineTo(70, 0)

        # Bottom notch (for connecting to next block)
        rect = self.rect()
        path.moveTo(50, rect.height())
        path.lineTo(55, rect.height() + 5)
        path.lineTo(65, rect.height() + 5)
        path.lineTo(70, rect.height())


    def itemChange(self, change, value):
        """Handle item changes"""
        if change == QGraphicsItem.ItemPositionChange:
            # Update block instance position
            new_pos = value
            self.block_instance.x = new_pos.x()
            self.block_instance.y = new_pos.y()

        return super().itemChange(change, value)


class BlockPaletteWidget(QWidget):
    """Widget displaying available blocks organized by category"""

    block_selected = Signal(str)  # block_id

    def __init__(self, service: VisualProgrammingService, parent=None):
        super().__init__(parent)

        self.service = service

        self._setup_ui()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title = QLabel("Block Palette")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)

        # Toolbox with categories
        self.toolbox = QToolBox()

        # Add each category
        for category in self.service.get_all_categories():
            category_widget = self._create_category_widget(category)
            self.toolbox.addItem(category_widget, category.value)

        layout.addWidget(self.toolbox)


    def _create_category_widget(self, category: BlockCategory) -> QWidget:
        """Create widget for a block category"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)

        blocks = self.service.get_blocks_by_category(category)

        for block_def in blocks:
            block_button = QPushButton(block_def.label)
            block_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {block_def.color};
                    color: white;
                    border: 2px solid {QColor(block_def.color).darker(120).name()};
                    border-radius: 5px;
                    padding: 8px;
                    text-align: left;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {QColor(block_def.color).lighter(110).name()};
                }}
            """)
            block_button.setToolTip(block_def.tooltip)
            block_button.clicked.connect(lambda checked, bid=block_def.id: self.block_selected.emit(bid))

            layout.addWidget(block_button)

        layout.addStretch()
        return widget


class BlockWorkspaceView(QGraphicsView):
    """Graphics view for the block workspace"""

    def __init__(self, service: VisualProgrammingService, parent=None):
        super().__init__(parent)

        self.service = service
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Block items
        self.block_items: Dict[str, BlockGraphicsItem] = {}

        # Setup view
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setSceneRect(-2000, -2000, 4000, 4000)

        # Grid background
        self.setBackgroundBrush(QBrush(QColor("#F5F5F5")))

        # Connect to service
        self.service.block_added.connect(self._on_block_added)
        self.service.block_removed.connect(self._on_block_removed)

        logger.info("Block workspace view initialized")


    @Slot(str)
    def _on_block_added(self, instance_id: str):
        """Handle block added to workspace"""
        blocks = self.service.get_workspace_blocks()
        block_instance = next((b for b in blocks if b.instance_id == instance_id), None)

        if not block_instance:
            return

        block_def = self.service.get_block_definition(block_instance.definition_id)
        if not block_def:
            return

        # Create graphics item
        item = BlockGraphicsItem(block_def, block_instance)
        self.scene.addItem(item)
        self.block_items[instance_id] = item

        logger.debug(f"Added block to workspace: {instance_id}")


    @Slot(str)
    def _on_block_removed(self, instance_id: str):
        """Handle block removed from workspace"""
        if instance_id in self.block_items:
            item = self.block_items[instance_id]
            self.scene.removeItem(item)
            del self.block_items[instance_id]

            logger.debug(f"Removed block from workspace: {instance_id}")


    def add_block_at_center(self, block_id: str):
        """Add a block at the center of the view"""
        # Get center position in scene coordinates
        center = self.mapToScene(self.viewport().rect().center())

        # Create block instance
        self.service.create_block_instance(block_id, center.x(), center.y())


    def clear_workspace(self):
        """Clear all blocks"""
        self.service.clear_workspace()
        self.scene.clear()
        self.block_items.clear()


    def drawBackground(self, painter, rect):
        """Draw grid background"""
        super().drawBackground(painter, rect)

        # Draw grid
        grid_size = 20
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        painter.setPen(QPen(QColor("#E0E0E0"), 1, Qt.DotLine))

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


class VisualProgrammingEditor(QWidget):
    """
    Main visual programming editor widget
    Combines block palette and workspace
    """

    code_generated = Signal(str)

    def __init__(self, service: Optional[VisualProgrammingService] = None, parent=None):
        super().__init__(parent)

        self.service = service or VisualProgrammingService()

        self._setup_ui()
        self._setup_connections()

        logger.info("Visual programming editor initialized")


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()

        self.new_btn = QPushButton("New")
        self.new_btn.setToolTip("Clear workspace")

        self.load_btn = QPushButton("Load")
        self.load_btn.setToolTip("Load workspace from file")

        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("Save workspace to file")

        self.generate_code_btn = QPushButton("Generate Code")
        self.generate_code_btn.setToolTip("Generate Arduino code from blocks")
        self.generate_code_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        toolbar.addWidget(self.new_btn)
        toolbar.addWidget(self.load_btn)
        toolbar.addWidget(self.save_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.generate_code_btn)

        layout.addLayout(toolbar)

        # Main content - splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left: Block palette
        self.palette = BlockPaletteWidget(self.service)
        self.palette.setMaximumWidth(250)
        splitter.addWidget(self.palette)

        # Right: Workspace
        self.workspace = BlockWorkspaceView(self.service)
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
        self.generate_code_btn.clicked.connect(self._on_generate_code)

        self.palette.block_selected.connect(self._on_block_selected)

        self.service.workspace_changed.connect(self._on_workspace_changed)
        self.service.code_generated.connect(self._on_code_generated)


    @Slot()
    def _on_new_clicked(self):
        """Handle new workspace"""
        reply = QMessageBox.question(
            self,
            "New Workspace",
            "Clear current workspace?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.workspace.clear_workspace()
            self.status_label.setText("Workspace cleared")


    @Slot(str)
    def _on_block_selected(self, block_id: str):
        """Handle block selected from palette"""
        self.workspace.add_block_at_center(block_id)
        self.status_label.setText(f"Added block: {block_id}")


    @Slot()
    def _on_workspace_changed(self):
        """Handle workspace change"""
        block_count = len(self.service.get_workspace_blocks())
        self.status_label.setText(f"Blocks: {block_count}")


    @Slot()
    def _on_generate_code(self):
        """Handle generate code button"""
        try:
            code = self.service.generate_code()

            if not code:
                QMessageBox.warning(
                    self,
                    "No Code",
                    "Add Setup and Loop blocks to generate code."
                )
                return

            # Emit signal with generated code
            self.code_generated.emit(code)

            # Show success message
            QMessageBox.information(
                self,
                "Code Generated",
                "Arduino code has been generated successfully!"
            )

            self.status_label.setText("Code generated successfully")

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to generate code: {str(e)}"
            )


    @Slot(str)
    def _on_code_generated(self, code: str):
        """Handle code generated"""
        logger.info("Code generated from blocks")


    def get_generated_code(self) -> str:
        """Get generated Arduino code"""
        return self.service.generate_code()


    def save_workspace_to_file(self, file_path: str) -> bool:
        """Save workspace to file"""
        return self.service.save_workspace(file_path)


    def load_workspace_from_file(self, file_path: str) -> bool:
        """Load workspace from file"""
        return self.service.load_workspace(file_path)
