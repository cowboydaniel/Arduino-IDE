"""Debugger workspace dialog.

This dialog composes the debugger widgets (toolbar, breakpoints, call
stack, variable watch, memory, execution timeline) around a shared
``DebugService`` instance.  It provides a single entry point for the
application to manage the debugging UI.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
)

from arduino_ide.services.debug_service import DebugService
from arduino_ide.ui.breakpoints_panel import BreakpointsPanel
from arduino_ide.ui.call_stack_panel import CallStackPanel
from arduino_ide.ui.debug_toolbar import DebugToolbar
from arduino_ide.ui.execution_timeline import ExecutionTimelinePanel
from arduino_ide.ui.memory_panel import MemoryPanel
from arduino_ide.ui.variable_watch import VariableWatch


class DebugWorkspaceDialog(QDialog):
    """Container dialog for debugger UI components."""

    def __init__(self, debug_service: Optional[DebugService] = None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Debugger Workspace")
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.resize(1200, 750)

        self._debug_service: Optional[DebugService] = None

        self._build_ui()

        if debug_service is not None:
            self.set_debug_service(debug_service)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar across the top
        self.debug_toolbar = DebugToolbar(parent=self)
        layout.addWidget(self.debug_toolbar)

        # Main splitter with panels
        self.main_splitter = QSplitter(Qt.Horizontal, self)
        layout.addWidget(self.main_splitter, 1)

        # Left side: breakpoints and call stack stacked vertically
        left_splitter = QSplitter(Qt.Vertical, self.main_splitter)
        self.breakpoints_panel = BreakpointsPanel(parent=left_splitter)
        self.call_stack_panel = CallStackPanel(parent=left_splitter)
        left_splitter.addWidget(self.breakpoints_panel)
        left_splitter.addWidget(self.call_stack_panel)
        left_splitter.setStretchFactor(0, 3)
        left_splitter.setStretchFactor(1, 2)

        self.main_splitter.addWidget(left_splitter)

        # Right side: variables, memory, execution timeline in tabs
        self.side_tabs = QTabWidget(self.main_splitter)
        self.variable_watch = VariableWatch(parent=self.side_tabs)
        self.memory_panel = MemoryPanel(parent=self.side_tabs)
        self.timeline_panel = ExecutionTimelinePanel(parent=self.side_tabs)
        self.side_tabs.addTab(self.variable_watch, "Variables")
        self.side_tabs.addTab(self.memory_panel, "Memory")
        self.side_tabs.addTab(self.timeline_panel, "Timeline")
        self.main_splitter.addWidget(self.side_tabs)

        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 4)

        # Hook toolbar start button to the service lazily through a slot.
        self.debug_toolbar.start_debug_requested.connect(self._on_start_requested)

    def debug_service(self) -> Optional[DebugService]:
        """Return the currently attached ``DebugService``."""

        return self._debug_service

    def set_debug_service(self, debug_service: DebugService) -> None:
        """Attach a debug service and propagate it to child widgets."""

        if debug_service is self._debug_service:
            return

        self._debug_service = debug_service
        self.debug_toolbar.set_debug_service(debug_service)
        self.breakpoints_panel.set_debug_service(debug_service)
        self.call_stack_panel.set_debug_service(debug_service)
        self.variable_watch.set_debug_service(debug_service)
        self.memory_panel.set_debug_service(debug_service)
        self.timeline_panel.set_debug_service(debug_service)

    @Slot()
    def _on_start_requested(self) -> None:
        if self._debug_service is not None:
            self._debug_service.start_debugging()
