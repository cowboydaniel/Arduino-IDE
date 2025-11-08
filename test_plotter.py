#!/usr/bin/env python3
"""
Test script for the Serial Plotter functionality
Simulates serial data to test plotting
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from arduino_ide.ui.plotter_panel import PlotterPanel


def main():
    app = QApplication(sys.argv)

    # Create a simple window with the plotter
    window = QMainWindow()
    plotter = PlotterPanel()
    window.setCentralWidget(plotter)
    window.setWindowTitle("Plotter Test")
    window.resize(800, 600)

    # Start plotting
    plotter.toggle_plotting()

    # Simulate some data
    import random
    from PySide6.QtCore import QTimer

    def generate_data():
        """Generate random test data"""
        temp = 20 + random.random() * 10
        humidity = 40 + random.random() * 20
        light = 100 + random.random() * 50
        # Send as CSV
        data = f"{temp:.2f},{humidity:.2f},{light:.2f}\n"
        plotter.append_output(data)

    # Generate data every 100ms
    timer = QTimer()
    timer.timeout.connect(generate_data)
    timer.start(100)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
