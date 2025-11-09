import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from arduino_ide.services import background_updater
from arduino_ide.services.background_updater import OfflineMode


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_get_cached_packages_count(tmp_path, monkeypatch):
    library_index = tmp_path / "library_index.json"
    package_index = tmp_path / "package_index.json"

    _write_json(
        library_index,
        {
            "libraries": [
                {"name": "LibA"},
                {"name": "LibB"},
                {"name": "LibC"},
            ]
        },
    )

    _write_json(
        package_index,
        {
            "packages": [
                {"name": "Pkg1"},
                {"name": "Pkg2"},
            ]
        },
    )

    monkeypatch.setattr(background_updater.OfflineDetector, "is_online", lambda: False)

    offline = OfflineMode(cache_dir=tmp_path)

    assert offline.get_cached_packages_count() == 5


def test_get_offline_status_message_reports_cached_count(tmp_path, monkeypatch):
    library_index = tmp_path / "library_index.json"
    package_index = tmp_path / "package_index.json"

    _write_json(library_index, {"libraries": [{"name": "LibA"}]})
    _write_json(package_index, {"packages": [{"name": "Pkg1"}, {"name": "Pkg2"}]})

    monkeypatch.setattr(background_updater.OfflineDetector, "is_online", lambda: False)

    offline = OfflineMode(cache_dir=tmp_path)

    message = offline.get_offline_status_message()

    assert "Offline Mode - Limited functionality" in message
    assert "• 3 cached packages available" in message
