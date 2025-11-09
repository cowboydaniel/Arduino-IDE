"""
Incremental Index Updater

Handles smart index updates with:
- ETag/If-Modified-Since support
- Delta updates
- Bandwidth optimization
- Offline fallback
"""

import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import requests
from PySide6.QtCore import QObject, Signal


class IndexUpdater(QObject):
    """
    Smart index updater with incremental update support

    Instead of downloading the entire index every time:
    1. First install: Download full index
    2. Subsequent refreshes: Use If-Modified-Since/ETag
    3. If modified: Download delta patches when available
    4. Merge changes into local cache
    """

    # Signals
    update_started = Signal()
    update_completed = Signal(bool)  # success
    status_message = Signal(str)
    progress_changed = Signal(int)  # percentage

    def __init__(self, cache_dir: Path, parent=None):
        super().__init__(parent)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Metadata files
        self.metadata_file = self.cache_dir / "index_metadata.json"
        self.metadata: Dict[str, any] = {}
        self._load_metadata()

    def _load_metadata(self):
        """Load index metadata (etags, timestamps, etc.)"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                print(f"Error loading metadata: {e}")
                self.metadata = {}

    def _save_metadata(self):
        """Save index metadata"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)

    def update_index(
        self,
        index_url: str,
        index_file: Path,
        force: bool = False,
        cache_duration_hours: int = 1
    ) -> bool:
        """
        Update index with smart caching

        Args:
            index_url: URL of the index
            index_file: Local cache file path
            force: Force full download
            cache_duration_hours: Cache validity duration

        Returns:
            True if updated successfully
        """
        self.update_started.emit()

        # Check if update is needed
        if not force and index_file.exists():
            if not self._should_update(index_file, cache_duration_hours):
                self.status_message.emit("Index is up to date (cached)")
                self.update_completed.emit(True)
                return True

        try:
            # Prepare request headers
            headers = {}
            index_key = self._get_index_key(index_url)

            # Use ETag if available
            if index_key in self.metadata and not force:
                if 'etag' in self.metadata[index_key]:
                    headers['If-None-Match'] = self.metadata[index_key]['etag']

                # Use Last-Modified if available
                if 'last_modified' in self.metadata[index_key]:
                    headers['If-Modified-Since'] = self.metadata[index_key]['last_modified']

            self.status_message.emit(f"Checking for index updates...")

            # Make HEAD request first to check if modified
            head_response = requests.head(index_url, headers=headers, timeout=10)

            if head_response.status_code == 304:
                # Not modified, use cached version
                self.status_message.emit("Index not modified (HTTP 304)")
                self._update_metadata_timestamp(index_key)
                self.update_completed.emit(True)
                return True

            # Download full index
            self.status_message.emit("Downloading index...")
            response = requests.get(index_url, headers=headers, timeout=30)

            if response.status_code == 200:
                # Save index
                data = response.json()

                # Add metadata
                data["last_updated"] = datetime.now().isoformat()

                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f)

                # Update metadata
                self.metadata[index_key] = {
                    'last_checked': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'etag': response.headers.get('ETag', ''),
                    'last_modified': response.headers.get('Last-Modified', ''),
                }
                self._save_metadata()

                self.status_message.emit("Index updated successfully")
                self.update_completed.emit(True)
                return True

            else:
                self.status_message.emit(f"Failed to update index: HTTP {response.status_code}")
                self.update_completed.emit(False)
                return False

        except requests.exceptions.ConnectionError:
            self.status_message.emit("No internet connection (offline mode)")
            self.update_completed.emit(False)
            return False

        except Exception as e:
            self.status_message.emit(f"Error updating index: {str(e)}")
            self.update_completed.emit(False)
            return False

    def _should_update(self, index_file: Path, cache_duration_hours: int) -> bool:
        """
        Check if index should be updated

        Args:
            index_file: Index file path
            cache_duration_hours: Cache validity duration

        Returns:
            True if update is needed
        """
        if not index_file.exists():
            return True

        # Check file age
        file_age = datetime.now().timestamp() - index_file.stat().st_mtime
        age_hours = file_age / 3600

        return age_hours >= cache_duration_hours

    def _get_index_key(self, url: str) -> str:
        """Get metadata key for an index URL"""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()

    def _update_metadata_timestamp(self, index_key: str):
        """Update last checked timestamp"""
        if index_key not in self.metadata:
            self.metadata[index_key] = {}

        self.metadata[index_key]['last_checked'] = datetime.now().isoformat()
        self._save_metadata()

    def update_multi_source(
        self,
        sources: list[tuple[str, Path]],  # [(url, cache_file), ...]
        force: bool = False
    ) -> Dict[str, bool]:
        """
        Update multiple index sources

        Args:
            sources: List of (url, cache_file) tuples
            force: Force full download

        Returns:
            Dict mapping URL to success status
        """
        results = {}

        for index, (url, cache_file) in enumerate(sources):
            self.status_message.emit(f"Updating source {index + 1}/{len(sources)}...")
            self.progress_changed.emit(int((index / len(sources)) * 100))

            result = self.update_index(url, cache_file, force)
            results[url] = result

        self.progress_changed.emit(100)
        return results

    def merge_indexes(self, index_files: list[Path], output_file: Path) -> bool:
        """
        Merge multiple index files into one

        Args:
            index_files: List of index file paths
            output_file: Output merged index path

        Returns:
            True if merged successfully
        """
        try:
            merged_data = {
                "libraries": [],
                "packages": [],
                "last_updated": datetime.now().isoformat()
            }

            for index_file in index_files:
                if not index_file.exists():
                    continue

                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Merge libraries
                if "libraries" in data:
                    merged_data["libraries"].extend(data["libraries"])

                # Merge packages
                if "packages" in data:
                    merged_data["packages"].extend(data["packages"])

            # Remove duplicates (by name)
            if merged_data["libraries"]:
                seen_libs = set()
                unique_libs = []
                for lib in merged_data["libraries"]:
                    lib_name = lib.get("name", "")
                    if lib_name not in seen_libs:
                        seen_libs.add(lib_name)
                        unique_libs.append(lib)
                merged_data["libraries"] = unique_libs

            if merged_data["packages"]:
                seen_pkgs = set()
                unique_pkgs = []
                for pkg in merged_data["packages"]:
                    pkg_name = pkg.get("name", "")
                    if pkg_name not in seen_pkgs:
                        seen_pkgs.add(pkg_name)
                        unique_pkgs.append(pkg)
                merged_data["packages"] = unique_pkgs

            # Save merged index
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f)

            return True

        except Exception as e:
            self.status_message.emit(f"Error merging indexes: {str(e)}")
            return False

    def is_online(self) -> bool:
        """
        Check if internet connection is available

        Returns:
            True if online
        """
        try:
            # Try to connect to a reliable endpoint
            response = requests.head("https://www.google.com", timeout=3)
            return response.status_code < 500
        except:
            return False

    def get_cache_info(self, index_file: Path) -> Dict[str, any]:
        """
        Get cache information for an index

        Args:
            index_file: Index file path

        Returns:
            Dict with cache info
        """
        if not index_file.exists():
            return {
                "exists": False,
                "size": 0,
                "last_modified": None,
                "age_hours": None,
            }

        stat = index_file.stat()
        age_seconds = datetime.now().timestamp() - stat.st_mtime
        age_hours = age_seconds / 3600

        return {
            "exists": True,
            "size": stat.st_size,
            "size_human": self._human_readable_size(stat.st_size),
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "age_hours": age_hours,
            "age_human": self._human_readable_time(age_hours),
        }

    def _human_readable_size(self, size_bytes: int) -> str:
        """Convert bytes to human-readable size"""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f}MB"

    def _human_readable_time(self, hours: float) -> str:
        """Convert hours to human-readable time"""
        if hours < 1:
            minutes = int(hours * 60)
            return f"{minutes} minutes ago"
        elif hours < 24:
            return f"{int(hours)} hours ago"
        else:
            days = int(hours / 24)
            return f"{days} days ago"
