"""
Background Update Checker

Handles:
- Background update checking
- Offline mode detection
- User notifications
- Scheduled updates
"""

import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from threading import Thread, Event
import requests
from PySide6.QtCore import QObject, Signal


class OfflineDetector:
    """
    Detects offline mode by checking internet connectivity
    """

    @staticmethod
    def is_online() -> bool:
        """
        Check if internet connection is available

        Returns:
            True if online
        """
        try:
            # Try multiple reliable endpoints
            endpoints = [
                "https://www.google.com",
                "https://www.cloudflare.com",
                "https://1.1.1.1",
            ]

            for endpoint in endpoints:
                try:
                    response = requests.head(endpoint, timeout=3)
                    if response.status_code < 500:
                        return True
                except:
                    continue

            return False

        except:
            return False

    @staticmethod
    def get_connection_quality() -> str:
        """
        Get connection quality

        Returns:
            "excellent", "good", "poor", or "offline"
        """
        try:
            start = time.time()
            response = requests.head("https://www.google.com", timeout=5)
            latency = (time.time() - start) * 1000  # ms

            if response.status_code >= 500:
                return "offline"

            if latency < 100:
                return "excellent"
            elif latency < 300:
                return "good"
            elif latency < 1000:
                return "poor"
            else:
                return "poor"

        except:
            return "offline"


class BackgroundUpdater(QObject):
    """
    Background update checker that runs periodically

    Features:
    - Non-blocking update checks
    - Scheduled updates (every N hours)
    - Notifications when updates available
    - Respects offline mode
    """

    # Signals
    updates_available = Signal(list)  # List of packages with updates
    update_check_started = Signal()
    update_check_completed = Signal(bool)  # success
    offline_mode_changed = Signal(bool)  # is_offline
    status_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # State
        self.is_running = False
        self.is_offline = False
        self.check_interval_hours = 24  # Check every 24 hours
        self.last_check: Optional[datetime] = None

        # Thread management
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

        # Update callbacks
        self._update_callbacks: List[callable] = []

    def start(self):
        """Start background update checker"""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()

        self._thread = Thread(target=self._run_background_checker, daemon=True)
        self._thread.start()

        self.status_message.emit("Background updater started")

    def stop(self):
        """Stop background update checker"""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        self.status_message.emit("Background updater stopped")

    def check_now(self):
        """Force an immediate update check"""
        if not self.is_running:
            self.start()

        # Trigger check by setting last_check to None
        self.last_check = None

    def add_update_callback(self, callback: callable):
        """
        Add a callback for when updates are found

        Args:
            callback: Function that takes list of updates
        """
        self._update_callbacks.append(callback)

    def _run_background_checker(self):
        """Background thread that periodically checks for updates"""
        while not self._stop_event.is_set():
            try:
                # Check if we should update
                if self._should_check_updates():
                    self._perform_update_check()

                # Check offline status every minute
                current_offline = not OfflineDetector.is_online()
                if current_offline != self.is_offline:
                    self.is_offline = current_offline
                    self.offline_mode_changed.emit(self.is_offline)

                    if self.is_offline:
                        self.status_message.emit("Offline mode detected")
                    else:
                        self.status_message.emit("Online mode restored")

            except Exception as e:
                self.status_message.emit(f"Background update error: {str(e)}")

            # Sleep for 1 minute
            self._stop_event.wait(60)

    def _should_check_updates(self) -> bool:
        """
        Check if we should perform update check

        Returns:
            True if check is needed
        """
        # Don't check if offline
        if self.is_offline:
            return False

        # Check if never checked
        if self.last_check is None:
            return True

        # Check if interval has passed
        time_since_check = datetime.now() - self.last_check
        return time_since_check.total_seconds() >= (self.check_interval_hours * 3600)

    def _perform_update_check(self):
        """Perform update check"""
        self.update_check_started.emit()
        self.status_message.emit("Checking for updates in background...")

        try:
            # Get available updates
            updates = self._find_updates()

            # Update last check time
            self.last_check = datetime.now()

            if updates:
                self.status_message.emit(f"Found {len(updates)} updates")
                self.updates_available.emit(updates)

                # Call registered callbacks
                for callback in self._update_callbacks:
                    try:
                        callback(updates)
                    except Exception as e:
                        print(f"Update callback error: {e}")
            else:
                self.status_message.emit("All packages are up to date")

            self.update_check_completed.emit(True)

        except Exception as e:
            self.status_message.emit(f"Update check failed: {str(e)}")
            self.update_check_completed.emit(False)

    def _find_updates(self) -> List[Dict]:
        """
        Find available updates

        Returns:
            List of update info dicts
        """
        # This would integrate with LibraryManager and BoardManager
        # For now, return empty list
        # TODO: Integrate with actual managers
        return []

    def set_check_interval(self, hours: int):
        """
        Set update check interval

        Args:
            hours: Interval in hours
        """
        self.check_interval_hours = max(1, hours)  # Minimum 1 hour

    def get_last_check_info(self) -> Dict:
        """
        Get information about last update check

        Returns:
            Dict with last check info
        """
        if self.last_check is None:
            return {
                "last_check": None,
                "last_check_human": "Never",
                "next_check": None,
                "next_check_human": "On startup",
            }

        next_check = self.last_check + timedelta(hours=self.check_interval_hours)
        time_until_next = next_check - datetime.now()

        return {
            "last_check": self.last_check.isoformat(),
            "last_check_human": self._time_ago(self.last_check),
            "next_check": next_check.isoformat(),
            "next_check_human": self._time_until(time_until_next),
        }

    def _time_ago(self, dt: datetime) -> str:
        """Convert datetime to human-readable 'time ago' string"""
        diff = datetime.now() - dt
        seconds = diff.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"

    def _time_until(self, delta: timedelta) -> str:
        """Convert timedelta to human-readable 'time until' string"""
        seconds = delta.total_seconds()

        if seconds < 0:
            return "now"
        elif seconds < 60:
            return "in less than a minute"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"in {hours} hour{'s' if hours != 1 else ''}"
        else:
            days = int(seconds / 86400)
            return f"in {days} day{'s' if days != 1 else ''}"


class OfflineMode:
    """
    Offline mode manager

    Provides offline-friendly functionality:
    - Cached library browsing
    - Local package management
    - Offline documentation
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.is_offline = not OfflineDetector.is_online()

    def get_offline_capabilities(self) -> Dict:
        """
        Get available capabilities in offline mode

        Returns:
            Dict with capability status
        """
        return {
            "browse_installed": True,
            "browse_cached": True,
            "uninstall": True,
            "view_documentation": True,
            "open_examples": True,
            "search_local": True,
            "install_new": False,
            "check_updates": False,
            "download": False,
        }

    def get_cached_packages_count(self) -> int:
        """
        Get count of cached packages

        Returns:
            Number of cached packages
        """
        # Count cached index entries
        # TODO: Implement actual counting
        return 0

    def get_offline_status_message(self) -> str:
        """
        Get user-friendly offline status message

        Returns:
            Status message
        """
        if not self.is_offline:
            return "Online - All features available"

        cached_count = self.get_cached_packages_count()

        return (
            f"Offline Mode - Limited functionality\n"
            f"• {cached_count} cached packages available\n"
            f"• Can browse and manage installed packages\n"
            f"• Cannot install new packages or check for updates"
        )
