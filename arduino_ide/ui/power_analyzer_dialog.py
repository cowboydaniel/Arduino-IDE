"""User interface for exploring power consumption analytics."""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

from arduino_ide.services.power_analyzer_service import (
    PowerAnalyzerService,
    PowerMeasurement,
    PowerSession,
    PowerSessionPhase,
)


class PowerAnalyzerDialog(QDialog):
    """Rich dialog that visualises power metrics using charts and tables."""

    def __init__(self, service: PowerAnalyzerService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Power Consumption Analyzer")
        self.setModal(False)
        self.resize(1100, 720)

        self._service = service
        self._active_session_id: Optional[str] = None
        self._session_items: Dict[str, QListWidgetItem] = {}
        self._latest_reports: Dict[str, Dict[str, object]] = {}

        self._build_ui()
        self._connect_signals()
        self._refresh_session_list()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel(
            "Monitor power usage during sketch uploads and runtime telemetry. "
            "Live measurements and heuristic estimates are combined to help spot trends."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal, self)
        layout.addWidget(splitter, 1)

        # Left column: sessions and actions
        sessions_container = QWidget(splitter)
        sessions_layout = QVBoxLayout(sessions_container)
        sessions_layout.setContentsMargins(0, 0, 0, 0)
        sessions_layout.setSpacing(6)

        sessions_label = QLabel("Sessions")
        sessions_label.setStyleSheet("font-weight: 600;")
        sessions_layout.addWidget(sessions_label)

        self.session_list = QListWidget(sessions_container)
        self.session_list.setAlternatingRowColors(True)
        sessions_layout.addWidget(self.session_list, 1)

        self.summary_label = QLabel("Select a session to view details.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setObjectName("powerSummaryLabel")
        sessions_layout.addWidget(self.summary_label)

        self.export_button = QPushButton("Export Report…", sessions_container)
        self.export_button.setEnabled(False)
        sessions_layout.addWidget(self.export_button)

        sessions_layout.addStretch(1)

        # Right column: analytics
        analytics_splitter = QSplitter(Qt.Vertical, splitter)

        chart_container = QWidget(analytics_splitter)
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(4)

        chart_label = QLabel("Power & Energy Trend")
        chart_label.setStyleSheet("font-weight: 600;")
        chart_layout.addWidget(chart_label)

        self.chart = QChart()
        self.chart.setTitle("Power (mW) and cumulative energy (mJ) over time")
        self.chart.legend().setVisible(True)

        self.power_series = QLineSeries()
        self.power_series.setName("Power (mW)")
        self.energy_series = QLineSeries()
        self.energy_series.setName("Energy (mJ)")
        self.chart.addSeries(self.power_series)
        self.chart.addSeries(self.energy_series)

        self.time_axis = QValueAxis()
        self.time_axis.setTitleText("Time (s)")
        self.time_axis.setLabelFormat("%d")
        self.chart.addAxis(self.time_axis, Qt.AlignBottom)

        self.power_axis = QValueAxis()
        self.power_axis.setTitleText("Power (mW)")
        self.chart.addAxis(self.power_axis, Qt.AlignLeft)

        self.energy_axis = QValueAxis()
        self.energy_axis.setTitleText("Energy (mJ)")
        self.chart.addAxis(self.energy_axis, Qt.AlignRight)

        self.power_series.attachAxis(self.time_axis)
        self.power_series.attachAxis(self.power_axis)
        self.energy_series.attachAxis(self.time_axis)
        self.energy_series.attachAxis(self.energy_axis)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        chart_layout.addWidget(self.chart_view, 1)

        table_container = QWidget(analytics_splitter)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(6)

        table_label = QLabel("Measurements")
        table_label.setStyleSheet("font-weight: 600;")
        table_layout.addWidget(table_label)

        headers = [
            "Timestamp",
            "Stage",
            "Voltage (V)",
            "Current (mA)",
            "Power (mW)",
            "Δ Energy (mJ)",
            "Total Energy (mJ)",
            "Source",
        ]
        self.measurement_table = QTableWidget(0, len(headers), table_container)
        self.measurement_table.setHorizontalHeaderLabels(headers)
        self.measurement_table.horizontalHeader().setStretchLastSection(True)
        self.measurement_table.verticalHeader().setVisible(False)
        self.measurement_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.measurement_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.measurement_table.setSelectionMode(QTableWidget.NoSelection)
        self.measurement_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.measurement_table, 3)

        recommendations_label = QLabel("Recommendations")
        recommendations_label.setStyleSheet("font-weight: 600;")
        table_layout.addWidget(recommendations_label)

        self.report_text = QTextEdit(table_container)
        self.report_text.setReadOnly(True)
        self.report_text.setPlaceholderText("Reports will appear once data is available.")
        table_layout.addWidget(self.report_text, 2)

        splitter.addWidget(sessions_container)
        splitter.addWidget(analytics_splitter)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        analytics_splitter.setStretchFactor(0, 3)
        analytics_splitter.setStretchFactor(1, 4)

    def _connect_signals(self) -> None:
        self.session_list.currentItemChanged.connect(self._on_session_selected)
        self.export_button.clicked.connect(self._on_export_report)

        self._service.session_started.connect(self._on_session_started)
        self._service.session_updated.connect(self._on_session_updated)
        self._service.measurement_added.connect(self._on_measurement_added)
        self._service.session_finished.connect(self._on_session_finished)
        self._service.report_generated.connect(self._on_report_generated)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def _refresh_session_list(self) -> None:
        sessions = self._service.list_sessions()

        self.session_list.blockSignals(True)
        self.session_list.clear()
        self._session_items.clear()

        for session in sessions:
            item = QListWidgetItem(self._format_session_label(session))
            item.setData(Qt.UserRole, session.session_id)
            self.session_list.addItem(item)
            self._session_items[session.session_id] = item

        self.session_list.blockSignals(False)

        if not sessions:
            self.summary_label.setText("No sessions captured yet.")
            self.export_button.setEnabled(False)
            self._active_session_id = None
            self._clear_measurements()
            return

        if self._active_session_id and self._active_session_id in self._session_items:
            self.session_list.setCurrentItem(self._session_items[self._active_session_id])
        else:
            self.session_list.setCurrentRow(self.session_list.count() - 1)

    def _format_session_label(self, session: PowerSession) -> str:
        status = "active" if not session.ended_at else "completed"
        return (
            f"{session.phase.value.title()} @ {session.started_at.strftime('%H:%M:%S')}"
            f"  ({status})"
        )

    def _on_session_started(self, session: PowerSession) -> None:
        item = QListWidgetItem(self._format_session_label(session))
        item.setData(Qt.UserRole, session.session_id)
        self.session_list.addItem(item)
        self._session_items[session.session_id] = item
        self.session_list.setCurrentItem(item)

    def _on_session_finished(self, session: PowerSession) -> None:
        item = self._session_items.get(session.session_id)
        if item:
            item.setText(self._format_session_label(session))
        if self._active_session_id == session.session_id:
            self._update_summary(session)
            self.export_button.setEnabled(True)

    def _on_session_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        if not current:
            self._active_session_id = None
            self._clear_measurements()
            self.export_button.setEnabled(False)
            return

        session_id = current.data(Qt.UserRole)
        self._active_session_id = session_id
        session = self._resolve_session(session_id)
        if not session:
            return

        self._populate_measurements(session)
        self._update_summary(session)
        report = self._latest_reports.get(session.session_id) or self._service.generate_report(session.session_id)
        if report:
            self._update_report(session.session_id, report)
        self.export_button.setEnabled(True)

    def _resolve_session(self, session_id: str) -> Optional[PowerSession]:
        for session in self._service.list_sessions():
            if session.session_id == session_id:
                return session
        return None

    # ------------------------------------------------------------------
    # Measurement updates
    # ------------------------------------------------------------------
    def _on_session_updated(self, session: PowerSession) -> None:
        if self._active_session_id == session.session_id:
            self._update_summary(session)

    def _on_measurement_added(self, measurement: PowerMeasurement) -> None:
        if self._active_session_id != measurement.session_id:
            return

        session = self._resolve_session(measurement.session_id)
        if not session:
            return

        self._append_measurement_row(measurement)
        self._append_chart_point(measurement, session)
        self._update_summary(session)

    def _populate_measurements(self, session: PowerSession) -> None:
        self.measurement_table.setRowCount(0)
        self.power_series.clear()
        self.energy_series.clear()

        for measurement in session.measurements:
            self._append_measurement_row(measurement)
            self._append_chart_point(measurement, session)

        self._recompute_axes(session)

    def _append_measurement_row(self, measurement: PowerMeasurement) -> None:
        row = self.measurement_table.rowCount()
        self.measurement_table.insertRow(row)

        values = [
            measurement.timestamp.strftime("%H:%M:%S"),
            measurement.stage,
            f"{measurement.voltage_v:.2f}",
            f"{measurement.current_ma:.2f}",
            f"{measurement.power_mw:.2f}",
            f"{measurement.energy_increment_mj:.2f}",
            f"{measurement.cumulative_energy_mj:.2f}",
            measurement.source,
        ]

        for col, text in enumerate(values):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            self.measurement_table.setItem(row, col, item)

        self.measurement_table.scrollToBottom()

    def _append_chart_point(self, measurement: PowerMeasurement, session: PowerSession) -> None:
        time_base = session.measurements[0].timestamp if session.measurements else session.started_at
        seconds = max(0.0, (measurement.timestamp - time_base).total_seconds())
        self.power_series.append(seconds, measurement.power_mw)
        self.energy_series.append(seconds, measurement.cumulative_energy_mj)
        self._recompute_axes(session)

    def _recompute_axes(self, session: PowerSession) -> None:
        if not session.measurements:
            self.time_axis.setRange(0, 1)
            self.power_axis.setRange(0, 1)
            self.energy_axis.setRange(0, 1)
            return

        first = session.measurements[0].timestamp
        last = session.measurements[-1].timestamp
        duration = max(1.0, (last - first).total_seconds())
        peak_power = max(m.power_mw for m in session.measurements)
        peak_energy = max(m.cumulative_energy_mj for m in session.measurements)

        self.time_axis.setRange(0, duration)
        self.power_axis.setRange(0, max(1.0, peak_power * 1.1))
        self.energy_axis.setRange(0, max(1.0, peak_energy * 1.05))

    def _clear_measurements(self) -> None:
        self.measurement_table.setRowCount(0)
        self.power_series.clear()
        self.energy_series.clear()
        self.summary_label.setText("Select a session to view details.")
        self.report_text.clear()

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def _update_summary(self, session: PowerSession) -> None:
        board = session.board_name or "Unknown board"
        duration = session.duration_seconds()
        status = "running" if not session.ended_at else "completed"
        if session.phase == PowerSessionPhase.UPLOAD:
            context = "upload workflow"
        else:
            context = "runtime monitoring"
        summary = (
            f"<b>{session.phase.value.title()}</b> session ({context}) on <b>{board}</b> "
            f"is {status}.<br/>"
            f"Average power: <b>{session.average_power_mw():.2f} mW</b>, "
            f"Peak power: <b>{session.peak_power_mw():.2f} mW</b>, "
            f"Energy: <b>{session.total_energy_mj():.2f} mJ</b> over {duration:.1f}s."
        )
        self.summary_label.setText(summary)

    def _on_report_generated(self, session_id: str, report: Dict[str, object]) -> None:
        self._latest_reports[session_id] = report
        if self._active_session_id == session_id:
            self._update_report(session_id, report)

    def _update_report(self, session_id: str, report: Dict[str, object]) -> None:
        session_info = report.get("session", {})
        recommendations = report.get("recommendations", [])
        lines = [
            f"Session: {session_info.get('session_id', session_id)}",
            f"Phase: {session_info.get('phase', 'unknown')}",
            f"Duration: {session_info.get('duration_seconds', 0):.1f} s",
            f"Average power: {session_info.get('average_power_mw', 0):.2f} mW",
            f"Peak power: {session_info.get('peak_power_mw', 0):.2f} mW",
            f"Total energy: {session_info.get('total_energy_mj', 0):.2f} mJ",
            "",
            "Recommendations:",
        ]
        for rec in recommendations:
            lines.append(f" • {rec}")

        self.report_text.setPlainText("\n".join(lines))

    def _on_export_report(self) -> None:
        if not self._active_session_id:
            QMessageBox.information(self, "Export Report", "Select a session first.")
            return

        report = self._latest_reports.get(self._active_session_id) or self._service.generate_report(
            self._active_session_id
        )
        if not report:
            QMessageBox.warning(self, "Export Report", "No report data available for this session yet.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export Power Report", filter="JSON Files (*.json);;All Files (*.*)")
        if not path:
            return

        try:
            import json

            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2)
        except OSError as exc:
            QMessageBox.critical(self, "Export Report", f"Failed to write report: {exc}")
            return

        QMessageBox.information(self, "Export Report", "Report saved successfully.")

