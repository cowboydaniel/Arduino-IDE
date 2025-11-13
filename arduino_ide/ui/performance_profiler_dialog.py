"""Dialog that visualises performance profiling data."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QBrush
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

from arduino_ide.services.performance_profiler_service import (
    PerformanceProfilerService,
    ProfileMode,
    ProfilingSession,
)


class PerformanceProfilerDialog(QDialog):
    """Interactive dashboard for browsing profiling sessions."""

    start_requested = Signal(object)  # ProfileMode
    stop_requested = Signal()
    export_requested = Signal()
    location_requested = Signal(str, int)
    session_changed = Signal(str)

    def __init__(self, service: PerformanceProfilerService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Performance Profiler")
        self.setModal(False)
        self.resize(1180, 760)

        self._service = service
        self._session_items: Dict[str, QListWidgetItem] = {}
        self._current_session_id: Optional[str] = None
        self._profiling_active = False

        self._build_ui()
        self._connect_widget_signals()
        self._connect_service_signals()
        self._refresh_sessions()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel(
            "Profile sketches to identify hotspots, timing regressions, and memory"
            " pressure. Double-click hotspot rows to jump to source lines."
        )
        header.setWordWrap(True)
        header.setObjectName("profilerHeaderLabel")
        layout.addWidget(header)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(6)

        mode_label = QLabel("Mode:")
        controls_layout.addWidget(mode_label)

        self.mode_combo = QComboBox(self)
        self.mode_combo.addItem("Host (desktop)", ProfileMode.HOST_BASED)
        self.mode_combo.addItem("On Device", ProfileMode.ON_DEVICE)
        self.mode_combo.addItem("Simulation", ProfileMode.SIMULATION)
        controls_layout.addWidget(self.mode_combo)

        controls_layout.addStretch(1)

        self.start_button = QPushButton("Start Profiling", self)
        self.start_button.setObjectName("profilerStartButton")
        controls_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop", self)
        self.stop_button.setEnabled(False)
        self.stop_button.setObjectName("profilerStopButton")
        controls_layout.addWidget(self.stop_button)

        self.export_button = QPushButton("Export Report…", self)
        self.export_button.setEnabled(False)
        self.export_button.setObjectName("profilerExportButton")
        controls_layout.addWidget(self.export_button)

        layout.addLayout(controls_layout)

        self.context_label = QLabel("Active project: —")
        self.context_label.setStyleSheet("color: #555;")
        layout.addWidget(self.context_label)

        splitter = QSplitter(Qt.Horizontal, self)
        layout.addWidget(splitter, 1)

        # Left column with session list
        sessions_widget = QWidget(splitter)
        sessions_layout = QVBoxLayout(sessions_widget)
        sessions_layout.setContentsMargins(0, 0, 0, 0)
        sessions_layout.setSpacing(6)

        sessions_label = QLabel("Sessions")
        sessions_label.setStyleSheet("font-weight: 600;")
        sessions_layout.addWidget(sessions_label)

        self.session_list = QListWidget(sessions_widget)
        self.session_list.setAlternatingRowColors(True)
        sessions_layout.addWidget(self.session_list, 1)

        self.summary_label = QLabel("Start a profiling session to view metrics.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setObjectName("profilerSummaryLabel")
        sessions_layout.addWidget(self.summary_label)

        splitter.addWidget(sessions_widget)

        # Right column with analytics
        analytics_splitter = QSplitter(Qt.Vertical, splitter)
        splitter.addWidget(analytics_splitter)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)

        timeline_container = QWidget(analytics_splitter)
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(4)

        timeline_label = QLabel("Memory Timeline")
        timeline_label.setStyleSheet("font-weight: 600;")
        timeline_layout.addWidget(timeline_label)

        self.timeline_chart = QChart()
        self.timeline_chart.setTitle("Heap and stack usage over profiling run")
        self.timeline_chart.legend().setVisible(True)

        self.heap_series = QLineSeries()
        self.heap_series.setName("Heap (KB)")
        self.stack_series = QLineSeries()
        self.stack_series.setName("Stack (KB)")
        self.timeline_chart.addSeries(self.heap_series)
        self.timeline_chart.addSeries(self.stack_series)

        self.time_axis = QValueAxis()
        self.time_axis.setTitleText("Time (s)")
        self.time_axis.setLabelFormat("%.1f")
        self.timeline_chart.addAxis(self.time_axis, Qt.AlignBottom)

        self.memory_axis = QValueAxis()
        self.memory_axis.setTitleText("Usage (KB)")
        self.memory_axis.setLabelFormat("%.0f")
        self.timeline_chart.addAxis(self.memory_axis, Qt.AlignLeft)

        self.heap_series.attachAxis(self.time_axis)
        self.heap_series.attachAxis(self.memory_axis)
        self.stack_series.attachAxis(self.time_axis)
        self.stack_series.attachAxis(self.memory_axis)

        self.timeline_chart_view = QChartView(self.timeline_chart)
        self.timeline_chart_view.setRenderHint(QPainter.Antialiasing)
        timeline_layout.addWidget(self.timeline_chart_view, 1)

        self.timeline_placeholder = QLabel("Memory samples will appear once profiling captures runtime data.")
        self.timeline_placeholder.setAlignment(Qt.AlignCenter)
        self.timeline_placeholder.setStyleSheet("color: #777; font-style: italic;")
        timeline_layout.addWidget(self.timeline_placeholder)

        bottom_splitter = QSplitter(Qt.Horizontal, analytics_splitter)
        analytics_splitter.setStretchFactor(0, 3)
        analytics_splitter.setStretchFactor(1, 4)

        # Hotspot table
        hotspots_container = QWidget(bottom_splitter)
        hotspots_layout = QVBoxLayout(hotspots_container)
        hotspots_layout.setContentsMargins(0, 0, 0, 0)
        hotspots_layout.setSpacing(4)

        hotspots_label = QLabel("Hotspots")
        hotspots_label.setStyleSheet("font-weight: 600;")
        hotspots_layout.addWidget(hotspots_label)

        headers = [
            "Function",
            "Calls",
            "Total (ms)",
            "Avg (µs)",
            "% Total",
            "File",
            "Line",
        ]
        self.hotspot_table = QTableWidget(0, len(headers), hotspots_container)
        self.hotspot_table.setHorizontalHeaderLabels(headers)
        self.hotspot_table.verticalHeader().setVisible(False)
        self.hotspot_table.setAlternatingRowColors(True)
        self.hotspot_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.hotspot_table.setSelectionMode(QTableWidget.SingleSelection)
        self.hotspot_table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.hotspot_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        hotspots_layout.addWidget(self.hotspot_table, 1)

        bottom_splitter.addWidget(hotspots_container)

        # Bottlenecks and suggestions
        details_container = QWidget(bottom_splitter)
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(4)

        bottleneck_label = QLabel("Detected Bottlenecks")
        bottleneck_label.setStyleSheet("font-weight: 600;")
        details_layout.addWidget(bottleneck_label)

        self.bottleneck_table = QTableWidget(0, 4, details_container)
        self.bottleneck_table.setHorizontalHeaderLabels(["Function", "Severity", "Type", "Description"])
        self.bottleneck_table.verticalHeader().setVisible(False)
        self.bottleneck_table.setWordWrap(True)
        self.bottleneck_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.bottleneck_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bottleneck_table.setSelectionMode(QTableWidget.NoSelection)
        bottleneck_header = self.bottleneck_table.horizontalHeader()
        bottleneck_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        bottleneck_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        bottleneck_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        bottleneck_header.setSectionResizeMode(3, QHeaderView.Stretch)
        details_layout.addWidget(self.bottleneck_table, 2)

        suggestions_label = QLabel("Optimization Suggestions")
        suggestions_label.setStyleSheet("font-weight: 600;")
        details_layout.addWidget(suggestions_label)

        self.suggestions_text = QTextEdit(details_container)
        self.suggestions_text.setReadOnly(True)
        self.suggestions_text.setPlaceholderText("Recommendations will appear after profiling data is analysed.")
        details_layout.addWidget(self.suggestions_text, 1)

        bottom_splitter.addWidget(details_container)
        bottom_splitter.setStretchFactor(0, 3)
        bottom_splitter.setStretchFactor(1, 4)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------
    def _connect_widget_signals(self) -> None:
        self.start_button.clicked.connect(self._on_start_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.export_button.clicked.connect(self._on_export_clicked)
        self.session_list.currentItemChanged.connect(self._on_session_selected)
        self.hotspot_table.cellDoubleClicked.connect(self._on_hotspot_activated)

    def _connect_service_signals(self) -> None:
        self._service.profiling_started.connect(self._on_service_session_started)
        self._service.profiling_finished.connect(self._on_service_session_finished)
        self._service.function_profiled.connect(self._on_service_data_updated)
        self._service.memory_snapshot_taken.connect(self._on_service_data_updated)
        self._service.bottleneck_detected.connect(self._on_service_data_updated)

    # ------------------------------------------------------------------
    # Widget event handlers
    # ------------------------------------------------------------------
    def _on_start_clicked(self) -> None:
        mode = self.mode_combo.currentData()
        if mode is None:
            mode = ProfileMode.HOST_BASED
        self.start_requested.emit(mode)

    def _on_stop_clicked(self) -> None:
        self.stop_requested.emit()

    def _on_export_clicked(self) -> None:
        self.export_requested.emit()

    def _on_session_selected(self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]) -> None:
        session_id = current.data(Qt.UserRole) if current else ""
        self._current_session_id = session_id or None
        if session_id:
            session = self._service.get_session(session_id)
            if session:
                self._display_session(session)
        else:
            self._clear_details()
        self.export_button.setEnabled(bool(session_id))
        self.session_changed.emit(session_id or "")

    def _on_hotspot_activated(self, row: int, _column: int) -> None:
        item = self.hotspot_table.item(row, 0)
        if not item:
            return
        payload = item.data(Qt.UserRole)
        if not payload:
            return
        file_path, line_number = payload
        if not file_path:
            return
        self.location_requested.emit(file_path, max(line_number or 1, 1))

    # ------------------------------------------------------------------
    # Service signal handlers
    # ------------------------------------------------------------------
    def _on_service_session_started(self, session_id: str) -> None:
        session = self._service.get_session(session_id)
        if not session:
            return
        self._profiling_active = True
        self._add_or_update_session_item(session)
        self.stop_button.setEnabled(True)
        self.start_button.setEnabled(False)
        self.summary_label.setText(
            f"Profiling started at {session.started_at.strftime('%H:%M:%S')} in {session.mode.name.title()} mode."
        )
        self._select_session(session_id)

    def _on_service_session_finished(self, session_id: str) -> None:
        session = self._service.get_session(session_id)
        self._profiling_active = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if session:
            self._add_or_update_session_item(session)
            if self._current_session_id == session_id:
                self._display_session(session)
            self.summary_label.setText(
                f"Profiling completed in {session.duration_seconds():.2f}s. Review hotspots for optimisation opportunities."
            )
        self.export_button.setEnabled(bool(session_id))

    def _on_service_data_updated(self, _payload) -> None:  # noqa: ANN001
        if not self._current_session_id:
            return
        session = self._service.get_session(self._current_session_id)
        if not session:
            return
        self._display_session(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def current_session_id(self) -> Optional[str]:
        return self._current_session_id

    def update_context(self, project_path: str, board: str, port: str) -> None:
        details = []
        if project_path:
            details.append(f"Project: {project_path}")
        if board:
            details.append(f"Board: {board}")
        if port:
            details.append(f"Port: {port}")
        if details:
            self.context_label.setText(" • ".join(details))
        else:
            self.context_label.setText("Active project: —")

    def set_profiling_active(self, active: bool) -> None:
        self._profiling_active = active
        self.start_button.setEnabled(not active)
        self.stop_button.setEnabled(active)

    def focus_session(self, session_id: str) -> None:
        if not session_id:
            return
        self._select_session(session_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _refresh_sessions(self) -> None:
        self.session_list.blockSignals(True)
        self.session_list.clear()
        self._session_items.clear()

        sessions = sorted(self._service.sessions.values(), key=lambda s: s.started_at, reverse=True)
        for session in sessions:
            self._add_or_update_session_item(session)

        self.session_list.blockSignals(False)

        if sessions:
            latest_id = sessions[0].session_id
            self._select_session(latest_id)
        else:
            self._clear_details()

    def _add_or_update_session_item(self, session: ProfilingSession) -> None:
        item = self._session_items.get(session.session_id)
        label = self._format_session_label(session)
        if item is None:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, session.session_id)
            self.session_list.addItem(item)
            self._session_items[session.session_id] = item
        else:
            item.setText(label)

    def _format_session_label(self, session: ProfilingSession) -> str:
        time_str = session.started_at.strftime("%Y-%m-%d %H:%M:%S")
        status = "Active" if session.ended_at is None else f"{session.duration_seconds():.2f}s"
        return f"{time_str} — {session.mode.name.title()} ({status})"

    def _select_session(self, session_id: str) -> None:
        item = self._session_items.get(session_id)
        if not item:
            return
        row = self.session_list.row(item)
        if row < 0:
            return
        self.session_list.setCurrentRow(row)

    def _display_session(self, session: ProfilingSession) -> None:
        self._current_session_id = session.session_id
        duration = session.duration_seconds() or 0.0
        function_count = len(session.function_profiles)
        bottleneck_count = len(session.bottlenecks)
        self.summary_label.setText(
            f"Session {session.session_id} • Duration: {duration:.2f}s • Functions: {function_count} • "
            f"Bottlenecks: {bottleneck_count}"
        )
        self._populate_memory_chart(session)
        self._populate_hotspots(session)
        self._populate_bottlenecks(session)
        self._populate_suggestions(session)

    def _clear_details(self) -> None:
        self.summary_label.setText("Start a profiling session to view metrics.")
        self.heap_series.clear()
        self.stack_series.clear()
        self.hotspot_table.setRowCount(0)
        self.bottleneck_table.setRowCount(0)
        self.suggestions_text.clear()
        self.timeline_placeholder.setVisible(True)

    def _populate_memory_chart(self, session: ProfilingSession) -> None:
        snapshots = list(session.memory_snapshots)
        self.heap_series.blockSignals(True)
        self.stack_series.blockSignals(True)
        self.heap_series.clear()
        self.stack_series.clear()

        if not snapshots:
            self.timeline_placeholder.setVisible(True)
            self.heap_series.blockSignals(False)
            self.stack_series.blockSignals(False)
            self.timeline_chart.setTitle("Heap and stack usage over profiling run")
            self.time_axis.setRange(0, 1)
            self.memory_axis.setRange(0, 1)
            return

        self.timeline_placeholder.setVisible(False)
        snapshots.sort(key=lambda snap: snap.timestamp)
        start_time = session.started_at
        max_time = 0.0
        max_usage = 0.0

        for snap in snapshots:
            delta = (snap.timestamp - start_time).total_seconds() if start_time else 0.0
            heap_kb = snap.heap_used / 1024.0
            stack_kb = snap.stack_used / 1024.0
            self.heap_series.append(delta, heap_kb)
            self.stack_series.append(delta, stack_kb)
            max_time = max(max_time, delta)
            max_usage = max(max_usage, heap_kb, stack_kb)

        self.timeline_chart.setTitle(
            f"Memory usage over time (max {max_usage:.0f} KB across {len(snapshots)} samples)"
        )
        self.time_axis.setRange(0, max(max_time, 1.0))
        self.memory_axis.setRange(0, max(max_usage * 1.1, 1.0))

        self.heap_series.blockSignals(False)
        self.stack_series.blockSignals(False)

    def _populate_hotspots(self, session: ProfilingSession) -> None:
        profiles = list(session.function_profiles.values())
        total_time_us = session.total_execution_time_us or sum(p.total_time_us for p in profiles)
        self.hotspot_table.setRowCount(0)
        if not profiles:
            return

        profiles.sort(key=lambda p: p.total_time_us, reverse=True)

        for profile in profiles:
            profile.update_stats()
            row = self.hotspot_table.rowCount()
            self.hotspot_table.insertRow(row)

            name_item = QTableWidgetItem(profile.name or "<anonymous>")
            name_item.setData(Qt.UserRole, (profile.file_path, profile.line_number))
            self.hotspot_table.setItem(row, 0, name_item)

            calls_item = QTableWidgetItem(str(profile.call_count))
            calls_item.setTextAlignment(Qt.AlignCenter)
            self.hotspot_table.setItem(row, 1, calls_item)

            total_ms = profile.total_time_us / 1000.0
            total_item = QTableWidgetItem(f"{total_ms:.2f}")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.hotspot_table.setItem(row, 2, total_item)

            avg_item = QTableWidgetItem(f"{profile.avg_time_us:.1f}")
            avg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.hotspot_table.setItem(row, 3, avg_item)

            percentage = profile.percentage_of_total(total_time_us) if total_time_us else 0.0
            pct_item = QTableWidgetItem(f"{percentage:.1f}%")
            pct_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.hotspot_table.setItem(row, 4, pct_item)

            file_item = QTableWidgetItem(profile.file_path or "—")
            self.hotspot_table.setItem(row, 5, file_item)

            line_text = str(profile.line_number) if profile.line_number else "—"
            line_item = QTableWidgetItem(line_text)
            line_item.setTextAlignment(Qt.AlignCenter)
            self.hotspot_table.setItem(row, 6, line_item)

    def _populate_bottlenecks(self, session: ProfilingSession) -> None:
        bottlenecks = list(session.bottlenecks)
        self.bottleneck_table.setRowCount(0)
        if not bottlenecks:
            return

        severity_colors = {
            "high": QColor(214, 45, 32),
            "medium": QColor(216, 144, 43),
            "low": QColor(84, 169, 91),
        }

        for bottleneck in bottlenecks:
            row = self.bottleneck_table.rowCount()
            self.bottleneck_table.insertRow(row)

            function_item = QTableWidgetItem(bottleneck.function_name or "<unknown>")
            self.bottleneck_table.setItem(row, 0, function_item)

            severity_item = QTableWidgetItem(bottleneck.severity.title())
            color = severity_colors.get(bottleneck.severity.lower())
            if color:
                severity_item.setForeground(QBrush(color))
            self.bottleneck_table.setItem(row, 1, severity_item)

            type_item = QTableWidgetItem(bottleneck.issue_type.title())
            self.bottleneck_table.setItem(row, 2, type_item)

            description_parts = [bottleneck.description]
            if bottleneck.suggestion:
                description_parts.append(f"Suggestion: {bottleneck.suggestion}")
            description_item = QTableWidgetItem("\n".join(filter(None, description_parts)))
            self.bottleneck_table.setItem(row, 3, description_item)

    def _populate_suggestions(self, session: ProfilingSession) -> None:
        suggestions = self._service.get_optimization_suggestions(session.session_id)
        if not suggestions:
            self.suggestions_text.setPlainText("No specific suggestions generated for this session.")
            return
        bullet_lines = "\n".join(f"• {s}" for s in suggestions)
        self.suggestions_text.setPlainText(bullet_lines)

    # ------------------------------------------------------------------
    # Memory snapshot helpers for tests / debugging
    # ------------------------------------------------------------------
    def debug_dump_current_session(self) -> Optional[Dict[str, object]]:
        """Return a serialisable snapshot of the current session for tests."""
        if not self._current_session_id:
            return None
        session = self._service.get_session(self._current_session_id)
        if not session:
            return None
        payload = asdict(session)
        payload["started_at"] = session.started_at.isoformat()
        payload["ended_at"] = session.ended_at.isoformat() if session.ended_at else None
        return payload
