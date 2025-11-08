"""
Enhanced status bar for Arduino IDE Modern
Displays comprehensive IDE status information
"""

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor


class StatusBarSection(QLabel):
    """Individual section in the status bar"""

    clicked = Signal()

    def __init__(self, text="", clickable=False, parent=None):
        super().__init__(text, parent)
        self.is_clickable = clickable

        if clickable:
            self.setCursor(QCursor(Qt.PointingHandCursor))

        self.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                padding: 2px 8px;
                font-size: 12px;
                border-right: 1px solid #3E3E42;
            }
            QLabel:hover {
                background-color: #2A2D2E;
            }
        """)

    def mousePressEvent(self, event):
        """Handle mouse clicks"""
        if self.is_clickable and event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class StatusBar(QWidget):
    """
    Enhanced status bar showing:
    - Status indicator (Ready/Compiling/Uploading/Error)
    - Cursor position (Line, Column)
    - File encoding (UTF-8)
    - Language type (C++/Python)
    - Board selection
    - Port selection
    - Connection status
    """

    # Signals for user interactions
    board_clicked = Signal()
    port_clicked = Signal()
    encoding_clicked = Signal()
    language_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Initialize the status bar UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Status indicator (left side)
        self.status_label = StatusBarSection("Ready")
        layout.addWidget(self.status_label)

        # Cursor position
        self.cursor_label = StatusBarSection("Line 1, Col 1")
        layout.addWidget(self.cursor_label)

        # File encoding (clickable)
        self.encoding_label = StatusBarSection("UTF-8", clickable=True)
        self.encoding_label.clicked.connect(self.encoding_clicked.emit)
        layout.addWidget(self.encoding_label)

        # Language type (clickable)
        self.language_label = StatusBarSection("C++", clickable=True)
        self.language_label.clicked.connect(self.language_clicked.emit)
        layout.addWidget(self.language_label)

        # Add stretch to push next items to the right
        layout.addStretch()

        # Board selection (right side, clickable)
        self.board_label = StatusBarSection("Board: Arduino Uno", clickable=True)
        self.board_label.clicked.connect(self.board_clicked.emit)
        layout.addWidget(self.board_label)

        # Port selection (clickable)
        self.port_label = StatusBarSection("Port: Not Selected", clickable=True)
        self.port_label.clicked.connect(self.port_clicked.emit)
        layout.addWidget(self.port_label)

        # Connection status
        self.connection_label = StatusBarSection("🔌 Disconnected")
        layout.addWidget(self.connection_label)

        # Overall styling
        self.setStyleSheet("""
            QWidget {
                background-color: #007ACC;
                border-top: 1px solid #0098FF;
                min-height: 24px;
                max-height: 24px;
            }
        """)

    def set_status(self, status):
        """
        Set the main status indicator

        Args:
            status: Status text (e.g., "Ready", "Compiling", "Uploading", "Error")
        """
        self.status_label.setText(status)

        # Change color based on status
        if "error" in status.lower() or "failed" in status.lower():
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #F48771;
                    font-weight: bold;
                    padding: 2px 8px;
                    font-size: 12px;
                    border-right: 1px solid #3E3E42;
                }
            """)
        elif "compiling" in status.lower() or "uploading" in status.lower():
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #FFD700;
                    padding: 2px 8px;
                    font-size: 12px;
                    border-right: 1px solid #3E3E42;
                }
            """)
        else:
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #CCCCCC;
                    padding: 2px 8px;
                    font-size: 12px;
                    border-right: 1px solid #3E3E42;
                }
            """)

    def set_cursor_position(self, line, column):
        """
        Update cursor position display

        Args:
            line: Current line number (1-based)
            column: Current column number (1-based)
        """
        self.cursor_label.setText(f"Line {line}, Col {column}")

    def set_encoding(self, encoding):
        """
        Set file encoding display

        Args:
            encoding: Encoding name (e.g., "UTF-8", "ASCII")
        """
        self.encoding_label.setText(encoding)

    def set_language(self, language):
        """
        Set language/file type display

        Args:
            language: Language name (e.g., "C++", "Python", "Plain Text")
        """
        self.language_label.setText(language)

    def set_board(self, board_name):
        """
        Set board name display

        Args:
            board_name: Name of the selected board
        """
        self.board_label.setText(f"Board: {board_name}")

    def set_port(self, port_name):
        """
        Set port name display

        Args:
            port_name: Name of the selected port (or None)
        """
        if port_name and port_name != "No ports available":
            # Extract just the port device name (e.g., "COM3" from "COM3 - USB Serial Port")
            port_device = port_name.split(" - ")[0] if " - " in port_name else port_name
            self.port_label.setText(f"Port: {port_device}")
        else:
            self.port_label.setText("Port: Not Selected")

    def set_connection_status(self, connected):
        """
        Set connection status

        Args:
            connected: True if connected to board, False otherwise
        """
        if connected:
            self.connection_label.setText("🔌 Connected")
            self.connection_label.setStyleSheet("""
                QLabel {
                    color: #4EC9B0;
                    font-weight: bold;
                    padding: 2px 8px;
                    font-size: 12px;
                    border-right: 1px solid #3E3E42;
                }
            """)
        else:
            self.connection_label.setText("🔌 Disconnected")
            self.connection_label.setStyleSheet("""
                QLabel {
                    color: #858585;
                    padding: 2px 8px;
                    font-size: 12px;
                    border-right: 1px solid #3E3E42;
                }
            """)

    def detect_language_from_filename(self, filename):
        """
        Detect programming language from file extension

        Args:
            filename: Name of the file

        Returns:
            Language name string
        """
        if filename.endswith('.ino') or filename.endswith('.cpp') or filename.endswith('.c') or filename.endswith('.h'):
            return "C++"
        elif filename.endswith('.py'):
            return "Python"
        elif filename.endswith('.json'):
            return "JSON"
        elif filename.endswith('.xml'):
            return "XML"
        elif filename.endswith('.md'):
            return "Markdown"
        else:
            return "Plain Text"
