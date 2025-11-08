"""
Quick Actions Panel for Arduino IDE
Provides quick access to common IDE actions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont


class CollapsibleSection(QWidget):
    """A collapsible section widget with a header and content area."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.is_collapsed = False
        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header = QPushButton(f"▼ {self.title}")
        self.header.setFlat(True)
        self.header.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px;
                font-weight: bold;
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.header.clicked.connect(self.toggle_collapse)
        layout.addWidget(self.header)

        # Content container
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(2)
        layout.addWidget(self.content_widget)

    def toggle_collapse(self):
        """Toggle the collapsed state."""
        self.is_collapsed = not self.is_collapsed
        self.content_widget.setVisible(not self.is_collapsed)
        arrow = "▶" if self.is_collapsed else "▼"
        self.header.setText(f"{arrow} {self.title}")

    def add_action_button(self, text, icon_text, callback):
        """Add an action button to this section."""
        btn = QPushButton(f"{icon_text}  {text}")
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px 15px;
                background-color: transparent;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 215, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(0, 120, 215, 0.5);
            }
        """)
        btn.setCursor(Qt.PointingHandCursor)
        if callback:
            btn.clicked.connect(callback)
        self.content_layout.addWidget(btn)
        return btn


class QuickActionsPanel(QWidget):
    """
    Quick Actions Panel providing fast access to common IDE functions.
    """

    # Signals for actions
    upload_clicked = Signal()
    find_clicked = Signal()
    libraries_clicked = Signal()
    examples_clicked = Signal()
    board_clicked = Signal()
    verify_clicked = Signal()
    new_sketch_clicked = Signal()
    open_sketch_clicked = Signal()
    save_sketch_clicked = Signal()
    serial_monitor_clicked = Signal()
    serial_plotter_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title header
        header = QLabel("Quick Actions")
        header.setStyleSheet("""
            QLabel {
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                background-color: rgba(0, 120, 215, 0.2);
                border-bottom: 2px solid rgba(0, 120, 215, 0.5);
            }
        """)
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Content widget
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Main Quick Tools section (always visible)
        self.add_quick_tools_section(content_layout)

        # Additional collapsible sections
        self.add_sketch_section(content_layout)
        self.add_file_section(content_layout)
        self.add_tools_section(content_layout)

        # Add stretch to push everything to the top
        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    def add_quick_tools_section(self, layout):
        """Add the main quick tools section (non-collapsible)."""
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 8, 0, 8)
        section_layout.setSpacing(2)

        # Quick action buttons
        actions = [
            ("📤", "Upload", self.upload_clicked.emit),
            ("🔍", "Find", self.find_clicked.emit),
            ("📚", "Libraries", self.libraries_clicked.emit),
            ("🔧", "Examples", self.examples_clicked.emit),
            ("⚙️", "Board", self.board_clicked.emit),
        ]

        for icon, text, callback in actions:
            btn = self.create_action_button(icon, text, callback)
            section_layout.addWidget(btn)

        layout.addWidget(section)

    def add_sketch_section(self, layout):
        """Add collapsible sketch section."""
        section = CollapsibleSection("Sketch")
        section.add_action_button("Verify", "✓", self.verify_clicked.emit)
        section.add_action_button("Upload", "📤", self.upload_clicked.emit)
        layout.addWidget(section)

    def add_file_section(self, layout):
        """Add collapsible file section."""
        section = CollapsibleSection("File")
        section.add_action_button("New", "📄", self.new_sketch_clicked.emit)
        section.add_action_button("Open", "📂", self.open_sketch_clicked.emit)
        section.add_action_button("Save", "💾", self.save_sketch_clicked.emit)
        layout.addWidget(section)

    def add_tools_section(self, layout):
        """Add collapsible tools section."""
        section = CollapsibleSection("Tools")
        section.add_action_button("Serial Monitor", "📟", self.serial_monitor_clicked.emit)
        section.add_action_button("Serial Plotter", "📊", self.serial_plotter_clicked.emit)
        section.add_action_button("Board Manager", "⚙️", self.board_clicked.emit)
        section.add_action_button("Library Manager", "📚", self.libraries_clicked.emit)
        layout.addWidget(section)

    def create_action_button(self, icon, text, callback):
        """Create a styled action button."""
        btn = QPushButton(f"{icon}  {text}")
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 12px 15px;
                font-size: 13px;
                background-color: transparent;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 215, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(0, 120, 215, 0.5);
            }
        """)
        btn.setCursor(Qt.PointingHandCursor)
        if callback:
            btn.clicked.connect(callback)
        return btn
