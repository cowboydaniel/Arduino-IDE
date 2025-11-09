"""Utility for running Arduino CLI commands asynchronously."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List, Optional

from PySide6.QtCore import QObject, QProcess, Signal


class ArduinoCliService(QObject):
    """Run the bundled ``arduino-cli`` helper asynchronously.

    The service wraps :class:`QProcess` so that long running operations such as
    compilation or uploads do not block the UI.  Output from the process is
    streamed through Qt signals which can be connected directly to console
    widgets.
    """

    output_received = Signal(str)
    error_received = Signal(str)
    finished = Signal(int)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._cli_path = (Path(__file__).resolve().parents[2] / "arduino-cli").resolve()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_running(self) -> bool:
        """Return ``True`` if a CLI command is currently executing."""

        return self._process is not None and self._process.state() != QProcess.NotRunning

    def run_compile(self, sketch_path: str, fqbn: str, *, build_path: Optional[str] = None,
                    config: Optional[str] = None) -> None:
        """Compile ``sketch_path`` for ``fqbn`` asynchronously."""

        args: List[str] = ["compile", "-b", fqbn, sketch_path]
        if build_path:
            args.extend(["--build-path", build_path])
        if config:
            args.extend(["--config", config])
        self._start_process(args)

    def run_upload(self, sketch_path: str, fqbn: str, port: str, *, build_path: Optional[str] = None,
                   verify: bool = False) -> None:
        """Upload ``sketch_path`` to ``fqbn`` through ``port`` asynchronously."""

        args: List[str] = ["upload", "-b", fqbn, "-p", port, sketch_path]
        if build_path:
            args.extend(["--build-path", build_path])
        if verify:
            args.append("--verify")
        self._start_process(args)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _start_process(self, args: Iterable[str]) -> None:
        if self.is_running():
            raise RuntimeError("A CLI command is already running")

        if not self._cli_path.exists():
            raise FileNotFoundError(f"arduino-cli helper not found at {self._cli_path}")

        process = QProcess(self)
        self._process = process

        process.setProgram(sys.executable)
        process.setArguments([str(self._cli_path), *list(args)])
        process.setProcessChannelMode(QProcess.SeparateChannels)

        process.readyReadStandardOutput.connect(self._read_stdout)  # type: ignore[attr-defined]
        process.readyReadStandardError.connect(self._read_stderr)  # type: ignore[attr-defined]
        process.errorOccurred.connect(self._on_process_error)  # type: ignore[attr-defined]
        process.finished.connect(self._on_process_finished)  # type: ignore[attr-defined]

        process.start()
        if not process.waitForStarted(1000):
            error = process.error()
            self._cleanup_process()
            raise RuntimeError(f"Failed to start arduino-cli (error code {int(error)})")

    def _read_stdout(self) -> None:
        if not self._process:
            return
        data = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.output_received.emit(data)

    def _read_stderr(self) -> None:
        if not self._process:
            return
        data = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        if data:
            self.error_received.emit(data)

    def _on_process_error(self, _error: QProcess.ProcessError) -> None:  # pragma: no cover - Qt callback
        # ``finished`` will still be emitted; make sure we surface the error output.
        pass

    def _on_process_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        try:
            self.finished.emit(exit_code)
        finally:
            self._cleanup_process()

    def _cleanup_process(self) -> None:
        if self._process:
            self._process.deleteLater()
        self._process = None
