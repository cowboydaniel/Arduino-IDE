"""
Breakpoint Gutter Extension for Code Editor
Adds breakpoint indicators and click handling to the line number area
"""

from PySide6.QtCore import Qt, Signal, QObject, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import QMenu
import logging
from typing import Set, Optional, Dict

logger = logging.getLogger(__name__)


class BreakpointGutter(QObject):
    """
    Manages breakpoint display and interaction in the code editor's line number area
    This is a mixin-style class that extends CodeEditor functionality
    """

    # Signals
    breakpoint_toggled = Signal(str, int)  # file_path, line_number
    breakpoint_added = Signal(str, int)    # file_path, line_number
    breakpoint_removed = Signal(str, int)  # file_path, line_number

    def __init__(self, editor, parent=None):
        super().__init__(parent)

        self.editor = editor
        self.file_path: Optional[str] = None

        # Track breakpoints for this file (line numbers)
        self.breakpoint_lines: Set[int] = set()

        # Visual settings
        self.breakpoint_color = QColor("#E51400")  # Red
        self.breakpoint_disabled_color = QColor("#888888")  # Gray
        self.current_line_color = QColor("#FFFF00")  # Yellow for execution line
        self.breakpoint_radius = 4

        # Current execution line (during debugging)
        self.current_execution_line: Optional[int] = None

        logger.debug("Breakpoint gutter initialized")


    def set_file_path(self, file_path: str):
        """Set the current file path"""
        self.file_path = file_path


    def has_breakpoint(self, line: int) -> bool:
        """Check if line has a breakpoint"""
        return line in self.breakpoint_lines


    def add_breakpoint(self, line: int) -> bool:
        """Add a breakpoint at line"""
        if line in self.breakpoint_lines:
            return False

        self.breakpoint_lines.add(line)
        self.editor.line_number_area.update()

        if self.file_path:
            self.breakpoint_added.emit(self.file_path, line)

        logger.debug(f"Breakpoint added at line {line}")
        return True


    def remove_breakpoint(self, line: int) -> bool:
        """Remove a breakpoint at line"""
        if line not in self.breakpoint_lines:
            return False

        self.breakpoint_lines.discard(line)
        self.editor.line_number_area.update()

        if self.file_path:
            self.breakpoint_removed.emit(self.file_path, line)

        logger.debug(f"Breakpoint removed at line {line}")
        return True


    def toggle_breakpoint(self, line: int) -> bool:
        """Toggle breakpoint at line"""
        if line in self.breakpoint_lines:
            self.remove_breakpoint(line)
            return False
        else:
            self.add_breakpoint(line)
            return True


    def clear_breakpoints(self):
        """Clear all breakpoints"""
        lines = list(self.breakpoint_lines)
        self.breakpoint_lines.clear()
        self.editor.line_number_area.update()

        # Emit signals for each removed breakpoint
        if self.file_path:
            for line in lines:
                self.breakpoint_removed.emit(self.file_path, line)


    def set_breakpoints(self, lines: Set[int]):
        """Set breakpoints from a set of line numbers"""
        self.breakpoint_lines = set(lines)
        self.editor.line_number_area.update()


    def get_breakpoints(self) -> Set[int]:
        """Get all breakpoint line numbers"""
        return self.breakpoint_lines.copy()


    def set_current_execution_line(self, line: Optional[int]):
        """Set the current execution line (highlighted during debugging)"""
        self.current_execution_line = line
        self.editor.line_number_area.update()

        # Also highlight the line in the editor
        if line is not None:
            self._highlight_execution_line(line)


    def _highlight_execution_line(self, line: int):
        """Highlight the current execution line in the editor"""
        # Move cursor to line
        cursor = self.editor.textCursor()
        cursor.movePosition(cursor.Start)
        for _ in range(line - 1):
            cursor.movePosition(cursor.Down)

        self.editor.setTextCursor(cursor)
        self.editor.centerCursor()


    def paint_breakpoints(self, painter: QPainter, event, block, top, line_num):
        """
        Paint breakpoint indicators in the line number area
        Called from the editor's line_number_area_paint_event
        """

        # Calculate breakpoint indicator position
        # Position it to the left of line numbers, after git markers
        bp_x = 15  # Offset from left edge (after git diff markers)

        # Draw current execution line indicator (yellow arrow)
        if self.current_execution_line == line_num:
            painter.setBrush(QBrush(self.current_line_color))
            painter.setPen(QPen(self.current_line_color))

            # Draw arrow pointing to current line
            arrow_y = top + self.editor.fontMetrics().height() // 2
            points = [
                QPoint(bp_x - 5, arrow_y - 4),
                QPoint(bp_x - 5, arrow_y + 4),
                QPoint(bp_x + 1, arrow_y)
            ]
            from PySide6.QtGui import QPolygon
            painter.drawPolygon(QPolygon(points))

        # Draw breakpoint indicator (red circle)
        if line_num in self.breakpoint_lines:
            painter.setBrush(QBrush(self.breakpoint_color))
            painter.setPen(QPen(Qt.white, 1))

            # Calculate center position for breakpoint circle
            bp_y = top + self.editor.fontMetrics().height() // 2

            # Draw filled circle
            painter.drawEllipse(
                bp_x - self.breakpoint_radius,
                bp_y - self.breakpoint_radius,
                self.breakpoint_radius * 2,
                self.breakpoint_radius * 2
            )


    def handle_gutter_click(self, event, line_num: int) -> bool:
        """
        Handle clicks in the gutter area
        Returns True if breakpoint was toggled, False otherwise
        """

        # Check if click is in the breakpoint area (left side of gutter)
        # Breakpoint area is roughly the first 25 pixels
        if event.pos().x() < 25:
            # Toggle breakpoint
            self.toggle_breakpoint(line_num)

            if self.file_path:
                self.breakpoint_toggled.emit(self.file_path, line_num)

            return True

        return False


    def show_breakpoint_context_menu(self, event, line_num: int):
        """Show context menu for breakpoint actions"""
        menu = QMenu()

        if line_num in self.breakpoint_lines:
            remove_action = menu.addAction("Remove Breakpoint")
            remove_action.triggered.connect(lambda: self.remove_breakpoint(line_num))

            disable_action = menu.addAction("Disable Breakpoint")
            # TODO: Implement disable functionality

        else:
            add_action = menu.addAction("Add Breakpoint")
            add_action.triggered.connect(lambda: self.add_breakpoint(line_num))

        menu.addSeparator()

        conditional_action = menu.addAction("Conditional Breakpoint...")
        # TODO: Implement conditional breakpoint dialog

        remove_all_action = menu.addAction("Remove All Breakpoints")
        remove_all_action.triggered.connect(self.clear_breakpoints)

        # Show menu at click position
        menu.exec_(event.globalPos())


    def sync_with_debug_service(self, debug_service):
        """Sync breakpoints with debug service"""
        if not debug_service or not self.file_path:
            return

        # Get breakpoints from debug service for this file
        breakpoints = debug_service.get_breakpoints(self.file_path)

        # Update local breakpoint set
        self.breakpoint_lines = {bp.line for bp in breakpoints}
        self.editor.line_number_area.update()


    def on_breakpoint_hit(self, file_path: str, line: int):
        """Handle breakpoint hit event"""
        if file_path == self.file_path:
            self.set_current_execution_line(line)


def install_breakpoint_gutter(editor, debug_service=None):
    """
    Install breakpoint gutter functionality into a CodeEditor instance
    This modifies the editor to support breakpoints
    """

    # Create breakpoint gutter
    bp_gutter = BreakpointGutter(editor)

    # Store reference in editor
    editor.breakpoint_gutter = bp_gutter

    # Connect to debug service if provided
    if debug_service:
        bp_gutter.sync_with_debug_service(debug_service)

        # Connect signals
        debug_service.breakpoint_hit.connect(bp_gutter.on_breakpoint_hit)

    # Patch the line_number_area_paint_event to include breakpoint painting
    original_paint_event = editor.line_number_area_paint_event

    def enhanced_paint_event(event):
        # Call original paint event
        original_paint_event(event)

        # Paint breakpoints
        painter = QPainter(editor.line_number_area)

        block = editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(editor.blockBoundingGeometry(block).translated(
            editor.contentOffset()).top())
        bottom = top + int(editor.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_num = block_number + 1

                # Paint breakpoint indicators
                bp_gutter.paint_breakpoints(painter, event, block, top, line_num)

            block = block.next()
            block_number += 1
            top = bottom
            bottom = top + int(editor.blockBoundingRect(block).height())

    editor.line_number_area_paint_event = enhanced_paint_event

    # Patch the handle_line_number_click to support breakpoint toggling
    original_click_handler = editor.handle_line_number_click

    def enhanced_click_handler(event):
        # Calculate which line was clicked
        block = editor.firstVisibleBlock()
        top = int(editor.blockBoundingGeometry(block).translated(editor.contentOffset()).top())
        bottom = top + int(editor.blockBoundingRect(block).height())

        while block.isValid() and top <= event.pos().y():
            if top <= event.pos().y() <= bottom:
                line_num = block.blockNumber() + 1

                # Try to handle as breakpoint click first
                if bp_gutter.handle_gutter_click(event, line_num):
                    return  # Breakpoint was toggled, done

                # Otherwise, handle as fold click (original behavior)
                break

            block = block.next()
            top = bottom
            bottom = top + int(editor.blockBoundingRect(block).height())

        # Call original handler for folding
        original_click_handler(event)

    editor.handle_line_number_click = enhanced_click_handler

    logger.info("Breakpoint gutter installed in code editor")

    return bp_gutter
