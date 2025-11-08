"""
Problems Panel for Arduino IDE
Displays compilation errors, warnings, and diagnostics
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon


class ProblemsPanel(QWidget):
    """Panel for displaying code problems (errors, warnings, info)"""

    # Signal emitted when user clicks on a problem (file_path, line_number)
    problem_clicked = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.problems = []  # List of (severity, file, line, message)
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Control bar
        control_layout = QHBoxLayout()

        # Filter by severity
        control_layout.addWidget(QLabel("Show:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Errors Only", "Warnings Only", "Info Only"])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        control_layout.addWidget(self.filter_combo)

        # Problem count label
        self.count_label = QLabel("0 problems")
        self.count_label.setStyleSheet("color: #888; margin-left: 10px;")
        control_layout.addWidget(self.count_label)

        control_layout.addStretch()

        # Clear button
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_problems)
        control_layout.addWidget(clear_btn)

        layout.addLayout(control_layout)

        # Problems table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", "File", "Line", "Message"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 30)  # Icon column
        self.table.setColumnWidth(2, 60)  # Line column
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.on_problem_double_clicked)

        layout.addWidget(self.table)

        # Info label
        info_label = QLabel("Double-click a problem to jump to the code location")
        info_label.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        layout.addWidget(info_label)

    def add_problem(self, severity, file_path, line_number, message):
        """Add a problem to the list

        Args:
            severity: "error", "warning", or "info"
            file_path: Path to the file with the problem
            line_number: Line number (1-indexed)
            message: Description of the problem
        """
        self.problems.append({
            'severity': severity.lower(),
            'file': file_path,
            'line': line_number,
            'message': message
        })
        self.refresh_table()

    def clear_problems(self):
        """Clear all problems"""
        self.problems = []
        self.refresh_table()

    def refresh_table(self):
        """Refresh the problems table"""
        # Get current filter
        filter_text = self.filter_combo.currentText()

        # Filter problems
        if filter_text == "Errors Only":
            filtered = [p for p in self.problems if p['severity'] == 'error']
        elif filter_text == "Warnings Only":
            filtered = [p for p in self.problems if p['severity'] == 'warning']
        elif filter_text == "Info Only":
            filtered = [p for p in self.problems if p['severity'] == 'info']
        else:
            filtered = self.problems

        # Update table
        self.table.setRowCount(len(filtered))

        for i, problem in enumerate(filtered):
            # Severity icon
            severity_item = QTableWidgetItem(self.get_severity_icon(problem['severity']))
            severity_item.setForeground(self.get_severity_color(problem['severity']))
            severity_item.setData(Qt.UserRole, problem)  # Store problem data
            self.table.setItem(i, 0, severity_item)

            # File
            file_item = QTableWidgetItem(problem['file'])
            self.table.setItem(i, 1, file_item)

            # Line
            line_item = QTableWidgetItem(str(problem['line']))
            line_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, line_item)

            # Message
            message_item = QTableWidgetItem(problem['message'])
            self.table.setItem(i, 3, message_item)

            # Set row background based on severity
            bg_color = self.get_severity_bg_color(problem['severity'])
            for col in range(4):
                self.table.item(i, col).setBackground(bg_color)

        # Update count
        error_count = sum(1 for p in self.problems if p['severity'] == 'error')
        warning_count = sum(1 for p in self.problems if p['severity'] == 'warning')
        info_count = sum(1 for p in self.problems if p['severity'] == 'info')

        count_parts = []
        if error_count > 0:
            count_parts.append(f"{error_count} error{'s' if error_count != 1 else ''}")
        if warning_count > 0:
            count_parts.append(f"{warning_count} warning{'s' if warning_count != 1 else ''}")
        if info_count > 0:
            count_parts.append(f"{info_count} info")

        if count_parts:
            self.count_label.setText(", ".join(count_parts))
        else:
            self.count_label.setText("0 problems")

    def apply_filter(self):
        """Apply the current filter"""
        self.refresh_table()

    def get_severity_icon(self, severity):
        """Get icon for severity level"""
        icons = {
            'error': '✖',
            'warning': '⚠',
            'info': 'ℹ'
        }
        return icons.get(severity, '•')

    def get_severity_color(self, severity):
        """Get color for severity level"""
        colors = {
            'error': QColor(231, 76, 60),    # Red
            'warning': QColor(241, 196, 15),  # Yellow
            'info': QColor(52, 152, 219)      # Blue
        }
        return colors.get(severity, QColor(200, 200, 200))

    def get_severity_bg_color(self, severity):
        """Get background color for severity level"""
        colors = {
            'error': QColor(60, 30, 30),     # Dark red
            'warning': QColor(60, 50, 20),   # Dark yellow
            'info': QColor(20, 40, 60)       # Dark blue
        }
        return colors.get(severity, QColor(40, 40, 40))

    def on_problem_double_clicked(self, item):
        """Handle double-click on a problem"""
        row = item.row()
        problem = self.table.item(row, 0).data(Qt.UserRole)
        if problem:
            self.problem_clicked.emit(problem['file'], problem['line'])

    def parse_compiler_output(self, output):
        """Parse compiler output and extract problems

        Parses common Arduino compiler error formats:
        - sketch.ino:10:5: error: 'foo' was not declared in this scope
        - sketch.ino:20:1: warning: unused variable 'bar'
        """
        self.clear_problems()

        for line in output.split('\n'):
            # Try to match common error pattern: file:line:col: severity: message
            import re
            match = re.match(r'(.+?):(\d+):\d+:\s*(error|warning|note):\s*(.+)', line)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2))
                severity = match.group(3)
                message = match.group(4)

                # Convert 'note' to 'info'
                if severity == 'note':
                    severity = 'info'

                self.add_problem(severity, file_path, line_num, message)

        self.refresh_table()
