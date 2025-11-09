"""
Plotter Panel for Arduino IDE
Displays real-time plots of serial data
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QCheckBox, QSpinBox, QFileDialog,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QGuiApplication
import re
import csv
from datetime import datetime


class PlotWidget(QWidget):
    """Custom widget for plotting data"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_series = []  # List of data points for each series
        self.series_labels = []  # Labels for each series
        self.max_points = 500
        self.colors = [
            QColor(52, 152, 219),   # Blue
            QColor(46, 204, 113),   # Green
            QColor(231, 76, 60),    # Red
            QColor(241, 196, 15),   # Yellow
            QColor(155, 89, 182),   # Purple
            QColor(230, 126, 34),   # Orange
        ]
        screen = QGuiApplication.primaryScreen()
        if screen:
            available_height = screen.availableGeometry().height()
            min_height = max(150, min(300, available_height // 3))
        else:
            min_height = 200

        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        size_policy.setVerticalStretch(1)
        self.setSizePolicy(size_policy)
        self.setMinimumHeight(min_height)

    def add_data_point(self, values, labels=None):
        """Add a data point (can be multiple series)"""
        if not isinstance(values, list):
            values = [values]

        # Initialize series if needed
        while len(self.data_series) < len(values):
            self.data_series.append([])
            # Generate default label if not provided
            if labels and len(labels) > len(self.series_labels):
                self.series_labels.append(labels[len(self.series_labels)])
            else:
                self.series_labels.append(f"Series {len(self.series_labels) + 1}")

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
        self.series_labels = []
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

        # Draw legend
        if self.series_labels:
            legend_x = width - margin - 120
            legend_y = margin + 10
            legend_spacing = 20

            for idx, label in enumerate(self.series_labels):
                color = self.colors[idx % len(self.colors)]

                # Draw color box
                painter.fillRect(legend_x, legend_y + idx * legend_spacing, 15, 10, color)

                # Draw label text
                painter.setPen(QColor(200, 200, 200))
                painter.setFont(QFont("Arial", 9))
                painter.drawText(legend_x + 20, legend_y + idx * legend_spacing + 9, label)


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

        # Export CSV button
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.export_to_csv)
        control_layout.addWidget(export_btn)

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

    def export_to_csv(self):
        """Export plot data to CSV file"""
        if not self.plot_widget.data_series or not any(self.plot_widget.data_series):
            self.status_label.setText("No data to export")
            return

        # Open file dialog
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"plotter_data_{timestamp}.csv"

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plot Data",
            default_filename,
            "CSV Files (*.csv);;All Files (*)"
        )

        if not filename:
            return

        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                # Write header
                headers = ['Index'] + [
                    self.plot_widget.series_labels[i] if i < len(self.plot_widget.series_labels)
                    else f"Series {i+1}"
                    for i in range(len(self.plot_widget.data_series))
                ]
                writer.writerow(headers)

                # Find max length
                max_length = max(len(series) for series in self.plot_widget.data_series if series)

                # Write data rows
                for i in range(max_length):
                    row = [i]
                    for series in self.plot_widget.data_series:
                        if i < len(series):
                            row.append(series[i])
                        else:
                            row.append('')
                    writer.writerow(row)

            self.status_label.setText(f"Data exported to {filename}")
        except Exception as e:
            self.status_label.setText(f"Export failed: {str(e)}")

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
