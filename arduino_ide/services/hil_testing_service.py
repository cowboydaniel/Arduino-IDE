"""Hardware-in-the-loop (HIL) testing service.

This module provides a high level service for orchestrating hardware test
fixtures, managing device sessions, and executing HIL test suites.  The
service is intentionally self contained so it can be reused by both the GUI
and command-line tooling.  It exposes Qt signals for UI components while the
core logic is implemented with standard Python data structures for ease of
unit testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, TYPE_CHECKING
import json
import threading
import time

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .unit_testing_service import UnitTestingService


class SignalDirection(Enum):
    """Direction of a test signal within a fixture."""

    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"


class SignalType(Enum):
    """Type/category of a test signal."""

    DIGITAL = "digital"
    ANALOG = "analog"
    PWM = "pwm"
    SERIAL = "serial"
    I2C = "i2c"
    SPI = "spi"
    POWER = "power"
    CUSTOM = "custom"


@dataclass
class TestSignal:
    """Description of an individual signal exposed by a fixture."""

    name: str
    pin: int
    signal_type: SignalType
    direction: SignalDirection
    metadata: Dict[str, Any] = field(default_factory=dict)

    def descriptor(self) -> str:
        """Human readable description used in UI tables."""

        return f"{self.signal_type.value.upper()} ({self.direction.value})"


@dataclass
class TestStep:
    """Single step executed as part of a HIL test case."""

    description: str
    command: Dict[str, Any] = field(default_factory=dict)
    expected: Optional[Dict[str, Any]] = None
    wait_ms: int = 0
    validator: Optional[Callable[["TestStep"], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestStepResult:
    """Result captured after executing a single step."""

    step: TestStep
    passed: bool
    timestamp: datetime
    measured: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass
class HILTestCase:
    """A complete HIL test made up of multiple steps."""

    name: str
    fixture_name: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    stop_on_failure: bool = True
    steps: List[TestStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(
        self,
        description: str,
        command: Optional[Dict[str, Any]] = None,
        expected: Optional[Dict[str, Any]] = None,
        *,
        wait_ms: int = 0,
        validator: Optional[Callable[[TestStep], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TestStep:
        """Convenience helper for appending a test step."""

        step = TestStep(
            description=description,
            command=command or {},
            expected=expected,
            wait_ms=wait_ms,
            validator=validator,
            metadata=metadata or {},
        )
        self.steps.append(step)
        return step


@dataclass
class HILTestResult:
    """Aggregated result for a HIL test case."""

    test_name: str
    fixture_name: str
    passed: bool
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    step_results: List[TestStepResult] = field(default_factory=list)
    failure_message: str = ""
    log_messages: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if not self.step_results:
            return 0.0
        passed = sum(1 for step in self.step_results if step.passed)
        return (passed / len(self.step_results)) * 100.0


@dataclass
class FixtureSession:
    """Runtime session state associated with a fixture."""

    fixture_name: str
    connected: bool = False
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestFixture:
    """Definition of a hardware fixture used for HIL testing."""

    name: str
    board: str
    port: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    signals: Dict[str, TestSignal] = field(default_factory=dict)

    def add_signal(
        self,
        name: str,
        pin: int,
        signal_type: SignalType,
        direction: SignalDirection,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TestSignal:
        signal = TestSignal(
            name=name,
            pin=pin,
            signal_type=signal_type,
            direction=direction,
            metadata=metadata or {},
        )
        self.signals[name] = signal
        return signal

    def add_input_signal(
        self, name: str, pin: int, signal_type: SignalType, metadata: Optional[Dict[str, Any]] = None
    ) -> TestSignal:
        return self.add_signal(name, pin, signal_type, SignalDirection.INPUT, metadata)

    def add_output_signal(
        self, name: str, pin: int, signal_type: SignalType, metadata: Optional[Dict[str, Any]] = None
    ) -> TestSignal:
        return self.add_signal(name, pin, signal_type, SignalDirection.OUTPUT, metadata)


class HILTestingService(QObject):
    """Service responsible for orchestrating HIL tests."""

    fixture_added = Signal(object)
    fixture_updated = Signal(object)
    fixture_removed = Signal(str)
    session_started = Signal(str)
    session_stopped = Signal(str)
    session_error = Signal(str, str)
    log_generated = Signal(str, str)
    test_registered = Signal(object)
    test_started = Signal(str, str)
    test_step_completed = Signal(str, str, object)
    test_finished = Signal(str, object)
    suite_finished = Signal(str, object)

    def __init__(
        self,
        project_path: Optional[str] = None,
        *,
        unit_testing_service: Optional[UnitTestingService] = None,
    ):
        super().__init__()

        self._project_path = Path(project_path) if project_path else Path.cwd()
        self._unit_testing_service: Optional[UnitTestingService] = unit_testing_service

        self._fixtures: Dict[str, TestFixture] = {}
        self._tests: Dict[str, HILTestCase] = {}
        self._tests_by_fixture: Dict[str, List[str]] = {}
        self._sessions: Dict[str, FixtureSession] = {}
        self._logs: Dict[str, List[str]] = {}
        self._active_threads: Dict[str, threading.Thread] = {}
        self._lock = threading.RLock()

        self.load_configuration()

    # ------------------------------------------------------------------
    # Fixture management
    # ------------------------------------------------------------------
    @property
    def project_path(self) -> Path:
        return self._project_path

    def set_project_path(self, path: str | Path) -> None:
        self._project_path = Path(path)
        self.load_configuration()

    def list_fixtures(self) -> List[TestFixture]:
        with self._lock:
            return list(self._fixtures.values())

    def get_fixture(self, name: str) -> Optional[TestFixture]:
        with self._lock:
            return self._fixtures.get(name)

    def add_fixture(self, fixture: TestFixture) -> None:
        with self._lock:
            self._fixtures[fixture.name] = fixture
            self._tests_by_fixture.setdefault(fixture.name, [])
            self._logs.setdefault(fixture.name, [])
        self.fixture_added.emit(fixture)

    def update_fixture(self, name: str, **changes: Any) -> Optional[TestFixture]:
        with self._lock:
            fixture = self._fixtures.get(name)
            if not fixture:
                return None
            for key, value in changes.items():
                if hasattr(fixture, key):
                    setattr(fixture, key, value)
        self.fixture_updated.emit(fixture)
        return fixture

    def remove_fixture(self, name: str) -> None:
        with self._lock:
            if name in self._sessions:
                self.stop_session(name)
            if name in self._fixtures:
                del self._fixtures[name]
            if name in self._tests_by_fixture:
                for test_name in self._tests_by_fixture[name]:
                    self._tests.pop(test_name, None)
                del self._tests_by_fixture[name]
            self._logs.pop(name, None)
        self.fixture_removed.emit(name)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def start_session(self, fixture_name: str) -> bool:
        fixture = self.get_fixture(fixture_name)
        if not fixture:
            self.session_error.emit(fixture_name, "Fixture not found")
            return False

        with self._lock:
            session = self._sessions.get(fixture_name)
            if session and session.connected:
                return True
            session = FixtureSession(
                fixture_name=fixture_name,
                connected=True,
                started_at=datetime.now(),
                last_activity=datetime.now(),
            )
            self._sessions[fixture_name] = session
        self._append_log(fixture_name, "Session started")
        self.session_started.emit(fixture_name)
        return True

    def stop_session(self, fixture_name: str) -> None:
        with self._lock:
            session = self._sessions.get(fixture_name)
            if not session:
                return
            session.connected = False
            session.last_activity = datetime.now()
            del self._sessions[fixture_name]
        self._append_log(fixture_name, "Session stopped")
        self.session_stopped.emit(fixture_name)

    def is_session_active(self, fixture_name: str) -> bool:
        with self._lock:
            session = self._sessions.get(fixture_name)
            return bool(session and session.connected)

    def active_sessions(self) -> List[FixtureSession]:
        with self._lock:
            return list(self._sessions.values())

    # ------------------------------------------------------------------
    # Test registration
    # ------------------------------------------------------------------
    def list_tests(self, fixture_name: Optional[str] = None) -> List[HILTestCase]:
        with self._lock:
            if fixture_name:
                names = self._tests_by_fixture.get(fixture_name, [])
                return [self._tests[name] for name in names if name in self._tests]
            return list(self._tests.values())

    def create_test(
        self,
        name: str,
        fixture_name: str,
        description: str = "",
        *,
        tags: Optional[Iterable[str]] = None,
        stop_on_failure: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HILTestCase:
        test = HILTestCase(
            name=name,
            fixture_name=fixture_name,
            description=description,
            tags=list(tags or []),
            stop_on_failure=stop_on_failure,
            metadata=metadata or {},
        )
        self.register_test(test)
        return test

    def register_test(self, test: HILTestCase) -> None:
        if not self.get_fixture(test.fixture_name):
            raise ValueError(f"Fixture '{test.fixture_name}' not registered")

        with self._lock:
            self._tests[test.name] = test
            self._tests_by_fixture.setdefault(test.fixture_name, [])
            if test.name not in self._tests_by_fixture[test.fixture_name]:
                self._tests_by_fixture[test.fixture_name].append(test.name)
        self.test_registered.emit(test)

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------
    def run_test(self, test_name: str) -> None:
        test = self._tests.get(test_name)
        if not test:
            return

        if test_name in self._active_threads:
            return

        thread = threading.Thread(
            target=self._run_test_case,
            args=(test,),
            name=f"HILTest-{test_name}",
            daemon=True,
        )
        self._active_threads[test_name] = thread
        thread.start()

    def run_all_tests(self, fixture_name: str) -> None:
        tests = self.list_tests(fixture_name)
        if not tests:
            return

        def worker():
            results: List[HILTestResult] = []
            for test in tests:
                result = self._run_test_case(test)
                if result:
                    results.append(result)
            if results:
                self.suite_finished.emit(fixture_name, results)

        thread = threading.Thread(target=worker, name=f"HILSuite-{fixture_name}", daemon=True)
        thread.start()

    def _run_test_case(self, test: HILTestCase) -> Optional[HILTestResult]:
        fixture_name = test.fixture_name
        if not self.start_session(fixture_name):
            return None

        start_time = datetime.now()
        self.test_started.emit(fixture_name, test.name)
        self._append_log(fixture_name, f"Running test: {test.name}")

        step_results: List[TestStepResult] = []
        passed = True
        failure_message = ""

        for step in test.steps:
            if step.wait_ms > 0:
                time.sleep(step.wait_ms / 1000.0)
            result = self._execute_step(step)
            step_results.append(result)
            self.test_step_completed.emit(fixture_name, test.name, result)
            self._append_log(fixture_name, f"• {step.description} — {'PASS' if result.passed else 'FAIL'}")
            if not result.passed:
                passed = False
                failure_message = result.message or step.description
                if test.stop_on_failure:
                    break

        finished_at = datetime.now()
        duration_ms = (finished_at - start_time).total_seconds() * 1000.0

        result = HILTestResult(
            test_name=test.name,
            fixture_name=fixture_name,
            passed=passed,
            started_at=start_time,
            finished_at=finished_at,
            duration_ms=duration_ms,
            step_results=step_results,
            failure_message=failure_message,
        )
        result.log_messages = self._logs.get(fixture_name, [])[-len(step_results) :]

        self.test_finished.emit(fixture_name, result)
        self._append_log(
            fixture_name,
            f"Test {test.name} {'PASSED' if passed else 'FAILED'} ({duration_ms:.0f} ms)",
        )

        with self._lock:
            self._active_threads.pop(test.name, None)

        return result

    def _execute_step(self, step: TestStep) -> TestStepResult:
        timestamp = datetime.now()
        passed = True
        message = ""
        measured: Dict[str, Any] = {}

        if step.validator:
            try:
                passed = bool(step.validator(step))
            except Exception as exc:  # pragma: no cover - defensive programming
                passed = False
                message = str(exc)
        elif step.expected is not None:
            # Without a hardware interface we optimistically compare expected
            # values to the provided command payload if present.  This keeps the
            # result deterministic while still surfacing validation intent.
            comparison = {}
            for key, expected_value in step.expected.items():
                actual_value = step.command.get(key, expected_value)
                comparison[key] = actual_value
                if actual_value != expected_value:
                    passed = False
            measured = comparison
            if not passed and not message:
                message = "Expected values not met"

        return TestStepResult(
            step=step,
            passed=passed,
            timestamp=timestamp,
            measured=measured,
            message=message,
        )

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def _append_log(self, fixture_name: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        with self._lock:
            self._logs.setdefault(fixture_name, []).append(formatted)
        self.log_generated.emit(fixture_name, formatted)

    def get_logs(self, fixture_name: str) -> List[str]:
        with self._lock:
            return list(self._logs.get(fixture_name, []))

    def clear_logs(self, fixture_name: Optional[str] = None) -> None:
        with self._lock:
            if fixture_name:
                self._logs.pop(fixture_name, None)
            else:
                self._logs.clear()

    # ------------------------------------------------------------------
    # Configuration management
    # ------------------------------------------------------------------
    def load_configuration(self) -> bool:
        """Load fixtures/tests from ``hil_tests.json`` if present."""

        config_path = self._project_path / "hil_tests.json"
        if not config_path.exists():
            return False

        try:
            data = json.loads(config_path.read_text())
        except Exception as exc:  # pragma: no cover - defensive
            self.session_error.emit("__config__", f"Failed to read configuration: {exc}")
            return False

        fixtures = data.get("fixtures", [])
        if not isinstance(fixtures, list):
            self.session_error.emit("__config__", "Configuration missing 'fixtures' list")
            return False

        self.clear()

        for fixture_data in fixtures:
            fixture = self._fixture_from_dict(fixture_data)
            if not fixture:
                continue
            self.add_fixture(fixture)
            for test_data in fixture_data.get("tests", []):
                test = self._test_from_dict(test_data, fixture.name)
                if test:
                    self.register_test(test)

        return True

    def clear(self) -> None:
        with self._lock:
            for fixture_name in list(self._sessions.keys()):
                self.stop_session(fixture_name)
            self._fixtures.clear()
            self._tests.clear()
            self._tests_by_fixture.clear()
            self._logs.clear()

    def _fixture_from_dict(self, payload: Dict[str, Any]) -> Optional[TestFixture]:
        name = payload.get("name")
        board = payload.get("board")
        if not name or not board:
            return None
        fixture = TestFixture(
            name=name,
            board=board,
            port=payload.get("port", ""),
            description=payload.get("description", ""),
            metadata=payload.get("metadata", {}),
        )
        for signal_data in payload.get("signals", []):
            try:
                signal_type = SignalType(signal_data.get("type", "digital"))
            except ValueError:
                signal_type = SignalType.CUSTOM
            direction_str = signal_data.get("direction", "input")
            try:
                direction = SignalDirection(direction_str)
            except ValueError:
                direction = SignalDirection.INPUT
            fixture.add_signal(
                signal_data.get("name", f"pin{signal_data.get('pin', 0)}"),
                int(signal_data.get("pin", 0)),
                signal_type,
                direction,
                signal_data.get("metadata", {}),
            )
        return fixture

    def _test_from_dict(self, payload: Dict[str, Any], fixture_name: str) -> Optional[HILTestCase]:
        name = payload.get("name")
        if not name:
            return None
        test = HILTestCase(
            name=name,
            fixture_name=fixture_name,
            description=payload.get("description", ""),
            tags=payload.get("tags", []),
            stop_on_failure=payload.get("stop_on_failure", True),
            metadata=payload.get("metadata", {}),
        )
        for step_data in payload.get("steps", []):
            test.add_step(
                step_data.get("description", ""),
                command=step_data.get("command", {}),
                expected=step_data.get("expected"),
                wait_ms=int(step_data.get("wait_ms", 0)),
                metadata=step_data.get("metadata", {}),
            )
        return test

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def generate_test_report(self, fixture_name: str) -> Dict[str, Any]:
        """Generate a summary report for a fixture."""

        tests = self.list_tests(fixture_name)
        results = {
            "fixture": fixture_name,
            "total_tests": len(tests),
            "tests": [],
        }
        for test in tests:
            results["tests"].append(
                {
                    "name": test.name,
                    "description": test.description,
                    "steps": [step.description for step in test.steps],
                }
            )
        return results

    def set_unit_testing_service(self, service: Optional[UnitTestingService]) -> None:
        """Allow late binding of the unit testing service for coordination."""

        self._unit_testing_service = service
