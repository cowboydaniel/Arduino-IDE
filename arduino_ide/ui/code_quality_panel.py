"""Code Quality Panel displaying live static analysis metrics."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class CodeQualityPanel(QDockWidget):
    """Live code metrics and suggestions."""

    metrics: Dict[str, object] = {
        "memory_efficiency": 85,  # % optimal
        "power_efficiency": 70,  # based on heuristic power analyzer
        "code_complexity": "Medium",
        "blocking_delays": 3,  # count of delay() calls
        "interrupt_safety": "⚠ Not ISR-safe",
    }

    def __init__(self, parent=None):
        super().__init__("Code Quality", parent)
        self.setObjectName("CodeQualityPanel")
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea
        )

        self.metrics = dict(self.metrics)  # Instance copy
        self.metric_widgets: Dict[str, object] = {}

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Real-time Code Quality Dashboard")
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        layout.addWidget(title)

        self.status_label = QLabel("Waiting for sketch analysis…")
        self.status_label.setStyleSheet("color: #8a8d93;")
        layout.addWidget(self.status_label)

        self.last_run_label = QLabel("Last analysis: —")
        self.last_run_label.setStyleSheet("color: #8a8d93; font-size: 11px;")
        layout.addWidget(self.last_run_label)

        layout.addWidget(self._build_separator())

        # Numeric metrics
        for key, label_text in (
            ("memory_efficiency", "Memory Efficiency"),
            ("power_efficiency", "Power Efficiency"),
        ):
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(int(self.metrics.get(key, 0)))
            progress.setFormat("%v%")
            progress.setTextVisible(True)
            progress.setAlignment(Qt.AlignCenter)
            self.metric_widgets[key] = progress
            layout.addWidget(self._build_metric_row(label_text, progress))

        # Textual metrics
        for key, label_text in (
            ("code_complexity", "Code Complexity"),
            ("blocking_delays", "Blocking delay() calls"),
            ("interrupt_safety", "Interrupt Safety"),
        ):
            value_label = QLabel(str(self.metrics.get(key, "—")))
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_label.setStyleSheet("font-weight: 500;")
            self.metric_widgets[key] = value_label
            layout.addWidget(self._build_metric_row(label_text, value_label))

        layout.addWidget(self._build_separator())

        suggestions_title = QLabel("Static Analysis Suggestions")
        suggestions_title.setStyleSheet("font-weight: 600;")
        layout.addWidget(suggestions_title)

        self.suggestions_list = QListWidget()
        self.suggestions_list.setAlternatingRowColors(True)
        self.suggestions_list.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self.suggestions_list)

        container.setLayout(layout)
        self.setWidget(container)

        self.show_idle_state("Open or edit a sketch to analyze code quality.")

    def _build_metric_row(self, label_text: str, widget: QWidget) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setStyleSheet("color: #c8c8c8;")
        row_layout.addWidget(label)
        row_layout.addWidget(widget, 1)

        return row

    def _build_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: rgba(255,255,255,0.1);")
        return line

    def analyze_code(self, code: str) -> None:
        """Analyze the provided code and update metrics."""

        if not code or not code.strip():
            self.show_idle_state("No sketch content available for analysis.")
            return

        metrics, suggestions = self._compute_metrics(code)
        self.update_metrics(metrics)
        self.update_suggestions(suggestions)

    def update_metrics(self, metrics: Dict[str, object]) -> None:
        """Update metric widgets and labels."""

        self.metrics.update(metrics)
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.last_run_label.setText(f"Last analysis: {timestamp}")
        self.status_label.setText("Static analysis updated from current editor.")

        for key, value in metrics.items():
            widget = self.metric_widgets.get(key)
            if widget is None:
                continue
            if isinstance(widget, QProgressBar):
                widget.setValue(int(value))
            elif isinstance(widget, QLabel):
                widget.setText(str(value))

    def update_suggestions(self, suggestions: List[str]) -> None:
        """Refresh the suggestion list."""

        self.suggestions_list.clear()
        if not suggestions:
            suggestions = ["Code looks solid. No warnings detected."]
        for text in suggestions:
            item = QListWidgetItem(f"• {text}")
            self.suggestions_list.addItem(item)

    def show_idle_state(self, message: str) -> None:
        """Reset panel to idle state when no code is available."""

        self.status_label.setText(message)
        self.last_run_label.setText("Last analysis: —")
        for key, widget in self.metric_widgets.items():
            if isinstance(widget, QProgressBar):
                widget.setValue(0)
            elif isinstance(widget, QLabel):
                widget.setText("—" if key != "blocking_delays" else "0")
        self.suggestions_list.clear()
        self.suggestions_list.addItem("• Awaiting sketch content…")

    def _compute_metrics(self, code: str) -> Tuple[Dict[str, object], List[str]]:
        """Return heuristically computed metrics and suggestions for the code."""

        lowered = code.lower()
        delay_calls = len(re.findall(r"\bdelay\s*\(", lowered))
        dynamic_allocs = len(
            re.findall(r"\bmalloc\b|\bcalloc\b|\brealloc\b|\bnew\b", lowered)
        )
        string_allocs = len(re.findall(r"\bstring\b", code))

        memory_penalty = string_allocs * 6 + dynamic_allocs * 8 + len(code) // 1000
        memory_score = max(5, min(100, 95 - memory_penalty))

        power_penalty = delay_calls * 4
        power_penalty += len(re.findall(r"\banalogwrite\s*\(", lowered)) * 3
        power_penalty += len(re.findall(r"\bdigitalwrite\s*\(", lowered)) * 2
        busy_waits = len(re.findall(r"while\s*\(true|while\s*\(1", lowered))
        power_penalty += busy_waits * 5
        power_score = max(5, min(100, 90 - power_penalty))

        complexity_tokens = len(
            re.findall(r"\bif\b|\bfor\b|\bwhile\b|\bswitch\b|\bcase\b", lowered)
        )
        complexity_tokens += lowered.count("&&") + lowered.count("||")
        if complexity_tokens < 12:
            complexity = "Low"
        elif complexity_tokens < 28:
            complexity = "Medium"
        else:
            complexity = "High"

        has_isr = bool(re.search(r"\bisr\s*\(|attachinterrupt", lowered))
        has_volatile = bool(re.search(r"\bvolatile\b", lowered))
        if has_isr and not has_volatile:
            interrupt_status = "⚠ Not ISR-safe"
        elif has_isr:
            interrupt_status = "⚠ Review ISR shared data"
        else:
            interrupt_status = "✓ ISR-safe"

        metrics = {
            "memory_efficiency": memory_score,
            "power_efficiency": power_score,
            "code_complexity": complexity,
            "blocking_delays": delay_calls,
            "interrupt_safety": interrupt_status,
        }

        suggestions: List[str] = []
        if memory_score < 70:
            suggestions.append("Reduce dynamic allocations or large global objects to free RAM.")
        if power_score < 70:
            suggestions.append("Limit blocking loops/delay() usage to cut idle power draw.")
        if delay_calls > 0:
            suggestions.append(
                "Consider replacing delay() with millis()-based scheduling for responsiveness."
            )
        if complexity == "High":
            suggestions.append("Refactor complex logic into smaller functions to lower complexity.")
        if "⚠" in interrupt_status:
            suggestions.append(
                "Mark shared ISR variables volatile and avoid heavy work inside handlers."
            )

        return metrics, suggestions

