"""
Modern Library Manager Dialog

Features:
- Smart search with filters
- Library detail view with stats
- Version management
- Dependency resolution
- Bulk operations
- Conflict detection
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QTextBrowser, QCheckBox, QComboBox, QGroupBox, QFormLayout,
    QProgressBar, QTabWidget, QWidget, QScrollArea, QRadioButton,
    QMessageBox, QMenu, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QAction
from pathlib import Path

from ..models import Library, LibraryStatus, LibraryType
from ..services.library_manager import LibraryManager


class LibraryDetailView(QWidget):
    """Detailed view for a single library"""

    install_clicked = Signal(str, str)  # name, version
    uninstall_clicked = Signal(str)  # name
    update_clicked = Signal(str)  # name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_library = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Content widget
        content = QWidget()
        content_layout = QVBoxLayout(content)

        # Title and rating
        title_layout = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        self.rating_label = QLabel()
        title_layout.addWidget(self.rating_label)
        content_layout.addLayout(title_layout)

        # Author
        self.author_label = QLabel()
        content_layout.addWidget(self.author_label)

        # Version info
        version_layout = QHBoxLayout()
        self.version_label = QLabel()
        version_layout.addWidget(self.version_label)
        version_layout.addStretch()
        self.install_btn = QPushButton("Install")
        self.install_btn.clicked.connect(self.on_install_clicked)
        version_layout.addWidget(self.install_btn)
        self.update_btn = QPushButton("Update")
        self.update_btn.clicked.connect(self.on_update_clicked)
        version_layout.addWidget(self.update_btn)
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.clicked.connect(self.on_uninstall_clicked)
        version_layout.addWidget(self.uninstall_btn)
        content_layout.addLayout(version_layout)

        # Stats group
        stats_group = QGroupBox("📊 Stats")
        stats_layout = QFormLayout()
        self.downloads_label = QLabel()
        self.size_label = QLabel()
        self.updated_label = QLabel()
        self.license_label = QLabel()
        stats_layout.addRow("Downloads:", self.downloads_label)
        stats_layout.addRow("Size:", self.size_label)
        stats_layout.addRow("Last updated:", self.updated_label)
        stats_layout.addRow("License:", self.license_label)
        stats_group.setLayout(stats_layout)
        content_layout.addWidget(stats_group)

        # Dependencies group
        self.deps_group = QGroupBox("🔗 Dependencies")
        deps_layout = QVBoxLayout()
        self.deps_list = QTreeWidget()
        self.deps_list.setHeaderLabels(["Dependency", "Version", "Status"])
        self.deps_list.setMaximumHeight(150)
        deps_layout.addWidget(self.deps_list)
        self.deps_group.setLayout(deps_layout)
        content_layout.addWidget(self.deps_group)

        # Compatibility group
        compat_group = QGroupBox("📱 Compatible Boards")
        compat_layout = QVBoxLayout()
        self.compat_label = QLabel()
        self.compat_label.setWordWrap(True)
        compat_layout.addWidget(self.compat_label)
        compat_group.setLayout(compat_layout)
        content_layout.addWidget(compat_group)

        # Description
        desc_group = QGroupBox("📝 Description")
        desc_layout = QVBoxLayout()
        self.desc_text = QTextBrowser()
        self.desc_text.setMaximumHeight(150)
        self.desc_text.setOpenExternalLinks(True)
        desc_layout.addWidget(self.desc_text)
        desc_group.setLayout(desc_layout)
        content_layout.addWidget(desc_group)

        # Known issues
        self.issues_group = QGroupBox("🐛 Known Issues")
        issues_layout = QVBoxLayout()
        self.issues_text = QTextBrowser()
        self.issues_text.setMaximumHeight(100)
        issues_layout.addWidget(self.issues_text)
        self.issues_group.setLayout(issues_layout)
        content_layout.addWidget(self.issues_group)

        # Examples
        self.examples_group = QGroupBox("📚 Examples")
        examples_layout = QVBoxLayout()
        self.examples_list = QTreeWidget()
        self.examples_list.setHeaderLabels(["Example", "Description"])
        self.examples_list.setMaximumHeight(150)
        examples_layout.addWidget(self.examples_list)
        self.examples_group.setLayout(examples_layout)
        content_layout.addWidget(self.examples_group)

        # Links
        links_layout = QHBoxLayout()
        self.docs_btn = QPushButton("📖 Documentation")
        self.repo_btn = QPushButton("🔗 Repository")
        links_layout.addWidget(self.docs_btn)
        links_layout.addWidget(self.repo_btn)
        links_layout.addStretch()
        content_layout.addLayout(links_layout)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def set_library(self, library: Library):
        """Display library details"""
        self.current_library = library

        if not library:
            return

        # Title and rating
        self.title_label.setText(library.name)
        if library.stats and library.stats.rating > 0:
            self.rating_label.setText(f"⭐ {library.stats.rating:.1f}")
        else:
            self.rating_label.setText("")

        # Author
        self.author_label.setText(f"by {library.author}")

        # Version info
        if library.installed_version:
            version_text = f"Installed: v{library.installed_version}"
            if library.latest_version and library.installed_version != library.latest_version:
                version_text += f"  →  Available: v{library.latest_version}"
            self.version_label.setText(version_text)
        else:
            if library.latest_version:
                self.version_label.setText(f"Latest: v{library.latest_version}")
            else:
                self.version_label.setText("No version available")

        # Button states
        if library.installed_version:
            self.install_btn.setVisible(False)
            self.uninstall_btn.setVisible(True)
            if library.has_update():
                self.update_btn.setVisible(True)
            else:
                self.update_btn.setVisible(False)
        else:
            self.install_btn.setVisible(True)
            self.uninstall_btn.setVisible(False)
            self.update_btn.setVisible(False)

        # Stats
        if library.stats:
            downloads = library.stats.downloads
            if downloads >= 1000000:
                self.downloads_label.setText(f"{downloads / 1000000:.1f}M")
            elif downloads >= 1000:
                self.downloads_label.setText(f"{downloads / 1000:.0f}K")
            else:
                self.downloads_label.setText(str(downloads))
        else:
            self.downloads_label.setText("N/A")

        latest_version = library.get_latest_version_obj()
        if latest_version:
            self.size_label.setText(latest_version.size_human_readable())
        else:
            self.size_label.setText("N/A")

        if library.last_updated:
            days_ago = (library.last_updated - library.last_updated).days
            if days_ago < 30:
                self.updated_label.setText(f"{days_ago} days ago")
            elif days_ago < 365:
                self.updated_label.setText(f"{days_ago // 30} months ago")
            else:
                self.updated_label.setText(f"{days_ago // 365} years ago")
        else:
            self.updated_label.setText("Unknown")

        self.license_label.setText(library.license or "N/A")

        # Dependencies
        self.deps_list.clear()
        if latest_version and latest_version.dependencies:
            for dep in latest_version.dependencies:
                item = QTreeWidgetItem()
                item.setText(0, dep.name)
                item.setText(1, dep.version)
                item.setText(2, "Optional" if dep.optional else "Required")
                self.deps_list.addTopLevelItem(item)
            self.deps_group.setVisible(True)
        else:
            self.deps_group.setVisible(False)

        # Compatibility
        if library.architectures and "*" not in library.architectures:
            self.compat_label.setText("✅ " + ", ".join(library.architectures))
        else:
            self.compat_label.setText("✅ All boards")

        # Description
        desc_html = f"<p><strong>{library.sentence or library.description}</strong></p>"
        if library.paragraph:
            desc_html += f"<p>{library.paragraph}</p>"
        self.desc_text.setHtml(desc_html)

        # Known issues
        if library.known_issues:
            issues_html = "<ul>"
            for issue in library.known_issues:
                issues_html += f"<li>{issue}</li>"
            issues_html += "</ul>"
            self.issues_text.setHtml(issues_html)
            self.issues_group.setVisible(True)
        else:
            self.issues_group.setVisible(False)

        # Examples
        self.examples_list.clear()
        if library.examples:
            for example in library.examples:
                item = QTreeWidgetItem()
                item.setText(0, example.name)
                item.setText(1, example.description)
                self.examples_list.addTopLevelItem(item)
            self.examples_group.setVisible(True)
        else:
            self.examples_group.setVisible(False)

    def on_install_clicked(self):
        """Handle install button click"""
        if self.current_library:
            self.install_clicked.emit(self.current_library.name, self.current_library.latest_version)

    def on_update_clicked(self):
        """Handle update button click"""
        if self.current_library:
            self.update_clicked.emit(self.current_library.name)

    def on_uninstall_clicked(self):
        """Handle uninstall button click"""
        if self.current_library:
            reply = QMessageBox.question(
                self, "Confirm Uninstall",
                f"Are you sure you want to uninstall '{self.current_library.name}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.uninstall_clicked.emit(self.current_library.name)


class LibraryManagerDialog(QDialog):
    """Modern Library Manager Dialog"""

    def __init__(self, library_manager: LibraryManager, parent=None):
        super().__init__(parent)
        self.library_manager = library_manager
        self.current_libraries = []

        # Connect signals
        self.library_manager.status_message.connect(self.on_status_message)
        self.library_manager.progress_changed.connect(self.on_progress_changed)
        self.library_manager.library_installed.connect(self.on_library_changed)
        self.library_manager.library_uninstalled.connect(self.on_library_changed)
        self.library_manager.library_updated.connect(self.on_library_changed)
        self.library_manager.index_updated.connect(self.refresh_libraries)

        self.init_ui()
        self.setWindowTitle("Library Manager")
        self.resize(1200, 800)

        # Initial load
        self.refresh_libraries()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Top toolbar
        toolbar = QHBoxLayout()

        # Refresh button
        refresh_btn = QPushButton("🔄 Check Updates")
        refresh_btn.clicked.connect(self.update_index)
        toolbar.addWidget(refresh_btn)

        # Install from ZIP button
        install_zip_btn = QPushButton("📦 Install from ZIP")
        install_zip_btn.clicked.connect(self.install_from_zip)
        toolbar.addWidget(install_zip_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Categories
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        categories_label = QLabel("Categories")
        categories_label.setFont(QFont("Arial", 10, QFont.Bold))
        left_layout.addWidget(categories_label)

        self.categories_tree = QTreeWidget()
        self.categories_tree.setHeaderHidden(True)
        self.categories_tree.itemClicked.connect(self.on_category_clicked)
        left_layout.addWidget(self.categories_tree)

        # Populate categories
        self.populate_categories()

        splitter.addWidget(left_panel)

        # Center panel - Library list
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("DHT sensor, OLED, WiFi...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input)

        center_layout.addLayout(search_layout)

        # Filters
        filters_layout = QHBoxLayout()

        self.filter_installed = QCheckBox("Installed only")
        self.filter_installed.stateChanged.connect(self.refresh_libraries)
        filters_layout.addWidget(self.filter_installed)

        self.filter_updates = QCheckBox("Updates available")
        self.filter_updates.stateChanged.connect(self.refresh_libraries)
        filters_layout.addWidget(self.filter_updates)

        self.filter_official = QCheckBox("Official only")
        self.filter_official.stateChanged.connect(self.refresh_libraries)
        filters_layout.addWidget(self.filter_official)

        filters_layout.addStretch()

        # Sort by
        filters_layout.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Relevance", "Downloads", "Name", "Updated"])
        self.sort_combo.currentTextChanged.connect(self.refresh_libraries)
        filters_layout.addWidget(self.sort_combo)

        center_layout.addLayout(filters_layout)

        # Library list
        self.library_list = QTreeWidget()
        self.library_list.setHeaderLabels(["Library", "Version", "Status"])
        self.library_list.itemClicked.connect(self.on_library_clicked)
        self.library_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.library_list.customContextMenuRequested.connect(self.show_library_context_menu)
        center_layout.addWidget(self.library_list)

        # Bulk operations
        bulk_layout = QHBoxLayout()
        self.update_all_btn = QPushButton("Update All")
        self.update_all_btn.clicked.connect(self.update_all_libraries)
        bulk_layout.addWidget(self.update_all_btn)
        bulk_layout.addStretch()
        center_layout.addLayout(bulk_layout)

        splitter.addWidget(center_panel)

        # Right panel - Library details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.detail_view = LibraryDetailView()
        self.detail_view.install_clicked.connect(self.install_library)
        self.detail_view.uninstall_clicked.connect(self.uninstall_library)
        self.detail_view.update_clicked.connect(self.update_library)
        right_layout.addWidget(self.detail_view)

        splitter.addWidget(right_panel)

        # Set splitter sizes
        splitter.setSizes([200, 400, 600])

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

    def populate_categories(self):
        """Populate category tree"""
        self.categories_tree.clear()

        # All libraries
        all_item = QTreeWidgetItem(["📚 All Libraries"])
        all_item.setData(0, Qt.UserRole, {"type": "all"})
        self.categories_tree.addTopLevelItem(all_item)

        # Installed
        installed_item = QTreeWidgetItem(["✓ Installed"])
        installed_item.setData(0, Qt.UserRole, {"type": "installed"})
        self.categories_tree.addTopLevelItem(installed_item)

        # Updates
        updates_item = QTreeWidgetItem(["🔄 Updates Available"])
        updates_item.setData(0, Qt.UserRole, {"type": "updates"})
        self.categories_tree.addTopLevelItem(updates_item)

        # Categories
        categories = self.library_manager.library_index.get_categories()
        for category in categories:
            cat_item = QTreeWidgetItem([f"🏷️ {category}"])
            cat_item.setData(0, Qt.UserRole, {"type": "category", "value": category})
            self.categories_tree.addTopLevelItem(cat_item)

    def on_category_clicked(self, item, column):
        """Handle category selection"""
        self.refresh_libraries()

    def on_search_changed(self, text):
        """Handle search text change"""
        # Debounce search
        if hasattr(self, 'search_timer'):
            self.search_timer.stop()

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.refresh_libraries)
        self.search_timer.start(300)  # 300ms debounce

    def refresh_libraries(self):
        """Refresh library list based on filters"""
        # Get filters
        query = self.search_input.text()
        installed_only = self.filter_installed.isChecked()
        updates_only = self.filter_updates.isChecked()
        official_only = self.filter_official.isChecked()

        # Get category filter
        category = None
        selected_items = self.categories_tree.selectedItems()
        if selected_items:
            item_data = selected_items[0].data(0, Qt.UserRole)
            if item_data and item_data["type"] == "category":
                category = item_data["value"]
            elif item_data and item_data["type"] == "installed":
                installed_only = True
            elif item_data and item_data["type"] == "updates":
                updates_only = True

        # Search libraries
        self.current_libraries = self.library_manager.search_libraries(
            query=query,
            category=category,
            installed_only=installed_only,
            updates_only=updates_only,
            official_only=official_only
        )

        # Sort libraries
        sort_by = self.sort_combo.currentText()
        if sort_by == "Name":
            self.current_libraries.sort(key=lambda lib: lib.name.lower())
        elif sort_by == "Downloads":
            self.current_libraries.sort(
                key=lambda lib: lib.stats.downloads if lib.stats else 0,
                reverse=True
            )
        elif sort_by == "Updated":
            self.current_libraries.sort(
                key=lambda lib: lib.last_updated if lib.last_updated else "",
                reverse=True
            )

        # Update list
        self.library_list.clear()
        for library in self.current_libraries[:100]:  # Limit to 100 for performance
            item = QTreeWidgetItem()
            item.setText(0, library.name)
            item.setText(1, library.installed_version or library.latest_version or "N/A")

            if library.installed_version:
                if library.has_update():
                    item.setText(2, "✓ Update available")
                else:
                    item.setText(2, "✓ Installed")
            else:
                item.setText(2, "Not installed")

            item.setData(0, Qt.UserRole, library)
            self.library_list.addTopLevelItem(item)

    def on_library_clicked(self, item, column):
        """Handle library selection"""
        library = item.data(0, Qt.UserRole)
        if library:
            self.detail_view.set_library(library)

    def show_library_context_menu(self, position):
        """Show context menu for library"""
        item = self.library_list.itemAt(position)
        if not item:
            return

        library = item.data(0, Qt.UserRole)
        if not library:
            return

        menu = QMenu(self)

        if library.installed_version:
            if library.has_update():
                update_action = QAction("Update", self)
                update_action.triggered.connect(lambda: self.update_library(library.name))
                menu.addAction(update_action)

            uninstall_action = QAction("Uninstall", self)
            uninstall_action.triggered.connect(lambda: self.uninstall_library(library.name))
            menu.addAction(uninstall_action)
        else:
            install_action = QAction("Install", self)
            install_action.triggered.connect(lambda: self.install_library(library.name, library.latest_version))
            menu.addAction(install_action)

        menu.exec_(self.library_list.viewport().mapToGlobal(position))

    def install_library(self, name: str, version: str):
        """Install a library"""
        self.progress_bar.setVisible(True)
        self.library_manager.install_library(name, version)

    def uninstall_library(self, name: str):
        """Uninstall a library"""
        self.library_manager.uninstall_library(name)

    def update_library(self, name: str):
        """Update a library"""
        self.progress_bar.setVisible(True)
        self.library_manager.update_library(name)

    def update_all_libraries(self):
        """Update all libraries"""
        reply = QMessageBox.question(
            self, "Update All Libraries",
            "Are you sure you want to update all libraries?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.progress_bar.setVisible(True)
            count = self.library_manager.update_all_libraries()
            QMessageBox.information(
                self, "Update Complete",
                f"Updated {count} libraries"
            )

    def update_index(self):
        """Update library index"""
        self.progress_bar.setVisible(True)
        self.library_manager.update_index(force=True)

    def install_from_zip(self):
        """Install library from ZIP file"""
        # Open file dialog
        zip_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Library ZIP File",
            "",
            "ZIP Files (*.zip);;All Files (*)"
        )

        if zip_path:
            # Convert to Path object
            zip_file = Path(zip_path)

            # Confirm installation
            reply = QMessageBox.question(
                self,
                "Install Library from ZIP",
                f"Install library from:\n{zip_file.name}?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.progress_bar.setVisible(True)
                success = self.library_manager.install_library_from_zip(zip_file)

                if success:
                    QMessageBox.information(
                        self,
                        "Installation Successful",
                        "Library installed successfully from ZIP file."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Installation Failed",
                        "Failed to install library from ZIP file. Check the status messages for details."
                    )

                self.progress_bar.setVisible(False)
                self.refresh_libraries()

    def on_status_message(self, message: str):
        """Handle status message"""
        self.status_label.setText(message)

    def on_progress_changed(self, progress: int):
        """Handle progress change"""
        self.progress_bar.setValue(progress)

    def on_library_changed(self, *args):
        """Handle library installation/uninstallation/update"""
        self.progress_bar.setVisible(False)
        self.refresh_libraries()

        # Refresh detail view if current library changed
        if self.detail_view.current_library:
            updated_lib = self.library_manager.get_library(self.detail_view.current_library.name)
            if updated_lib:
                self.detail_view.set_library(updated_lib)
