"""Power consumption analysis service for Arduino IDE Modern.

This module provides a centralised place to collect, aggregate and analyse
power measurements that originate from different parts of the IDE such as
upload operations, serial monitor telemetry or profiling hooks.  The service
derives estimated values when no direct measurements are available so that the
Power Analyzer dialog can always present a meaningful data stream.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, Signal


class PowerSessionPhase(str, Enum):
    """High level phases that a power monitoring session can belong to."""

    UPLOAD = "upload"
    RUNTIME = "runtime"


class PowerSessionStage(str, Enum):
    """Stages within a session used for estimating load profiles."""

    IDLE = "idle"
    COMPILE = "compile"
    UPLOAD = "upload"
    RUNNING = "running"
    COOL_DOWN = "cool_down"


@dataclass
class PowerMeasurement:
    """Single power reading captured during a session."""

    session_id: str
    timestamp: datetime
    voltage_v: float
    current_ma: float
    power_mw: float
    stage: str
    source: str = "estimated"
    notes: str = ""
    energy_increment_mj: float = 0.0
    cumulative_energy_mj: float = 0.0


@dataclass
class PowerSession:
    """Represents the lifecycle of a monitored activity."""

    session_id: str
    phase: PowerSessionPhase
    started_at: datetime
    board_name: str = ""
    board_fqbn: str = ""
    port: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)
    measurements: List[PowerMeasurement] = field(default_factory=list)
    stage: PowerSessionStage = PowerSessionStage.IDLE
    ended_at: Optional[datetime] = None

    def duration_seconds(self) -> float:
        """Return the total captured duration in seconds."""

        if self.measurements:
            start = self.measurements[0].timestamp
            end = self.measurements[-1].timestamp
            return max(0.0, (end - start).total_seconds())
        if self.ended_at:
            return max(0.0, (self.ended_at - self.started_at).total_seconds())
        return max(0.0, (datetime.now() - self.started_at).total_seconds())

    def total_energy_mj(self) -> float:
        """Return cumulative consumed energy in milli-joules."""

        if not self.measurements:
            return 0.0
        return self.measurements[-1].cumulative_energy_mj

    def average_power_mw(self) -> float:
        """Return the average power draw for the session."""

        duration = self.duration_seconds()
        if duration <= 0:
            return 0.0
        return self.total_energy_mj() / duration

    def peak_power_mw(self) -> float:
        """Return the highest recorded instantaneous power."""

        if not self.measurements:
            return 0.0
        return max(m.power_mw for m in self.measurements)

    def to_dict(self) -> Dict[str, object]:
        """Serialise session data for reporting."""

        return {
            "session_id": self.session_id,
            "phase": self.phase.value,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "board": {
                "name": self.board_name,
                "fqbn": self.board_fqbn,
            },
            "port": self.port,
            "duration_seconds": self.duration_seconds(),
            "average_power_mw": self.average_power_mw(),
            "peak_power_mw": self.peak_power_mw(),
            "total_energy_mj": self.total_energy_mj(),
            "metadata": dict(self.metadata),
        }


class PowerAnalyzerService(QObject):
    """Service responsible for aggregating and analysing power usage data."""

    session_started = Signal(object)
    session_updated = Signal(object)
    measurement_added = Signal(object)
    session_finished = Signal(object)
    report_generated = Signal(str, dict)

    ESTIMATION_INTERVAL_MS = 1000
    MAX_SESSION_HISTORY = 12

    _DEFAULT_VOLTAGE = 5.0
    _DEFAULT_CURRENT_MA = 80.0

    _STAGE_MULTIPLIERS: Dict[PowerSessionStage, float] = {
        PowerSessionStage.IDLE: 0.25,
        PowerSessionStage.COMPILE: 0.6,
        PowerSessionStage.UPLOAD: 1.25,
        PowerSessionStage.RUNNING: 0.85,
        PowerSessionStage.COOL_DOWN: 0.4,
    }

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._sessions: Dict[str, PowerSession] = {}
        self._session_order: List[str] = []
        self._active_session_id: Optional[str] = None
        self._baseline_current_ma: float = self._DEFAULT_CURRENT_MA
        self._board_voltage_v: float = self._DEFAULT_VOLTAGE
        self._stage_multiplier: float = self._STAGE_MULTIPLIERS[PowerSessionStage.IDLE]
        self._estimation_enabled = False
        self._last_estimate_timestamp: Optional[datetime] = None
        self._rng = random.Random()

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self.ESTIMATION_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._generate_estimate)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------
    @property
    def active_session(self) -> Optional[PowerSession]:
        """Return the currently active session, if any."""

        if not self._active_session_id:
            return None
        return self._sessions.get(self._active_session_id)

    def list_sessions(self) -> List[PowerSession]:
        """Return sessions in chronological order."""

        return [self._sessions[sid] for sid in self._session_order if sid in self._sessions]

    def start_upload_session(
        self,
        *,
        board: Optional[object] = None,
        port: str = "",
        sketch_path: str = "",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Start a new session tied to an upload workflow."""

        return self._begin_session(
            phase=PowerSessionPhase.UPLOAD,
            stage=PowerSessionStage.COMPILE,
            board=board,
            port=port,
            metadata=self._build_metadata(board, sketch_path, metadata),
            enable_estimation=True,
        )

    def start_runtime_session(
        self,
        *,
        board: Optional[object] = None,
        port: str = "",
        metadata: Optional[Dict[str, str]] = None,
        enable_estimation: bool = True,
    ) -> str:
        """Start a new runtime monitoring session."""

        return self._begin_session(
            phase=PowerSessionPhase.RUNTIME,
            stage=PowerSessionStage.RUNNING,
            board=board,
            port=port,
            metadata=metadata or {},
            enable_estimation=enable_estimation,
        )

    def ensure_runtime_session(
        self,
        *,
        board: Optional[object] = None,
        port: str = "",
        metadata: Optional[Dict[str, str]] = None,
        enable_estimation: bool = True,
    ) -> Optional[str]:
        """Ensure a runtime session exists and return its identifier."""

        session = self.active_session
        if session and session.phase == PowerSessionPhase.RUNTIME:
            return session.session_id
        return self.start_runtime_session(
            board=board,
            port=port,
            metadata=metadata,
            enable_estimation=enable_estimation,
        )

    def update_stage(self, stage: PowerSessionStage | str) -> None:
        """Update the active session stage."""

        session = self.active_session
        if not session:
            return

        if isinstance(stage, str):
            try:
                stage_enum = PowerSessionStage(stage)
            except ValueError:
                stage_enum = PowerSessionStage.IDLE
        else:
            stage_enum = stage

        session.stage = stage_enum
        self._stage_multiplier = self._STAGE_MULTIPLIERS.get(stage_enum, 1.0)
        self.session_updated.emit(session)

    def finish_active_session(self, *, success: bool = True, reason: str = "completed") -> None:
        """Stop the active session and emit a final report."""

        session = self.active_session
        if not session:
            return

        if self._estimation_enabled:
            # Produce a final estimate before shutting down to capture the tail
            self._generate_estimate(force=True)

        self._poll_timer.stop()
        self._estimation_enabled = False
        session.ended_at = datetime.now()
        session.metadata.setdefault("outcome", "success" if success else "failure")
        session.metadata.setdefault("completion_reason", reason)

        self.session_finished.emit(session)
        report = self.generate_report(session.session_id)
        self.report_generated.emit(session.session_id, report)
        self._active_session_id = None
        self._last_estimate_timestamp = None

    def abort_active_session(self, reason: str = "interrupted") -> None:
        """Abort the current session due to an error."""

        session = self.active_session
        if not session:
            return
        session.metadata["outcome"] = "failure"
        session.metadata["completion_reason"] = reason
        self.finish_active_session(success=False, reason=reason)

    # ------------------------------------------------------------------
    # Data ingestion
    # ------------------------------------------------------------------
    def ingest_cli_output(self, operation: Optional[str], text: str) -> None:
        """Allow upload sessions to react to CLI output for context."""

        if not text or not operation:
            return

        session = self.active_session
        if not session or session.phase != PowerSessionPhase.UPLOAD:
            return

        lowered = text.lower()
        if "progress" in lowered or "%" in lowered:
            # Promote smoother ramp-up when we see progress markers
            self._stage_multiplier = min(self._stage_multiplier + 0.05, 1.5)

        if "resetting" in lowered:
            self.update_stage(PowerSessionStage.COOL_DOWN)

    def handle_cli_finished(self, operation: Optional[str], exit_code: int, *, is_background: bool = False) -> None:
        """React to CLI completions to wrap up sessions when needed."""

        session = self.active_session
        if not session or session.phase != PowerSessionPhase.UPLOAD:
            return

        if operation == "compile":
            if exit_code == 0:
                # Compilation finished successfully; wait for upload stage.
                self.update_stage(PowerSessionStage.IDLE)
            elif not is_background:
                self.abort_active_session("compile_failed")
        elif operation == "upload":
            if exit_code == 0:
                self.update_stage(PowerSessionStage.COOL_DOWN)
                self.finish_active_session(success=True, reason="upload_success")
            else:
                self.abort_active_session("upload_failed")

    def ingest_serial_stream(
        self,
        payload: str,
        *,
        board: Optional[object] = None,
        port: str = "",
    ) -> None:
        """Parse serial output for power telemetry hints."""

        if not payload or not payload.strip():
            return

        measurements = [m for m in map(self._parse_power_line, payload.splitlines()) if m]
        if not measurements:
            return

        session = self.active_session
        if not session or session.phase != PowerSessionPhase.RUNTIME:
            self.start_runtime_session(board=board, port=port, metadata={"source": "serial_monitor"}, enable_estimation=False)
            session = self.active_session

        if not session:
            return

        # Disable estimations while direct measurements stream in.
        self._poll_timer.stop()
        self._estimation_enabled = False

        for voltage_v, current_ma, power_mw in measurements:
            measurement = PowerMeasurement(
                session_id=session.session_id,
                timestamp=datetime.now(),
                voltage_v=voltage_v,
                current_ma=current_ma,
                power_mw=power_mw,
                stage=PowerSessionStage.RUNNING.value,
                source="serial",
                notes="Serial telemetry",
            )
            self._append_measurement(session, measurement)

    def record_measurement(
        self,
        *,
        current_ma: float,
        voltage_v: Optional[float] = None,
        stage: Optional[PowerSessionStage | str] = None,
        source: str = "manual",
        notes: str = "",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Append a manually supplied measurement to the active session."""

        session = self.active_session
        if not session:
            return

        if isinstance(stage, str):
            try:
                stage_enum = PowerSessionStage(stage)
            except ValueError:
                stage_enum = session.stage
        else:
            stage_enum = stage or session.stage

        voltage = voltage_v if voltage_v is not None else self._board_voltage_v
        power_mw = voltage * current_ma
        measurement = PowerMeasurement(
            session_id=session.session_id,
            timestamp=timestamp or datetime.now(),
            voltage_v=voltage,
            current_ma=current_ma,
            power_mw=power_mw,
            stage=stage_enum.value,
            source=source,
            notes=notes,
        )
        self._append_measurement(session, measurement)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def generate_report(self, session_id: Optional[str] = None) -> Dict[str, object]:
        """Return a comprehensive report for the requested session."""

        session = self._resolve_session(session_id)
        if not session:
            return {}

        recommendations = self._build_recommendations(session)
        return {
            "session": session.to_dict(),
            "measurements": [self._measurement_to_dict(m) for m in session.measurements],
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _begin_session(
        self,
        *,
        phase: PowerSessionPhase,
        stage: PowerSessionStage,
        board: Optional[object],
        port: str,
        metadata: Dict[str, str],
        enable_estimation: bool,
    ) -> str:
        """Initialise a new session with shared setup logic."""

        if self._active_session_id:
            self.finish_active_session(success=True, reason="superseded")

        session_id = f"{phase.value}-{int(datetime.now().timestamp())}"
        board_name, board_fqbn = self._derive_board_identity(board)

        session = PowerSession(
            session_id=session_id,
            phase=phase,
            started_at=datetime.now(),
            board_name=board_name,
            board_fqbn=board_fqbn,
            port=port,
            metadata=metadata,
            stage=stage,
        )
        self._sessions[session_id] = session
        self._session_order.append(session_id)
        self._trim_history()

        self._active_session_id = session_id
        self._baseline_current_ma = self._derive_baseline_current(board)
        self._board_voltage_v = self._derive_nominal_voltage(board)
        session.metadata.setdefault("baseline_current_ma", f"{self._baseline_current_ma:.2f}")
        session.metadata.setdefault("nominal_voltage_v", f"{self._board_voltage_v:.2f}")

        self._stage_multiplier = self._STAGE_MULTIPLIERS.get(stage, 1.0)
        self._estimation_enabled = enable_estimation
        self._last_estimate_timestamp = None

        if enable_estimation:
            self._poll_timer.start()
        else:
            self._poll_timer.stop()

        self.session_started.emit(session)
        return session_id

    def _generate_estimate(self, force: bool = False) -> None:
        """Create an estimated measurement for the active session."""

        session = self.active_session
        if not session:
            return

        if not self._estimation_enabled and not force:
            return

        now = datetime.now()
        if not force and self._last_estimate_timestamp and (now - self._last_estimate_timestamp).total_seconds() < (self.ESTIMATION_INTERVAL_MS / 1000.0 * 0.5):
            return

        self._last_estimate_timestamp = now
        base_current = self._baseline_current_ma * self._stage_multiplier
        jitter = base_current * self._rng.uniform(-0.15, 0.12)
        current_ma = max(0.0, base_current + jitter)
        power_mw = self._board_voltage_v * current_ma

        measurement = PowerMeasurement(
            session_id=session.session_id,
            timestamp=now,
            voltage_v=self._board_voltage_v,
            current_ma=current_ma,
            power_mw=power_mw,
            stage=session.stage.value,
            source="estimated",
            notes="Heuristic estimate",
        )
        self._append_measurement(session, measurement)

    def _append_measurement(self, session: PowerSession, measurement: PowerMeasurement) -> None:
        """Add a measurement and update cumulative statistics."""

        previous = session.measurements[-1] if session.measurements else None
        if previous:
            delta = (measurement.timestamp - previous.timestamp).total_seconds()
            if delta < 0:
                delta = 0.0
            average_power = (previous.power_mw + measurement.power_mw) / 2.0
            energy_increment = average_power * delta
            measurement.energy_increment_mj = energy_increment
            measurement.cumulative_energy_mj = previous.cumulative_energy_mj + energy_increment
        else:
            measurement.energy_increment_mj = 0.0
            measurement.cumulative_energy_mj = 0.0

        session.measurements.append(measurement)
        self.measurement_added.emit(measurement)
        self.session_updated.emit(session)

    def _build_metadata(
        self,
        board: Optional[object],
        sketch_path: str,
        metadata: Optional[Dict[str, str]],
    ) -> Dict[str, str]:
        base = dict(metadata or {})
        if sketch_path:
            base.setdefault("sketch", sketch_path)
        if board:
            name, fqbn = self._derive_board_identity(board)
            base.setdefault("board_name", name)
            base.setdefault("board_fqbn", fqbn)
        return base

    def _derive_board_identity(self, board: Optional[object]) -> Tuple[str, str]:
        name = getattr(board, "name", "Unknown") if board else "Unknown"
        fqbn = getattr(board, "fqbn", "") if board else ""
        return name, fqbn

    def _derive_baseline_current(self, board: Optional[object]) -> float:
        """Estimate baseline current draw from board specifications."""

        if not board:
            return self._DEFAULT_CURRENT_MA

        specs = getattr(board, "specs", None)
        power_str = getattr(specs, "power_typical", "") if specs else ""
        if not power_str:
            return self._DEFAULT_CURRENT_MA

        match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(mA|A)", str(power_str))
        if not match:
            return self._DEFAULT_CURRENT_MA

        value = float(match.group(1))
        unit = match.group(2).lower()
        if unit == "a":
            value *= 1000.0
        return max(10.0, value)

    def _derive_nominal_voltage(self, board: Optional[object]) -> float:
        """Extract nominal voltage from board specs."""

        if not board:
            return self._DEFAULT_VOLTAGE

        specs = getattr(board, "specs", None)
        voltage_text = getattr(specs, "voltage", "") if specs else ""
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(voltage_text))
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return self._DEFAULT_VOLTAGE
        return self._DEFAULT_VOLTAGE

    def _parse_power_line(self, line: str) -> Optional[Tuple[float, float, float]]:
        """Extract voltage/current/power triples from a line of telemetry."""

        tokens = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*(mA|A|V|mW|W)", line)
        if not tokens:
            return None

        voltage_v: Optional[float] = None
        current_ma: Optional[float] = None
        power_mw: Optional[float] = None

        for raw_value, unit in tokens:
            value = float(raw_value)
            unit = unit.lower()
            if unit == "v":
                voltage_v = value
            elif unit == "ma":
                current_ma = value
            elif unit == "a":
                current_ma = value * 1000.0
            elif unit == "mw":
                power_mw = value
            elif unit == "w":
                power_mw = value * 1000.0

        if voltage_v is None:
            voltage_v = self._board_voltage_v

        if current_ma is None:
            if power_mw is None or voltage_v <= 0:
                return None
            current_ma = power_mw / voltage_v

        if power_mw is None:
            power_mw = voltage_v * current_ma

        return voltage_v, current_ma, power_mw

    def _measurement_to_dict(self, measurement: PowerMeasurement) -> Dict[str, object]:
        return {
            "timestamp": measurement.timestamp.isoformat(),
            "voltage_v": measurement.voltage_v,
            "current_ma": measurement.current_ma,
            "power_mw": measurement.power_mw,
            "stage": measurement.stage,
            "source": measurement.source,
            "notes": measurement.notes,
            "energy_increment_mj": measurement.energy_increment_mj,
            "cumulative_energy_mj": measurement.cumulative_energy_mj,
        }

    def _build_recommendations(self, session: PowerSession) -> List[str]:
        """Generate high level optimisation tips based on collected data."""

        recommendations: List[str] = []
        average_power = session.average_power_mw()
        peak_power = session.peak_power_mw()
        baseline_power = float(session.metadata.get("baseline_current_ma", self._baseline_current_ma)) * float(
            session.metadata.get("nominal_voltage_v", self._board_voltage_v)
        )

        if peak_power > baseline_power * 1.5:
            recommendations.append(
                "Peak draw exceeded nominal expectations. Consider staggering peripheral start-up or enabling brown-out detection."
            )

        if average_power > baseline_power * 1.2:
            recommendations.append(
                "Average power usage is high; review duty cycles and leverage sleep modes to reduce consumption."
            )

        if session.phase == PowerSessionPhase.RUNTIME and session.duration_seconds() > 0:
            idle_ratio = self._estimate_idle_ratio(session.measurements)
            if idle_ratio < 0.3:
                recommendations.append(
                    "Runtime telemetry indicates the sketch rarely idles. Investigate event driven patterns to increase idle time."
                )

        if not recommendations:
            recommendations.append("Power profile is within expected range. No immediate action required.")

        return recommendations

    def _estimate_idle_ratio(self, measurements: Iterable[PowerMeasurement]) -> float:
        """Heuristic estimate of idle vs active share from power variation."""

        powers = [m.power_mw for m in measurements]
        if len(powers) < 2:
            return 0.0
        avg = sum(powers) / len(powers)
        idle_threshold = avg * 0.7
        idle_points = sum(1 for value in powers if value <= idle_threshold)
        return idle_points / len(powers)

    def _resolve_session(self, session_id: Optional[str]) -> Optional[PowerSession]:
        if session_id:
            return self._sessions.get(session_id)
        return self.active_session

    def _trim_history(self) -> None:
        """Keep the session history bounded."""

        while len(self._session_order) > self.MAX_SESSION_HISTORY:
            oldest_id = self._session_order[0]
            if oldest_id == self._active_session_id:
                break
            self._session_order.pop(0)
            self._sessions.pop(oldest_id, None)


__all__ = [
    "PowerAnalyzerService",
    "PowerMeasurement",
    "PowerSession",
    "PowerSessionPhase",
    "PowerSessionStage",
]
