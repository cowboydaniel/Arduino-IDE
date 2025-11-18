"""
Code editor with syntax highlighting and IntelliSense
"""

from PySide6.QtWidgets import (
    QPlainTextEdit, QWidget, QTextEdit, QCompleter, QLabel, QHBoxLayout,
    QVBoxLayout, QScrollBar, QToolTip, QMenu, QDialog, QFormLayout, QPushButton,
    QListWidget, QListWidgetItem, QTextBrowser, QDialogButtonBox, QStyledItemDelegate,
    QStyle
)
from PySide6.QtCore import Qt, QRect, QSize, Signal, QStringListModel, QTimer, QPoint, QAbstractListModel, QModelIndex
from PySide6.QtGui import (
    QColor, QPainter, QTextFormat, QFont, QSyntaxHighlighter,
    QTextCharFormat, QPalette, QTextCursor, QPainterPath, QPen, QBrush, QAction
)
import re
from pathlib import Path
from typing import Dict, List
try:
    from git import Repo
except ImportError:
    Repo = None

# Import suggestion analyzer
from arduino_ide.services.suggestion_analyzer import SuggestionAnalyzer
from arduino_ide.services.git_diff_utils import calculate_git_changes
from arduino_ide.data.arduino_api_reference import get_api_info
from arduino_ide.services.contextual_help_service import (
    ContextualHelpService,
    InlineHint,
)


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

    def update_breadcrumb(self, file_path, function_name=None, line_number=None, project_name=None):
        """Update breadcrumb text with format: 'Project > filename > function > Line X'"""
        parts = []

        # Add project name if provided
        if project_name:
            parts.append(project_name)

        # Add file name
        if file_path:
            parts.append(Path(file_path).name)

        # Add function name
        if function_name:
            parts.append(f"{function_name}()")

        # Add line number
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
        self.type_format.setForeground(QColor("#4EC9B0"))  # Cyan

        self.object_format = QTextCharFormat()
        self.object_format.setForeground(QColor("#4EC9B0"))  # Cyan

        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#DCDCAA"))  # Yellow

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#CE9178"))  # Orange

        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6A9955"))  # Green
        self.comment_format.setFontItalic(True)

        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#D19A66"))  # Orange

        self.preprocessor_format = QTextCharFormat()
        self.preprocessor_format.setForeground(QColor("#C586C0"))  # Purple

        self.constant_format = QTextCharFormat()
        self.constant_format.setForeground(QColor("#C586C0"))  # Purple

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

        # Define objects
        self.objects = [
            "Serial", "Wire", "SPI", "EEPROM"
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

        # Arduino functions
        for func in self.arduino_functions:
            pattern = r'\b' + re.escape(func) + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(),
                             self.function_format)

        # Arduino constants
        for constant in self.constants:
            pattern = r'\b' + re.escape(constant) + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(),
                             self.constant_format)

        # Objects
        for obj in self.objects:
            pattern = r'\b' + re.escape(obj) + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(),
                             self.object_format)

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


class CompletionItem:
    """Single completion item with text and description"""

    def __init__(self, text, description="", snippet=None, type="function"):
        self.text = text
        self.description = description
        self.snippet = snippet if snippet else text
        self.type = type  # function, keyword, type, constant, snippet


class CompletionDatabase:
    """Database of Arduino API completions with descriptions"""

    def __init__(self):
        self.completions = {}
        self.setup_arduino_api()

    def setup_arduino_api(self):
        """Setup Arduino API completions"""

        # Serial class methods
        self.completions['Serial'] = [
            CompletionItem('println()', 'Send data with newline', 'println($0)', 'function'),
            CompletionItem('print()', 'Send data without newline', 'print($0)', 'function'),
            CompletionItem('printf()', 'Formatted printing', 'printf("$0")', 'function'),
            CompletionItem('available()', 'Get number of bytes available to read', 'available()', 'function'),
            CompletionItem('read()', 'Read incoming byte', 'read()', 'function'),
            CompletionItem('write()', 'Write binary data', 'write($0)', 'function'),
            CompletionItem('begin()', 'Initialize serial communication', 'begin(9600)', 'function'),
            CompletionItem('end()', 'Close serial communication', 'end()', 'function'),
            CompletionItem('flush()', 'Wait for outgoing data to complete', 'flush()', 'function'),
            CompletionItem('peek()', 'Read byte without removing from buffer', 'peek()', 'function'),
            CompletionItem('readString()', 'Read incoming data as String', 'readString()', 'function'),
            CompletionItem('readBytes()', 'Read bytes into buffer', 'readBytes($0)', 'function'),
            CompletionItem('setTimeout()', 'Set timeout for read operations', 'setTimeout($0)', 'function'),
        ]

        # Wire (I2C) class methods
        self.completions['Wire'] = [
            CompletionItem('begin()', 'Initialize I2C communication', 'begin()', 'function'),
            CompletionItem('beginTransmission()', 'Begin transmission to I2C device', 'beginTransmission($0)', 'function'),
            CompletionItem('endTransmission()', 'End transmission to I2C device', 'endTransmission()', 'function'),
            CompletionItem('requestFrom()', 'Request bytes from I2C device', 'requestFrom($0)', 'function'),
            CompletionItem('write()', 'Write data to I2C', 'write($0)', 'function'),
            CompletionItem('available()', 'Get number of bytes available', 'available()', 'function'),
            CompletionItem('read()', 'Read byte from I2C', 'read()', 'function'),
            CompletionItem('setClock()', 'Set I2C clock speed', 'setClock($0)', 'function'),
        ]

        # SPI class methods
        self.completions['SPI'] = [
            CompletionItem('begin()', 'Initialize SPI bus', 'begin()', 'function'),
            CompletionItem('end()', 'Disable SPI bus', 'end()', 'function'),
            CompletionItem('transfer()', 'Transfer data (send and receive)', 'transfer($0)', 'function'),
            CompletionItem('transfer16()', 'Transfer 16-bit data', 'transfer16($0)', 'function'),
            CompletionItem('beginTransaction()', 'Start SPI transaction', 'beginTransaction(SPISettings($0))', 'function'),
            CompletionItem('endTransaction()', 'End SPI transaction', 'endTransaction()', 'function'),
            CompletionItem('setBitOrder()', 'Set bit order (MSBFIRST/LSBFIRST)', 'setBitOrder($0)', 'function'),
            CompletionItem('setDataMode()', 'Set SPI mode (SPI_MODE0-3)', 'setDataMode($0)', 'function'),
            CompletionItem('setClockDivider()', 'Set clock divider', 'setClockDivider($0)', 'function'),
        ]

        # EEPROM class methods
        self.completions['EEPROM'] = [
            CompletionItem('read()', 'Read byte from EEPROM', 'read($0)', 'function'),
            CompletionItem('write()', 'Write byte to EEPROM', 'write($0, value)', 'function'),
            CompletionItem('update()', 'Update byte (write only if changed)', 'update($0, value)', 'function'),
            CompletionItem('get()', 'Read any data type from EEPROM', 'get($0, data)', 'function'),
            CompletionItem('put()', 'Write any data type to EEPROM', 'put($0, data)', 'function'),
            CompletionItem('length()', 'Get EEPROM size in bytes', 'length()', 'function'),
        ]

        # String class methods
        self.completions['String'] = [
            CompletionItem('charAt()', 'Get character at index', 'charAt($0)', 'function'),
            CompletionItem('compareTo()', 'Compare strings', 'compareTo($0)', 'function'),
            CompletionItem('concat()', 'Concatenate strings', 'concat($0)', 'function'),
            CompletionItem('endsWith()', 'Check if string ends with substring', 'endsWith($0)', 'function'),
            CompletionItem('equals()', 'Compare strings for equality', 'equals($0)', 'function'),
            CompletionItem('indexOf()', 'Find first occurrence of substring', 'indexOf($0)', 'function'),
            CompletionItem('lastIndexOf()', 'Find last occurrence of substring', 'lastIndexOf($0)', 'function'),
            CompletionItem('length()', 'Get string length', 'length()', 'function'),
            CompletionItem('replace()', 'Replace substring', 'replace($0)', 'function'),
            CompletionItem('startsWith()', 'Check if string starts with substring', 'startsWith($0)', 'function'),
            CompletionItem('substring()', 'Get substring', 'substring($0)', 'function'),
            CompletionItem('toCharArray()', 'Convert to char array', 'toCharArray($0)', 'function'),
            CompletionItem('toInt()', 'Convert to integer', 'toInt()', 'function'),
            CompletionItem('toLowerCase()', 'Convert to lowercase', 'toLowerCase()', 'function'),
            CompletionItem('toUpperCase()', 'Convert to uppercase', 'toUpperCase()', 'function'),
            CompletionItem('trim()', 'Remove whitespace', 'trim()', 'function'),
        ]

        # Servo library methods
        self.completions['Servo'] = [
            CompletionItem('attach()', 'Attach servo to pin', 'attach($0)', 'function'),
            CompletionItem('detach()', 'Detach servo from pin', 'detach()', 'function'),
            CompletionItem('write()', 'Write angle to servo (0-180 degrees)', 'write($0)', 'function'),
            CompletionItem('writeMicroseconds()', 'Write microseconds to servo (544-2400)', 'writeMicroseconds($0)', 'function'),
            CompletionItem('read()', 'Read current servo angle', 'read()', 'function'),
            CompletionItem('attached()', 'Check if servo is attached', 'attached()', 'function'),
        ]

        # SD library methods
        self.completions['SD'] = [
            CompletionItem('begin()', 'Initialize SD card', 'begin($0)', 'function'),
            CompletionItem('open()', 'Open file on SD card', 'open("$0", FILE_READ)', 'function'),
            CompletionItem('exists()', 'Check if file or directory exists', 'exists("$0")', 'function'),
            CompletionItem('mkdir()', 'Create directory', 'mkdir("$0")', 'function'),
            CompletionItem('remove()', 'Delete file', 'remove("$0")', 'function'),
            CompletionItem('rmdir()', 'Remove directory', 'rmdir("$0")', 'function'),
        ]

        # File object methods (from SD library)
        self.completions['File'] = [
            CompletionItem('available()', 'Get number of bytes available', 'available()', 'function'),
            CompletionItem('read()', 'Read next byte from file', 'read()', 'function'),
            CompletionItem('write()', 'Write data to file', 'write($0)', 'function'),
            CompletionItem('print()', 'Print data to file', 'print($0)', 'function'),
            CompletionItem('println()', 'Print data with newline to file', 'println($0)', 'function'),
            CompletionItem('peek()', 'Read byte without advancing', 'peek()', 'function'),
            CompletionItem('flush()', 'Flush file buffer', 'flush()', 'function'),
            CompletionItem('close()', 'Close file', 'close()', 'function'),
            CompletionItem('seek()', 'Seek to position in file', 'seek($0)', 'function'),
            CompletionItem('position()', 'Get current position in file', 'position()', 'function'),
            CompletionItem('size()', 'Get file size', 'size()', 'function'),
            CompletionItem('name()', 'Get file name', 'name()', 'function'),
            CompletionItem('isDirectory()', 'Check if File is a directory', 'isDirectory()', 'function'),
            CompletionItem('openNextFile()', 'Open next file in directory', 'openNextFile()', 'function'),
            CompletionItem('rewindDirectory()', 'Rewind directory to first file', 'rewindDirectory()', 'function'),
        ]

        # LiquidCrystal library methods
        self.completions['LiquidCrystal'] = [
            CompletionItem('begin()', 'Initialize LCD (columns, rows)', 'begin(16, 2)', 'function'),
            CompletionItem('clear()', 'Clear LCD display', 'clear()', 'function'),
            CompletionItem('home()', 'Move cursor to home position', 'home()', 'function'),
            CompletionItem('setCursor()', 'Set cursor position (col, row)', 'setCursor($0, $1)', 'function'),
            CompletionItem('print()', 'Print text to LCD', 'print($0)', 'function'),
            CompletionItem('write()', 'Write character to LCD', 'write($0)', 'function'),
            CompletionItem('display()', 'Turn on LCD display', 'display()', 'function'),
            CompletionItem('noDisplay()', 'Turn off LCD display', 'noDisplay()', 'function'),
            CompletionItem('cursor()', 'Show underline cursor', 'cursor()', 'function'),
            CompletionItem('noCursor()', 'Hide cursor', 'noCursor()', 'function'),
            CompletionItem('blink()', 'Blink cursor', 'blink()', 'function'),
            CompletionItem('noBlink()', 'Stop cursor blinking', 'noBlink()', 'function'),
            CompletionItem('scrollDisplayLeft()', 'Scroll display left', 'scrollDisplayLeft()', 'function'),
            CompletionItem('scrollDisplayRight()', 'Scroll display right', 'scrollDisplayRight()', 'function'),
            CompletionItem('leftToRight()', 'Text flows left to right', 'leftToRight()', 'function'),
            CompletionItem('rightToLeft()', 'Text flows right to left', 'rightToLeft()', 'function'),
            CompletionItem('autoscroll()', 'Enable autoscroll', 'autoscroll()', 'function'),
            CompletionItem('noAutoscroll()', 'Disable autoscroll', 'noAutoscroll()', 'function'),
            CompletionItem('createChar()', 'Create custom character', 'createChar($0, data[])', 'function'),
        ]

        # Ethernet library methods
        self.completions['Ethernet'] = [
            CompletionItem('begin()', 'Initialize Ethernet with MAC', 'begin(mac)', 'function'),
            CompletionItem('localIP()', 'Get local IP address', 'localIP()', 'function'),
            CompletionItem('subnetMask()', 'Get subnet mask', 'subnetMask()', 'function'),
            CompletionItem('gatewayIP()', 'Get gateway IP', 'gatewayIP()', 'function'),
            CompletionItem('dnsServerIP()', 'Get DNS server IP', 'dnsServerIP()', 'function'),
            CompletionItem('maintain()', 'Maintain DHCP lease', 'maintain()', 'function'),
            CompletionItem('linkStatus()', 'Get link status', 'linkStatus()', 'function'),
            CompletionItem('hardwareStatus()', 'Get hardware status', 'hardwareStatus()', 'function'),
        ]

        # EthernetClient methods
        self.completions['EthernetClient'] = [
            CompletionItem('connect()', 'Connect to server', 'connect(ip, port)', 'function'),
            CompletionItem('connected()', 'Check if connected', 'connected()', 'function'),
            CompletionItem('available()', 'Get bytes available to read', 'available()', 'function'),
            CompletionItem('read()', 'Read incoming byte', 'read()', 'function'),
            CompletionItem('write()', 'Write data to server', 'write($0)', 'function'),
            CompletionItem('print()', 'Print data to server', 'print($0)', 'function'),
            CompletionItem('println()', 'Print data with newline', 'println($0)', 'function'),
            CompletionItem('flush()', 'Flush outgoing data', 'flush()', 'function'),
            CompletionItem('stop()', 'Close connection', 'stop()', 'function'),
        ]

        # WiFi library methods (ESP8266/ESP32)
        self.completions['WiFi'] = [
            CompletionItem('begin()', 'Connect to WiFi network', 'begin("ssid", "password")', 'function'),
            CompletionItem('disconnect()', 'Disconnect from WiFi', 'disconnect()', 'function'),
            CompletionItem('status()', 'Get connection status', 'status()', 'function'),
            CompletionItem('localIP()', 'Get local IP address', 'localIP()', 'function'),
            CompletionItem('SSID()', 'Get current SSID', 'SSID()', 'function'),
            CompletionItem('RSSI()', 'Get signal strength', 'RSSI()', 'function'),
            CompletionItem('macAddress()', 'Get MAC address', 'macAddress()', 'function'),
            CompletionItem('mode()', 'Set WiFi mode', 'mode(WIFI_STA)', 'function'),
            CompletionItem('scanNetworks()', 'Scan for networks', 'scanNetworks()', 'function'),
            CompletionItem('softAP()', 'Create access point', 'softAP("ssid", "password")', 'function'),
            CompletionItem('softAPIP()', 'Get AP IP address', 'softAPIP()', 'function'),
        ]

        # Stepper library methods
        self.completions['Stepper'] = [
            CompletionItem('setSpeed()', 'Set motor speed (RPM)', 'setSpeed($0)', 'function'),
            CompletionItem('step()', 'Move number of steps', 'step($0)', 'function'),
        ]

        # Global Arduino functions
        self.completions['global'] = [
            # Digital I/O
            CompletionItem('pinMode()', 'Configure pin mode (INPUT/OUTPUT/INPUT_PULLUP)', 'pinMode($0, OUTPUT)', 'function'),
            CompletionItem('digitalWrite()', 'Write digital value (HIGH/LOW)', 'digitalWrite($0, HIGH)', 'function'),
            CompletionItem('digitalRead()', 'Read digital value from pin', 'digitalRead($0)', 'function'),

            # Analog I/O
            CompletionItem('analogRead()', 'Read analog value (0-1023)', 'analogRead($0)', 'function'),
            CompletionItem('analogWrite()', 'Write PWM value (0-255)', 'analogWrite($0, 128)', 'function'),
            CompletionItem('analogReference()', 'Set analog reference voltage', 'analogReference($0)', 'function'),

            # Time
            CompletionItem('delay()', 'Pause execution (milliseconds)', 'delay($0)', 'function'),
            CompletionItem('delayMicroseconds()', 'Pause execution (microseconds)', 'delayMicroseconds($0)', 'function'),
            CompletionItem('millis()', 'Get milliseconds since program start', 'millis()', 'function'),
            CompletionItem('micros()', 'Get microseconds since program start', 'micros()', 'function'),

            # Math
            CompletionItem('abs()', 'Absolute value', 'abs($0)', 'function'),
            CompletionItem('constrain()', 'Constrain value to range', 'constrain($0, min, max)', 'function'),
            CompletionItem('map()', 'Map value from one range to another', 'map($0, fromLow, fromHigh, toLow, toHigh)', 'function'),
            CompletionItem('max()', 'Maximum of two values', 'max($0, $1)', 'function'),
            CompletionItem('min()', 'Minimum of two values', 'min($0, $1)', 'function'),
            CompletionItem('pow()', 'Raise to power', 'pow($0, $1)', 'function'),
            CompletionItem('sqrt()', 'Square root', 'sqrt($0)', 'function'),
            CompletionItem('sq()', 'Square a number', 'sq($0)', 'function'),

            # Trigonometry
            CompletionItem('sin()', 'Sine (radians)', 'sin($0)', 'function'),
            CompletionItem('cos()', 'Cosine (radians)', 'cos($0)', 'function'),
            CompletionItem('tan()', 'Tangent (radians)', 'tan($0)', 'function'),
            CompletionItem('asin()', 'Arc sine (returns radians)', 'asin($0)', 'function'),
            CompletionItem('acos()', 'Arc cosine (returns radians)', 'acos($0)', 'function'),
            CompletionItem('atan()', 'Arc tangent (returns radians)', 'atan($0)', 'function'),
            CompletionItem('atan2()', 'Arc tangent of y/x (returns radians)', 'atan2($0, $1)', 'function'),

            # Angle Conversion
            CompletionItem('radians()', 'Convert degrees to radians', 'radians($0)', 'function'),
            CompletionItem('degrees()', 'Convert radians to degrees', 'degrees($0)', 'function'),

            # Advanced Math
            CompletionItem('exp()', 'Exponential function (e^x)', 'exp($0)', 'function'),
            CompletionItem('log()', 'Natural logarithm', 'log($0)', 'function'),
            CompletionItem('log10()', 'Base-10 logarithm', 'log10($0)', 'function'),
            CompletionItem('ceil()', 'Round up to nearest integer', 'ceil($0)', 'function'),
            CompletionItem('floor()', 'Round down to nearest integer', 'floor($0)', 'function'),
            CompletionItem('round()', 'Round to nearest integer', 'round($0)', 'function'),
            CompletionItem('fmod()', 'Floating-point remainder', 'fmod($0, $1)', 'function'),

            # Random
            CompletionItem('random()', 'Generate random number', 'random($0)', 'function'),
            CompletionItem('randomSeed()', 'Initialize random number generator', 'randomSeed($0)', 'function'),

            # Bits and Bytes
            CompletionItem('bit()', 'Get bit value', 'bit($0)', 'function'),
            CompletionItem('bitClear()', 'Clear bit', 'bitClear($0, $1)', 'function'),
            CompletionItem('bitRead()', 'Read bit', 'bitRead($0, $1)', 'function'),
            CompletionItem('bitSet()', 'Set bit', 'bitSet($0, $1)', 'function'),
            CompletionItem('bitWrite()', 'Write bit', 'bitWrite($0, $1, $2)', 'function'),
            CompletionItem('highByte()', 'Get high byte', 'highByte($0)', 'function'),
            CompletionItem('lowByte()', 'Get low byte', 'lowByte($0)', 'function'),

            # Interrupts
            CompletionItem('attachInterrupt()', 'Attach interrupt handler', 'attachInterrupt(digitalPinToInterrupt($0), ISR, RISING)', 'function'),
            CompletionItem('detachInterrupt()', 'Detach interrupt handler', 'detachInterrupt(digitalPinToInterrupt($0))', 'function'),
            CompletionItem('interrupts()', 'Enable interrupts', 'interrupts()', 'function'),
            CompletionItem('noInterrupts()', 'Disable interrupts', 'noInterrupts()', 'function'),

            # Advanced I/O
            CompletionItem('tone()', 'Generate tone on pin', 'tone($0, frequency)', 'function'),
            CompletionItem('noTone()', 'Stop tone on pin', 'noTone($0)', 'function'),
            CompletionItem('shiftOut()', 'Shift out data', 'shiftOut($0, clockPin, bitOrder, value)', 'function'),
            CompletionItem('shiftIn()', 'Shift in data', 'shiftIn($0, clockPin, bitOrder)', 'function'),
            CompletionItem('pulseIn()', 'Measure pulse duration (microseconds)', 'pulseIn($0, state)', 'function'),
            CompletionItem('pulseInLong()', 'Measure long pulse duration (microseconds)', 'pulseInLong($0, state)', 'function'),

            # Utility Functions
            CompletionItem('yield()', 'Pass control to other tasks', 'yield()', 'function'),
            CompletionItem('sizeof()', 'Get size of variable or type', 'sizeof($0)', 'function'),
            CompletionItem('digitalPinToInterrupt()', 'Convert pin number to interrupt', 'digitalPinToInterrupt($0)', 'function'),

            # Structure snippets
            CompletionItem('setup()', 'Setup function (runs once)', 'void setup() {\n  $0\n}', 'snippet'),
            CompletionItem('loop()', 'Loop function (runs repeatedly)', 'void loop() {\n  $0\n}', 'snippet'),
            CompletionItem('if', 'If statement with else', 'if ($0) {\n  \n} else {\n  \n}', 'keyword'),
            CompletionItem('for', 'For loop', 'for (int i = 0; i < $0; i++) {\n  \n}', 'keyword'),
            CompletionItem('while', 'While loop', 'while ($0) {\n  \n}', 'keyword'),
            CompletionItem('do', 'Do-while loop', 'do {\n  $0\n} while ();', 'keyword'),
            CompletionItem('switch', 'Switch statement', 'switch ($0) {\n  case value:\n    break;\n  default:\n    break;\n}', 'keyword'),

            # Common Arduino patterns
            CompletionItem('blink', 'Blink LED pattern', 'digitalWrite($0, HIGH);\ndelay(1000);\ndigitalWrite($0, LOW);\ndelay(1000);', 'snippet'),
            CompletionItem('button', 'Read button with debounce', 'int buttonState = digitalRead($0);\nif (buttonState == HIGH) {\n  // Button pressed\n}', 'snippet'),
            CompletionItem('analogMap', 'Map analog reading', 'int value = analogRead($0);\nvalue = map(value, 0, 1023, 0, 255);', 'snippet'),
            CompletionItem('serialInit', 'Initialize Serial', 'Serial.begin(9600);\nwhile (!Serial) {\n  ; // Wait for serial port\n}', 'snippet'),
            CompletionItem('serialRead', 'Read from Serial', 'if (Serial.available() > 0) {\n  char data = Serial.read();\n  $0\n}', 'snippet'),
            CompletionItem('millis', 'Non-blocking delay with millis', 'unsigned long previousMillis = 0;\nconst long interval = 1000;\n\nunsigned long currentMillis = millis();\nif (currentMillis - previousMillis >= interval) {\n  previousMillis = currentMillis;\n  $0\n}', 'snippet'),
            CompletionItem('interrupt', 'Attach interrupt', 'attachInterrupt(digitalPinToInterrupt($0), ISR_name, RISING);', 'snippet'),
            CompletionItem('pwm', 'PWM output', 'pinMode($0, OUTPUT);\nanalogWrite($0, 128); // 0-255', 'snippet'),
            CompletionItem('servo', 'Servo control pattern', '#include <Servo.h>\nServo myServo;\n\nvoid setup() {\n  myServo.attach($0);\n}\n\nvoid loop() {\n  myServo.write(90);\n}', 'snippet'),

            # LCD patterns
            CompletionItem('lcd', 'LCD initialization pattern', '#include <LiquidCrystal.h>\nLiquidCrystal lcd(12, 11, 5, 4, 3, 2);\n\nvoid setup() {\n  lcd.begin(16, 2);\n  lcd.print("$0");\n}', 'snippet'),
            CompletionItem('lcdPrint', 'Print to LCD with cursor', 'lcd.setCursor(0, 0);\nlcd.print("$0");', 'snippet'),

            # SD Card patterns
            CompletionItem('sdInit', 'Initialize SD card', '#include <SD.h>\nconst int chipSelect = 10;\n\nvoid setup() {\n  Serial.begin(9600);\n  if (!SD.begin(chipSelect)) {\n    Serial.println("SD init failed!");\n    return;\n  }\n  Serial.println("SD initialized");\n}', 'snippet'),
            CompletionItem('sdWrite', 'Write to SD card file', 'File myFile = SD.open("$0.txt", FILE_WRITE);\nif (myFile) {\n  myFile.println("Data");\n  myFile.close();\n}', 'snippet'),
            CompletionItem('sdRead', 'Read from SD card file', 'File myFile = SD.open("$0.txt");\nif (myFile) {\n  while (myFile.available()) {\n    Serial.write(myFile.read());\n  }\n  myFile.close();\n}', 'snippet'),

            # Servo patterns
            CompletionItem('servoSweep', 'Servo sweep pattern', 'for (int pos = 0; pos <= 180; pos++) {\n  myServo.write(pos);\n  delay(15);\n}\nfor (int pos = 180; pos >= 0; pos--) {\n  myServo.write(pos);\n  delay(15);\n}', 'snippet'),

            # WiFi patterns
            CompletionItem('wifiConnect', 'WiFi connection pattern', '#include <WiFi.h>\nconst char* ssid = "$0";\nconst char* password = "$1";\n\nvoid setup() {\n  Serial.begin(115200);\n  WiFi.begin(ssid, password);\n  while (WiFi.status() != WL_CONNECTED) {\n    delay(500);\n    Serial.print(".");\n  }\n  Serial.println("\\nConnected!");\n  Serial.println(WiFi.localIP());\n}', 'snippet'),

            # Sensor patterns
            CompletionItem('tempSensor', 'Temperature sensor reading (TMP36)', 'int reading = analogRead($0);\nfloat voltage = reading * 5.0 / 1024.0;\nfloat temperatureC = (voltage - 0.5) * 100.0;', 'snippet'),
            CompletionItem('ultrasonic', 'Ultrasonic sensor HC-SR04', 'digitalWrite(trigPin, LOW);\ndelayMicroseconds(2);\ndigitalWrite(trigPin, HIGH);\ndelayMicroseconds(10);\ndigitalWrite(trigPin, LOW);\nlong duration = pulseIn(echoPin, HIGH);\nfloat distance = duration * 0.034 / 2;', 'snippet'),

            # State machine pattern
            CompletionItem('stateMachine', 'Simple state machine', 'enum State { STATE_IDLE, STATE_RUNNING, STATE_STOPPED };\nState currentState = STATE_IDLE;\n\nvoid loop() {\n  switch (currentState) {\n    case STATE_IDLE:\n      // Idle logic\n      break;\n    case STATE_RUNNING:\n      // Running logic\n      break;\n    case STATE_STOPPED:\n      // Stopped logic\n      break;\n  }\n}', 'snippet'),
        ]

        # Constants
        self.completions['constants'] = [
            CompletionItem('HIGH', 'Logic level HIGH (5V)', 'HIGH', 'constant'),
            CompletionItem('LOW', 'Logic level LOW (0V)', 'LOW', 'constant'),
            CompletionItem('INPUT', 'Pin mode: input', 'INPUT', 'constant'),
            CompletionItem('OUTPUT', 'Pin mode: output', 'OUTPUT', 'constant'),
            CompletionItem('INPUT_PULLUP', 'Pin mode: input with internal pullup', 'INPUT_PULLUP', 'constant'),
            CompletionItem('LED_BUILTIN', 'Built-in LED pin (usually 13)', 'LED_BUILTIN', 'constant'),
            CompletionItem('true', 'Boolean true', 'true', 'constant'),
            CompletionItem('false', 'Boolean false', 'false', 'constant'),

            # Analog pins
            CompletionItem('A0', 'Analog input pin 0', 'A0', 'constant'),
            CompletionItem('A1', 'Analog input pin 1', 'A1', 'constant'),
            CompletionItem('A2', 'Analog input pin 2', 'A2', 'constant'),
            CompletionItem('A3', 'Analog input pin 3', 'A3', 'constant'),
            CompletionItem('A4', 'Analog input pin 4 (I2C SDA)', 'A4', 'constant'),
            CompletionItem('A5', 'Analog input pin 5 (I2C SCL)', 'A5', 'constant'),
            CompletionItem('A6', 'Analog input pin 6', 'A6', 'constant'),
            CompletionItem('A7', 'Analog input pin 7', 'A7', 'constant'),

            # Math constants
            CompletionItem('PI', 'Pi constant (3.14159...)', 'PI', 'constant'),
            CompletionItem('HALF_PI', 'Half Pi constant', 'HALF_PI', 'constant'),
            CompletionItem('TWO_PI', 'Two Pi constant', 'TWO_PI', 'constant'),

            # Interrupt modes
            CompletionItem('RISING', 'Interrupt on rising edge', 'RISING', 'constant'),
            CompletionItem('FALLING', 'Interrupt on falling edge', 'FALLING', 'constant'),
            CompletionItem('CHANGE', 'Interrupt on any change', 'CHANGE', 'constant'),
            CompletionItem('LOW', 'Interrupt when pin is LOW', 'LOW', 'constant'),

            # Serial constants
            CompletionItem('SERIAL_5N1', 'Serial config: 5 data, no parity, 1 stop', 'SERIAL_5N1', 'constant'),
            CompletionItem('SERIAL_6N1', 'Serial config: 6 data, no parity, 1 stop', 'SERIAL_6N1', 'constant'),
            CompletionItem('SERIAL_7N1', 'Serial config: 7 data, no parity, 1 stop', 'SERIAL_7N1', 'constant'),
            CompletionItem('SERIAL_8N1', 'Serial config: 8 data, no parity, 1 stop (default)', 'SERIAL_8N1', 'constant'),

            # Analog reference
            CompletionItem('DEFAULT', 'Default analog reference (5V)', 'DEFAULT', 'constant'),
            CompletionItem('INTERNAL', 'Internal analog reference', 'INTERNAL', 'constant'),
            CompletionItem('EXTERNAL', 'External analog reference', 'EXTERNAL', 'constant'),

            # SPI constants
            CompletionItem('MSBFIRST', 'SPI bit order: most significant bit first', 'MSBFIRST', 'constant'),
            CompletionItem('LSBFIRST', 'SPI bit order: least significant bit first', 'LSBFIRST', 'constant'),
            CompletionItem('SPI_MODE0', 'SPI mode 0', 'SPI_MODE0', 'constant'),
            CompletionItem('SPI_MODE1', 'SPI mode 1', 'SPI_MODE1', 'constant'),
            CompletionItem('SPI_MODE2', 'SPI mode 2', 'SPI_MODE2', 'constant'),
            CompletionItem('SPI_MODE3', 'SPI mode 3', 'SPI_MODE3', 'constant'),

            # WiFi constants
            CompletionItem('WL_CONNECTED', 'WiFi connected status', 'WL_CONNECTED', 'constant'),
            CompletionItem('WL_DISCONNECTED', 'WiFi disconnected status', 'WL_DISCONNECTED', 'constant'),
            CompletionItem('WL_IDLE_STATUS', 'WiFi idle status', 'WL_IDLE_STATUS', 'constant'),
            CompletionItem('WL_NO_SSID_AVAIL', 'WiFi SSID not available', 'WL_NO_SSID_AVAIL', 'constant'),
            CompletionItem('WL_CONNECT_FAILED', 'WiFi connection failed', 'WL_CONNECT_FAILED', 'constant'),
            CompletionItem('WIFI_STA', 'WiFi station mode', 'WIFI_STA', 'constant'),
            CompletionItem('WIFI_AP', 'WiFi access point mode', 'WIFI_AP', 'constant'),
            CompletionItem('WIFI_AP_STA', 'WiFi station + AP mode', 'WIFI_AP_STA', 'constant'),

            # SD Card constants
            CompletionItem('FILE_READ', 'Open file for reading', 'FILE_READ', 'constant'),
            CompletionItem('FILE_WRITE', 'Open file for writing', 'FILE_WRITE', 'constant'),

            # Data type size constants
            CompletionItem('DEC', 'Decimal format', 'DEC', 'constant'),
            CompletionItem('HEX', 'Hexadecimal format', 'HEX', 'constant'),
            CompletionItem('OCT', 'Octal format', 'OCT', 'constant'),
            CompletionItem('BIN', 'Binary format', 'BIN', 'constant'),
        ]

    def get_completions(self, context=None):
        """Get completions for a given context

        Args:
            context: String like 'Serial', 'Wire', etc. or None for global

        Returns:
            List of CompletionItem objects
        """
        if context and context in self.completions:
            return self.completions[context]
        elif context is None:
            # Return all global completions
            result = []
            result.extend(self.completions.get('global', []))
            result.extend(self.completions.get('constants', []))
            return result
        else:
            return []


class CompletionListModel(QAbstractListModel):
    """Custom model for completion items with descriptions"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []

    def set_items(self, items):
        """Set completion items"""
        self.beginResetModel()
        self.items = items
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.items):
            return None

        item = self.items[index.row()]

        if role == Qt.DisplayRole:
            # Return just the completion text for filtering
            return item.text
        elif role == Qt.UserRole:
            # Store the full item for later use
            return item

        return None


class CompletionDelegate(QStyledItemDelegate):
    """Custom delegate to render completions with descriptions"""

    def paint(self, painter, option, index):
        """Custom paint for completion items"""
        painter.save()

        # Get the completion item
        item = index.data(Qt.UserRole)
        if not item:
            super().paint(painter, option, index)
            painter.restore()
            return

        # Set background color
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor("#094771"))  # Selected blue
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, QColor("#2A2D2E"))  # Hover gray
        else:
            painter.fillRect(option.rect, QColor("#1E1E1E"))  # Background

        # Draw icon based on type
        icon_rect = QRect(option.rect.left() + 5, option.rect.top() + 5, 16, 16)
        icon_color = {
            'function': QColor("#DCDCAA"),  # Yellow
            'keyword': QColor("#569CD6"),   # Blue
            'type': QColor("#4EC9B0"),      # Teal
            'constant': QColor("#B5CEA8"),  # Light green
            'snippet': QColor("#C586C0"),   # Purple
        }.get(item.type, QColor("#808080"))

        painter.setBrush(icon_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(icon_rect)

        # Draw completion text (bold)
        text_rect = QRect(option.rect.left() + 28, option.rect.top(),
                         option.rect.width() // 2 - 28, option.rect.height())
        painter.setPen(QColor("#FFFFFF"))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, item.text)

        # Draw description (normal, gray)
        if item.description:
            desc_rect = QRect(option.rect.left() + option.rect.width() // 2,
                            option.rect.top(),
                            option.rect.width() // 2 - 5,
                            option.rect.height())
            painter.setPen(QColor("#858585"))
            font.setBold(False)
            font.setItalic(True)
            painter.setFont(font)

            # Add arrow separator
            painter.drawText(desc_rect, Qt.AlignLeft | Qt.AlignVCenter, f"→ {item.description}")

        painter.restore()

    def sizeHint(self, option, index):
        """Return size hint for completion item"""
        return QSize(option.rect.width(), 26)


class CodeEditor(QPlainTextEdit):
    """
    Advanced code editor with:
    - Line numbers
    - Syntax highlighting
    - Auto-indentation
    - Code completion hints
    - Error squiggles
    - Inline suggestions (tips, best practices)
    - Git diff markers
    - Code folding
    - Minimap
    """

    # Signal emitted when user clicks on a function name
    function_clicked = Signal(str, str)  # function_name, full_context

    def __init__(self, parent=None, file_path=None):
        super().__init__(parent)

        self.file_path = file_path
        self.errors = []  # List of (line_number, message) tuples
        self.suggestions = []  # List of Suggestion objects
        self.contextual_help_service = ContextualHelpService()
        self.inline_hints: List[InlineHint] = []
        self._editor_state: Dict[str, bool] = {"serial_monitor_open": False}
        self.folded_blocks = set()  # Set of line numbers that are folded
        self.git_changes = {}  # {line_number: 'added'|'modified'|'deleted'}

        # Initialize suggestion analyzer
        self.suggestion_analyzer = SuggestionAnalyzer()

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

    def set_serial_monitor_open(self, is_open: bool):
        """Update the cached Serial Monitor state for contextual help."""

        if self._editor_state.get("serial_monitor_open") == bool(is_open):
            return

        self._editor_state["serial_monitor_open"] = bool(is_open)
        # Re-run analysis so Serial hints update immediately
        self.check_errors()

    def setup_autocomplete(self):
        """Setup code completion with descriptions"""
        # Create completion database
        self.completion_db = CompletionDatabase()

        # Create custom model and delegate
        self.completion_model = CompletionListModel(self)
        self.completion_delegate = CompletionDelegate(self)

        # Setup completer
        self.completer = QCompleter(self)
        self.completer.setModel(self.completion_model)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)

        # Set custom delegate for rendering
        self.completer.popup().setItemDelegate(self.completion_delegate)

        # Style the popup
        self.completer.popup().setStyleSheet("""
            QListView {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #3E3E42;
                outline: none;
                selection-background-color: #094771;
            }
            QListView::item {
                padding: 3px;
                border: none;
            }
        """)

        # Connect completion signal
        self.completer.activated.connect(self.insert_completion)

        # Load default global completions
        self.update_completions(None)

    def update_completions(self, context):
        """Update completion model with items for given context

        Args:
            context: String like 'Serial', 'Wire', etc. or None for global
        """
        completions = self.completion_db.get_completions(context)
        self.completion_model.set_items(completions)

    def detect_completion_context(self):
        """Detect context for auto-completion (e.g., 'Serial', 'Wire')

        Returns:
            Tuple of (context, prefix) where:
            - context is the object name (e.g., 'Serial') or None for global
            - prefix is the text to complete
        """
        cursor = self.textCursor()
        cursor.select(QTextCursor.LineUnderCursor)
        line = cursor.selectedText()

        # Get position in line
        pos_in_line = self.textCursor().positionInBlock()

        # Get text before cursor in current line
        text_before = line[:pos_in_line]

        # Check for object method access (e.g., "Serial.pr")
        match = re.search(r'(\w+)\.(\w*)$', text_before)
        if match:
            object_name = match.group(1)
            prefix = match.group(2)
            return (object_name, prefix)

        # Global context - get word under cursor
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        prefix = cursor.selectedText()

        return (None, prefix)

    def insert_completion(self, completion_text):
        """Insert selected completion"""
        # Get the current model index
        popup = self.completer.popup()
        index = popup.currentIndex()

        # Get the completion item
        item = index.data(Qt.UserRole)
        if not item:
            # Fallback to simple text insertion
            tc = self.textCursor()
            extra = len(completion_text) - len(self.completer.completionPrefix())
            tc.movePosition(QTextCursor.Left)
            tc.movePosition(QTextCursor.EndOfWord)
            tc.insertText(completion_text[-extra:])
            self.setTextCursor(tc)
            return

        # Remove the prefix that's already typed
        tc = self.textCursor()
        prefix_len = len(self.completer.completionPrefix())

        if prefix_len > 0:
            tc.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, prefix_len)
            tc.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, prefix_len)
            tc.removeSelectedText()

        # Insert the completion text (without snippet placeholders for now)
        # Remove $0 placeholders from snippet
        insert_text = item.text
        tc.insertText(insert_text)
        self.setTextCursor(tc)

    def on_cursor_changed(self):
        """Handle cursor position changes"""
        self.highlight_current_line()

    def on_text_changed(self):
        """Handle text changes - trigger error checking"""
        self.error_check_timer.start(500)  # Check after 500ms of no typing

    def check_errors(self):
        """Check for basic syntax errors and suggestions"""
        self.errors.clear()
        self.suggestions.clear()
        text = self.toPlainText()
        lines = text.split('\n')

        # Run suggestion analysis
        self.suggestions = self.suggestion_analyzer.analyze(text)

        # Run contextual inline hint analysis
        cursor_position = self.textCursor().position()
        editor_state = dict(self._editor_state)
        self.inline_hints = self.contextual_help_service.analyze_context(
            cursor_position,
            text,
            editor_state=editor_state,
        )

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
            changes = calculate_git_changes(self.file_path, self.toPlainText())
        except Exception:
            return

        if changes is None:
            changes = {}

        self.git_changes = changes
        if hasattr(self, 'line_number_area'):
            self.line_number_area.update()
        self.viewport().update()

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

    def find_matching_brace(self, start_block):
        """Find the closing brace matching the opening brace in start_block"""
        brace_count = 0
        block = start_block

        while block.isValid():
            text = block.text()
            for char in text:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return block.blockNumber()
            block = block.next()

        return None

    def toggle_fold(self, line_num):
        """Toggle folding for a block starting at line_num"""
        block = self.document().findBlockByNumber(line_num)
        if not block.isValid() or '{' not in block.text():
            return

        # Find matching closing brace
        end_line = self.find_matching_brace(block)
        if end_line is None or end_line <= line_num:
            return

        # Toggle folding state
        if line_num in self.folded_blocks:
            # Unfold: show all blocks
            self.folded_blocks.remove(line_num)
            for i in range(line_num + 1, end_line + 1):
                b = self.document().findBlockByNumber(i)
                if b.isValid():
                    b.setVisible(True)
        else:
            # Fold: hide blocks between opening and closing brace
            self.folded_blocks.add(line_num)
            for i in range(line_num + 1, end_line + 1):
                b = self.document().findBlockByNumber(i)
                if b.isValid():
                    b.setVisible(False)

        # Update the document layout and viewport
        self.document().markContentsDirty(
            self.document().findBlockByNumber(line_num).position(),
            self.document().findBlockByNumber(end_line).position() if end_line else 0
        )
        self.viewport().update()
        self.update_line_number_area_width(0)

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
                self.toggle_fold(line_num)
                break

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    def line_number_area_width(self):
        """Calculate width needed for line numbers"""
        digits = len(str(max(1, self.blockCount())))
        # Extra space for git markers, fold indicators, and trailing space after number
        space = 15 + self.fontMetrics().horizontalAdvance('9' * digits + ' ')
        return space

    def update_line_number_area_width(self, _):
        """Update line number area width"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
        # Update the line number area's geometry to reflect the new width
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
                                               self.line_number_area_width(),
                                               cr.height()))

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
                painter.drawText(15, top, self.line_number_area_width() - 15,
                               self.fontMetrics().height(),
                               Qt.AlignRight, number + " ")

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        """Highlight the current line and show error squiggles and suggestions"""
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

        # Add suggestion decorations
        for suggestion in self.suggestions:
            block = self.document().findBlockByNumber(suggestion.line_number - 1)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.cursor = QTextCursor(block)

                # If column and length are specified, highlight specific text
                if suggestion.length > 0:
                    selection.cursor.setPosition(block.position() + suggestion.column)
                    selection.cursor.setPosition(
                        block.position() + suggestion.column + suggestion.length,
                        QTextCursor.KeepAnchor
                    )
                else:
                    # Otherwise highlight the whole line
                    selection.cursor.select(QTextCursor.LineUnderCursor)

                # Different colors for different severity levels
                suggestion_format = QTextCharFormat()
                suggestion_format.setUnderlineStyle(QTextCharFormat.DotLine)  # Dotted line for suggestions

                if suggestion.severity == 'tip':
                    # Teal/cyan for tips (like the light bulb icon)
                    suggestion_format.setUnderlineColor(QColor("#4EC9B0"))
                elif suggestion.severity == 'info':
                    # Blue for info
                    suggestion_format.setUnderlineColor(QColor("#569CD6"))
                elif suggestion.severity == 'warning':
                    # Orange for warnings
                    suggestion_format.setUnderlineColor(QColor("#CE9178"))

                selection.format = suggestion_format
                extra_selections.append(selection)

        # Add contextual inline hint decorations
        for hint in self.inline_hints:
            block = self.document().findBlockByNumber(hint.line - 1)
            if not block.isValid():
                continue

            selection = QTextEdit.ExtraSelection()
            selection.cursor = QTextCursor(block)
            selection.cursor.select(QTextCursor.LineUnderCursor)

            hint_format = QTextCharFormat()
            hint_format.setUnderlineStyle(QTextCharFormat.DashUnderline)

            if hint.severity == "warning":
                hint_format.setUnderlineColor(QColor("#F2C744"))
            elif hint.severity == "tip":
                hint_format.setUnderlineColor(QColor("#4EC9B0"))
            else:
                hint_format.setUnderlineColor(QColor("#569CD6"))

            selection.format = hint_format
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, event):
        """Handle key press for auto-indentation, autocomplete, and smart completions"""
        # Handle autocomplete popup navigation
        if self.completer.popup().isVisible():
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape, Qt.Key_Tab):
                event.ignore()
                return

        # Handle smart bracket/quote auto-closing
        cursor = self.textCursor()
        char = event.text()

        # Auto-close brackets, braces, parentheses, and quotes
        closing_chars = {
            '(': ')',
            '[': ']',
            '{': '}',
            '"': '"',
            "'": "'"
        }

        if char in closing_chars:
            # Check if we should auto-close (not already followed by closing char)
            next_char = self.get_next_char()
            # Only auto-close quotes if not already in a string and not followed by same quote
            if char in ['"', "'"]:
                if next_char != char:
                    super().keyPressEvent(event)
                    self.insertPlainText(closing_chars[char])
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.Left)
                    self.setTextCursor(cursor)
                    return
            else:
                super().keyPressEvent(event)
                self.insertPlainText(closing_chars[char])
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.Left)
                self.setTextCursor(cursor)
                return

        # Handle smart code block completion for 'if', 'else', 'for', 'while'
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()
            stripped = text.strip()

            # Count leading spaces/tabs
            indent = len(text) - len(text.lstrip())
            indent_str = text[:indent]

            # Smart if/else completion
            if stripped == 'if' or stripped.startswith('if '):
                # Complete if statement with condition and braces
                super().keyPressEvent(event)
                if '(' not in stripped:
                    self.insertPlainText(indent_str + "if () {\n")
                    self.insertPlainText(indent_str + "  \n")
                    self.insertPlainText(indent_str + "} else {\n")
                    self.insertPlainText(indent_str + "  \n")
                    self.insertPlainText(indent_str + "}")
                    # Move cursor to condition
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor, 4)
                    cursor.movePosition(QTextCursor.EndOfLine)
                    cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 4)
                    self.setTextCursor(cursor)
                elif '{' not in stripped:
                    self.insertPlainText(indent_str + "  \n")
                    self.insertPlainText(indent_str + "} else {\n")
                    self.insertPlainText(indent_str + "  \n")
                    self.insertPlainText(indent_str + "}")
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor, 3)
                    cursor.movePosition(QTextCursor.EndOfLine)
                    self.setTextCursor(cursor)
                else:
                    self.insertPlainText(indent_str + "  ")
                return

            # Smart else completion
            elif stripped == 'else' or stripped == '} else':
                super().keyPressEvent(event)
                self.insertPlainText(indent_str + "  \n")
                self.insertPlainText(indent_str + "}")
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.Up)
                cursor.movePosition(QTextCursor.EndOfLine)
                self.setTextCursor(cursor)
                return

            # Smart for loop completion
            elif stripped == 'for' or stripped.startswith('for '):
                super().keyPressEvent(event)
                if '(' not in stripped:
                    self.insertPlainText(indent_str + "for (int i = 0; i < 10; i++) {\n")
                    self.insertPlainText(indent_str + "  \n")
                    self.insertPlainText(indent_str + "}")
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor, 2)
                    cursor.movePosition(QTextCursor.EndOfLine)
                    cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 14)
                    # Select the "10" for easy replacement
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 2)
                    self.setTextCursor(cursor)
                elif '{' not in stripped:
                    self.insertPlainText(indent_str + "  \n")
                    self.insertPlainText(indent_str + "}")
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.Up)
                    cursor.movePosition(QTextCursor.EndOfLine)
                    self.setTextCursor(cursor)
                else:
                    self.insertPlainText(indent_str + "  ")
                return

            # Smart while loop completion
            elif stripped == 'while' or stripped.startswith('while '):
                super().keyPressEvent(event)
                if '(' not in stripped:
                    self.insertPlainText(indent_str + "while () {\n")
                    self.insertPlainText(indent_str + "  \n")
                    self.insertPlainText(indent_str + "}")
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor, 2)
                    cursor.movePosition(QTextCursor.EndOfLine)
                    cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, 4)
                    self.setTextCursor(cursor)
                elif '{' not in stripped:
                    self.insertPlainText(indent_str + "  \n")
                    self.insertPlainText(indent_str + "}")
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.Up)
                    cursor.movePosition(QTextCursor.EndOfLine)
                    self.setTextCursor(cursor)
                else:
                    self.insertPlainText(indent_str + "  ")
                return

            # Standard newline with auto-indentation
            else:
                # Check if line ends with { to add extra indent
                extra_indent = ""
                if text.rstrip().endswith('{'):
                    extra_indent = "  "  # 2 spaces

                # Insert newline and indentation
                super().keyPressEvent(event)
                self.insertPlainText(indent_str + extra_indent)
                return

        # Call parent to insert the character
        super().keyPressEvent(event)

        # Detect completion context
        context, prefix = self.detect_completion_context()

        # Update completions based on context
        if context != getattr(self, '_last_completion_context', None):
            self.update_completions(context)
            self._last_completion_context = context

        # Trigger autocomplete if we have enough characters or just typed '.'
        # IMPORTANT: Show popup even with empty prefix after '.'
        if event.text() == '.':
            # Just typed dot - show all methods for this object
            self.completer.setCompletionPrefix("")
            popup = self.completer.popup()
            popup.setMinimumWidth(600)

            # Make sure we have items to show
            if self.completion_model.rowCount() > 0:
                popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
                cr = self.cursorRect()
                cr.setWidth(600)
                self.completer.complete(cr)
            else:
                popup.hide()
        elif len(prefix) >= 2:
            # Filter completions by prefix
            self.completer.setCompletionPrefix(prefix)
            popup = self.completer.popup()
            popup.setMinimumWidth(600)

            if self.completion_model.rowCount() > 0:
                popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
                cr = self.cursorRect()
                cr.setWidth(600)
                self.completer.complete(cr)
            else:
                popup.hide()
        elif len(prefix) == 0 and context:
            # Context but no prefix - hide popup
            self.completer.popup().hide()
        else:
            self.completer.popup().hide()

    def get_next_char(self):
        """Get the character immediately after the cursor"""
        cursor = self.textCursor()
        pos = cursor.position()
        text = self.toPlainText()
        if pos < len(text):
            return text[pos]
        return ""

    def mouseMoveEvent(self, event):
        """Show error and suggestion tooltips on hover"""
        cursor = self.cursorForPosition(event.pos())
        block_num = cursor.blockNumber() + 1

        tooltip_shown = False

        # Check if hovering over an error line (errors take priority)
        for line_num, message in self.errors:
            if line_num == block_num:
                QToolTip.showText(event.globalPos(), message, self)
                tooltip_shown = True
                break

        # If no error, check for suggestions
        if not tooltip_shown:
            for suggestion in self.suggestions:
                if suggestion.line_number == block_num:
                    QToolTip.showText(event.globalPos(), suggestion.message, self)
                    tooltip_shown = True
                    break

        # If still no tooltip, surface contextual inline hints
        if not tooltip_shown:
            for hint in self.inline_hints:
                if hint.line == block_num:
                    QToolTip.showText(event.globalPos(), hint.message, self)
                    tooltip_shown = True
                    break

        # Hide tooltip if not hovering over error or suggestion
        if not tooltip_shown:
            QToolTip.hideText()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """Detect clicks on function names for context panel"""
        # Only handle left clicks
        if event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            function_name = self.get_function_name_at_cursor(cursor)

            if function_name:
                # Get the full line context
                cursor_line = cursor
                cursor_line.select(QTextCursor.LineUnderCursor)
                full_context = cursor_line.selectedText().strip()

                # Emit signal for context panel
                self.function_clicked.emit(function_name, full_context)

        super().mousePressEvent(event)

    def get_function_name_at_cursor(self, cursor):
        """Get Arduino function name at cursor position, including dot notation

        Returns function name like 'Serial.begin', 'pinMode', 'digitalWrite', etc.
        Returns None if cursor is not on a recognized function.
        """
        # Get the position in the document
        position = cursor.position()
        text = self.toPlainText()

        # Find word boundaries
        # Move backward to find start
        start = position
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] in '._'):
            start -= 1

        # Move forward to find end
        end = position
        while end < len(text) and (text[end].isalnum() or text[end] in '._'):
            end += 1

        # Extract the word
        word = text[start:end]

        # Check if it looks like a function (followed by '(') or is a known Arduino identifier
        if end < len(text):
            # Skip whitespace
            next_pos = end
            while next_pos < len(text) and text[next_pos].isspace():
                next_pos += 1

            # Check if followed by '('
            if next_pos < len(text) and text[next_pos] == '(':
                return word

        # Also check common Arduino patterns without requiring '('
        # This handles cases where user clicks on 'Serial' in 'Serial.begin'
        if '.' in word:
            # For things like 'Serial.begin', 'Wire.write', etc.
            return word

        # Check if it's part of a qualified name (e.g., cursor is on 'Serial' in 'Serial.begin')
        if end < len(text) and text[end] == '.':
            # Extend to include the method name
            method_end = end + 1
            while method_end < len(text) and (text[method_end].isalnum() or text[method_end] == '_'):
                method_end += 1
            return text[start:method_end]

        # Check if word is in the comprehensive database (Arduino functions, C++ keywords, etc.)
        # This allows clicking on any documented language element
        if word and get_api_info(word):
            return word

        return None

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
