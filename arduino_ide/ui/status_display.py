"""
Real-time Status Display Panel
Shows live variable values and memory usage from Arduino
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGroupBox, QGridLayout, QPushButton, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
import re
import random


class VariableMonitor(QWidget):
    """Widget for monitoring a single variable with graph option"""

    graph_requested = Signal(str)  # Signal when graph button is clicked

    def __init__(self, var_name="", var_value="", parent=None):
        super().__init__(parent)
        self.var_name = var_name
        self.var_value = var_value
        self.trend = ""  # ▲ for increasing, ▼ for decreasing
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # Variable name and value
        self.label = QLabel(f"{self.var_name}: {self.var_value}")
        self.label.setFont(QFont("Consolas", 9))
        layout.addWidget(self.label, 1)

        # Trend indicator
        self.trend_label = QLabel("")
        self.trend_label.setFont(QFont("Consolas", 9))
        layout.addWidget(self.trend_label)

        # Graph button
        self.graph_btn = QPushButton("📊")
        self.graph_btn.setFixedSize(24, 24)
        self.graph_btn.setToolTip("Show graph")
        self.graph_btn.clicked.connect(lambda: self.graph_requested.emit(self.var_name))
        layout.addWidget(self.graph_btn)

    def update_value(self, new_value, trend=""):
        """Update the variable value and trend"""
        self.var_value = new_value
        self.trend = trend
        self.label.setText(f"{self.var_name}: {self.var_value}")
        self.trend_label.setText(trend)

        # Color code trend
        if trend == "▲":
            self.trend_label.setStyleSheet("color: #4CAF50;")  # Green
        elif trend == "▼":
            self.trend_label.setStyleSheet("color: #FF5252;")  # Red
        else:
            self.trend_label.setStyleSheet("")


class MemoryBar(QWidget):
    """Custom memory usage bar with label"""

    def __init__(self, label="", parent=None):
        super().__init__(parent)
        self.label_text = label
        self.usage_percent = 0
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # Label
        label = QLabel(self.label_text)
        label.setMinimumWidth(50)
        label.setFont(QFont("Consolas", 9))
        layout.addWidget(label)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setMinimumHeight(20)
        layout.addWidget(self.progress, 1)

    def update_usage(self, percent):
        """Update memory usage percentage"""
        self.usage_percent = percent
        self.progress.setValue(int(percent))

        # Color code based on usage
        if percent < 50:
            color = "#4CAF50"  # Green
        elif percent < 75:
            color = "#FFC107"  # Yellow
        else:
            color = "#FF5252"  # Red

        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                background-color: #2b2b2b;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)


class StatusDisplay(QWidget):
    """Real-time status display panel showing live values and memory usage"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Data storage
        self.monitored_vars = {}  # {var_name: {"value": val, "history": [...]}}
        self.serial_monitor = None  # Reference to serial monitor for data

        self.init_ui()

        # Setup update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)  # Update every second

    def init_ui(self):
        """Initialize UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title = QLabel("⚡ Real-time Status")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Live Values Section
        live_group = QGroupBox("Live Values")
        live_group.setFont(QFont("Arial", 10, QFont.Bold))
        live_layout = QVBoxLayout()

        # Scroll area for variables
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)

        self.vars_widget = QWidget()
        self.vars_layout = QVBoxLayout(self.vars_widget)
        self.vars_layout.setContentsMargins(2, 2, 2, 2)
        self.vars_layout.setSpacing(2)

        # Add some example variables
        self.add_variable("counter", "42")
        self.add_variable("ledState", "HIGH")
        self.add_variable("temp", "23.5°C")

        self.vars_layout.addStretch()

        scroll.setWidget(self.vars_widget)
        live_layout.addWidget(scroll)

        live_group.setLayout(live_layout)
        main_layout.addWidget(live_group)

        # Memory Usage Section
        memory_group = QGroupBox("Memory Usage")
        memory_group.setFont(QFont("Arial", 10, QFont.Bold))
        memory_layout = QVBoxLayout()
        memory_layout.setSpacing(10)

        # RAM usage
        self.ram_bar = MemoryBar("RAM:")
        memory_layout.addWidget(self.ram_bar)

        # Flash usage
        self.flash_bar = MemoryBar("Flash:")
        memory_layout.addWidget(self.flash_bar)

        memory_group.setLayout(memory_layout)
        main_layout.addWidget(memory_group)

        # Connection Status
        status_group = QGroupBox("Connection")
        status_group.setFont(QFont("Arial", 10, QFont.Bold))
        status_layout = QVBoxLayout()

        self.connection_label = QLabel("⚪ Not connected")
        self.connection_label.setFont(QFont("Consolas", 9))
        status_layout.addWidget(self.connection_label)

        self.last_update_label = QLabel("Last update: Never")
        self.last_update_label.setFont(QFont("Consolas", 8))
        self.last_update_label.setStyleSheet("color: #888;")
        status_layout.addWidget(self.last_update_label)

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # Control buttons
        controls_layout = QHBoxLayout()

        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        controls_layout.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("🗑 Clear")
        self.clear_btn.clicked.connect(self.clear_variables)
        controls_layout.addWidget(self.clear_btn)

        main_layout.addLayout(controls_layout)

        main_layout.addStretch()

    def add_variable(self, name, value, trend=""):
        """Add a new variable to monitor"""
        if name not in self.monitored_vars:
            var_monitor = VariableMonitor(name, value)
            var_monitor.graph_requested.connect(self.show_graph)
            self.vars_layout.insertWidget(self.vars_layout.count() - 1, var_monitor)

            self.monitored_vars[name] = {
                "widget": var_monitor,
                "value": value,
                "history": [value]
            }
        else:
            # Update existing variable
            self.update_variable(name, value, trend)

    def update_variable(self, name, value, trend=""):
        """Update an existing variable"""
        if name in self.monitored_vars:
            var_data = self.monitored_vars[name]
            var_data["value"] = value
            var_data["history"].append(value)

            # Keep only last 100 values
            if len(var_data["history"]) > 100:
                var_data["history"] = var_data["history"][-100:]

            var_data["widget"].update_value(value, trend)

    def remove_variable(self, name):
        """Remove a variable from monitoring"""
        if name in self.monitored_vars:
            widget = self.monitored_vars[name]["widget"]
            self.vars_layout.removeWidget(widget)
            widget.deleteLater()
            del self.monitored_vars[name]

    def clear_variables(self):
        """Clear all monitored variables"""
        for name in list(self.monitored_vars.keys()):
            self.remove_variable(name)

    def update_status(self):
        """Update status display with simulated or real data"""
        import datetime

        # Simulate data updates (in real implementation, this would come from serial data)
        if hasattr(self, '_paused') and self._paused:
            return

        # Update example variables with simulated data
        if "counter" in self.monitored_vars:
            current = int(self.monitored_vars["counter"]["value"])
            new_val = current + 1
            trend = "▲"
            self.update_variable("counter", str(new_val), trend)

        if "temp" in self.monitored_vars:
            # Simulate temperature fluctuation
            current = float(self.monitored_vars["temp"]["value"].replace("°C", ""))
            change = random.uniform(-0.5, 0.5)
            new_val = current + change
            trend = "▲" if change > 0 else ("▼" if change < 0 else "")
            self.update_variable("temp", f"{new_val:.1f}°C", trend)

        # Update memory usage (simulated)
        ram_usage = random.randint(40, 60)
        flash_usage = random.randint(30, 40)

        self.ram_bar.update_usage(ram_usage)
        self.flash_bar.update_usage(flash_usage)

        # Update connection status
        self.connection_label.setText("🟢 Connected (Simulated)")
        self.last_update_label.setText(f"Last update: {datetime.datetime.now().strftime('%H:%M:%S')}")

    def parse_serial_data(self, data):
        """Parse incoming serial data for variable updates

        Expected format:
        VAR:name=value

        Examples:
        VAR:counter=42
        VAR:temp=23.5
        VAR:ledState=HIGH
        """
        lines = data.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("VAR:"):
                # Parse variable update
                var_data = line[4:]  # Remove "VAR:" prefix
                if '=' in var_data:
                    name, value = var_data.split('=', 1)
                    name = name.strip()
                    value = value.strip()

                    # Detect trend
                    trend = ""
                    if name in self.monitored_vars:
                        old_value = self.monitored_vars[name]["value"]
                        try:
                            # Try to compare numerically
                            old_num = float(re.sub(r'[^\d.-]', '', old_value))
                            new_num = float(re.sub(r'[^\d.-]', '', value))
                            if new_num > old_num:
                                trend = "▲"
                            elif new_num < old_num:
                                trend = "▼"
                        except (ValueError, TypeError):
                            pass

                    self.add_variable(name, value, trend)

            elif line.startswith("MEM:"):
                # Parse memory update
                # Format: MEM:RAM=45,FLASH=32
                mem_data = line[4:]
                parts = mem_data.split(',')
                for part in parts:
                    if '=' in part:
                        mem_type, percent = part.split('=', 1)
                        mem_type = mem_type.strip().upper()
                        try:
                            percent_val = float(percent.strip())
                            if mem_type == "RAM":
                                self.ram_bar.update_usage(percent_val)
                            elif mem_type == "FLASH":
                                self.flash_bar.update_usage(percent_val)
                        except ValueError:
                            pass

    def connect_serial_monitor(self, serial_monitor):
        """Connect to serial monitor to receive data"""
        self.serial_monitor = serial_monitor
        if self.serial_monitor:
            self.serial_monitor.data_received.connect(self.parse_serial_data)
            self.connection_label.setText("🟢 Connected to Serial Monitor")

    def toggle_pause(self):
        """Toggle pause/resume updates"""
        if not hasattr(self, '_paused'):
            self._paused = False

        self._paused = not self._paused

        if self._paused:
            self.pause_btn.setText("▶ Resume")
            self.update_timer.stop()
        else:
            self.pause_btn.setText("⏸ Pause")
            self.update_timer.start(1000)

    def show_graph(self, var_name):
        """Show graph for a variable (placeholder)"""
        if var_name in self.monitored_vars:
            history = self.monitored_vars[var_name]["history"]
            # TODO: Implement graph visualization
            # For now, just print to console
            print(f"Graph requested for {var_name}")
            print(f"History: {history[-10:]}")  # Last 10 values
