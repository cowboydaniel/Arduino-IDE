"""
Console panel for build output and messages
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor, QColor


class ConsolePanel(QWidget):
    """Console for showing build output and messages"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Output area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas, Monaco, Courier New", 9))
        layout.addWidget(self.output_text)

    def append_output(self, text, color=None):
        """Append text to console"""
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.End)

        if color:
            self.output_text.setTextColor(QColor(color))

        self.output_text.append(text)

        if color:
            self.output_text.setTextColor(QColor(255, 255, 255))

        # Auto-scroll
        self.output_text.verticalScrollBar().setValue(
            self.output_text.verticalScrollBar().maximum()
        )

    def clear(self):
        """Clear console"""
        self.output_text.clear()
