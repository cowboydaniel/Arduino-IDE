"""Scoped storage placeholder used by the Android Gradle package."""
from __future__ import annotations

from pathlib import Path


class StorageService:
    """Minimal storage helper to validate the Android sandbox."""

    def __init__(self, base: Path | None = None) -> None:
        self.base = base or Path.cwd()

    def resolve_sketch_path(self, name: str) -> Path:
        return self.base / f"{name}.ino"
