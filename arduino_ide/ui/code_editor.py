"""
Code editor with syntax highlighting and IntelliSense
"""

from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PySide6.QtCore import Qt, QRect, QSize, Signal
from PySide6.QtGui import (
    QColor, QPainter, QTextFormat, QFont, QSyntaxHighlighter,
    QTextCharFormat, QPalette, QTextCursor
)
import re


class LineNumberArea(QWidget):
    """Widget for displaying line numbers"""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class ArduinoSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Arduino C/C++ code"""

    def __init__(self, document):
        super().__init__(document)

        # Define formats
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#569CD6"))  # Blue
        self.keyword_format.setFontWeight(QFont.Bold)

        self.type_format = QTextCharFormat()
        self.type_format.setForeground(QColor("#4EC9B0"))  # Teal

        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#DCDCAA"))  # Yellow

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#CE9178"))  # Orange

        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6A9955"))  # Green
        self.comment_format.setFontItalic(True)

        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#B5CEA8"))  # Light green

        self.preprocessor_format = QTextCharFormat()
        self.preprocessor_format.setForeground(QColor("#C586C0"))  # Purple

        # Define patterns
        self.keywords = [
            "if", "else", "for", "while", "do", "switch", "case", "break",
            "continue", "return", "goto", "default", "sizeof", "const",
            "static", "volatile", "extern", "auto", "register", "typedef",
            "struct", "union", "enum", "class", "public", "private",
            "protected", "virtual", "inline", "template", "namespace",
            "using", "new", "delete", "this", "true", "false", "nullptr"
        ]

        self.types = [
            "void", "int", "char", "float", "double", "bool", "byte",
            "word", "long", "short", "unsigned", "signed", "String",
            "boolean", "uint8_t", "uint16_t", "uint32_t", "int8_t",
            "int16_t", "int32_t", "size_t"
        ]

        self.arduino_functions = [
            # Digital I/O
            "pinMode", "digitalWrite", "digitalRead",
            # Analog I/O
            "analogRead", "analogWrite", "analogReference",
            # Time
            "delay", "delayMicroseconds", "millis", "micros",
            # Serial
            "Serial.begin", "Serial.print", "Serial.println", "Serial.read",
            "Serial.available", "Serial.write",
            # Math
            "abs", "constrain", "map", "max", "min", "pow", "sqrt",
            # Random
            "random", "randomSeed",
            # Bits
            "bit", "bitClear", "bitRead", "bitSet", "bitWrite",
            # Interrupts
            "attachInterrupt", "detachInterrupt", "interrupts", "noInterrupts",
            # Advanced I/O
            "tone", "noTone", "shiftOut", "shiftIn", "pulseIn"
        ]

        # Define constants
        self.constants = [
            "HIGH", "LOW", "INPUT", "OUTPUT", "INPUT_PULLUP",
            "LED_BUILTIN", "A0", "A1", "A2", "A3", "A4", "A5",
            "PI", "HALF_PI", "TWO_PI"
        ]

    def highlightBlock(self, text):
        """Highlight a block of text"""

        # Keywords
        for keyword in self.keywords:
            pattern = r'\b' + keyword + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(),
                             self.keyword_format)

        # Types
        for type_name in self.types:
            pattern = r'\b' + type_name + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(),
                             self.type_format)

        # Arduino functions and constants
        for func in self.arduino_functions + self.constants:
            pattern = r'\b' + re.escape(func) + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(),
                             self.function_format)

        # Numbers
        pattern = r'\b\d+\.?\d*\b'
        for match in re.finditer(pattern, text):
            self.setFormat(match.start(), match.end() - match.start(),
                         self.number_format)

        # Preprocessor directives
        pattern = r'#\s*\w+'
        for match in re.finditer(pattern, text):
            self.setFormat(match.start(), match.end() - match.start(),
                         self.preprocessor_format)

        # Strings
        pattern = r'"[^"\\]*(\\.[^"\\]*)*"'
        for match in re.finditer(pattern, text):
            self.setFormat(match.start(), match.end() - match.start(),
                         self.string_format)

        # Single-line comments
        pattern = r'//[^\n]*'
        for match in re.finditer(pattern, text):
            self.setFormat(match.start(), match.end() - match.start(),
                         self.comment_format)

        # Multi-line comments
        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            start_index = text.find('/*')

        while start_index >= 0:
            end_index = text.find('*/', start_index)
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + 2

            self.setFormat(start_index, comment_length, self.comment_format)
            start_index = text.find('/*', start_index + comment_length)


class CodeEditor(QPlainTextEdit):
    """
    Advanced code editor with:
    - Line numbers
    - Syntax highlighting
    - Auto-indentation
    - Code completion hints
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Setup font
        font = QFont("Consolas, Monaco, Courier New")
        font.setPointSize(11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        # Line number area
        self.line_number_area = LineNumberArea(self)

        # Syntax highlighter
        self.highlighter = ArduinoSyntaxHighlighter(self.document())

        # Connect signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        # Enable tab as spaces
        self.setTabStopDistance(40)  # 4 spaces

    def line_number_area_width(self):
        """Calculate width needed for line numbers"""
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        """Update line number area width"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Update line number area"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(),
                                        self.line_number_area.width(),
                                        rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Handle resize event"""
        super().resizeEvent(event)

        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
                                               self.line_number_area_width(),
                                               cr.height()))

    def line_number_area_paint_event(self, event):
        """Paint line numbers"""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#2D2D30"))  # Dark background

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#858585"))  # Gray
                painter.drawText(0, top, self.line_number_area.width(),
                               self.fontMetrics().height(),
                               Qt.AlignRight, number + " ")

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        """Highlight the current line"""
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()

            line_color = QColor("#2A2A2A")  # Slightly lighter than background

            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, event):
        """Handle key press for auto-indentation"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Get current line indentation
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()

            # Count leading spaces/tabs
            indent = len(text) - len(text.lstrip())
            indent_str = text[:indent]

            # Check if line ends with { to add extra indent
            extra_indent = ""
            if text.rstrip().endswith('{'):
                extra_indent = "  "  # 2 spaces

            # Insert newline and indentation
            super().keyPressEvent(event)
            self.insertPlainText(indent_str + extra_indent)
        else:
            super().keyPressEvent(event)
