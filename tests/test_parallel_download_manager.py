import sys
import threading
import time
from pathlib import Path

import pytest

# Ensure project root is on sys.path for imports during testing
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from arduino_ide.services.download_manager import (
    ParallelDownloadManager,
    DownloadManager,
    DownloadResult,
    NetworkError,
)


@pytest.fixture
def download_specs():
    return [
        {
            "urls": [f"http://example.com/file{i}.bin"],
            "filename": f"file{i}.bin",
            "checksum": None,
            "size": 1024,
        }
        for i in range(4)
    ]


def test_parallel_download_respects_max_concurrency(monkeypatch, tmp_path, download_specs):
    manager = ParallelDownloadManager(tmp_path, max_concurrent=2)

    active_counts = []
    lock = threading.Lock()

    def fake_download(self, urls, filename, expected_checksum=None, expected_size=None, resume=True):
        with lock:
            active_counts.append(len(manager.active_downloads))
        time.sleep(0.05)
        return DownloadResult(success=True, file_path=tmp_path / filename)

    monkeypatch.setattr(DownloadManager, "download", fake_download)

    results = manager.download_multiple(download_specs)

    assert all(result.success for result in results)
    assert len(results) == len(download_specs)
    assert manager.active_downloads == []
    assert max(active_counts) <= manager.max_concurrent
    assert manager.max_concurrent in active_counts


def test_parallel_download_propagates_errors(monkeypatch, tmp_path, download_specs):
    manager = ParallelDownloadManager(tmp_path, max_concurrent=2)

    call_count = 0

    def fake_download(self, urls, filename, expected_checksum=None, expected_size=None, resume=True):
        nonlocal call_count
        call_count += 1
        if "file1" in filename:
            raise NetworkError("Network failure")
        time.sleep(0.01)
        return DownloadResult(success=True, file_path=tmp_path / filename)

    monkeypatch.setattr(DownloadManager, "download", fake_download)

    results = manager.download_multiple(download_specs)

    assert call_count == len(download_specs)
    assert any(not result.success for result in results)
    failure_results = [result for result in results if not result.success]
    assert len(failure_results) == 1
    assert failure_results[0].error_message == "Network failure"
    assert all(result.success for result in results if result.success)
    assert manager.active_downloads == []
