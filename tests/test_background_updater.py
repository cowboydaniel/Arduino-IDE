import unittest
from types import SimpleNamespace
from unittest.mock import patch

from arduino_ide.models.board import BoardCategory
from arduino_ide.services.background_updater import BackgroundUpdater


class BackgroundUpdaterTests(unittest.TestCase):
    def setUp(self):
        self.updater = BackgroundUpdater()
        self.messages = []
        self.updater.status_message.connect(self.messages.append)

    def test_find_updates_respects_offline_mode(self):
        self.updater.is_offline = True

        with patch("arduino_ide.services.background_updater.LibraryManager") as mock_lib_manager, \
             patch("arduino_ide.services.background_updater.BoardManager") as mock_board_manager:
            updates = self.updater._find_updates()

        self.assertEqual(updates, [])
        mock_lib_manager.assert_not_called()
        mock_board_manager.assert_not_called()
        self.assertTrue(any("offline" in message.lower() for message in self.messages))

    def test_find_updates_aggregates_library_and_board_updates(self):
        fake_library = SimpleNamespace(
            name="Adafruit Sensor",
            installed_version="1.0.0",
            latest_version="1.2.0",
            description="Sensor helpers",
            sentence="",
            author="Adafruit",
            category="Sensors",
        )

        fake_package = SimpleNamespace(
            name="Arduino AVR Boards",
            installed_version="1.8.5",
            latest_version="1.8.6",
            description="Core boards",
            maintainer="Arduino",
            category=BoardCategory.OFFICIAL,
        )

        fake_library_manager = SimpleNamespace(
            library_index=SimpleNamespace(
                get_libraries_with_updates=lambda: [fake_library]
            )
        )
        fake_board_manager = SimpleNamespace(
            board_index=SimpleNamespace(
                get_packages_with_updates=lambda: [fake_package]
            )
        )

        with patch("arduino_ide.services.background_updater.LibraryManager", return_value=fake_library_manager) as lib_manager_cls, \
             patch("arduino_ide.services.background_updater.BoardManager", return_value=fake_board_manager) as board_manager_cls:
            updates = self.updater._find_updates()

        self.assertEqual(len(updates), 2)

        library_update = next(update for update in updates if update["type"] == "library")
        self.assertEqual(library_update["name"], fake_library.name)
        self.assertEqual(library_update["current"], fake_library.installed_version)
        self.assertEqual(library_update["latest"], fake_library.latest_version)

        board_update = next(update for update in updates if update["type"] == "board")
        self.assertEqual(board_update["name"], fake_package.name)
        self.assertEqual(board_update["current"], fake_package.installed_version)
        self.assertEqual(board_update["latest"], fake_package.latest_version)

        lib_manager_cls.assert_called_once()
        board_manager_cls.assert_called_once()

    def test_update_callbacks_receive_payload(self):
        payload = [{
            "type": "library",
            "name": "Example",
            "current": "1.0.0",
            "latest": "1.1.0",
        }]

        callback_invocations = []
        signal_payloads = []

        self.updater.add_update_callback(lambda updates: callback_invocations.append(updates))
        self.updater.updates_available.connect(lambda updates: signal_payloads.append(updates))

        with patch.object(BackgroundUpdater, "_find_updates", return_value=payload):
            self.updater._perform_update_check()

        self.assertEqual(callback_invocations, [payload])
        self.assertEqual(signal_payloads, [payload])


if __name__ == "__main__":
    unittest.main()
