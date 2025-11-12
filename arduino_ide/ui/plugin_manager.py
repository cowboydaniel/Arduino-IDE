"""
Plugin Manager UI
Interface for managing IDE plugins
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QPushButton, QLabel,
                               QMessageBox, QFileDialog, QTextEdit, QDialog,
                               QDialogButtonBox, QGroupBox, QCheckBox)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor
import logging
from typing import Optional

from arduino_ide.services.plugin_system import PluginManager, PluginInfo, PluginStatus, PluginType

logger = logging.getLogger(__name__)


class PluginDetailsDialog(QDialog):
    """Dialog showing plugin details"""

    def __init__(self, plugin_info: PluginInfo, parent=None):
        super().__init__(parent)

        self.plugin_info = plugin_info

        self.setWindowTitle(f"Plugin Details - {plugin_info.metadata.name}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._setup_ui()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Details
        details_text = f"""
<h2>{self.plugin_info.metadata.name}</h2>
<p><b>Version:</b> {self.plugin_info.metadata.version}</p>
<p><b>Author:</b> {self.plugin_info.metadata.author}</p>
<p><b>Type:</b> {self.plugin_info.metadata.plugin_type.value}</p>
<p><b>License:</b> {self.plugin_info.metadata.license}</p>
<p><b>Status:</b> {self.plugin_info.status.value}</p>
<hr>
<p><b>Description:</b></p>
<p>{self.plugin_info.metadata.description}</p>
"""

        if self.plugin_info.metadata.homepage:
            details_text += f"<p><b>Homepage:</b> <a href='{self.plugin_info.metadata.homepage}'>{self.plugin_info.metadata.homepage}</a></p>"

        if self.plugin_info.metadata.dependencies:
            deps = ", ".join(self.plugin_info.metadata.dependencies)
            details_text += f"<p><b>Dependencies:</b> {deps}</p>"

        if self.plugin_info.error_message:
            details_text += f"""
<hr>
<p style='color: red;'><b>Error:</b> {self.plugin_info.error_message}</p>
"""

        details_label = QLabel(details_text)
        details_label.setWordWrap(True)
        details_label.setTextFormat(Qt.RichText)
        details_label.setOpenExternalLinks(True)

        layout.addWidget(details_label)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class PluginManagerWidget(QWidget):
    """
    Plugin Manager UI
    """

    def __init__(self, plugin_manager: Optional[PluginManager] = None, parent=None):
        super().__init__(parent)

        self.plugin_manager = plugin_manager or PluginManager()

        self._setup_ui()
        self._setup_connections()

        # Initial discovery
        self.refresh_plugins()

        logger.info("Plugin manager widget initialized")


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title_layout = QHBoxLayout()

        title = QLabel("Plugin Manager")
        title.setStyleSheet("font-weight: bold; font-size: 14pt; padding: 5px;")
        title_layout.addWidget(title)

        self.plugin_count_label = QLabel()
        self.plugin_count_label.setStyleSheet("padding: 5px; color: #888;")
        title_layout.addWidget(self.plugin_count_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # Toolbar
        toolbar = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Refresh plugin list")

        self.install_btn = QPushButton("Install")
        self.install_btn.setToolTip("Install plugin from file")

        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.setToolTip("Uninstall selected plugin")

        self.activate_btn = QPushButton("Activate")
        self.activate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
        """)

        self.deactivate_btn = QPushButton("Deactivate")

        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.install_btn)
        toolbar.addWidget(self.uninstall_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.activate_btn)
        toolbar.addWidget(self.deactivate_btn)

        layout.addLayout(toolbar)

        # Plugins table
        self.plugins_table = QTableWidget()
        self.plugins_table.setColumnCount(6)
        self.plugins_table.setHorizontalHeaderLabels([
            "Name", "Version", "Author", "Type", "Status", "Description"
        ])

        header = self.plugins_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)

        self.plugins_table.verticalHeader().setVisible(False)
        self.plugins_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.plugins_table.setSelectionMode(QTableWidget.SingleSelection)
        self.plugins_table.setAlternatingRowColors(True)

        layout.addWidget(self.plugins_table)

        # Info box
        info_box = QGroupBox("Plugin Information")
        info_layout = QVBoxLayout(info_box)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        info_layout.addWidget(self.info_text)

        layout.addWidget(info_box)


    def _setup_connections(self):
        """Setup signal connections"""
        self.refresh_btn.clicked.connect(self.refresh_plugins)
        self.install_btn.clicked.connect(self._on_install)
        self.uninstall_btn.clicked.connect(self._on_uninstall)
        self.activate_btn.clicked.connect(self._on_activate)
        self.deactivate_btn.clicked.connect(self._on_deactivate)

        self.plugins_table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.plugins_table.currentCellChanged.connect(self._on_selection_changed)

        self.plugin_manager.plugin_loaded.connect(self._on_plugin_loaded)
        self.plugin_manager.plugin_activated.connect(self._on_plugin_activated)
        self.plugin_manager.plugin_deactivated.connect(self._on_plugin_deactivated)
        self.plugin_manager.plugin_error.connect(self._on_plugin_error)


    def refresh_plugins(self):
        """Refresh plugins list"""
        # Discover plugins
        count = self.plugin_manager.discover_plugins()

        # Clear table
        self.plugins_table.setRowCount(0)

        # Get all plugins
        plugins = self.plugin_manager.get_all_plugins()

        for plugin_info in plugins:
            self._add_plugin_to_table(plugin_info)

        self.plugin_count_label.setText(f"{len(plugins)} plugin(s) found")


    def _add_plugin_to_table(self, plugin_info: PluginInfo):
        """Add plugin to table"""
        row = self.plugins_table.rowCount()
        self.plugins_table.insertRow(row)

        # Store plugin ID in row
        id_item = QTableWidgetItem(plugin_info.metadata.name)
        id_item.setData(Qt.UserRole, plugin_info.metadata.id)
        self.plugins_table.setItem(row, 0, id_item)

        # Version
        version_item = QTableWidgetItem(plugin_info.metadata.version)
        self.plugins_table.setItem(row, 1, version_item)

        # Author
        author_item = QTableWidgetItem(plugin_info.metadata.author)
        self.plugins_table.setItem(row, 2, author_item)

        # Type
        type_item = QTableWidgetItem(plugin_info.metadata.plugin_type.value)
        self.plugins_table.setItem(row, 3, type_item)

        # Status
        status_item = QTableWidgetItem(plugin_info.status.value)

        # Color based on status
        if plugin_info.status == PluginStatus.ACTIVE:
            status_item.setForeground(QColor("#4CAF50"))
            font = QFont()
            font.setBold(True)
            status_item.setFont(font)
        elif plugin_info.status == PluginStatus.ERROR:
            status_item.setForeground(QColor("#E74C3C"))
        elif plugin_info.status == PluginStatus.DISABLED:
            status_item.setForeground(QColor("#95A5A6"))

        self.plugins_table.setItem(row, 4, status_item)

        # Description
        description_item = QTableWidgetItem(plugin_info.metadata.description[:100])
        self.plugins_table.setItem(row, 5, description_item)


    @Slot()
    def _on_install(self):
        """Install plugin from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Plugin File",
            "",
            "Plugin Files (*.zip);;All Files (*)"
        )

        if file_path:
            if self.plugin_manager.install_plugin(file_path):
                QMessageBox.information(self, "Success", "Plugin installed successfully!")
                self.refresh_plugins()
            else:
                QMessageBox.critical(self, "Error", "Failed to install plugin")


    @Slot()
    def _on_uninstall(self):
        """Uninstall selected plugin"""
        current_row = self.plugins_table.currentRow()
        if current_row < 0:
            return

        plugin_id = self.plugins_table.item(current_row, 0).data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Uninstall Plugin",
            "Uninstall this plugin? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.plugin_manager.uninstall_plugin(plugin_id):
                QMessageBox.information(self, "Success", "Plugin uninstalled")
                self.refresh_plugins()
            else:
                QMessageBox.critical(self, "Error", "Failed to uninstall plugin")


    @Slot()
    def _on_activate(self):
        """Activate selected plugin"""
        current_row = self.plugins_table.currentRow()
        if current_row < 0:
            return

        plugin_id = self.plugins_table.item(current_row, 0).data(Qt.UserRole)

        if self.plugin_manager.activate_plugin(plugin_id):
            QMessageBox.information(self, "Success", "Plugin activated")
            self.refresh_plugins()
        else:
            QMessageBox.critical(self, "Error", "Failed to activate plugin")


    @Slot()
    def _on_deactivate(self):
        """Deactivate selected plugin"""
        current_row = self.plugins_table.currentRow()
        if current_row < 0:
            return

        plugin_id = self.plugins_table.item(current_row, 0).data(Qt.UserRole)

        if self.plugin_manager.deactivate_plugin(plugin_id):
            QMessageBox.information(self, "Success", "Plugin deactivated")
            self.refresh_plugins()
        else:
            QMessageBox.critical(self, "Error", "Failed to deactivate plugin")


    @Slot(int, int)
    def _on_cell_double_clicked(self, row: int, column: int):
        """Show plugin details"""
        plugin_id = self.plugins_table.item(row, 0).data(Qt.UserRole)
        plugin_info = self.plugin_manager.get_plugin_info(plugin_id)

        if plugin_info:
            dialog = PluginDetailsDialog(plugin_info, self)
            dialog.exec()


    @Slot(int, int, int, int)
    def _on_selection_changed(self, currentRow: int, currentColumn: int,
                             previousRow: int, previousColumn: int):
        """Update info text when selection changes"""
        if currentRow < 0:
            self.info_text.clear()
            return

        plugin_id = self.plugins_table.item(currentRow, 0).data(Qt.UserRole)
        plugin_info = self.plugin_manager.get_plugin_info(plugin_id)

        if plugin_info:
            info = f"""
<b>{plugin_info.metadata.name}</b> v{plugin_info.metadata.version}
<br>
{plugin_info.metadata.description}
<br>
<i>Path: {plugin_info.path}</i>
"""
            self.info_text.setHtml(info)


    @Slot(str)
    def _on_plugin_loaded(self, plugin_id: str):
        """Handle plugin loaded"""
        logger.info(f"Plugin loaded: {plugin_id}")


    @Slot(str)
    def _on_plugin_activated(self, plugin_id: str):
        """Handle plugin activated"""
        logger.info(f"Plugin activated: {plugin_id}")


    @Slot(str)
    def _on_plugin_deactivated(self, plugin_id: str):
        """Handle plugin deactivated"""
        logger.info(f"Plugin deactivated: {plugin_id}")


    @Slot(str, str)
    def _on_plugin_error(self, plugin_id: str, error_message: str):
        """Handle plugin error"""
        QMessageBox.critical(
            self,
            "Plugin Error",
            f"Plugin '{plugin_id}' error:\n\n{error_message}"
        )
