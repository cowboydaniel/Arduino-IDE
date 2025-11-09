"""
Enhanced Download Manager

Handles package downloads with:
- Multi-source fallback
- Resume capability
- Integrity verification
- Progress tracking
- Retry logic with exponential backoff
"""

import os
import hashlib
import time
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass
import requests
from PySide6.QtCore import QObject, Signal


@dataclass
class DownloadProgress:
    """Download progress information"""
    total_bytes: int
    downloaded_bytes: int
    speed_bytes_per_sec: float
    percentage: int
    eta_seconds: int

    @property
    def speed_human_readable(self) -> str:
        """Get human-readable download speed"""
        if self.speed_bytes_per_sec < 1024:
            return f"{self.speed_bytes_per_sec:.1f} B/s"
        elif self.speed_bytes_per_sec < 1024 * 1024:
            return f"{self.speed_bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{self.speed_bytes_per_sec / (1024 * 1024):.1f} MB/s"

    @property
    def eta_human_readable(self) -> str:
        """Get human-readable ETA"""
        if self.eta_seconds < 60:
            return f"{self.eta_seconds}s"
        elif self.eta_seconds < 3600:
            return f"{self.eta_seconds // 60}m {self.eta_seconds % 60}s"
        else:
            hours = self.eta_seconds // 3600
            minutes = (self.eta_seconds % 3600) // 60
            return f"{hours}h {minutes}m"


@dataclass
class DownloadResult:
    """Download result information"""
    success: bool
    file_path: Optional[Path] = None
    error_message: Optional[str] = None
    bytes_downloaded: int = 0
    duration_seconds: float = 0.0


class NetworkError(Exception):
    """Network error exception"""
    pass


class ChecksumError(Exception):
    """Checksum verification error"""
    pass


class DownloadManager(QObject):
    """
    Robust download manager with:
    - Multi-source fallback
    - Resume capability
    - Integrity verification
    - Progress tracking
    - Retry logic
    """

    # Signals
    progress_changed = Signal(DownloadProgress)  # Download progress
    status_message = Signal(str)  # Status message
    download_started = Signal(str)  # URL
    download_completed = Signal(str)  # File path
    download_failed = Signal(str)  # Error message

    def __init__(self, cache_dir: Path, parent=None):
        super().__init__(parent)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Download settings
        self.chunk_size = 8192  # 8KB chunks
        self.timeout = 60  # 60 seconds
        self.max_retries = 4  # Max retry attempts
        self.retry_delays = [2, 4, 8, 16]  # Exponential backoff (seconds)

    def download(
        self,
        urls: List[str],
        filename: str,
        expected_checksum: Optional[str] = None,
        expected_size: Optional[int] = None,
        resume: bool = True
    ) -> DownloadResult:
        """
        Download a file with multi-source fallback and resume capability

        Args:
            urls: List of URLs to try (in order of priority)
            filename: Destination filename
            expected_checksum: Expected SHA-256 checksum
            expected_size: Expected file size in bytes
            resume: Enable resume capability

        Returns:
            DownloadResult with success status and file path
        """
        destination = self.cache_dir / filename
        start_time = time.time()

        # Try each URL
        for url_index, url in enumerate(urls):
            self.status_message.emit(f"Trying source {url_index + 1}/{len(urls)}...")

            try:
                # Try downloading from this URL with retries
                for retry in range(self.max_retries):
                    try:
                        result = self._download_with_resume(
                            url=url,
                            destination=destination,
                            resume=resume
                        )

                        # Verify integrity
                        if expected_checksum:
                            if not self._verify_checksum(destination, expected_checksum):
                                raise ChecksumError(f"Checksum mismatch for {filename}")

                        if expected_size:
                            actual_size = destination.stat().st_size
                            if actual_size != expected_size:
                                raise ChecksumError(
                                    f"Size mismatch: expected {expected_size}, got {actual_size}"
                                )

                        # Success!
                        duration = time.time() - start_time
                        self.download_completed.emit(str(destination))
                        return DownloadResult(
                            success=True,
                            file_path=destination,
                            bytes_downloaded=destination.stat().st_size,
                            duration_seconds=duration
                        )

                    except (NetworkError, requests.RequestException) as e:
                        if retry < self.max_retries - 1:
                            delay = self.retry_delays[retry]
                            self.status_message.emit(
                                f"Download failed, retrying in {delay}s... (attempt {retry + 2}/{self.max_retries})"
                            )
                            time.sleep(delay)
                        else:
                            # Max retries reached for this URL, try next
                            raise

            except Exception as e:
                # This URL failed, try next
                self.status_message.emit(f"Source {url_index + 1} failed: {str(e)}")
                continue

        # All URLs failed
        duration = time.time() - start_time
        error_msg = f"All download sources failed for {filename}"
        self.download_failed.emit(error_msg)
        return DownloadResult(
            success=False,
            error_message=error_msg,
            duration_seconds=duration
        )

    def _download_with_resume(
        self,
        url: str,
        destination: Path,
        resume: bool = True
    ) -> None:
        """
        Download file with resume capability

        Args:
            url: Source URL
            destination: Destination path
            resume: Enable resume from partial download
        """
        # Check for partial download
        existing_size = 0
        if resume and destination.exists():
            existing_size = destination.stat().st_size

        # Prepare request headers
        headers = {}
        if existing_size > 0:
            headers['Range'] = f'bytes={existing_size}-'
            self.status_message.emit(f"Resuming download from {existing_size} bytes...")

        # Make request
        self.download_started.emit(url)
        response = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=self.timeout
        )

        # Check response
        if response.status_code not in [200, 206]:  # 206 = Partial Content
            raise NetworkError(f"HTTP {response.status_code}")

        # Get total size
        total_size = int(response.headers.get('content-length', 0))
        if existing_size > 0 and response.status_code == 206:
            total_size += existing_size

        # Download with progress tracking
        mode = 'ab' if existing_size > 0 else 'wb'
        downloaded = existing_size
        start_time = time.time()

        with open(destination, mode) as f:
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Calculate progress
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        speed = (downloaded - existing_size) / elapsed
                        eta = int((total_size - downloaded) / speed) if speed > 0 else 0
                        percentage = int((downloaded / total_size) * 100) if total_size > 0 else 0

                        progress = DownloadProgress(
                            total_bytes=total_size,
                            downloaded_bytes=downloaded,
                            speed_bytes_per_sec=speed,
                            percentage=percentage,
                            eta_seconds=eta
                        )

                        self.progress_changed.emit(progress)

    def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """
        Verify file checksum

        Args:
            file_path: Path to file
            expected_checksum: Expected SHA-256 checksum

        Returns:
            True if checksum matches
        """
        self.status_message.emit("Verifying checksum...")

        # Calculate SHA-256
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        actual_checksum = sha256_hash.hexdigest()

        # Compare (case-insensitive)
        expected = expected_checksum.lower().replace('sha-256:', '')
        actual = actual_checksum.lower()

        return expected == actual

    def get_partial_download(self, filename: str) -> Optional[Path]:
        """
        Get partial download if exists

        Args:
            filename: Filename to check

        Returns:
            Path to partial download or None
        """
        destination = self.cache_dir / filename
        if destination.exists():
            return destination
        return None

    def cleanup_partial_download(self, filename: str) -> bool:
        """
        Clean up partial download

        Args:
            filename: Filename to clean up

        Returns:
            True if cleaned up
        """
        destination = self.cache_dir / filename
        if destination.exists():
            try:
                destination.unlink()
                return True
            except Exception:
                return False
        return False


class ParallelDownloadManager:
    """
    Manages multiple parallel downloads

    This can be used to download multiple packages simultaneously
    """

    def __init__(self, cache_dir: Path, max_concurrent: int = 3):
        self.cache_dir = cache_dir
        self.max_concurrent = max_concurrent
        self.active_downloads: List[DownloadManager] = []

    def download_multiple(self, download_specs: List[dict]) -> List[DownloadResult]:
        """
        Download multiple files in parallel

        Args:
            download_specs: List of download specifications
                Each spec is a dict with: urls, filename, checksum, size

        Returns:
            List of DownloadResults
        """
        results = []

        # TODO: Implement parallel download queue
        # For now, download sequentially
        for spec in download_specs:
            manager = DownloadManager(self.cache_dir)
            result = manager.download(
                urls=spec.get('urls', []),
                filename=spec.get('filename', ''),
                expected_checksum=spec.get('checksum'),
                expected_size=spec.get('size')
            )
            results.append(result)

        return results
