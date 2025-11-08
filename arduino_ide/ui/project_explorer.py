"""
Project explorer for file navigation
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QPushButton, QHBoxLayout,
    QFileSystemModel, QMenu
)
from PySide6.QtCore import Qt, QDir
from PySide6.QtGui import QStandardItemModel, QStandardItem


class ProjectExplorer(QWidget):
    """Project file explorer"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        new_file_btn = QPushButton("+")
        new_file_btn.setToolTip("New File")
        new_file_btn.setMaximumWidth(30)
        toolbar.addWidget(new_file_btn)

        new_folder_btn = QPushButton("📁+")
        new_folder_btn.setToolTip("New Folder")
        new_folder_btn.setMaximumWidth(30)
        toolbar.addWidget(new_folder_btn)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Refresh")
        refresh_btn.setMaximumWidth(30)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Tree view
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)

        # Use a simple model for now
        self.model = QStandardItemModel()

        root_item = QStandardItem("📁 My Project")

        # Add example files
        main_file = QStandardItem("📄 sketch.ino")
        root_item.appendRow(main_file)

        lib_folder = QStandardItem("📁 libraries")
        lib_file = QStandardItem("📄 mylib.h")
        lib_folder.appendRow(lib_file)
        root_item.appendRow(lib_folder)

        readme = QStandardItem("📄 README.md")
        root_item.appendRow(readme)

        self.model.appendRow(root_item)

        self.tree_view.setModel(self.model)
        self.tree_view.expandAll()

        layout.addWidget(self.tree_view)

    def load_project(self, project_path):
        """Load project from path"""
        # TODO: Implement project loading
        pass
