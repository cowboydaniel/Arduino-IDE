#!/usr/bin/env python3
"""Main entry point for Arduino IDE Modern"""

import json
import subprocess
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from arduino_ide.config import APP_NAME, APP_ORGANIZATION, APP_VERSION, get_arduino_cli_path
from arduino_ide.ui.main_window import MainWindow


def _ensure_default_core_installed() -> None:
    """Ensure the ``arduino:avr`` core is installed before the UI starts."""

    cli_path = get_arduino_cli_path()
    if cli_path is None:
        print("arduino-cli binary not found on PATH. Skipping core installation.")
        return

    def run_cli(args, *, expect_json: bool = False):
        result = subprocess.run(
            [str(cli_path), *args],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                result.args,
                output=result.stdout,
                stderr=result.stderr,
            )

        if expect_json and result.stdout.strip():
            return json.loads(result.stdout)

        return result.stdout

    try:
        cores = run_cli(["core", "list", "--format", "json"], expect_json=True)
        # The official arduino-cli returns a list of platform objects directly
        installed = cores if isinstance(cores, list) else cores.get("platforms", cores.get("installed", []))
        if any(core.get("id") == "arduino:avr" for core in installed):
            return
    except json.JSONDecodeError as exc:
        print(f"Failed to parse Arduino core list JSON: {exc}")
    except (subprocess.CalledProcessError, OSError) as exc:
        message = (
            (exc.stderr or exc.output or str(exc))
            if isinstance(exc, subprocess.CalledProcessError)
            else str(exc)
        )
        try:
            cores_text = run_cli(["core", "list"])
        except subprocess.CalledProcessError:
            if message:
                print(f"Failed to query installed Arduino cores: {message}")
            else:
                print("Failed to query installed Arduino cores")
        else:
            if "arduino:avr" in cores_text:
                return
            if message:
                print(f"Failed to query installed Arduino cores: {message}")

    try:
        run_cli(["core", "update-index"])
    except subprocess.CalledProcessError as exc:
        error_text = (exc.stderr or exc.output or "").strip()
        if "invalid choice" not in error_text:
            print(
                "Failed to update Arduino core index: "
                f"{error_text or exc}"
            )

    try:
        run_cli(["core", "install", "arduino:avr"])
    except subprocess.CalledProcessError as exc:
        print(f"Failed to install arduino:avr core: {exc.stderr.strip() if exc.stderr else exc}")


def main() -> int:
    """Initialize and run the application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    _ensure_default_core_installed()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORGANIZATION)
    app.setApplicationVersion(APP_VERSION)

    # Create and show main window maximized
    window = MainWindow()
    window.setWindowState(window.windowState() | Qt.WindowMaximized)
    window.showMaximized()
    QTimer.singleShot(0, window.showMaximized)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
