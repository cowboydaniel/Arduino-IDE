#!/usr/bin/env python3
"""
Standalone launcher for KiCad-style Schematic Editor
Run this to see the KiCad-lookalike UI
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from arduino_ide.eeschema.sch_edit_frame import SchEditFrame


def main():
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    # Create and show the KiCad-style editor
    editor = SchEditFrame()
    editor.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
