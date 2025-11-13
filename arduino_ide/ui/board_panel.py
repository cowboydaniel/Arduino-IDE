"""Board information and selection panel."""

from typing import Dict, Optional, Sequence

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox,
    QGroupBox, QFormLayout
)
from PySide6.QtCore import Signal

from arduino_ide.models.board import Board


class BoardPanel(QWidget):
    """Panel showing board information and configuration."""

    board_selected = Signal(object)  # Emits the selected Board

    def __init__(self, parent=None):
        super().__init__(parent)
        self._boards_by_index: Dict[int, Board] = {}
        self.init_ui()

    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)

        # Board selection
        board_group = QGroupBox("Board")
        board_layout = QFormLayout()

        self.board_combo = QComboBox()
        self.board_combo.currentIndexChanged.connect(self._on_combo_changed)
        board_layout.addRow("Type:", self.board_combo)

        self.port_label = QLabel("Not connected")
        board_layout.addRow("Port:", self.port_label)

        board_group.setLayout(board_layout)
        layout.addWidget(board_group)

        # Board info
        info_group = QGroupBox("Information")
        info_layout = QFormLayout()

        self.cpu_label = QLabel("Unknown")
        info_layout.addRow("CPU:", self.cpu_label)

        self.flash_label = QLabel("Unknown")
        info_layout.addRow("Flash:", self.flash_label)

        self.ram_label = QLabel("Unknown")
        info_layout.addRow("RAM:", self.ram_label)

        self.clock_label = QLabel("Unknown")
        info_layout.addRow("Clock:", self.clock_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()

    def set_boards(self, boards: Sequence[Board]):
        """Populate the combo box with the provided boards."""
        self._boards_by_index = {}
        self.board_combo.blockSignals(True)
        self.board_combo.clear()
        for index, board in enumerate(boards):
            self.board_combo.addItem(board.name)
            self._boards_by_index[index] = board
        if boards:
            self.board_combo.setCurrentIndex(0)
        self.board_combo.blockSignals(False)

        self.update_board_info(self._boards_by_index.get(self.board_combo.currentIndex()))

    def select_board(self, board: Board):
        """Select the given board without emitting selection signals."""
        if not board:
            return

        for index, stored_board in self._boards_by_index.items():
            if stored_board.fqbn == board.fqbn:
                if self.board_combo.currentIndex() == index:
                    # Ensure info is up-to-date even if the index already matches
                    self.update_board_info(stored_board)
                    return
                self.board_combo.blockSignals(True)
                self.board_combo.setCurrentIndex(index)
                self.board_combo.blockSignals(False)
                self.update_board_info(stored_board)
                return

    def update_board_info(self, board: Optional[Board] = None):
        """Update board information based on selected board.

        Dynamically extracts board specifications from the Board object,
        allowing it to work with any board from the Arduino ecosystem.

        Args:
            board: Optional Board object from arduino_ide.models.board.
        """
        if board is None:
            board = self._boards_by_index.get(self.board_combo.currentIndex())

        # Default values
        cpu = "Unknown"
        flash = "Unknown"
        ram = "Unknown"
        clock = "Unknown"

        # Extract specs from Board object
        if board and hasattr(board, 'specs'):
            specs = board.specs
            cpu = specs.cpu if specs.cpu else "Unknown"
            flash = specs.flash if specs.flash else "Unknown"
            ram = specs.ram if specs.ram else "Unknown"
            clock = specs.clock if specs.clock else "Unknown"

        # Update labels
        self.cpu_label.setText(cpu)
        self.flash_label.setText(flash)
        self.ram_label.setText(ram)
        self.clock_label.setText(clock)

    def set_port(self, port):
        """Set connected port"""
        self.port_label.setText(port)

    def _on_combo_changed(self, index: int):
        board = self._boards_by_index.get(index)
        self.update_board_info(board)
        if board:
            self.board_selected.emit(board)
