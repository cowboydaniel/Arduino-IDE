#!/usr/bin/env python3
"""
Standalone Circuit Designer Test
Run this script to test the Circuit Designer as a standalone application
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from arduino_ide.ui.circuit_editor import CircuitDesignerWindow
from arduino_ide.services.circuit_service import CircuitService


def main():
    """Run Circuit Designer as standalone application"""
    app = QApplication(sys.argv)

    # Create circuit service
    circuit_service = CircuitService()

    # Create and show circuit designer window
    window = CircuitDesignerWindow(circuit_service)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
