"""Board information and selection panel."""

from typing import Dict, Optional, Sequence

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QGroupBox,
    QFormLayout,
)
from PySide6.QtCore import Signal

from arduino_ide.models.board import Board
from arduino_ide.ui.board_formatting import (
    format_board_features,
    format_board_power,
    format_board_specifications,
)


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

        self.voltage_label = QLabel("Unknown")
        info_layout.addRow("Operating Voltage:", self.voltage_label)

        self.digital_pins_label = QLabel("Unknown")
        info_layout.addRow("Digital I/O Pins:", self.digital_pins_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        features_group = QGroupBox("Features")
        features_layout = QFormLayout()

        self.wifi_label = QLabel("Unknown")
        features_layout.addRow("WiFi:", self.wifi_label)

        self.bluetooth_label = QLabel("Unknown")
        features_layout.addRow("Bluetooth:", self.bluetooth_label)

        self.usb_label = QLabel("Unknown")
        features_layout.addRow("USB:", self.usb_label)

        self.adc_label = QLabel("Unknown")
        features_layout.addRow("ADC Resolution:", self.adc_label)

        self.dac_label = QLabel("Unknown")
        features_layout.addRow("DAC:", self.dac_label)

        self.touch_label = QLabel("Unknown")
        features_layout.addRow("Touch Pins:", self.touch_label)

        self.rtc_label = QLabel("Unknown")
        features_layout.addRow("RTC:", self.rtc_label)

        self.sleep_label = QLabel("Unknown")
        features_layout.addRow("Sleep Mode:", self.sleep_label)

        features_group.setLayout(features_layout)
        layout.addWidget(features_group)

        power_group = QGroupBox("Power")
        power_layout = QFormLayout()

        self.power_typical_label = QLabel("Unknown")
        power_layout.addRow("Typical:", self.power_typical_label)

        self.power_max_label = QLabel("Unknown")
        power_layout.addRow("Maximum:", self.power_max_label)

        power_group.setLayout(power_layout)
        layout.addWidget(power_group)

        layout.addStretch()

    def set_boards(self, boards: Sequence[Board]):
        """Populate the combo box with the provided boards."""
        # Remember the currently selected board so we can restore it when possible
        current_index = self.board_combo.currentIndex()
        current_board = self._boards_by_index.get(current_index)
        preferred_fqbn = current_board.fqbn if current_board else None
        preferred_name = current_board.name if current_board else None

        self._boards_by_index = {}
        self.board_combo.blockSignals(True)
        self.board_combo.clear()

        target_index = 0
        for index, board in enumerate(boards):
            self.board_combo.addItem(board.name)
            self._boards_by_index[index] = board
            if preferred_fqbn and board.fqbn == preferred_fqbn:
                target_index = index
            elif not preferred_fqbn and preferred_name and board.name == preferred_name:
                target_index = index

        if boards:
            self.board_combo.setCurrentIndex(target_index)
        self.board_combo.blockSignals(False)

        self.update_board_info(self._boards_by_index.get(self.board_combo.currentIndex()))

    def select_board(self, board: Board):
        """Select the given board without emitting selection signals."""
        if not board:
            return

        for index, stored_board in self._boards_by_index.items():
            if (stored_board.fqbn and stored_board.fqbn == board.fqbn) or (
                not stored_board.fqbn and stored_board.name == board.name
            ):
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

        specs = format_board_specifications(board)
        self.cpu_label.setText(specs["cpu"])
        self.flash_label.setText(specs["flash"])
        self.ram_label.setText(specs["ram"])
        self.clock_label.setText(specs["clock"])
        self.voltage_label.setText(specs["voltage"])
        self.digital_pins_label.setText(specs["digital_pins"])

        features = format_board_features(board)
        self.wifi_label.setText(features["wifi"])
        self.bluetooth_label.setText(features["bluetooth"])
        self.usb_label.setText(features["usb"])
        self.adc_label.setText(features["adc"])
        self.dac_label.setText(features["dac"])
        self.touch_label.setText(features["touch"])
        self.rtc_label.setText(features["rtc"])
        self.sleep_label.setText(features["sleep"])

        power = format_board_power(board)
        self.power_typical_label.setText(power["typical"])
        self.power_max_label.setText(power["maximum"])

    def set_port(self, port):
        """Set connected port"""
        self.port_label.setText(port)

    def _on_combo_changed(self, index: int):
        board = self._boards_by_index.get(index)
        self.update_board_info(board)
        if board:
            self.board_selected.emit(board)
