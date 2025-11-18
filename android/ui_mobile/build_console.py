from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from services_mobile.build_service import BuildError, BuildResult


class BuildConsole(QtWidgets.QWidget):
    """Displays build output and clickable compiler errors."""

    error_selected = QtCore.Signal(BuildError)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.output_view = QtWidgets.QPlainTextEdit(readOnly=True)
        self.output_view.setFont(QtGui.QFont("Fira Code", 11))
        self.output_view.setMaximumBlockCount(2000)
        self.error_list = QtWidgets.QListWidget()
        self.error_list.itemDoubleClicked.connect(self._emit_error)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(QtWidgets.QLabel("Build Output"))
        layout.addWidget(self.output_view, 3)
        layout.addWidget(QtWidgets.QLabel("Compiler Errors"))
        layout.addWidget(self.error_list, 1)

    def append_output(self, text: str) -> None:
        cursor = self.output_view.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        cursor.insertBlock()
        self.output_view.setTextCursor(cursor)
        self.output_view.ensureCursorVisible()

    def show_result(self, result: BuildResult) -> None:
        self.output_view.clear()
        self.error_list.clear()
        self.append_output(result.output)
        for error in result.errors:
            item = QtWidgets.QListWidgetItem(f"{error.file}:{error.line}:{error.column} - {error.message}")
            item.setData(QtCore.Qt.UserRole, error)
            self.error_list.addItem(item)

    def _emit_error(self, item: QtWidgets.QListWidgetItem) -> None:
        error = item.data(QtCore.Qt.UserRole)
        if isinstance(error, BuildError):
            self.error_selected.emit(error)


__all__ = ["BuildConsole"]
