import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QtWidgets = pytest.importorskip(
    "PySide6.QtWidgets", reason="PySide6 widgets require system GL libraries", exc_type=ImportError
)
QApplication = QtWidgets.QApplication
QDockWidget = QtWidgets.QDockWidget

from arduino_ide.services.circuit_service import CircuitService
from arduino_ide.ui.circuit_editor import CircuitDesignerWindow, ToolMode


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_designer_exposes_kicad_docks():
    app = _app()
    service = CircuitService()
    window = CircuitDesignerWindow(service)
    docks = window.findChildren(QDockWidget)
    titles = sorted(dock.windowTitle() for dock in docks)
    assert {"Inspector", "Messages", "Sheets", "Symbols"}.issubset(set(titles))
    app.processEvents()


def test_workspace_tool_mode_switches():
    _app()
    service = CircuitService()
    window = CircuitDesignerWindow(service)
    workspace = window.circuit_editor.workspace
    workspace.set_tool_mode(ToolMode.BUS)
    assert workspace.tool_mode == ToolMode.BUS
    workspace.set_tool_mode(ToolMode.NET_LABEL)
    assert workspace.tool_mode == ToolMode.NET_LABEL
