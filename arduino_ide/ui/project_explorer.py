"""Project explorer for file navigation."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Qt, Signal, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem


PATH_ROLE = Qt.UserRole + 1
IS_DIR_ROLE = Qt.UserRole + 2
RELATIVE_PATH_ROLE = Qt.UserRole + 3


class ProjectExplorer(QWidget):
    """Project file explorer"""

    file_open_requested = Signal(str)

    IGNORED_DIRECTORIES = {".git", "__pycache__", ".idea", ".vscode", "node_modules"}
    IGNORED_FILES = {".DS_Store", "Thumbs.db"}
    IGNORED_SUFFIXES = {".pyc", ".pyo", ".swp", ".tmp"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_root: Path | None = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        self.new_file_btn = QPushButton("+")
        self.new_file_btn.setToolTip("New File")
        self.new_file_btn.setMaximumWidth(30)
        toolbar.addWidget(self.new_file_btn)

        self.new_folder_btn = QPushButton("📁+")
        self.new_folder_btn.setToolTip("New Folder")
        self.new_folder_btn.setMaximumWidth(30)
        toolbar.addWidget(self.new_folder_btn)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setToolTip("Refresh")
        self.refresh_btn.setMaximumWidth(30)
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Tree view
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)

        # Use a simple model for now
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Project Files"])
        self.tree_view.setModel(self.model)
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.tree_view.expandAll()

        layout.addWidget(self.tree_view)

    def load_project(self, project_path):
        """Load project from path"""
        root = Path(project_path).expanduser().resolve()

        if not root.exists():
            return

        self._project_root = root
        self._rebuild_model()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _rebuild_model(self):
        if self._project_root is None:
            return

        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Project Files"])

        root_item = self._create_item(self._project_root, is_root=True)
        self.model.appendRow(root_item)

        self._populate_children(root_item, self._project_root)

        # Expand the top level for better visibility
        self.tree_view.expand(self.model.indexFromItem(root_item))
        self.tree_view.expandAll()

    def _populate_children(self, parent_item: QStandardItem, directory: Path):
        for entry in self._iter_directory(directory):
            if entry.is_dir():
                item = self._create_item(entry)
                parent_item.appendRow(item)
                self._populate_children(item, entry)
            else:
                parent_item.appendRow(self._create_item(entry))

    def _create_item(self, path: Path, *, is_root: bool = False) -> QStandardItem:
        prefix = "📁" if path.is_dir() else "📄"
        label = path.name if not is_root else path.name or str(path)
        item = QStandardItem(f"{prefix} {label}")
        item.setEditable(False)

        item.setData(str(path), PATH_ROLE)
        item.setData(path.is_dir(), IS_DIR_ROLE)
        if self._project_root and path != self._project_root:
            try:
                relative = path.relative_to(self._project_root)
            except ValueError:
                relative = path.name
            item.setData(str(relative), RELATIVE_PATH_ROLE)
        else:
            item.setData(".", RELATIVE_PATH_ROLE)

        tooltip_lines = [str(path)]
        if path.is_dir():
            tooltip_lines.append("Directory")
        else:
            tooltip_lines.append("File")
        item.setToolTip("\n".join(tooltip_lines))
        return item

    def _iter_directory(self, directory: Path) -> Iterable[Path]:
        try:
            entries = list(directory.iterdir())
        except (PermissionError, OSError):
            return []

        def sort_key(path: Path):
            return (path.is_file(), path.name.lower())

        for entry in sorted(entries, key=sort_key):
            if self._should_ignore(entry):
                continue
            yield entry

    def _should_ignore(self, path: Path) -> bool:
        name = path.name
        if path.is_dir():
            return name in self.IGNORED_DIRECTORIES
        if name in self.IGNORED_FILES:
            return True
        return any(name.endswith(suffix) for suffix in self.IGNORED_SUFFIXES)

    # ------------------------------------------------------------------
    # Slots / actions
    # ------------------------------------------------------------------
    def refresh(self):
        """Refresh the current project tree"""
        self._rebuild_model()

    def on_item_clicked(self, index: QModelIndex):
        item = self.model.itemFromIndex(index)
        if not item:
            return

        is_dir = bool(item.data(IS_DIR_ROLE))
        path = item.data(PATH_ROLE)

        if is_dir or not path:
            return

        file_path = Path(path)
        if file_path.is_file():
            self.file_open_requested.emit(str(file_path))
