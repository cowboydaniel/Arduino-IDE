import pytest
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from arduino_ide.services.cli_runner import ArduinoCliService


@pytest.fixture(scope="module")
def qt_app():
    """Ensure a Qt application instance exists for QProcess tests."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def _wait_for_process(service: ArduinoCliService, timeout: int = 10000) -> int:
    """Wait for the CLI process to finish and return its exit code."""
    loop = QEventLoop()
    result = {}

    def on_finished(exit_code: int):
        result["code"] = exit_code
        loop.quit()

    service.finished.connect(on_finished)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(timeout)

    loop.exec()

    service.finished.disconnect(on_finished)
    timer.stop()

    if "code" not in result:
        raise TimeoutError("CLI command did not finish within timeout")

    return result["code"]


def test_compile_sketch_success(qt_app, tmp_path):
    sketch_path = tmp_path / "Blink.ino"
    sketch_path.write_text(
        "void setup() {}\nvoid loop() {}\n",
        encoding="utf-8",
    )

    service = ArduinoCliService()
    outputs = []
    errors = []
    service.output_received.connect(outputs.append)
    service.error_received.connect(errors.append)

    service.run_compile(str(sketch_path), "arduino:avr:uno", config="Debug")
    exit_code = _wait_for_process(service)

    combined_output = "".join(outputs)
    assert exit_code == 0
    assert "Compiling sketch" in combined_output
    assert "Sketch uses" in combined_output
    assert errors == []

    service.deleteLater()


def test_compile_sketch_invalid_board(qt_app, tmp_path):
    sketch_path = tmp_path / "Blink.ino"
    sketch_path.write_text(
        "void setup() {}\nvoid loop() {}\n",
        encoding="utf-8",
    )

    service = ArduinoCliService()
    errors = []
    service.error_received.connect(errors.append)

    service.run_compile(str(sketch_path), "invalid:board")
    exit_code = _wait_for_process(service)

    combined_error = "".join(errors)
    assert exit_code != 0
    assert "Board 'invalid:board' not found" in combined_error

    service.deleteLater()


def test_run_compile_includes_library_paths(monkeypatch, tmp_path):
    service = ArduinoCliService()

    captured = {}

    def fake_start(args):
        captured["args"] = list(args)

    monkeypatch.setattr(service, "_start_process", fake_start)

    library_dir = tmp_path / "libraries"
    library_dir.mkdir()
    service.set_library_search_paths([library_dir])

    service.run_compile(str(tmp_path / "Example.ino"), "arduino:avr:uno")

    assert "--libraries" in captured["args"]
    assert str(library_dir) in captured["args"]
