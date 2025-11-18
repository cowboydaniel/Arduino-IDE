from __future__ import annotations

from pathlib import Path
from typing import Optional


class StorageService:
    """Handles sketch storage with scoped-friendly defaults."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or (Path.home() / "ArduinoMobile" / "sketches")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def default_file_path(self, name: str = "sketch.ino") -> Path:
        return self.base_dir / name

    def read_file(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def write_file(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def delete_file(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def list_sketches(self) -> list[Path]:
        return sorted(self.base_dir.glob("**/*.ino"))

    def ensure_android_scoped_directory(self, package_name: str | None = None) -> Path:
        """
        Placeholder for Android scoped storage directory setup.

        On Android 11+, apps must use app-specific directories for user data.
        Buildozer/python-for-android can supply the package name; until then we
        fall back to an easily discoverable directory for development.
        """

        if package_name:
            android_dir = Path("/storage/emulated/0/Android/data") / package_name / "files" / "sketches"
            android_dir.mkdir(parents=True, exist_ok=True)
            self.base_dir = android_dir
        return self.base_dir


__all__ = ["StorageService"]
