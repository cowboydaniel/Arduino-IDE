"""
Modern Board Manager Dialog

Features:
- Board package management
- Board search and filtering
- Board comparison tool
- Package URL management
- Version selection
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QTextBrowser, QCheckBox, QComboBox, QGroupBox, QFormLayout,
    QProgressBar, QTableWidget, QTableWidgetItem, QWidget,
    QMessageBox, QMenu, QScrollArea, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QAction

from ..models import Board, BoardPackage, BoardCategory
from ..services.board_manager import BoardManager


class BoardComparisonDialog(QDialog):
    """Board comparison tool"""

    def __init__(self, boards, parent=None):
        super().__init__(parent)
        self.boards = boards
        self.init_ui()
        self.setWindowTitle("Compare Boards")
        self.resize(900, 600)

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Compare Boards")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)

        # Comparison table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.boards))
        self.table.setHorizontalHeaderLabels([board.name for board in self.boards])

        # Comparison rows
        rows = [
            ("CPU", [board.specs.cpu for board in self.boards]),
            ("Clock", [board.specs.clock for board in self.boards]),
            ("Flash", [board.specs.flash for board in self.boards]),
            ("RAM", [board.specs.ram for board in self.boards]),
            ("Price", [board.price for board in self.boards]),
            ("WiFi", ["✅" if board.specs.wifi else "❌" for board in self.boards]),
            ("Bluetooth", ["✅" if board.specs.bluetooth else "❌" for board in self.boards]),
            ("USB", ["✅" if board.specs.usb else "❌" for board in self.boards]),
            ("ADC", [board.specs.adc_resolution for board in self.boards]),
            ("DAC", ["✅" if board.specs.dac else "❌" for board in self.boards]),
            ("Touch Pins", [str(board.specs.touch_pins) if board.specs.touch_pins > 0 else "❌" for board in self.boards]),
            ("RTC", ["✅" if board.specs.rtc else "❌" for board in self.boards]),
            ("Power (typical)", [board.specs.power_typical for board in self.boards]),
            ("Sleep Mode", ["✅" if board.specs.sleep_mode else "❌" for board in self.boards]),
            ("Best For", [", ".join(board.best_for) if board.best_for else "N/A" for board in self.boards]),
        ]

        self.table.setRowCount(len(rows))
        self.table.setVerticalHeaderLabels([row[0] for row in rows])

        for row_idx, (label, values) in enumerate(rows):
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)

        # Adjust column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self.table)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class PackageURLDialog(QDialog):
    """Dialog for managing package URLs"""

    def __init__(self, package_urls, parent=None):
        super().__init__(parent)
        self.package_urls = package_urls
        self.init_ui()
        self.setWindowTitle("Additional Board Manager URLs")
        self.resize(700, 500)

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Popular Packages:")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)

        # URL list
        self.url_list = QTreeWidget()
        self.url_list.setHeaderLabels(["Name", "URL", "Enabled"])
        self.url_list.itemChanged.connect(self.on_item_changed)

        for url_obj in self.package_urls:
            item = QTreeWidgetItem()
            item.setText(0, url_obj.name)
            item.setText(1, url_obj.url)
            item.setCheckState(2, Qt.Checked if url_obj.enabled else Qt.Unchecked)
            item.setData(0, Qt.UserRole, url_obj)
            self.url_list.addTopLevelItem(item)

        # Adjust column widths
        self.url_list.setColumnWidth(0, 200)
        self.url_list.setColumnWidth(1, 400)

        layout.addWidget(self.url_list)

        # Add custom URL
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("➕ Add Custom URL:"))
        self.custom_name_input = QLineEdit()
        self.custom_name_input.setPlaceholderText("Name")
        custom_layout.addWidget(self.custom_name_input)
        self.custom_url_input = QLineEdit()
        self.custom_url_input.setPlaceholderText("https://...")
        custom_layout.addWidget(self.custom_url_input)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_custom_url)
        custom_layout.addWidget(add_btn)
        layout.addLayout(custom_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def on_item_changed(self, item, column):
        """Handle item state change"""
        if column == 2:
            url_obj = item.data(0, Qt.UserRole)
            if url_obj:
                url_obj.enabled = item.checkState(2) == Qt.Checked

    def add_custom_url(self):
        """Add custom URL"""
        name = self.custom_name_input.text().strip()
        url = self.custom_url_input.text().strip()

        if not name or not url:
            QMessageBox.warning(self, "Invalid Input", "Please provide both name and URL")
            return

        from ..models import BoardPackageURL
        url_obj = BoardPackageURL(name=name, url=url, enabled=True)

        item = QTreeWidgetItem()
        item.setText(0, name)
        item.setText(1, url)
        item.setCheckState(2, Qt.Checked)
        item.setData(0, Qt.UserRole, url_obj)
        self.url_list.addTopLevelItem(item)

        self.package_urls.append(url_obj)

        self.custom_name_input.clear()
        self.custom_url_input.clear()


class BoardDetailView(QWidget):
    """Detailed view for a board"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_board = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Content widget
        content = QWidget()
        content_layout = QVBoxLayout(content)

        # Title
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 16, QFont.Bold))
        content_layout.addWidget(self.title_label)

        # Description
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        content_layout.addWidget(self.desc_label)

        # Specs group
        specs_group = QGroupBox("⚙️ Technical Specifications")
        specs_layout = QFormLayout()
        self.cpu_label = QLabel()
        self.clock_label = QLabel()
        self.flash_label = QLabel()
        self.ram_label = QLabel()
        self.voltage_label = QLabel()
        self.pins_label = QLabel()

        specs_layout.addRow("CPU:", self.cpu_label)
        specs_layout.addRow("Clock Speed:", self.clock_label)
        specs_layout.addRow("Flash Memory:", self.flash_label)
        specs_layout.addRow("SRAM:", self.ram_label)
        specs_layout.addRow("Operating Voltage:", self.voltage_label)
        specs_layout.addRow("Digital I/O Pins:", self.pins_label)

        specs_group.setLayout(specs_layout)
        content_layout.addWidget(specs_group)

        # Features group
        features_group = QGroupBox("✨ Features")
        features_layout = QFormLayout()
        self.wifi_label = QLabel()
        self.bluetooth_label = QLabel()
        self.usb_label = QLabel()
        self.adc_label = QLabel()
        self.dac_label = QLabel()
        self.touch_label = QLabel()
        self.rtc_label = QLabel()
        self.sleep_label = QLabel()

        features_layout.addRow("WiFi:", self.wifi_label)
        features_layout.addRow("Bluetooth:", self.bluetooth_label)
        features_layout.addRow("USB:", self.usb_label)
        features_layout.addRow("ADC Resolution:", self.adc_label)
        features_layout.addRow("DAC:", self.dac_label)
        features_layout.addRow("Touch Pins:", self.touch_label)
        features_layout.addRow("RTC:", self.rtc_label)
        features_layout.addRow("Sleep Mode:", self.sleep_label)

        features_group.setLayout(features_layout)
        content_layout.addWidget(features_group)

        # Power group
        power_group = QGroupBox("🔋 Power Consumption")
        power_layout = QFormLayout()
        self.power_typical_label = QLabel()
        self.power_max_label = QLabel()
        power_layout.addRow("Typical:", self.power_typical_label)
        power_layout.addRow("Maximum:", self.power_max_label)
        power_group.setLayout(power_layout)
        content_layout.addWidget(power_group)

        # Best for
        bestfor_group = QGroupBox("🎯 Best For")
        bestfor_layout = QVBoxLayout()
        self.bestfor_label = QLabel()
        self.bestfor_label.setWordWrap(True)
        bestfor_layout.addWidget(self.bestfor_label)
        bestfor_group.setLayout(bestfor_layout)
        content_layout.addWidget(bestfor_group)

        # Price
        price_layout = QHBoxLayout()
        price_layout.addWidget(QLabel("💰 Typical Price:"))
        self.price_label = QLabel()
        self.price_label.setFont(QFont("Arial", 12, QFont.Bold))
        price_layout.addWidget(self.price_label)
        price_layout.addStretch()
        content_layout.addLayout(price_layout)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def set_board(self, board: Board):
        """Display board details"""
        self.current_board = board

        if not board:
            return

        self.title_label.setText(board.name)
        self.desc_label.setText(board.description)

        # Specs
        self.cpu_label.setText(board.specs.cpu)
        self.clock_label.setText(board.specs.clock)
        self.flash_label.setText(board.specs.flash)
        self.ram_label.setText(board.specs.ram)
        self.voltage_label.setText(board.specs.voltage)
        self.pins_label.setText(f"{board.specs.digital_pins} (PWM: {board.specs.pwm_pins})")

        # Features
        self.wifi_label.setText("✅ Yes" if board.specs.wifi else "❌ No")
        self.bluetooth_label.setText("✅ Yes" if board.specs.bluetooth else "❌ No")
        self.usb_label.setText("✅ Yes" if board.specs.usb else "❌ No")
        self.adc_label.setText(board.specs.adc_resolution)
        self.dac_label.setText("✅ Yes" if board.specs.dac else "❌ No")
        self.touch_label.setText(str(board.specs.touch_pins) if board.specs.touch_pins > 0 else "❌ No")
        self.rtc_label.setText("✅ Yes" if board.specs.rtc else "❌ No")
        self.sleep_label.setText("✅ Yes" if board.specs.sleep_mode else "❌ No")

        # Power
        self.power_typical_label.setText(board.specs.power_typical)
        self.power_max_label.setText(board.specs.power_max)

        # Best for
        if board.best_for:
            self.bestfor_label.setText("• " + "\n• ".join(board.best_for))
        else:
            self.bestfor_label.setText("General purpose")

        # Price
        self.price_label.setText(board.price)


class BoardManagerDialog(QDialog):
    """Modern Board Manager Dialog"""

    board_selected = Signal(str)  # FQBN

    def __init__(self, board_manager: BoardManager, parent=None):
        super().__init__(parent)
        self.board_manager = board_manager
        self.current_packages = []
        self.selected_boards_for_comparison = []

        # Connect signals
        self.board_manager.status_message.connect(self.on_status_message)
        self.board_manager.progress_changed.connect(self.on_progress_changed)
        self.board_manager.package_installed.connect(self.on_package_changed)
        self.board_manager.package_uninstalled.connect(self.on_package_changed)
        self.board_manager.package_updated.connect(self.on_package_changed)
        self.board_manager.index_updated.connect(self.refresh_packages)

        self.init_ui()
        self.setWindowTitle("Board Manager")
        self.resize(1200, 800)

        # Initial load
        self.refresh_packages()

        # Automatically update index every time the board manager is opened
        self.board_manager.update_index(force=True)

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Top toolbar
        toolbar = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Refresh Packages")
        refresh_btn.clicked.connect(self.update_index)
        toolbar.addWidget(refresh_btn)

        urls_btn = QPushButton("📋 Package URLs")
        urls_btn.clicked.connect(self.manage_package_urls)
        toolbar.addWidget(urls_btn)

        compare_btn = QPushButton("📊 Compare Boards")
        compare_btn.clicked.connect(self.show_board_comparison)
        toolbar.addWidget(compare_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Package list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Search
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("ESP32, Arduino, STM32...")
        self.search_input.textChanged.connect(self.refresh_packages)
        search_layout.addWidget(self.search_input)
        left_layout.addLayout(search_layout)

        # Filters
        self.filter_installed = QCheckBox("Installed only")
        self.filter_installed.stateChanged.connect(self.refresh_packages)
        left_layout.addWidget(self.filter_installed)

        self.filter_updates = QCheckBox("Updates available")
        self.filter_updates.stateChanged.connect(self.refresh_packages)
        left_layout.addWidget(self.filter_updates)

        # Action buttons
        action_buttons_layout = QHBoxLayout()

        self.install_btn = QPushButton("Install")
        self.install_btn.setEnabled(False)
        self.install_btn.clicked.connect(self.on_install_button_clicked)
        action_buttons_layout.addWidget(self.install_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.on_cancel_button_clicked)
        action_buttons_layout.addWidget(self.cancel_btn)

        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.setEnabled(False)
        self.uninstall_btn.clicked.connect(self.on_uninstall_button_clicked)
        action_buttons_layout.addWidget(self.uninstall_btn)

        action_buttons_layout.addStretch()
        left_layout.addLayout(action_buttons_layout)

        # Package list
        self.package_list = QTreeWidget()
        self.package_list.setHeaderLabels(["Package", "Version", "Boards", "Status"])
        self.package_list.itemClicked.connect(self.on_package_clicked)
        self.package_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.package_list.customContextMenuRequested.connect(self.show_package_context_menu)
        left_layout.addWidget(self.package_list)

        splitter.addWidget(left_panel)

        # Right panel - Board details/comparison
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Board selection for comparison
        compare_layout = QHBoxLayout()
        compare_layout.addWidget(QLabel("Select boards to compare:"))
        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self.clear_board_selection)
        compare_layout.addWidget(self.clear_selection_btn)
        compare_layout.addStretch()
        right_layout.addLayout(compare_layout)

        # Board list
        self.board_list = QTreeWidget()
        self.board_list.setHeaderLabels(["Board", "Architecture", ""])
        self.board_list.itemClicked.connect(self.on_board_clicked)
        self.board_list.itemDoubleClicked.connect(self.on_board_double_clicked)
        right_layout.addWidget(self.board_list)

        # Board detail view
        self.board_detail = BoardDetailView()
        right_layout.addWidget(self.board_detail)

        splitter.addWidget(right_panel)

        # Set splitter sizes
        splitter.setSizes([600, 600])

        layout.addWidget(splitter)

        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)

        layout.addLayout(status_layout)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def refresh_packages(self):
        """Refresh package list"""
        query = self.search_input.text()
        installed_only = self.filter_installed.isChecked()
        updates_only = self.filter_updates.isChecked()

        self.current_packages = self.board_manager.search_packages(
            query=query,
            installed_only=installed_only,
            updates_only=updates_only
        )

        # Ensure boards are discovered for installed packages
        # This is needed on initial load or when packages are installed
        if any(pkg.installed_version for pkg in self.current_packages):
            # Only discover if we have installed packages and boards haven't been loaded
            if not any(pkg.boards for pkg in self.current_packages if pkg.installed_version):
                self.board_manager.get_all_boards()

        self.package_list.clear()
        for package in self.current_packages:
            item = QTreeWidgetItem()
            item.setText(0, package.name)
            item.setText(1, package.installed_version or package.latest_version or "N/A")

            # Get board count from package metadata (works for both installed and non-installed)
            board_count = self._get_package_board_count(package)
            item.setText(2, str(board_count))

            # Show operation status
            if self.board_manager.is_operation_in_progress(package.name):
                item.setText(3, "In Progress")
            elif package.installed_version:
                item.setText(3, "Installed")
            else:
                item.setText(3, "Not Installed")

            item.setData(0, Qt.UserRole, package)
            self.package_list.addTopLevelItem(item)

    def _get_package_board_count(self, package: BoardPackage) -> int:
        """Get board count for a package.

        For installed packages: Uses discovered boards from boards.txt
        For non-installed packages: Uses metadata from package index
        """
        # If we have discovered boards (from installed package), use that count
        if package.boards:
            return len(package.boards)

        # Otherwise, get count from package index metadata
        # This allows showing board count even for non-installed packages
        latest_version = package.get_latest_version_obj()
        if latest_version and latest_version.boards_count > 0:
            return latest_version.boards_count

        # Fallback: check if any version has board count metadata
        for version in package.versions:
            if version.boards_count > 0:
                return version.boards_count

        return 0

    def on_package_clicked(self, item, column):
        """Handle package selection"""
        package = item.data(0, Qt.UserRole)
        if package:
            self.show_package_boards(package)
            self.update_action_buttons(package)

    def show_package_boards(self, package: BoardPackage):
        """Show boards in package"""
        self.board_list.clear()

        for board in package.boards:
            item = QTreeWidgetItem()
            item.setText(0, board.name)
            item.setText(1, board.architecture)

            # Checkbox for comparison
            item.setCheckState(2, Qt.Unchecked)
            item.setData(0, Qt.UserRole, board)

            self.board_list.addTopLevelItem(item)

    def on_board_clicked(self, item, column):
        """Handle board selection"""
        board = item.data(0, Qt.UserRole)
        if board:
            if column == 2:  # Checkbox column
                # Add/remove from comparison list
                if item.checkState(2) == Qt.Checked:
                    if board not in self.selected_boards_for_comparison:
                        self.selected_boards_for_comparison.append(board)
                else:
                    if board in self.selected_boards_for_comparison:
                        self.selected_boards_for_comparison.remove(board)
            else:
                self.board_detail.set_board(board)

    def on_board_double_clicked(self, item, column):
        """Handle board double-click (select for project)"""
        board = item.data(0, Qt.UserRole)
        if board:
            self.board_selected.emit(board.fqbn)
            self.accept()

    def clear_board_selection(self):
        """Clear board selection for comparison"""
        self.selected_boards_for_comparison.clear()

        # Uncheck all items
        for i in range(self.board_list.topLevelItemCount()):
            item = self.board_list.topLevelItem(i)
            item.setCheckState(2, Qt.Unchecked)

    def show_board_comparison(self):
        """Show board comparison dialog"""
        if len(self.selected_boards_for_comparison) < 2:
            QMessageBox.information(
                self, "Select Boards",
                "Please select at least 2 boards to compare"
            )
            return

        dialog = BoardComparisonDialog(self.selected_boards_for_comparison, self)
        dialog.exec_()

    def show_package_context_menu(self, position):
        """Show context menu for package"""
        item = self.package_list.itemAt(position)
        if not item:
            return

        package = item.data(0, Qt.UserRole)
        if not package:
            return

        menu = QMenu(self)

        # Check if operation is in progress
        in_progress = self.board_manager.is_operation_in_progress(package.name)

        if in_progress:
            # Only show cancel option if operation is in progress
            cancel_action = QAction("❌ Cancel", self)
            cancel_action.triggered.connect(lambda: self.cancel_operation(package.name))
            menu.addAction(cancel_action)
        else:
            # Show normal options only when no operation is in progress
            if package.installed_version:
                if package.has_update():
                    update_action = QAction("Update", self)
                    update_action.triggered.connect(lambda: self.update_package(package.name))
                    menu.addAction(update_action)

                uninstall_action = QAction("Uninstall", self)
                uninstall_action.triggered.connect(lambda: self.uninstall_package(package.name))
                menu.addAction(uninstall_action)
            else:
                install_action = QAction("Install", self)
                install_action.triggered.connect(lambda: self.install_package(package.name, package.latest_version))
                menu.addAction(install_action)

        menu.exec_(self.package_list.viewport().mapToGlobal(position))

    def install_package(self, name: str, version: str):
        """Install a package"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        worker = self.board_manager.install_package_async(name, version)
        if worker:
            # Connect worker signals for this specific operation
            worker.progress.connect(self.progress_bar.setValue)
            worker.status.connect(self.status_label.setText)
            # Immediately refresh to show "In Progress" status
            self.refresh_packages()

    def uninstall_package(self, name: str):
        """Uninstall a package"""
        reply = QMessageBox.question(
            self, "Confirm Uninstall",
            f"Are you sure you want to uninstall '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            worker = self.board_manager.uninstall_package_async(name)
            if worker:
                worker.status.connect(self.status_label.setText)
                # Immediately refresh to show "In Progress" status
                self.refresh_packages()

    def update_package(self, name: str):
        """Update a package"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        worker = self.board_manager.update_package_async(name)
        if worker:
            worker.progress.connect(self.progress_bar.setValue)
            worker.status.connect(self.status_label.setText)
            # Immediately refresh to show "In Progress" status
            self.refresh_packages()

    def cancel_operation(self, name: str):
        """Cancel an ongoing operation"""
        if self.board_manager.cancel_operation(name):
            self.status_label.setText(f"Cancelled operation for {name}")
            self.progress_bar.setVisible(False)
            # Refresh to update status column
            self.refresh_packages()

    def update_action_buttons(self, package: BoardPackage):
        """Update action buttons based on package state"""
        # Check if operation is in progress
        in_progress = self.board_manager.is_operation_in_progress(package.name)

        if in_progress:
            # Only enable cancel button during operation
            self.install_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
            self.uninstall_btn.setEnabled(False)
        else:
            # Enable install or uninstall based on installation state
            if package.installed_version:
                self.install_btn.setEnabled(False)
                self.cancel_btn.setEnabled(False)
                self.uninstall_btn.setEnabled(True)
            else:
                self.install_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)
                self.uninstall_btn.setEnabled(False)

    def on_install_button_clicked(self):
        """Handle install button click"""
        item = self.package_list.currentItem()
        if not item:
            return

        package = item.data(0, Qt.UserRole)
        if package and not package.installed_version:
            self.install_package(package.name, package.latest_version)

    def on_cancel_button_clicked(self):
        """Handle cancel button click"""
        item = self.package_list.currentItem()
        if not item:
            return

        package = item.data(0, Qt.UserRole)
        if package:
            self.cancel_operation(package.name)

    def on_uninstall_button_clicked(self):
        """Handle uninstall button click"""
        item = self.package_list.currentItem()
        if not item:
            return

        package = item.data(0, Qt.UserRole)
        if package and package.installed_version:
            self.uninstall_package(package.name)

    def manage_package_urls(self):
        """Manage package URLs"""
        dialog = PackageURLDialog(self.board_manager.board_index.package_urls, self)
        if dialog.exec_() == QDialog.Accepted:
            self.board_manager._save_package_urls()
            # Automatically refresh the package index
            self.update_index()

    def update_index(self):
        """Update board package index"""
        self.progress_bar.setVisible(True)
        self.board_manager.update_index(force=True)

    def on_status_message(self, message: str):
        """Handle status message"""
        self.status_label.setText(message)

    def on_progress_changed(self, progress: int):
        """Handle progress change"""
        self.progress_bar.setValue(progress)

    def on_package_changed(self, *args):
        """Handle package installation/uninstallation/update"""
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)

        # Discover boards from newly installed/updated packages
        # This populates package.boards so the count shows correctly
        self.board_manager.get_all_boards()

        self.refresh_packages()

        # Update action buttons if a package is selected
        current_item = self.package_list.currentItem()
        if current_item:
            package = current_item.data(0, Qt.UserRole)
            if package:
                self.update_action_buttons(package)

        # Update status message
        if args:
            self.status_label.setText(f"Operation completed")
