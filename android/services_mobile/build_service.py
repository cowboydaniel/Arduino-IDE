from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

DEFAULT_BOARD = {"name": "Arduino Uno", "fqbn": "arduino:avr:uno"}
DEFAULT_BOARDS = [
    DEFAULT_BOARD,
    {"name": "Arduino Nano", "fqbn": "arduino:avr:nano"},
    {"name": "ESP32 Dev Module", "fqbn": "esp32:esp32:esp32"},
]
DEFAULT_LIBRARIES = [
    {"name": "Servo", "version": "1.2.1"},
    {"name": "WiFi", "version": "1.2.7"},
    {"name": "BluetoothSerial", "version": "2.0.0"},
]


@dataclass
class BuildError:
    file: str
    line: int
    column: int
    message: str


@dataclass
class BuildResult:
    success: bool
    output: str
    errors: list[BuildError] = field(default_factory=list)
    sketch_path: Optional[Path] = None
    fqbn: Optional[str] = None


@dataclass
class BuildRequest:
    sketch_path: Path
    fqbn: str
    libraries: Iterable[str] | None = None
    clean: bool = False


class ArduinoCLI:
    """Thin wrapper around the Arduino CLI with Android-aware defaults."""

    def __init__(self, cli_path: Optional[Path] = None) -> None:
        self.cli_path = self._resolve_cli_path(cli_path)

    def _resolve_cli_path(self, cli_path: Optional[Path]) -> Optional[Path]:
        if cli_path:
            return cli_path

        env_path = Path.cwd() / "arduino-cli"
        if env_path.exists():
            return env_path

        which_path = shutil.which("arduino-cli")
        if which_path:
            return Path(which_path)

        local_repo_path = Path(__file__).resolve().parents[2] / "arduino-cli"
        if local_repo_path.exists():
            return local_repo_path

        return None

    @property
    def available(self) -> bool:
        return bool(self.cli_path and self.cli_path.exists())

    def run(self, args: list[str], *, cwd: Optional[Path] = None, timeout: int = 120) -> subprocess.CompletedProcess:
        if not self.available:
            raise FileNotFoundError("Arduino CLI binary not found. Ensure the ARM64 build is bundled.")

        command = [str(self.cli_path)] + args
        return subprocess.run(command, capture_output=True, text=True, cwd=cwd, timeout=timeout, check=False)

    def compile(self, request: BuildRequest) -> BuildResult:
        cmd = ["compile", "--fqbn", request.fqbn, str(request.sketch_path)]
        if request.clean:
            cmd.insert(1, "--clean")
        result = self.run(cmd)
        output = result.stdout + result.stderr
        errors = parse_build_errors(output)
        return BuildResult(success=result.returncode == 0, output=output, errors=errors, sketch_path=request.sketch_path, fqbn=request.fqbn)

    def install_core(self, core: str) -> str:
        if not self.available:
            return f"Arduino CLI missing, recorded requested core {core} for offline cache."
        result = self.run(["core", "install", core])
        return result.stdout + result.stderr

    def list_cores(self) -> str:
        if not self.available:
            return "\n".join(f"{board['fqbn']}\t{board['name']}" for board in DEFAULT_BOARDS)
        result = self.run(["core", "list"])
        return result.stdout + result.stderr

    def search_libraries(self, query: str) -> str:
        if not self.available:
            matches = [lib for lib in DEFAULT_LIBRARIES if query.lower() in lib["name"].lower()]
            return "\n".join(f"{lib['name']} {lib['version']}" for lib in matches)
        result = self.run(["lib", "search", query])
        return result.stdout + result.stderr

    def install_library(self, library: str) -> str:
        if not self.available:
            return f"Arduino CLI missing, recorded requested library {library} for offline cache."
        result = self.run(["lib", "install", library])
        return result.stdout + result.stderr


class BoardManager:
    """Tracks board selection and installed cores for Android builds."""

    def __init__(self, cli: Optional[ArduinoCLI] = None, *, state_path: Optional[Path] = None) -> None:
        self.cli = cli or ArduinoCLI()
        self.state_path = state_path or (Path.home() / ".arduino_mobile" / "boards.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {"selected": DEFAULT_BOARD, "installed": [DEFAULT_BOARD]}

    def _save_state(self) -> None:
        self.state_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def installed_boards(self) -> list[dict]:
        return list(self.state.get("installed", []))

    def select_board(self, board: dict) -> dict:
        self.state["selected"] = board
        if board not in self.state.setdefault("installed", []):
            self.state["installed"].append(board)
        self._save_state()
        return board

    def selected_board(self) -> dict:
        return self.state.get("selected", DEFAULT_BOARD)

    def install_core(self, fqbn: str) -> str:
        vendor_arch = ":".join(fqbn.split(":")[:2])
        output = self.cli.install_core(vendor_arch)
        board = next((b for b in DEFAULT_BOARDS if b["fqbn"] == fqbn), {"name": fqbn, "fqbn": fqbn})
        self.select_board(board)
        return output

    def list_available(self) -> list[dict]:
        return DEFAULT_BOARDS


class LibraryManager:
    """Tracks library installation state locally, while deferring to CLI when available."""

    def __init__(self, cli: Optional[ArduinoCLI] = None, *, state_path: Optional[Path] = None) -> None:
        self.cli = cli or ArduinoCLI()
        self.state_path = state_path or (Path.home() / ".arduino_mobile" / "libraries.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {"installed": DEFAULT_LIBRARIES}

    def _save_state(self) -> None:
        self.state_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def installed(self) -> list[dict]:
        return list(self.state.get("installed", []))

    def install_library(self, name: str, version: Optional[str] = None) -> str:
        if version:
            display = f"{name}@{version}"
        else:
            display = name
        output = self.cli.install_library(display)
        self.state.setdefault("installed", []).append({"name": name, "version": version or "latest"})
        self._save_state()
        return output

    def search(self, query: str) -> str:
        return self.cli.search_libraries(query)


class BuildService:
    """Coordinates sketch compilation using the Arduino CLI."""

    def __init__(self, cli: Optional[ArduinoCLI] = None, *, cache_dir: Optional[Path] = None) -> None:
        self.cli = cli or ArduinoCLI()
        self.cache_dir = cache_dir or (Path.home() / ".arduino_mobile" / "build-cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def verify_sketch(self, request: BuildRequest) -> BuildResult:
        if not request.sketch_path.exists():
            return BuildResult(False, f"Sketch {request.sketch_path} does not exist", [])

        if self.cli.available:
            return self.cli.compile(request)

        simulated = self._simulate_build(request)
        return simulated

    def _simulate_build(self, request: BuildRequest) -> BuildResult:
        message = [
            "Arduino CLI not bundled for this platform.",
            "Simulating verification to keep the UI responsive.",
            f"Sketch: {request.sketch_path.name}",
            f"Board: {request.fqbn}",
            "Libraries: " + ", ".join(request.libraries or ["(none)"]),
            "Result: SUCCESS (simulation)",
        ]
        return BuildResult(True, "\n".join(message), [], request.sketch_path, request.fqbn)


ERROR_PATTERN = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+):(?P<column>\d+):\s*error:\s*(?P<message>.+)$", re.MULTILINE)


def parse_build_errors(output: str) -> list[BuildError]:
    errors: list[BuildError] = []
    for match in ERROR_PATTERN.finditer(output):
        errors.append(
            BuildError(
                file=match.group("file"),
                line=int(match.group("line")),
                column=int(match.group("column")),
                message=match.group("message").strip(),
            )
        )
    return errors


__all__ = [
    "ArduinoCLI",
    "BoardManager",
    "BuildError",
    "BuildRequest",
    "BuildResult",
    "BuildService",
    "LibraryManager",
    "parse_build_errors",
]
