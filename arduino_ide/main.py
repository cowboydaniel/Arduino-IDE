#!/usr/bin/env python3
"""Main entry point for Arduino IDE Modern"""

import json
import subprocess
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from arduino_ide.config import APP_NAME, APP_ORGANIZATION, APP_VERSION
from arduino_ide.ui.main_window import MainWindow


def _ensure_default_core_installed() -> None:
    """Ensure the ``arduino:avr`` core is installed before the UI starts."""

    cli_path = (Path(__file__).resolve().parents[1] / "arduino-cli").resolve()
    if not cli_path.exists():
        print(f"arduino-cli helper not found at {cli_path}. Skipping core installation.")
        return

    def run_cli(args, *, expect_json: bool = False):
        result = subprocess.run(
            [sys.executable, str(cli_path), *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout) if expect_json and result.stdout.strip() else {}

    try:
        cores = run_cli(["core", "list", "--format", "json"], expect_json=True)
        installed = cores.get("installed", []) if isinstance(cores, dict) else []
        if any(core.get("id") == "arduino:avr" for core in installed):
            return
    except (json.JSONDecodeError, subprocess.CalledProcessError, OSError) as exc:
        print(f"Failed to query installed Arduino cores: {exc}")

    try:
        run_cli(["core", "update-index"])
    except subprocess.CalledProcessError as exc:
        print(f"Failed to update Arduino core index: {exc.stderr.strip() if exc.stderr else exc}")

    try:
        run_cli(["core", "install", "arduino:avr"])
    except subprocess.CalledProcessError as exc:
        print(f"Failed to install arduino:avr core: {exc.stderr.strip() if exc.stderr else exc}")


def main():
    """Initialize and run the application"""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    _ensure_default_core_installed()

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
