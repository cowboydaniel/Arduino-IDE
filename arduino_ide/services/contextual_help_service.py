"""Context-aware help and inline hint service."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union


@dataclass
class InlineHint:
    """Represents an inline hint tied to a location in the editor."""

    message: str
    line: int
    column: int = 0
    severity: str = "info"
    hint_type: str = "general"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the hint."""
        return {
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "hint_type": self.hint_type,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }


class ContextualHelpService:
    """Shows relevant help based on what the user is doing."""

    def __init__(self):
        self._last_context: Dict[str, Any] = {}
        self._last_hints: List[InlineHint] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze_context(
        self,
        cursor_position: Union[int, Tuple[int, int], Dict[str, int]],
        code: str,
        editor_state: Optional[Dict[str, Any]] = None,
    ) -> List[InlineHint]:
        """Analyze the current editor context and provide inline hints.

        Args:
            cursor_position: Zero-based absolute offset, (line, column) tuple,
                or {"line": int, "column": int} dict for the caret.
            code: Current source code.
            editor_state: Optional state dictionary (e.g. Serial monitor open).

        Returns:
            List of InlineHint entries sorted by relevance to the cursor.
        """

        cursor_line, cursor_column = self._normalise_cursor(cursor_position, code)
        lines = code.splitlines() or [""]
        editor_state = editor_state or {}

        hints: List[InlineHint] = []
        hints.extend(self._detect_unused_pin_modes(lines))
        hints.extend(self._detect_delay_in_loop(lines))
        hints.extend(self._detect_serial_monitor_state(code, lines, editor_state))

        # Store context for show_inline_hints
        self._last_context = {
            "cursor_line": cursor_line,
            "cursor_column": cursor_column,
            "editor_state": editor_state,
        }
        self._last_hints = self._rank_hints_by_cursor(hints, cursor_line)
        return self._last_hints

    def show_inline_hints(self) -> List[str]:
        """Return formatted inline hints ready for UI display."""
        if not self._last_hints:
            return []
        return [f"{hint.message} (line {hint.line})" for hint in self._last_hints]

    # ------------------------------------------------------------------
    # Hint detectors
    # ------------------------------------------------------------------
    def _detect_unused_pin_modes(self, lines: List[str]) -> List[InlineHint]:
        hints: List[InlineHint] = []
        pinmode_pattern = re.compile(r"pinMode\s*\(\s*(\w+)\s*,\s*(OUTPUT|INPUT|INPUT_PULLUP)\s*\)")
        usage_pattern = re.compile(
            r"(digitalWrite|digitalRead|analogWrite|analogRead)\s*\(\s*(\w+)"
        )

        pin_definitions: Dict[str, int] = {}
        for line_no, line in enumerate(lines, 1):
            for match in pinmode_pattern.finditer(line):
                pin = match.group(1)
                pin_definitions.setdefault(pin, line_no)

        if not pin_definitions:
            return hints

        used_pins = set()
        for line in lines:
            for match in usage_pattern.finditer(line):
                used_pins.add(match.group(2))

        for pin, line_no in pin_definitions.items():
            if pin not in used_pins:
                hints.append(
                    InlineHint(
                        message=f"pinMode() called for {pin} but the pin is never used",
                        line=line_no,
                        severity="warning",
                        hint_type="unused-pin",
                        tags=["pinMode", "usage"],
                    )
                )

        return hints

    def _detect_delay_in_loop(self, lines: List[str]) -> List[InlineHint]:
        hints: List[InlineHint] = []
        in_loop = False
        brace_depth = 0

        for line_no, line in enumerate(lines, 1):
            if re.search(r"void\s+loop\s*\(", line):
                in_loop = True
                brace_depth = 0
                continue

            if in_loop:
                brace_depth += line.count("{") - line.count("}")
                if brace_depth < 0:
                    in_loop = False
                    continue

                match = re.search(r"delay\s*\(\s*(\d+)\s*\)", line)
                if match and int(match.group(1)) > 50:
                    hints.append(
                        InlineHint(
                            message="Consider using millis() instead of delay() for non-blocking code",
                            line=line_no,
                            severity="tip",
                            hint_type="timing",
                            tags=["delay", "millis"],
                        )
                    )

        return hints

    def _detect_serial_monitor_state(
        self, code: str, lines: List[str], editor_state: Dict[str, Any]
    ) -> List[InlineHint]:
        hints: List[InlineHint] = []
        serial_monitor_open = editor_state.get("serial_monitor_open", True)

        if not serial_monitor_open and "Serial.begin" in code:
            for line_no, line in enumerate(lines, 1):
                if "Serial.begin" in line:
                    hints.append(
                        InlineHint(
                            message="Serial.begin() detected but Serial Monitor appears to be closed",
                            line=line_no,
                            severity="info",
                            hint_type="serial-monitor",
                            tags=["Serial", "monitor"],
                        )
                    )
                    break

        return hints

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _normalise_cursor(
        self, cursor_position: Union[int, Tuple[int, int], Dict[str, int]], code: str
    ) -> Tuple[int, int]:
        if isinstance(cursor_position, dict):
            line = cursor_position.get("line", 0)
            column = cursor_position.get("column", 0)
            return line, column

        if isinstance(cursor_position, tuple) and len(cursor_position) == 2:
            return cursor_position

        if isinstance(cursor_position, int):
            return self._absolute_to_line_col(cursor_position, code)

        # Fallback to the beginning of the document
        return 0, 0

    def _absolute_to_line_col(self, offset: int, code: str) -> Tuple[int, int]:
        offset = max(0, min(len(code), offset))
        up_to_offset = code[:offset]
        line = up_to_offset.count("\n")
        last_newline = up_to_offset.rfind("\n")
        column = offset if last_newline == -1 else offset - last_newline - 1
        return line, column

    def _rank_hints_by_cursor(self, hints: Iterable[InlineHint], cursor_line: int) -> List[InlineHint]:
        return sorted(
            hints,
            key=lambda hint: (
                abs(hint.line - (cursor_line + 1)),  # cursor_line is zero-based internally
                0 if hint.severity == "warning" else 1,
                hint.line,
            ),
        )
