"""Android entry point for Arduino IDE Modern.

This module keeps the Android packaging self contained so the Gradle project
can ship a ready-to-run PySide6 bundle without running pyside6-android-deploy.
"""
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt


def _bootstrap_environment() -> None:
    """Configure import paths so the bundled assets can resolve correctly.

    The Gradle build copies the python sources into ``assets/python``. When the
    Qt Python bootstrapper starts, it mounts that directory as the working
    directory. Adjust ``sys.path`` so the desktop package and mobile modules can
    be imported without extra regeneration steps.
    """

    assets_root = Path(__file__).resolve().parent
    if str(assets_root) not in sys.path:
        sys.path.insert(0, str(assets_root))

    package_root = assets_root / "arduino_ide"
    if package_root.exists() and str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root.parent))


class AndroidWarmupWindow(QLabel):
    """Lightweight splash used while the Python runtime starts up."""

    def __init__(self) -> None:
        super().__init__("Arduino IDE Modern for Android")
        self.setAlignment(Qt.AlignCenter)
        self.setMargin(24)
        self.setStyleSheet(
            "font-size: 18sp; color: #1E88E5; font-weight: 600;"
        )


def main() -> int:
    _bootstrap_environment()

    # The lightweight warmup window lets Gradle/Qt verify that the bundled
    # runtime is functional even before the full IDE UI loads.
    app = QApplication.instance() or QApplication(sys.argv)
    splash = AndroidWarmupWindow()
    splash.show()

    # Reuse the desktop entry point so Phase 0 shares the same feature surface.
    try:
        from arduino_ide.main import main as desktop_main
    except Exception as exc:  # noqa: BLE001 - we want to catch unexpected bootstrap failures
        print(f"Failed to start Arduino IDE: {exc}")
        return 1

    exit_code = desktop_main()
    splash.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
