"""
Code editor with syntax highlighting and IntelliSense
"""

from PySide6.QtWidgets import (
    QPlainTextEdit, QWidget, QTextEdit, QCompleter, QLabel, QHBoxLayout,
    QVBoxLayout, QScrollBar, QToolTip, QMenu, QDialog, QFormLayout, QPushButton,
    QListWidget, QListWidgetItem, QTextBrowser, QDialogButtonBox
)
from PySide6.QtCore import Qt, QRect, QSize, Signal, QStringListModel, QTimer, QPoint
from PySide6.QtGui import (
    QColor, QPainter, QTextFormat, QFont, QSyntaxHighlighter,
    QTextCharFormat, QPalette, QTextCursor, QPainterPath, QPen, QBrush, QAction
)
import re
from pathlib import Path
try:
    from git import Repo
except ImportError:
    Repo = None


class BreadcrumbBar(QWidget):
    """Breadcrumb navigation showing file path and current function"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        self.label = QLabel()
        self.label.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-size: 11px;
                padding: 2px;
            }
        """)
        layout.addWidget(self.label)
        layout.addStretch()

        self.setMaximumHeight(25)
        self.setStyleSheet("background-color: #2D2D30; border-bottom: 1px solid #3E3E42;")

    def update_breadcrumb(self, file_path, function_name=None, line_number=None):
        """Update breadcrumb text"""
        parts = []
        if file_path:
            parts.append(Path(file_path).name)
        if function_name:
            parts.append(function_name)
        if line_number is not None:
            parts.append(f"Line {line_number}")

        self.label.setText(" > ".join(parts) if parts else "")


class CodeMinimap(QPlainTextEdit):
    """Minimap showing zoomed-out view of code"""

    clicked = Signal(int)  # Emit line number when clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMaximumWidth(120)
        self.setMinimumWidth(80)

        # Tiny font for minimap
        font = QFont("Consolas")
        font.setPointSize(2)
        self.setFont(font)

        # Styling
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                border-left: 1px solid #3E3E42;
                color: #808080;
            }
        """)

        self.viewport().setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        """Handle clicks to jump to position"""
        cursor = self.cursorForPosition(event.pos())
        line_number = cursor.blockNumber()
        self.clicked.emit(line_number)
        super().mousePressEvent(event)


class LineNumberArea(QWidget):
    """Widget for displaying line numbers, git diff markers, and fold indicators"""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

    def mousePressEvent(self, event):
        """Handle clicks for code folding"""
        self.editor.handle_line_number_click(event)


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
    - Error squiggles
    - Git diff markers
    - Code folding
    - Minimap
    """

    def __init__(self, parent=None, file_path=None):
        super().__init__(parent)

        self.file_path = file_path
        self.errors = []  # List of (line_number, message) tuples
        self.folded_blocks = set()  # Set of line numbers that are folded
        self.git_changes = {}  # {line_number: 'added'|'modified'|'deleted'}

        # Setup font
        font = QFont("Consolas, Monaco, Courier New")
        font.setPointSize(11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        # Line number area
        self.line_number_area = LineNumberArea(self)

        # Syntax highlighter
        self.highlighter = ArduinoSyntaxHighlighter(self.document())

        # Setup autocomplete
        self.setup_autocomplete()

        # Connect signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.on_cursor_changed)
        self.textChanged.connect(self.on_text_changed)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        # Enable tab as spaces
        self.setTabStopDistance(40)  # 4 spaces

        # Timer for delayed error checking
        self.error_check_timer = QTimer()
        self.error_check_timer.setSingleShot(True)
        self.error_check_timer.timeout.connect(self.check_errors)

        # Initialize git tracking
        self.update_git_diff()

    def setup_autocomplete(self):
        """Setup code completion"""
        # Collect all completions
        completions = []
        completions.extend(self.highlighter.keywords)
        completions.extend(self.highlighter.types)
        completions.extend(self.highlighter.arduino_functions)
        completions.extend(self.highlighter.constants)

        # Add common Arduino snippets
        completions.extend([
            "setup()", "loop()", "Serial.begin(9600)", "pinMode(",
            "digitalWrite(", "digitalRead(", "analogRead(", "analogWrite(",
            "delay(", "millis()", "if (", "for (", "while (", "switch ("
        ])

        self.completer = QCompleter(sorted(set(completions)), self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.activated.connect(self.insert_completion)

    def insert_completion(self, completion):
        """Insert selected completion"""
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def on_cursor_changed(self):
        """Handle cursor position changes"""
        self.highlight_current_line()

    def on_text_changed(self):
        """Handle text changes - trigger error checking"""
        self.error_check_timer.start(500)  # Check after 500ms of no typing

    def check_errors(self):
        """Check for basic syntax errors"""
        self.errors.clear()
        text = self.toPlainText()
        lines = text.split('\n')

        # Track brace/paren/bracket balance
        brace_stack = []
        paren_stack = []
        bracket_stack = []

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            clean_line = re.sub(r'//.*', '', line)
            clean_line = re.sub(r'/\*.*?\*/', '', clean_line)

            # Check for common errors
            for i, char in enumerate(clean_line):
                if char == '{':
                    brace_stack.append(line_num)
                elif char == '}':
                    if not brace_stack:
                        self.errors.append((line_num, "Unmatched closing brace"))
                    else:
                        brace_stack.pop()
                elif char == '(':
                    paren_stack.append(line_num)
                elif char == ')':
                    if not paren_stack:
                        self.errors.append((line_num, "Unmatched closing parenthesis"))
                    else:
                        paren_stack.pop()
                elif char == '[':
                    bracket_stack.append(line_num)
                elif char == ']':
                    if not bracket_stack:
                        self.errors.append((line_num, "Unmatched closing bracket"))
                    else:
                        bracket_stack.pop()

            # Check for missing semicolons (simple heuristic)
            stripped = clean_line.strip()
            if stripped and not stripped.endswith(('{', '}', ';', ':', '\\', ',')):
                if not stripped.startswith('#') and not any(kw in stripped for kw in ['if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default']):
                    # Might be missing semicolon
                    if ')' in stripped or '=' in stripped:
                        self.errors.append((line_num, "Possibly missing semicolon"))

        # Check for unclosed braces/parens/brackets
        if brace_stack:
            self.errors.append((brace_stack[-1], "Unclosed opening brace"))
        if paren_stack:
            self.errors.append((paren_stack[-1], "Unclosed opening parenthesis"))
        if bracket_stack:
            self.errors.append((bracket_stack[-1], "Unclosed opening bracket"))

        # Trigger repaint to show error squiggles
        self.highlight_current_line()

    def update_git_diff(self):
        """Update git diff markers"""
        if not Repo or not self.file_path:
            return

        try:
            repo = Repo(Path(self.file_path).parent, search_parent_directories=True)
            if repo.bare:
                return

            # Get diff for current file
            self.git_changes.clear()
            # This is a simplified version - real implementation would parse git diff
            # For now, just mark it as a placeholder
        except Exception:
            pass

    def get_current_function(self):
        """Get the name of the function at cursor position"""
        cursor = self.textCursor()
        block_num = cursor.blockNumber()

        # Search backwards for function definition
        for line_num in range(block_num, -1, -1):
            block = self.document().findBlockByNumber(line_num)
            text = block.text()
            # Simple regex to match function definitions
            match = re.match(r'\s*(void|int|float|double|bool|char|String)\s+(\w+)\s*\(', text)
            if match:
                return match.group(2)

        return None

    def handle_line_number_click(self, event):
        """Handle clicks in line number area for code folding"""
        # Calculate which line was clicked
        block = self.firstVisibleBlock()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.pos().y():
            if top <= event.pos().y() <= bottom:
                line_num = block.blockNumber()
                # Toggle folding for this line
                if line_num in self.folded_blocks:
                    self.folded_blocks.remove(line_num)
                else:
                    # Check if this line can be folded (contains opening brace)
                    if '{' in block.text():
                        self.folded_blocks.add(line_num)
                self.viewport().update()
                break

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    def line_number_area_width(self):
        """Calculate width needed for line numbers"""
        digits = len(str(max(1, self.blockCount())))
        # Extra space for git markers and fold indicators
        space = 15 + self.fontMetrics().horizontalAdvance('9') * digits
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
        """Paint line numbers, git diff markers, and fold indicators"""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#2D2D30"))  # Dark background

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_num = block_number + 1

                # Draw git diff marker (left edge)
                if line_num in self.git_changes:
                    change_type = self.git_changes[line_num]
                    if change_type == 'added':
                        painter.fillRect(0, top, 3, self.fontMetrics().height(), QColor("#4EC9B0"))
                    elif change_type == 'modified':
                        painter.fillRect(0, top, 3, self.fontMetrics().height(), QColor("#569CD6"))
                    elif change_type == 'deleted':
                        painter.fillRect(0, top, 3, self.fontMetrics().height(), QColor("#F48771"))

                # Draw fold indicator if line has braces
                text = block.text()
                if '{' in text:
                    # Draw triangle for fold indicator
                    if block_number in self.folded_blocks:
                        # Collapsed - draw right-pointing triangle
                        points = [
                            QPoint(7, top + 5),
                            QPoint(7, top + 11),
                            QPoint(11, top + 8)
                        ]
                    else:
                        # Expanded - draw down-pointing triangle
                        points = [
                            QPoint(6, top + 6),
                            QPoint(12, top + 6),
                            QPoint(9, top + 10)
                        ]
                    painter.setBrush(QBrush(QColor("#858585")))
                    painter.setPen(Qt.NoPen)
                    painter.drawPolygon(points)

                # Draw line number
                number = str(line_num)
                painter.setPen(QColor("#858585"))  # Gray
                painter.drawText(15, top, self.line_number_area.width() - 15,
                               self.fontMetrics().height(),
                               Qt.AlignRight, number + " ")

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        """Highlight the current line and show error squiggles"""
        extra_selections = []

        # Highlight current line
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#2A2A2A")  # Slightly lighter than background
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        # Add error squiggles
        for line_num, message in self.errors:
            block = self.document().findBlockByNumber(line_num - 1)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.cursor = QTextCursor(block)
                selection.cursor.select(QTextCursor.LineUnderCursor)

                # Red wavy underline
                error_format = QTextCharFormat()
                error_format.setUnderlineStyle(QTextCharFormat.WaveUnderline)
                error_format.setUnderlineColor(QColor("#F48771"))  # Red
                selection.format = error_format

                extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, event):
        """Handle key press for auto-indentation and autocomplete"""
        # Handle autocomplete
        if self.completer.popup().isVisible():
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape, Qt.Key_Tab):
                event.ignore()
                return

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
            return

        # Call parent
        super().keyPressEvent(event)

        # Trigger autocomplete
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        text_under_cursor = cursor.selectedText()

        if len(text_under_cursor) >= 2:  # Show after 2 characters
            self.completer.setCompletionPrefix(text_under_cursor)
            popup = self.completer.popup()
            popup.setCurrentIndex(self.completer.completionModel().index(0, 0))

            cr = self.cursorRect()
            cr.setWidth(self.completer.popup().sizeHintForColumn(0)
                       + self.completer.popup().verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()

    def mouseMoveEvent(self, event):
        """Show error tooltips on hover"""
        cursor = self.cursorForPosition(event.pos())
        block_num = cursor.blockNumber() + 1

        # Check if hovering over an error line
        for line_num, message in self.errors:
            if line_num == block_num:
                QToolTip.showText(event.globalPos(), message, self)
                break
        else:
            QToolTip.hideText()

        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event):
        """Show context menu with pin-specific actions"""
        # Get word under cursor
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText()

        # Check if word is a pin number or identifier
        pin_info = self.detect_pin_under_cursor(cursor)

        if pin_info:
            # Create pin-specific context menu
            menu = QMenu(self)

            # Add separator with pin name
            pin_label = menu.addAction(f"Pin: {pin_info['display_name']}")
            pin_label.setEnabled(False)
            menu.addSeparator()

            # View in Pinout Diagram
            view_action = QAction("View in Pinout Diagram", self)
            view_action.triggered.connect(lambda: self.view_pin_diagram(pin_info))
            menu.addAction(view_action)

            # Show Pin Capabilities
            capabilities_action = QAction("Show Pin Capabilities", self)
            capabilities_action.triggered.connect(lambda: self.show_pin_capabilities(pin_info))
            menu.addAction(capabilities_action)

            # Find Other Uses
            find_uses_action = QAction("Find Other Uses", self)
            find_uses_action.triggered.connect(lambda: self.find_pin_uses(pin_info))
            menu.addAction(find_uses_action)

            menu.addSeparator()

            # Generate pinMode() submenu
            pinmode_menu = QMenu("Generate pinMode()", self)

            input_action = QAction("INPUT", self)
            input_action.triggered.connect(lambda: self.generate_pinmode(pin_info, "INPUT"))
            pinmode_menu.addAction(input_action)

            output_action = QAction("OUTPUT", self)
            output_action.triggered.connect(lambda: self.generate_pinmode(pin_info, "OUTPUT"))
            pinmode_menu.addAction(output_action)

            input_pullup_action = QAction("INPUT_PULLUP", self)
            input_pullup_action.triggered.connect(lambda: self.generate_pinmode(pin_info, "INPUT_PULLUP"))
            pinmode_menu.addAction(input_pullup_action)

            menu.addMenu(pinmode_menu)

            # Show the menu
            menu.exec_(event.globalPos())
        else:
            # Show standard context menu
            menu = self.createStandardContextMenu()
            menu.exec_(event.globalPos())

    def detect_pin_under_cursor(self, cursor):
        """Detect if cursor is on a pin number or identifier

        Returns dict with pin info or None if not a pin
        """
        # Select word under cursor
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText()

        if not word:
            return None

        # Check if it's a numeric pin (0-13 for digital, 14-19 for analog)
        if word.isdigit():
            pin_num = int(word)
            if 0 <= pin_num <= 19:
                display_name = f"D{pin_num}" if pin_num < 14 else f"A{pin_num - 14}"
                return {
                    'raw': word,
                    'display_name': display_name,
                    'pin_number': pin_num,
                    'type': 'digital' if pin_num < 14 else 'analog'
                }

        # Check for analog pins (A0-A7)
        if re.match(r'^A[0-7]$', word):
            return {
                'raw': word,
                'display_name': word,
                'pin_number': int(word[1:]) + 14,
                'type': 'analog'
            }

        # Check for special pin names
        special_pins = {
            'LED_BUILTIN': {'display_name': 'D13 (LED_BUILTIN)', 'pin_number': 13, 'type': 'digital'},
            'SCL': {'display_name': 'A5 (SCL)', 'pin_number': 19, 'type': 'i2c'},
            'SDA': {'display_name': 'A4 (SDA)', 'pin_number': 18, 'type': 'i2c'},
            'SS': {'display_name': 'D10 (SS)', 'pin_number': 10, 'type': 'spi'},
            'MOSI': {'display_name': 'D11 (MOSI)', 'pin_number': 11, 'type': 'spi'},
            'MISO': {'display_name': 'D12 (MISO)', 'pin_number': 12, 'type': 'spi'},
            'SCK': {'display_name': 'D13 (SCK)', 'pin_number': 13, 'type': 'spi'},
        }

        if word in special_pins:
            info = special_pins[word].copy()
            info['raw'] = word
            return info

        # Check if it's a variable that might be assigned a pin number
        # Look backwards in the code for assignments like "int ledPin = 13;"
        text = self.toPlainText()
        # Pattern: variable declaration with pin assignment
        pattern = rf'\b(?:const\s+)?(?:int|byte)\s+{re.escape(word)}\s*=\s*(\d+|A[0-7]|LED_BUILTIN)\b'
        match = re.search(pattern, text)

        if match:
            assigned_value = match.group(1)
            # Recursively detect what the assigned value is
            temp_cursor = QTextCursor(self.document())
            temp_cursor.movePosition(QTextCursor.Start)
            temp_cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, match.start(1))
            temp_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(assigned_value))

            result = self.detect_pin_under_cursor(temp_cursor)
            if result:
                result['variable_name'] = word
                return result

        return None

    def view_pin_diagram(self, pin_info):
        """Show pin in pinout diagram"""
        dialog = PinDiagramDialog(pin_info, self)
        dialog.exec_()

    def show_pin_capabilities(self, pin_info):
        """Show pin capabilities dialog"""
        dialog = PinCapabilitiesDialog(pin_info, self)
        dialog.exec_()

    def find_pin_uses(self, pin_info):
        """Find and highlight all uses of this pin in the code"""
        # Get all text
        text = self.toPlainText()

        # Create search terms (pin number, variable name, etc.)
        search_terms = [pin_info['raw']]
        if 'variable_name' in pin_info:
            search_terms.append(pin_info['variable_name'])

        # Find all occurrences
        occurrences = []
        for term in search_terms:
            pattern = r'\b' + re.escape(term) + r'\b'
            for match in re.finditer(pattern, text):
                line_num = text[:match.start()].count('\n') + 1
                occurrences.append((line_num, match.start(), match.end(), term))

        if occurrences:
            # Show results in a dialog
            dialog = PinUsesDialog(pin_info, occurrences, self)
            result = dialog.exec_()

            # If user clicked on a usage, jump to it
            if result and hasattr(dialog, 'selected_position'):
                cursor = QTextCursor(self.document())
                cursor.setPosition(dialog.selected_position)
                self.setTextCursor(cursor)
                self.centerCursor()
        else:
            # No uses found
            QToolTip.showText(self.mapToGlobal(self.cursorRect().center()),
                            f"No uses of {pin_info['display_name']} found", self)

    def generate_pinmode(self, pin_info, mode):
        """Generate pinMode() statement at cursor position"""
        # Determine what identifier to use
        if 'variable_name' in pin_info:
            pin_identifier = pin_info['variable_name']
        else:
            pin_identifier = pin_info['raw']

        # Generate the pinMode statement
        pinmode_statement = f"pinMode({pin_identifier}, {mode});"

        # Insert at cursor position
        cursor = self.textCursor()

        # Find the setup() function or insert at cursor
        text = self.toPlainText()
        setup_match = re.search(r'void\s+setup\s*\(\s*\)\s*\{', text)

        if setup_match:
            # Insert after the opening brace of setup()
            insert_pos = setup_match.end()

            # Find the indentation
            lines = text[:insert_pos].split('\n')
            last_line = lines[-1] if lines else ''
            indent = '  '  # Default 2 spaces

            # Insert the pinMode statement
            cursor.setPosition(insert_pos)
            cursor.insertText(f'\n{indent}{pinmode_statement}')
        else:
            # Insert at current cursor position
            cursor.insertText(pinmode_statement)

        # Move cursor after inserted text
        self.setTextCursor(cursor)


class PinDiagramDialog(QDialog):
    """Dialog showing Arduino pin diagram with highlighted pin"""

    def __init__(self, pin_info, parent=None):
        super().__init__(parent)
        self.pin_info = pin_info
        self.setWindowTitle("Arduino Pinout Diagram")
        self.setMinimumSize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"Pin: {self.pin_info['display_name']}")
        header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                background-color: #2d2d2d;
                color: #ffffff;
            }
        """)
        layout.addWidget(header)

        # Create Arduino Uno pinout diagram (simplified ASCII art version)
        diagram = self.create_pinout_diagram()
        diagram_label = QLabel(diagram)
        diagram_label.setFont(QFont("Courier New", 10))
        diagram_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #d4d4d4;
                padding: 20px;
                border: 1px solid #3e3e42;
            }
        """)
        diagram_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(diagram_label)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def create_pinout_diagram(self):
        """Create ASCII art pinout diagram with highlighted pin"""
        pin_num = self.pin_info['pin_number']

        # Arduino Uno pinout (simplified)
        diagram_lines = [
            "┌─────────────────────────────────────────────────┐",
            "│           Arduino Uno R3 Pinout                 │",
            "├─────────────────────────────────────────────────┤",
            "│                                                 │",
            "│  Digital I/O:                                   │",
            "│  ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐     │",
            "│  │ 0 │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │ 7 │ 8 │ 9 │     │",
            "│  └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘     │",
            "│  ┌────┬────┬────┬────┐                         │",
            "│  │ 10 │ 11 │ 12 │ 13 │                         │",
            "│  └────┴────┴────┴────┘                         │",
            "│                                                 │",
            "│  Analog Inputs:                                 │",
            "│  ┌────┬────┬────┬────┬────┬────┐               │",
            "│  │ A0 │ A1 │ A2 │ A3 │ A4 │ A5 │               │",
            "│  └────┴────┴────┴────┴────┴────┘               │",
            "│                                                 │",
            "│  Special Functions:                             │",
            "│  • Pins 0-1: Serial (RX/TX)                     │",
            "│  • Pins 2-3: External Interrupts                │",
            "│  • Pins 3,5,6,9,10,11: PWM                      │",
            "│  • Pin 13: Built-in LED                         │",
            "│  • A4-A5: I2C (SDA/SCL)                         │",
            "│  • Pins 10-13: SPI (SS/MOSI/MISO/SCK)           │",
            "│                                                 │",
            "└─────────────────────────────────────────────────┘"
        ]

        # Highlight the selected pin
        highlighted = []
        for line in diagram_lines:
            if pin_num < 14:
                # Digital pin
                pin_str = str(pin_num)
                if f' {pin_str} ' in line or f'│ {pin_str} │' in line:
                    line = line.replace(f' {pin_str} ', f'[{pin_str}]')
                    line = line.replace(f'│ {pin_str} │', f'│[{pin_str}]│')
            else:
                # Analog pin
                pin_str = f'A{pin_num - 14}'
                if f' {pin_str} ' in line or f'│ {pin_str} │' in line:
                    line = line.replace(f' {pin_str} ', f'[{pin_str}]')
                    line = line.replace(f'│ {pin_str} │', f'│[{pin_str}]│')

            highlighted.append(line)

        return '\n'.join(highlighted)


class PinCapabilitiesDialog(QDialog):
    """Dialog showing detailed pin capabilities"""

    def __init__(self, pin_info, parent=None):
        super().__init__(parent)
        self.pin_info = pin_info
        self.setWindowTitle("Pin Capabilities")
        self.setMinimumSize(500, 400)
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"Capabilities of {self.pin_info['display_name']}")
        header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                background-color: #2d2d2d;
                color: #ffffff;
            }
        """)
        layout.addWidget(header)

        # Capabilities content
        capabilities = self.get_pin_capabilities()
        content = QTextBrowser()
        content.setHtml(capabilities)
        content.setStyleSheet("""
            QTextBrowser {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e42;
                padding: 10px;
            }
        """)
        layout.addWidget(content)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def get_pin_capabilities(self):
        """Get HTML formatted pin capabilities"""
        pin_num = self.pin_info['pin_number']
        pin_type = self.pin_info['type']

        # Define capabilities for each pin
        capabilities = {
            'basic': ['Digital I/O (INPUT/OUTPUT/INPUT_PULLUP)'],
            'pwm': [],
            'analog': [],
            'special': []
        }

        # Digital pins
        if pin_num < 14:
            # PWM capable pins
            if pin_num in [3, 5, 6, 9, 10, 11]:
                capabilities['pwm'].append('PWM Output (analogWrite)')

            # Serial
            if pin_num == 0:
                capabilities['special'].append('Serial RX (receive)')
            elif pin_num == 1:
                capabilities['special'].append('Serial TX (transmit)')

            # External interrupts
            if pin_num in [2, 3]:
                capabilities['special'].append(f'External Interrupt INT{pin_num - 2}')

            # SPI
            if pin_num == 10:
                capabilities['special'].append('SPI SS (Slave Select)')
            elif pin_num == 11:
                capabilities['special'].append('SPI MOSI (Master Out Slave In)')
            elif pin_num == 12:
                capabilities['special'].append('SPI MISO (Master In Slave Out)')
            elif pin_num == 13:
                capabilities['special'].append('SPI SCK (Clock)')
                capabilities['special'].append('Built-in LED')

        # Analog pins
        else:
            analog_num = pin_num - 14
            capabilities['analog'].append(f'Analog Input A{analog_num} (analogRead)')
            capabilities['basic'].append('Can also be used as digital I/O')

            # I2C
            if pin_num == 18:  # A4
                capabilities['special'].append('I2C SDA (Data)')
            elif pin_num == 19:  # A5
                capabilities['special'].append('I2C SCL (Clock)')

        # Build HTML
        html = f"""
        <h3 style="color: #4EC9B0;">Basic Capabilities</h3>
        <ul>
        """

        for cap in capabilities['basic']:
            html += f"<li>{cap}</li>"

        if capabilities['pwm']:
            html += """
            </ul>
            <h3 style="color: #DCDCAA;">PWM (Pulse Width Modulation)</h3>
            <ul>
            """
            for cap in capabilities['pwm']:
                html += f"<li>{cap}</li>"

        if capabilities['analog']:
            html += """
            </ul>
            <h3 style="color: #CE9178;">Analog</h3>
            <ul>
            """
            for cap in capabilities['analog']:
                html += f"<li>{cap}</li>"

        if capabilities['special']:
            html += """
            </ul>
            <h3 style="color: #C586C0;">Special Functions</h3>
            <ul>
            """
            for cap in capabilities['special']:
                html += f"<li>{cap}</li>"

        html += """
        </ul>
        <hr>
        <h3 style="color: #569CD6;">Electrical Characteristics</h3>
        <ul>
            <li>Operating Voltage: 5V</li>
            <li>Max Current per Pin: 40 mA</li>
            <li>Recommended Current per Pin: 20 mA</li>
            <li>Input Voltage Range: 0-5V</li>
        """

        if capabilities['pwm']:
            html += "<li>PWM Frequency: ~490 Hz (pins 5,6: ~980 Hz)</li>"

        if capabilities['analog']:
            html += "<li>ADC Resolution: 10-bit (0-1023)</li>"
            html += "<li>Analog Input Range: 0-5V</li>"

        html += """
        </ul>
        """

        return html


class PinUsesDialog(QDialog):
    """Dialog showing all uses of a pin in the code"""

    def __init__(self, pin_info, occurrences, parent=None):
        super().__init__(parent)
        self.pin_info = pin_info
        self.occurrences = occurrences
        self.selected_position = None
        self.setWindowTitle("Find Pin Uses")
        self.setMinimumSize(500, 400)
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"Uses of {self.pin_info['display_name']} ({len(self.occurrences)} found)")
        header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: #2d2d2d;
                color: #ffffff;
            }
        """)
        layout.addWidget(header)

        # List of occurrences
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e42;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #2d2d2d;
            }
            QListWidget::item:selected {
                background-color: #094771;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
        """)

        # Get the full text to show context
        if self.parent():
            full_text = self.parent().toPlainText()
            lines = full_text.split('\n')

            for line_num, start, end, term in self.occurrences:
                if 0 < line_num <= len(lines):
                    line_text = lines[line_num - 1].strip()
                    item = QListWidgetItem(f"Line {line_num}: {line_text}")
                    item.setData(Qt.UserRole, start)  # Store position for jumping
                    self.list_widget.addItem(item)

        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def on_item_double_clicked(self, item):
        """Handle double-click on an item"""
        self.selected_position = item.data(Qt.UserRole)
        self.accept()

    def on_accept(self):
        """Handle OK button"""
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_position = current_item.data(Qt.UserRole)
        self.accept()
