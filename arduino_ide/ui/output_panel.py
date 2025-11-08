"""
Output Panel for Arduino IDE
Displays general debug and system output
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QCheckBox, QLabel, QComboBox
)
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QTextCursor, QColor


class OutputPanel(QWidget):
    """Panel for displaying general output, debug messages, and system logs"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Control bar
        control_layout = QHBoxLayout()

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_output)
        control_layout.addWidget(clear_btn)

        # Auto-scroll checkbox
        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        control_layout.addWidget(self.autoscroll_check)

        # Timestamp checkbox
        self.timestamp_check = QCheckBox("Show timestamps")
        self.timestamp_check.setChecked(True)
        control_layout.addWidget(self.timestamp_check)

        # Word wrap checkbox
        self.wordwrap_check = QCheckBox("Word wrap")
        self.wordwrap_check.setChecked(False)
        self.wordwrap_check.toggled.connect(self.toggle_word_wrap)
        control_layout.addWidget(self.wordwrap_check)

        # Output filter
        control_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Debug", "Info", "System", "Error"])
        control_layout.addWidget(self.filter_combo)

        control_layout.addStretch()

        # Line count label
        self.line_count_label = QLabel("0 lines")
        self.line_count_label.setStyleSheet("color: #888; font-size: 11px;")
        control_layout.addWidget(self.line_count_label)

        layout.addLayout(control_layout)

        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #3e3e3e;
            }
        """)
        layout.addWidget(self.output_text)

    def append_output(self, text, category="info", color=None):
        """Append text to the output panel

        Args:
            text: Text to append
            category: Category of the output (debug, info, system, error)
            color: Optional QColor to use for the text
        """
        # Get timestamp if enabled
        timestamp = ""
        if self.timestamp_check.isChecked():
            timestamp = f"[{QDateTime.currentDateTime().toString('HH:mm:ss')}] "

        # Build formatted message
        prefix = ""
        if category.lower() == "debug":
            prefix = "[DEBUG] "
            if not color:
                color = QColor(156, 220, 254)  # Light blue
        elif category.lower() == "error":
            prefix = "[ERROR] "
            if not color:
                color = QColor(244, 71, 71)  # Red
        elif category.lower() == "system":
            prefix = "[SYSTEM] "
            if not color:
                color = QColor(181, 206, 168)  # Light green
        elif category.lower() == "info":
            prefix = "[INFO] "
            if not color:
                color = QColor(206, 145, 120)  # Orange

        full_text = f"{timestamp}{prefix}{text}"

        # Insert text with color
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.End)

        if color:
            format = cursor.charFormat()
            format.setForeground(color)
            cursor.setCharFormat(format)

        cursor.insertText(full_text + "\n")

        # Auto-scroll if enabled
        if self.autoscroll_check.isChecked():
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        # Update line count
        self.update_line_count()

    def append_debug(self, text):
        """Append debug message"""
        self.append_output(text, "debug")

    def append_error(self, text):
        """Append error message"""
        self.append_output(text, "error")

    def append_system(self, text):
        """Append system message"""
        self.append_output(text, "system")

    def append_info(self, text):
        """Append info message"""
        self.append_output(text, "info")

    def clear_output(self):
        """Clear all output"""
        self.output_text.clear()
        self.update_line_count()

    def toggle_word_wrap(self, enabled):
        """Toggle word wrap"""
        if enabled:
            self.output_text.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.output_text.setLineWrapMode(QTextEdit.NoWrap)

    def update_line_count(self):
        """Update the line count label"""
        line_count = self.output_text.document().blockCount()
        self.line_count_label.setText(f"{line_count} line{'s' if line_count != 1 else ''}")

    def log(self, message, level="info"):
        """Log a message with specified level

        Args:
            message: Message to log
            level: Log level (debug, info, system, error)
        """
        self.append_output(message, level)
