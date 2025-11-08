"""
Plotter Panel for Arduino IDE
Displays real-time plots of serial data
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QPen, QColor
import re


class PlotWidget(QWidget):
    """Custom widget for plotting data"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_series = []  # List of data points for each series
        self.max_points = 500
        self.colors = [
            QColor(52, 152, 219),   # Blue
            QColor(46, 204, 113),   # Green
            QColor(231, 76, 60),    # Red
            QColor(241, 196, 15),   # Yellow
            QColor(155, 89, 182),   # Purple
            QColor(230, 126, 34),   # Orange
        ]
        self.setMinimumHeight(300)

    def add_data_point(self, values):
        """Add a data point (can be multiple series)"""
        if not isinstance(values, list):
            values = [values]

        # Initialize series if needed
        while len(self.data_series) < len(values):
            self.data_series.append([])

        # Add values to each series
        for i, value in enumerate(values):
            self.data_series[i].append(value)
            # Keep only max_points
            if len(self.data_series[i]) > self.max_points:
                self.data_series[i].pop(0)

        self.update()

    def clear_data(self):
        """Clear all data"""
        self.data_series = []
        self.update()

    def paintEvent(self, event):
        """Draw the plot"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        if not self.data_series or not any(self.data_series):
            # No data - show message
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignCenter, "No data to display")
            return

        # Calculate bounds
        width = self.width()
        height = self.height()
        margin = 40
        plot_width = width - 2 * margin
        plot_height = height - 2 * margin

        # Find min and max values across all series
        all_values = [val for series in self.data_series for val in series if series]
        if not all_values:
            return

        min_val = min(all_values)
        max_val = max(all_values)

        # Add padding to range
        value_range = max_val - min_val
        if value_range == 0:
            value_range = 1
        min_val -= value_range * 0.1
        max_val += value_range * 0.1
        value_range = max_val - min_val

        # Draw grid
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        for i in range(5):
            y = margin + (plot_height * i / 4)
            painter.drawLine(margin, int(y), width - margin, int(y))
            # Draw value labels
            value = max_val - (value_range * i / 4)
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(5, int(y) + 5, f"{value:.1f}")
            painter.setPen(QPen(QColor(60, 60, 60), 1))

        # Draw axes
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawRect(margin, margin, plot_width, plot_height)

        # Draw data series
        for series_idx, series in enumerate(self.data_series):
            if not series:
                continue

            color = self.colors[series_idx % len(self.colors)]
            painter.setPen(QPen(color, 2))

            # Calculate points
            num_points = len(series)
            if num_points < 2:
                continue

            # Draw lines between points
            for i in range(num_points - 1):
                x1 = margin + (plot_width * i / max(num_points - 1, 1))
                y1 = margin + plot_height - ((series[i] - min_val) / value_range * plot_height)
                x2 = margin + (plot_width * (i + 1) / max(num_points - 1, 1))
                y2 = margin + plot_height - ((series[i + 1] - min_val) / value_range * plot_height)

                painter.drawLine(int(x1), int(y1), int(x2), int(y2))


class PlotterPanel(QWidget):
    """Serial plotter panel for visualizing data"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.is_running = False

    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Control bar
        control_layout = QHBoxLayout()

        # Start/Pause button
        self.start_btn = QPushButton("▶ Start")
        self.start_btn.clicked.connect(self.toggle_plotting)
        control_layout.addWidget(self.start_btn)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_plot)
        control_layout.addWidget(clear_btn)

        control_layout.addWidget(QLabel("Max Points:"))

        # Max points spinner
        self.max_points_spinner = QSpinBox()
        self.max_points_spinner.setRange(50, 2000)
        self.max_points_spinner.setValue(500)
        self.max_points_spinner.setSingleStep(50)
        self.max_points_spinner.valueChanged.connect(self.on_max_points_changed)
        control_layout.addWidget(self.max_points_spinner)

        # Auto-scroll checkbox
        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        control_layout.addWidget(self.autoscroll_check)

        control_layout.addStretch()

        layout.addLayout(control_layout)

        # Plot widget
        self.plot_widget = PlotWidget()
        layout.addWidget(self.plot_widget)

        # Status label
        self.status_label = QLabel("Ready to plot data")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)

    def toggle_plotting(self):
        """Start or pause plotting"""
        self.is_running = not self.is_running
        if self.is_running:
            self.start_btn.setText("⏸ Pause")
            self.status_label.setText("Plotting...")
        else:
            self.start_btn.setText("▶ Start")
            self.status_label.setText("Paused")

    def clear_plot(self):
        """Clear all plot data"""
        self.plot_widget.clear_data()
        self.status_label.setText("Plot cleared")

    def on_max_points_changed(self, value):
        """Handle max points change"""
        self.plot_widget.max_points = value
        self.status_label.setText(f"Max points set to {value}")

    def add_data(self, data_string):
        """Parse and add data from serial input

        Supports formats like:
        - Single value: "123"
        - Multiple values: "123 456 789"
        - CSV: "123,456,789"
        """
        if not self.is_running:
            return

        try:
            # Try to parse numeric values
            # Remove any non-numeric characters except spaces, commas, dots, and minus
            cleaned = re.sub(r'[^\d\s,.\-]', '', data_string.strip())

            # Split by comma or space
            if ',' in cleaned:
                parts = cleaned.split(',')
            else:
                parts = cleaned.split()

            # Convert to floats
            values = []
            for part in parts:
                if part.strip():
                    try:
                        values.append(float(part.strip()))
                    except ValueError:
                        continue

            if values:
                self.plot_widget.add_data_point(values)
                self.status_label.setText(f"Received: {', '.join(f'{v:.2f}' for v in values)}")
        except Exception as e:
            # Silently ignore parsing errors
            pass

    def append_output(self, text):
        """Handle serial data input for plotting"""
        # Split by newlines and process each line
        for line in text.split('\n'):
            line = line.strip()
            if line:
                self.add_data(line)
