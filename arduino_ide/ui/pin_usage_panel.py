"""
Pin Usage Overview Panel
Shows which pins are being used in the current sketch
"""

from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from arduino_ide.ui.pin_usage_widget import PinUsageWidget


class PinUsagePanel(QDockWidget):
    """Dockable panel showing pin usage overview"""

    def __init__(self, parent=None):
        super().__init__("Pin Usage Overview", parent)
        self.setObjectName("PinUsagePanel")
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea
        )
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.pin_usage_widget = PinUsageWidget()
        layout.addWidget(self.pin_usage_widget)

        self.setWidget(container)

    def set_board(self, board):
        """Set the current board

        Args:
            board: Board object from arduino_ide.models.board
        """
        self.pin_usage_widget.set_board(board)

    def update_pin_usage(self, code_text):
        """Update pin usage overview from code

        Args:
            code_text: Arduino sketch code as string
        """
        self.pin_usage_widget.update_from_code(code_text)
