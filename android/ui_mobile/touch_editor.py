from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets


ARDUINO_KEYWORDS = [
    "void",
    "int",
    "float",
    "double",
    "char",
    "byte",
    "boolean",
    "String",
    "HIGH",
    "LOW",
    "INPUT",
    "OUTPUT",
    "pinMode",
    "digitalWrite",
    "digitalRead",
    "analogWrite",
    "analogRead",
    "delay",
    "millis",
    "micros",
    "setup",
    "loop",
]


class ArduinoHighlighter(QtGui.QSyntaxHighlighter):
    """Simple syntax highlighting tuned for Arduino sketches."""

    def __init__(self, document: QtGui.QTextDocument) -> None:
        super().__init__(document)
        keyword_format = QtGui.QTextCharFormat()
        keyword_format.setForeground(QtGui.QColor("#5ec4ff"))
        keyword_format.setFontWeight(QtGui.QFont.Bold)

        type_format = QtGui.QTextCharFormat()
        type_format.setForeground(QtGui.QColor("#c792ea"))

        comment_format = QtGui.QTextCharFormat()
        comment_format.setForeground(QtGui.QColor("#6a9955"))

        string_format = QtGui.QTextCharFormat()
        string_format.setForeground(QtGui.QColor("#ce9178"))

        self.highlighting_rules: list[tuple[QtCore.QRegularExpression, QtGui.QTextCharFormat]] = []
        for word in ARDUINO_KEYWORDS:
            pattern = QtCore.QRegularExpression(fr"\b{word}\b")
            self.highlighting_rules.append((pattern, keyword_format))

        types = ["int", "float", "double", "char", "boolean", "String", "void"]
        for word in types:
            pattern = QtCore.QRegularExpression(fr"\b{word}\b")
            self.highlighting_rules.append((pattern, type_format))

        self.comment_start = QtCore.QRegularExpression(r"/\*")
        self.comment_end = QtCore.QRegularExpression(r"\*/")
        self.comment_format = comment_format

        self.highlighting_rules.append((QtCore.QRegularExpression(r"//[^\n]*"), comment_format))
        self.highlighting_rules.append((QtCore.QRegularExpression(r'"[^"\\]*(?:\\.[^"\\]*)*"'), string_format))

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, text_format in self.highlighting_rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), text_format)

        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            match = self.comment_start.match(text)
            start_index = match.capturedStart() if match.hasMatch() else -1

        while start_index >= 0:
            end_match = self.comment_end.match(text, start_index)
            end_index = end_match.capturedStart()
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + end_match.capturedLength()
            self.setFormat(start_index, comment_length, self.comment_format)
            start_index = self.comment_start.match(text, start_index + comment_length).capturedStart()


class TouchEditor(QtWidgets.QPlainTextEdit):
    """Touch-friendly editor with Arduino syntax highlighting."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.file_path: Optional[Path] = None
        self.highlighter = ArduinoHighlighter(self.document())
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.textChanged.connect(self._sync_title)
        self.setAttribute(QtCore.Qt.WA_InputMethodEnabled, True)
        self.setUndoRedoEnabled(True)

    def _sync_title(self) -> None:
        if self.window():
            self.window().setWindowTitle(self.tab_title())

    def tab_title(self) -> str:
        if self.file_path:
            return f"{self.file_path.name}*" if self.document().isModified() else self.file_path.name
        return "Untitled*" if self.document().isModified() else "Untitled"

    def insert_symbol(self, symbol: str) -> None:
        cursor = self.textCursor()
        cursor.insertText(symbol)
        self.setTextCursor(cursor)

    def load_file(self, path: Path, content: str | None = None) -> None:
        self.file_path = path
        if content is None:
            with path.open("r", encoding="utf-8") as handle:
                content = handle.read()
        self.setPlainText(content)
        self.document().setModified(False)

    def save(self) -> None:
        if not self.file_path:
            return
        with self.file_path.open("w", encoding="utf-8") as handle:
            handle.write(self.toPlainText())
        self.document().setModified(False)

    def apply_touch_preferences(self) -> None:
        font = QtGui.QFont("Fira Code", 13)
        font.setStyleStrategy(QtGui.QFont.PreferAntialias)
        self.setFont(font)
        self.setCursorWidth(3)
        self.setViewportMargins(12, 12, 12, 12)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

    def enable_keyboard_shortcuts(self) -> None:
        undo_shortcut = QtGui.QShortcut(QtGui.QKeySequence.Undo, self)
        undo_shortcut.activated.connect(self.undo)
        redo_shortcut = QtGui.QShortcut(QtGui.QKeySequence.Redo, self)
        redo_shortcut.activated.connect(self.redo)

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:  # noqa: N802
        super().focusInEvent(event)
        if self.parent():
            self.parent().setFocus()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.viewport().update()

    def placeholderText(self) -> str:
        return getattr(self, "_placeholder", "")

    def setPlaceholderText(self, text: str) -> None:
        self._placeholder = text

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        if self.toPlainText() or not getattr(self, "_placeholder", None):
            return
        painter = QtGui.QPainter(self.viewport())
        painter.setPen(QtGui.QColor("#777"))
        painter.drawText(self.viewport().rect().adjusted(12, 12, -12, -12), QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft, self._placeholder)
        painter.end()

    def load_file_dialog(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Sketch", "", "Arduino Sketches (*.ino)")
        if path:
            self.load_file(Path(path))

    def tab_changed(self) -> None:
        if self.window():
            self.window().setWindowTitle(self.tab_title())

    def set_theme(self, mode: str) -> None:
        palette = self.palette()
        if mode == "dark":
            palette.setColor(QtGui.QPalette.Base, QtGui.QColor("#1e1e1e"))
            palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        else:
            palette.setColor(QtGui.QPalette.Base, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.Text, QtCore.Qt.black)
        self.setPalette(palette)


__all__ = ["TouchEditor", "ArduinoHighlighter"]
