"""Utility for running Arduino CLI commands asynchronously."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

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
                    build_cache_path: Optional[str] = None, config: Optional[str] = None,
                    verbose: bool = False, export_binaries: bool = False,
                    warnings: str = 'none', optimize_for_debug: bool = False) -> None:
        """Compile ``sketch_path`` for ``fqbn`` asynchronously.

        Args:
            sketch_path: Path to the sketch file or directory
            fqbn: Fully Qualified Board Name
            build_path: Optional path for build artifacts
            build_cache_path: Optional path for caching core.a
            config: Build configuration name (Release/Debug)
            verbose: Print detailed compilation logs
            export_binaries: Export compiled binaries to sketch folder
            warnings: Warning level (none/default/more/all)
            optimize_for_debug: Optimize for debugging instead of size
        """

        args: List[str] = ["compile", "-b", fqbn]

        if build_path:
            args.extend(["--build-path", build_path])
        if build_cache_path:
            args.extend(["--build-cache-path", build_cache_path])
        if config:
            args.extend(["--config", config])
        if verbose:
            args.append("-v")
        if export_binaries:
            args.append("-e")
        if warnings != 'none':
            args.extend(["--warnings", warnings])
        if optimize_for_debug:
            args.append("--optimize-for-debug")

        args.append(sketch_path)
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
    # Board and Platform Management (Synchronous)
    # ------------------------------------------------------------------
    def list_boards(self) -> List[Dict[str, Any]]:
        """List all available boards from installed platforms.

        Returns:
            List of board dictionaries with keys: name, fqbn, platform

        Raises:
            RuntimeError: If arduino-cli command fails
        """
        return self._run_sync_command(["board", "listall", "--format", "json"])

    def list_platforms(self) -> List[Dict[str, Any]]:
        """List installed platforms/cores.

        Returns:
            List of platform dictionaries with keys: id, installed, latest, name

        Raises:
            RuntimeError: If arduino-cli command fails
        """
        return self._run_sync_command(["core", "list", "--format", "json"])

    def search_platforms(self, query: str = "") -> List[Dict[str, Any]]:
        """Search for available platforms.

        Args:
            query: Optional search query to filter platforms

        Returns:
            List of platform dictionaries

        Raises:
            RuntimeError: If arduino-cli command fails
        """
        args = ["core", "search", "--format", "json"]
        if query:
            args.append(query)
        return self._run_sync_command(args)

    def install_platform(self, platform_id: str) -> bool:
        """Install a platform/core.

        Args:
            platform_id: Platform identifier (e.g., "arduino:avr", "esp32:esp32")

        Returns:
            True if installation succeeded, False otherwise
        """
        try:
            self._run_sync_command(["core", "install", platform_id], expect_json=False)
            return True
        except RuntimeError:
            return False

    def uninstall_platform(self, platform_id: str) -> bool:
        """Uninstall a platform/core.

        Args:
            platform_id: Platform identifier (e.g., "arduino:avr", "esp32:esp32")

        Returns:
            True if uninstallation succeeded, False otherwise
        """
        try:
            self._run_sync_command(["core", "uninstall", platform_id], expect_json=False)
            return True
        except RuntimeError:
            return False

    def get_board_details(self, fqbn: str) -> Dict[str, Any]:
        """Get detailed information about a specific board.

        Args:
            fqbn: Fully Qualified Board Name

        Returns:
            Dictionary with board details

        Raises:
            RuntimeError: If arduino-cli command fails
        """
        return self._run_sync_command(["board", "details", "-b", fqbn, "--format", "json"])

    def update_platform_index(self) -> bool:
        """Update the platform package index.

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            self._run_sync_command(["core", "update-index"], expect_json=False)
            return True
        except RuntimeError:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _run_sync_command(self, args: List[str], expect_json: bool = True) -> Any:
        """Run arduino-cli command synchronously and return output.

        Args:
            args: Command arguments for arduino-cli
            expect_json: If True, parse output as JSON

        Returns:
            Parsed JSON data if expect_json=True, otherwise raw stdout string

        Raises:
            RuntimeError: If command fails or JSON parsing fails
        """
        if not self._cli_path.exists():
            raise FileNotFoundError(f"arduino-cli helper not found at {self._cli_path}")

        try:
            result = subprocess.run(
                [sys.executable, str(self._cli_path)] + args,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )

            if expect_json:
                if not result.stdout.strip():
                    return []
                return json.loads(result.stdout)
            return result.stdout

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"arduino-cli command failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("arduino-cli command timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse arduino-cli JSON output: {e}")
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
