#!/usr/bin/env python3
"""
Main entry point for Arduino IDE Modern
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from arduino_ide.ui.main_window import MainWindow


def main():
    """Initialize and run the application"""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Arduino IDE Modern")
    app.setOrganizationName("Arduino IDE Modern")
    app.setApplicationVersion("0.1.0")

    # Create and show main window maximized
    window = MainWindow()
    window.setWindowState(window.windowState() | Qt.WindowMaximized)
    window.showMaximized()
    QTimer.singleShot(0, window.showMaximized)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
