"""
Real-time Status Display Panel
Shows live memory usage estimation as code is written
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGroupBox, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import re


class MemoryBar(QWidget):
    """Custom memory usage bar with label and detailed info"""

    def __init__(self, label="", parent=None):
        super().__init__(parent)
        self.label_text = label
        self.used_bytes = 0
        self.total_bytes = 0
        self.usage_percent = 0
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Title label
        self.title_label = QLabel(self.label_text)
        self.title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(self.title_label)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setMinimumHeight(25)
        layout.addWidget(self.progress)

        # Details label (bytes used / total)
        self.details_label = QLabel("0 / 0 bytes")
        self.details_label.setFont(QFont("Consolas", 9))
        self.details_label.setStyleSheet("color: #888;")
        layout.addWidget(self.details_label)

    def update_usage(self, used_bytes, total_bytes):
        """Update memory usage"""
        self.used_bytes = used_bytes
        self.total_bytes = total_bytes

        if total_bytes > 0:
            self.usage_percent = (used_bytes * 100) / total_bytes
        else:
            self.usage_percent = 0

        self.progress.setValue(int(self.usage_percent))

        # Format bytes nicely
        used_str = self.format_bytes(used_bytes)
        total_str = self.format_bytes(total_bytes)
        self.details_label.setText(f"{used_str} / {total_str}")

        # Color code based on usage
        if self.usage_percent < 50:
            color = "#4CAF50"  # Green
        elif self.usage_percent < 75:
            color = "#FFC107"  # Yellow/Orange
        elif self.usage_percent < 90:
            color = "#FF9800"  # Orange
        else:
            color = "#FF5252"  # Red

        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #2b2b2b;
                color: white;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)

    def format_bytes(self, bytes_val):
        """Format bytes into human-readable format"""
        if bytes_val < 1024:
            return f"{bytes_val} bytes"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        else:
            return f"{bytes_val / (1024 * 1024):.1f} MB"


class CodeAnalyzer:
    """Analyzes Arduino code to estimate memory usage"""

    @staticmethod
    def estimate_flash_usage(code_text):
        """Estimate Flash/Program storage usage from code

        This is a simplified estimation based on:
        - Function count and complexity
        - String literals
        - Global variables (const/PROGMEM)
        - Included libraries (estimated)
        """
        if not code_text.strip():
            return 0

        # Base overhead for Arduino runtime
        base_overhead = 1500  # bytes

        # Count functions (rough estimate: 100-200 bytes per function)
        function_pattern = r'\w+\s+\w+\s*\([^)]*\)\s*\{'
        functions = re.findall(function_pattern, code_text)
        function_bytes = len(functions) * 150

        # Count string literals (stored in Flash)
        string_pattern = r'"([^"\\]|\\.)*"'
        strings = re.findall(string_pattern, code_text)
        string_bytes = sum(len(s) for s in strings)

        # Estimate based on code complexity (LOC)
        lines = [line.strip() for line in code_text.split('\n')
                 if line.strip() and not line.strip().startswith('//')]
        code_lines = len(lines)
        complexity_bytes = code_lines * 15  # Rough estimate: 15 bytes per LOC

        # Library overhead estimation
        library_bytes = 0
        if 'Serial.begin' in code_text:
            library_bytes += 1000  # Serial library
        if 'Wire.' in code_text or '#include <Wire.h>' in code_text:
            library_bytes += 1500  # Wire (I2C)
        if 'SPI.' in code_text or '#include <SPI.h>' in code_text:
            library_bytes += 800  # SPI
        if 'Servo' in code_text:
            library_bytes += 1200  # Servo library
        if 'LCD' in code_text or 'lcd.' in code_text:
            library_bytes += 2000  # LCD library

        total = base_overhead + function_bytes + string_bytes + complexity_bytes + library_bytes

        return int(total)

    @staticmethod
    def estimate_ram_usage(code_text):
        """Estimate Dynamic Memory (RAM) usage from code

        This is based on:
        - Global variables
        - Static variables
        - String buffers
        - Arrays
        """
        if not code_text.strip():
            return 0

        # Base overhead for Arduino runtime and stack
        base_overhead = 200  # bytes

        total_ram = base_overhead

        # Parse global variables
        # Pattern for variable declarations
        var_patterns = [
            r'\bint\s+(\w+)\s*(?:=|;)',          # int
            r'\blong\s+(\w+)\s*(?:=|;)',         # long
            r'\bfloat\s+(\w+)\s*(?:=|;)',        # float
            r'\bdouble\s+(\w+)\s*(?:=|;)',       # double
            r'\bchar\s+(\w+)\s*(?:=|;)',         # char
            r'\bbyte\s+(\w+)\s*(?:=|;)',         # byte
            r'\bbool\s+(\w+)\s*(?:=|;)',         # bool
            r'\bunsigned\s+int\s+(\w+)\s*(?:=|;)',  # unsigned int
            r'\bunsigned\s+long\s+(\w+)\s*(?:=|;)', # unsigned long
        ]

        # Type sizes (in bytes)
        type_sizes = {
            'int': 2, 'long': 4, 'float': 4, 'double': 4,
            'char': 1, 'byte': 1, 'bool': 1,
            'unsigned int': 2, 'unsigned long': 4
        }

        # Count simple variables
        for pattern in var_patterns:
            matches = re.findall(pattern, code_text)
            # Estimate based on type
            if 'int' in pattern:
                total_ram += len(matches) * 2
            elif 'long' in pattern or 'float' in pattern or 'double' in pattern:
                total_ram += len(matches) * 4
            else:
                total_ram += len(matches) * 1

        # Count arrays
        array_pattern = r'\b(\w+)\s+(\w+)\s*\[(\d+)\]'
        arrays = re.findall(array_pattern, code_text)
        for type_name, var_name, size in arrays:
            size_val = int(size)
            if 'int' in type_name:
                total_ram += size_val * 2
            elif 'long' in type_name or 'float' in type_name:
                total_ram += size_val * 4
            else:
                total_ram += size_val  # char/byte arrays

        # String buffers (char arrays from strings)
        string_pattern = r'char\s+\w+\s*\[\s*(\d+)\s*\]'
        string_buffers = re.findall(string_pattern, code_text)
        for size in string_buffers:
            total_ram += int(size)

        # Estimate stack usage based on function calls
        function_pattern = r'\w+\s+\w+\s*\([^)]*\)\s*\{'
        functions = re.findall(function_pattern, code_text)
        stack_estimate = len(functions) * 32  # Rough estimate for stack frames

        total_ram += stack_estimate

        # Serial buffer if Serial is used
        if 'Serial.begin' in code_text:
            total_ram += 128  # Serial RX/TX buffers

        return int(total_ram)


class StatusDisplay(QWidget):
    """Real-time status display showing memory usage as code is written"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Board specifications (will be updated when board changes)
        self.board_specs = {
            "flash_total": 32768,  # Default: Arduino Uno
            "ram_total": 2048,
        }

        self.current_code = ""
        self.analyzer = CodeAnalyzer()

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Title
        title = QLabel("⚡ Real-time Memory Usage")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Description
        desc = QLabel("Updates live as you write code")
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: #888;")
        desc.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Flash Memory Usage
        self.flash_bar = MemoryBar("Program Storage (Flash)")
        main_layout.addWidget(self.flash_bar)

        # RAM Usage
        self.ram_bar = MemoryBar("Dynamic Memory (RAM)")
        main_layout.addWidget(self.ram_bar)

        # Board info
        board_group = QGroupBox("Board Information")
        board_group.setFont(QFont("Arial", 9, QFont.Bold))
        board_layout = QVBoxLayout()

        self.board_name_label = QLabel("Board: Arduino Uno")
        self.board_name_label.setFont(QFont("Consolas", 9))
        board_layout.addWidget(self.board_name_label)

        board_group.setLayout(board_layout)
        main_layout.addWidget(board_group)

        # Info note
        info_label = QLabel(
            "💡 These are estimates based on code analysis.\n"
            "Compile to see actual memory usage."
        )
        info_label.setFont(QFont("Arial", 8))
        info_label.setStyleSheet("color: #666; padding: 10px; background: #1e1e1e; border-radius: 5px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        main_layout.addStretch()

        # Initialize with default board
        self.update_board("Arduino Uno")

    def update_from_code(self, code_text):
        """Update memory estimates from code analysis"""
        self.current_code = code_text

        # Estimate memory usage
        flash_used = self.analyzer.estimate_flash_usage(code_text)
        ram_used = self.analyzer.estimate_ram_usage(code_text)

        # Update displays
        self.flash_bar.update_usage(flash_used, self.board_specs["flash_total"])
        self.ram_bar.update_usage(ram_used, self.board_specs["ram_total"])

    def update_board(self, board_name):
        """Update board specifications"""
        # Board specifications database
        board_specs_db = {
            "Arduino Uno": {
                "flash": 32768,   # 32 KB
                "ram": 2048,      # 2 KB
            },
            "Arduino Mega 2560": {
                "flash": 262144,  # 256 KB
                "ram": 8192,      # 8 KB
            },
            "Arduino Nano": {
                "flash": 32768,   # 32 KB
                "ram": 2048,      # 2 KB
            },
            "Arduino Leonardo": {
                "flash": 32768,   # 32 KB
                "ram": 2560,      # 2.5 KB
            },
            "Arduino Pro Mini": {
                "flash": 32768,   # 32 KB
                "ram": 2048,      # 2 KB
            },
            "Arduino Micro": {
                "flash": 32768,   # 32 KB
                "ram": 2560,      # 2.5 KB
            },
            "Arduino Uno R4 WiFi": {
                "flash": 262144,  # 256 KB
                "ram": 32768,     # 32 KB
            },
            "Arduino Uno R4 Minima": {
                "flash": 262144,  # 256 KB
                "ram": 32768,     # 32 KB
            },
            "ESP32 Dev Module": {
                "flash": 4194304, # 4 MB
                "ram": 532480,    # 520 KB
            },
            "ESP8266 NodeMCU": {
                "flash": 4194304, # 4 MB
                "ram": 81920,     # 80 KB
            },
            "Arduino Due": {
                "flash": 524288,  # 512 KB
                "ram": 98304,     # 96 KB
            }
        }

        # Get specs for the board or use defaults
        specs = board_specs_db.get(board_name, {
            "flash": 32768,
            "ram": 2048
        })

        self.board_specs = {
            "flash_total": specs["flash"],
            "ram_total": specs["ram"]
        }

        # Update board name display
        self.board_name_label.setText(f"Board: {board_name}")

        # Re-analyze current code with new board specs
        if self.current_code:
            self.update_from_code(self.current_code)
        else:
            # Reset displays
            self.flash_bar.update_usage(0, self.board_specs["flash_total"])
            self.ram_bar.update_usage(0, self.board_specs["ram_total"])
