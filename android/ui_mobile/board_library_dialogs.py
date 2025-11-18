from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from services_mobile.build_service import BoardManager, LibraryManager


class BoardSelectionDialog(QtWidgets.QDialog):
    """Simple board picker backed by the board manager."""

    def __init__(self, manager: BoardManager, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Select Board")
        self.resize(420, 360)

        self.list_widget = QtWidgets.QListWidget()
        for board in manager.list_available():
            item = QtWidgets.QListWidgetItem(f"{board['name']} ({board['fqbn']})")
            item.setData(QtCore.Qt.UserRole, board)
            self.list_widget.addItem(item)

        self.list_widget.itemDoubleClicked.connect(self.accept)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Detected and bundled boards"))
        layout.addWidget(self.list_widget)
        layout.addWidget(buttons)

    def selected_board(self) -> dict | None:
        item = self.list_widget.currentItem()
        if item:
            return item.data(QtCore.Qt.UserRole)
        return None


class LibraryManagerDialog(QtWidgets.QDialog):
    """Basic library search/install flow for Android."""

    def __init__(self, manager: LibraryManager, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Library Manager")
        self.resize(520, 420)

        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Search Arduino libraries")
        self.search_button = QtWidgets.QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)

        search_row = QtWidgets.QHBoxLayout()
        search_row.addWidget(self.search_bar)
        search_row.addWidget(self.search_button)

        self.results_view = QtWidgets.QListWidget()
        self.install_button = QtWidgets.QPushButton("Install Selected")
        self.install_button.clicked.connect(self.install_selected)
        self.status_label = QtWidgets.QLabel()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(search_row)
        layout.addWidget(self.results_view, 1)
        layout.addWidget(QtWidgets.QLabel("Installed"))
        self.installed_view = QtWidgets.QListWidget()
        layout.addWidget(self.installed_view, 1)
        layout.addWidget(self.install_button)
        layout.addWidget(self.status_label)

        self.refresh_installed()

    def refresh_installed(self) -> None:
        self.installed_view.clear()
        for lib in self.manager.installed():
            self.installed_view.addItem(f"{lib['name']} ({lib['version']})")

    def perform_search(self) -> None:
        query = self.search_bar.text().strip()
        if not query:
            self.status_label.setText("Enter a query to search.")
            return
        output = self.manager.search(query)
        self.results_view.clear()
        for line in output.splitlines():
            if not line.strip():
                continue
            item = QtWidgets.QListWidgetItem(line)
            self.results_view.addItem(item)
        self.status_label.setText(f"Found {self.results_view.count()} result(s)")

    def install_selected(self) -> None:
        item = self.results_view.currentItem()
        if not item:
            self.status_label.setText("Select a library to install.")
            return
        name = item.text().split()[0]
        output = self.manager.install_library(name)
        self.status_label.setText(f"Installed {name}")
        self.refresh_installed()
        QtWidgets.QMessageBox.information(self, "Library Installed", output)


__all__ = ["BoardSelectionDialog", "LibraryManagerDialog"]
