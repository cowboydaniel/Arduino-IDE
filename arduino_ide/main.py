#!/usr/bin/env python3
"""Main entry point for Arduino IDE Modern"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from arduino_ide.config import APP_NAME, APP_ORGANIZATION, APP_VERSION
from arduino_ide.ui.main_window import MainWindow


def main():
    """Initialize and run the application"""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORGANIZATION)
    app.setApplicationVersion(APP_VERSION)

    # Create and show main window maximized
    window = MainWindow()
    window.setWindowState(window.windowState() | Qt.WindowMaximized)
    window.showMaximized()
    QTimer.singleShot(0, window.showMaximized)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
