"""Dialog for managing Hardware-in-the-Loop (HIL) test execution."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from arduino_ide.services.hil_testing_service import HILTestingService, HILTestCase, HILTestResult, TestFixture


class HILTestingDialog(QDialog):
    """Interactive dialog for configuring and running HIL suites."""

    def __init__(self, service: HILTestingService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hardware-in-the-Loop Testing")
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.resize(1100, 680)

        self._service = service
        self._current_fixture: Optional[str] = None
        self._test_items: Dict[str, Dict[str, QTreeWidgetItem]] = {}
        self._test_status: Dict[tuple, str] = {}

        self._build_ui()
        self._connect_signals()
        self._refresh_fixtures()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal, self)
        layout.addWidget(splitter, 1)

        # ------------------------------------------------------------------
        # Left column - fixtures and device setup
        # ------------------------------------------------------------------
        left_container = QWidget(splitter)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        fixtures_label = QLabel("Fixtures")
        fixtures_label.setStyleSheet("font-weight: 600;")
        left_layout.addWidget(fixtures_label)

        self.fixture_list = QListWidget(left_container)
        self.fixture_list.setSelectionMode(QListWidget.SingleSelection)
        left_layout.addWidget(self.fixture_list, 1)

        self.fixture_details_label = QLabel("Select a fixture to view details")
        self.fixture_details_label.setWordWrap(True)
        left_layout.addWidget(self.fixture_details_label)

        session_row = QHBoxLayout()
        self.start_session_button = QPushButton("Start Session")
        self.stop_session_button = QPushButton("Stop Session")
        session_row.addWidget(self.start_session_button)
        session_row.addWidget(self.stop_session_button)
        left_layout.addLayout(session_row)

        self.reload_button = QPushButton("Reload Configuration")
        left_layout.addWidget(self.reload_button)

        signal_group = QGroupBox("Signals", left_container)
        signal_layout = QVBoxLayout(signal_group)
        signal_layout.setContentsMargins(6, 6, 6, 6)

        self.signal_table = QTableWidget(signal_group)
        self.signal_table.setColumnCount(4)
        self.signal_table.setHorizontalHeaderLabels(["Name", "Pin", "Type", "Direction"])
        self.signal_table.horizontalHeader().setStretchLastSection(True)
        self.signal_table.verticalHeader().setVisible(False)
        self.signal_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.signal_table.setSelectionMode(QTableWidget.NoSelection)
        signal_layout.addWidget(self.signal_table)

        left_layout.addWidget(signal_group, 2)

        # ------------------------------------------------------------------
        # Right column - suites and logs
        # ------------------------------------------------------------------
        right_splitter = QSplitter(Qt.Vertical, splitter)

        tests_container = QWidget(right_splitter)
        tests_layout = QVBoxLayout(tests_container)
        tests_layout.setContentsMargins(0, 0, 0, 0)
        tests_layout.setSpacing(6)

        header_row = QHBoxLayout()
        tests_label = QLabel("Tests")
        tests_label.setStyleSheet("font-weight: 600;")
        header_row.addWidget(tests_label)
        header_row.addStretch(1)
        self.run_selected_button = QPushButton("Run Selected")
        self.run_all_button = QPushButton("Run All")
        header_row.addWidget(self.run_selected_button)
        header_row.addWidget(self.run_all_button)
        tests_layout.addLayout(header_row)

        self.test_tree = QTreeWidget(tests_container)
        self.test_tree.setHeaderLabels(["Test", "Status", "Last Run"])
        self.test_tree.setColumnWidth(0, 250)
        self.test_tree.setRootIsDecorated(False)
        self.test_tree.setAlternatingRowColors(True)
        tests_layout.addWidget(self.test_tree, 1)

        log_container = QWidget(right_splitter)
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(6)

        log_label = QLabel("Logs")
        log_label.setStyleSheet("font-weight: 600;")
        log_layout.addWidget(log_label)

        self.log_view = QTextEdit(log_container)
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QTextEdit.NoWrap)
        log_layout.addWidget(self.log_view, 1)

        splitter.addWidget(left_container)
        splitter.addWidget(right_splitter)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 5)
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 2)

    def _connect_signals(self) -> None:
        self.fixture_list.currentItemChanged.connect(self._on_fixture_changed)
        self.start_session_button.clicked.connect(self._on_start_session)
        self.stop_session_button.clicked.connect(self._on_stop_session)
        self.reload_button.clicked.connect(self._on_reload_configuration)
        self.run_selected_button.clicked.connect(self._on_run_selected)
        self.run_all_button.clicked.connect(self._on_run_all)
        self.test_tree.currentItemChanged.connect(self._on_test_selected)

        self._service.fixture_added.connect(self._on_fixture_added)
        self._service.fixture_removed.connect(self._on_fixture_removed)
        self._service.fixture_updated.connect(self._on_fixture_updated)
        self._service.session_started.connect(self._on_session_started)
        self._service.session_stopped.connect(self._on_session_stopped)
        self._service.log_generated.connect(self._on_log_received)
        self._service.test_registered.connect(self._on_test_registered)
        self._service.test_started.connect(self._on_test_started)
        self._service.test_finished.connect(self._on_test_finished)
        self._service.suite_finished.connect(self._on_suite_finished)

    # ------------------------------------------------------------------
    # Data refresh helpers
    # ------------------------------------------------------------------
    def _refresh_fixtures(self) -> None:
        self.fixture_list.blockSignals(True)
        self.fixture_list.clear()
        self._test_items.clear()
        fixtures = self._service.list_fixtures()
        for fixture in fixtures:
            item = QListWidgetItem(fixture.name)
            item.setData(Qt.UserRole, fixture.name)
            self.fixture_list.addItem(item)
            self._test_items[fixture.name] = {}
        self.fixture_list.blockSignals(False)
        if fixtures:
            self.fixture_list.setCurrentRow(0)
        else:
            self._current_fixture = None
            self._clear_fixture_details()

    def _clear_fixture_details(self) -> None:
        self.fixture_details_label.setText("Select a fixture to view details")
        self.signal_table.setRowCount(0)
        self.test_tree.clear()
        self.log_view.clear()
        self.start_session_button.setEnabled(False)
        self.stop_session_button.setEnabled(False)
        self.run_all_button.setEnabled(False)
        self.run_selected_button.setEnabled(False)

    def _populate_fixture_details(self, fixture: TestFixture) -> None:
        self.fixture_details_label.setText(
            f"Board: {fixture.board}\nPort: {fixture.port or 'Auto-detect'}"
        )
        signals = list(fixture.signals.values())
        self.signal_table.setRowCount(len(signals))
        for row, signal in enumerate(signals):
            self.signal_table.setItem(row, 0, QTableWidgetItem(signal.name))
            self.signal_table.setItem(row, 1, QTableWidgetItem(str(signal.pin)))
            self.signal_table.setItem(row, 2, QTableWidgetItem(signal.signal_type.value.upper()))
            self.signal_table.setItem(row, 3, QTableWidgetItem(signal.direction.value.capitalize()))
        self.signal_table.resizeColumnsToContents()

        tests = self._service.list_tests(fixture.name)
        self.test_tree.clear()
        items_map: Dict[str, QTreeWidgetItem] = {}
        for test in tests:
            item = QTreeWidgetItem(self.test_tree)
            item.setText(0, test.name)
            item.setText(1, self._test_status.get((fixture.name, test.name), "Not run"))
            item.setText(2, "")
            item.setData(0, Qt.UserRole, test.name)
            items_map[test.name] = item
        self._test_items[fixture.name] = items_map
        self.test_tree.expandAll()

        is_active = self._service.is_session_active(fixture.name)
        self.start_session_button.setEnabled(not is_active)
        self.stop_session_button.setEnabled(is_active)
        has_tests = bool(tests)
        self.run_all_button.setEnabled(has_tests)
        self.run_selected_button.setEnabled(False)

        self.log_view.clear()
        for entry in self._service.get_logs(fixture.name):
            self.log_view.append(entry)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    @Slot()
    def _on_reload_configuration(self) -> None:
        file_path = self._service.project_path / "hil_tests.json"
        if not file_path.exists():
            # Offer to create a file via save dialog for convenience
            suggested = str(file_path)
            selected, _ = QFileDialog.getSaveFileName(
                self,
                "Create HIL Configuration",
                suggested,
                "JSON Files (*.json)",
            )
            if selected:
                Path(selected).write_text(
                    json_template_fixture(),
                    encoding="utf-8",
                )
        self._service.load_configuration()
        self._refresh_fixtures()

    @Slot(QListWidgetItem, QListWidgetItem)
    def _on_fixture_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        fixture_name = current.data(Qt.UserRole) if current else None
        self._current_fixture = fixture_name
        if not fixture_name:
            self._clear_fixture_details()
            return
        fixture = self._service.get_fixture(fixture_name)
        if not fixture:
            self._clear_fixture_details()
            return
        self._populate_fixture_details(fixture)

    @Slot()
    def _on_start_session(self) -> None:
        if not self._current_fixture:
            return
        self._service.start_session(self._current_fixture)

    @Slot()
    def _on_stop_session(self) -> None:
        if not self._current_fixture:
            return
        self._service.stop_session(self._current_fixture)

    @Slot()
    def _on_run_selected(self) -> None:
        if not self._current_fixture:
            return
        current_item = self.test_tree.currentItem()
        if not current_item:
            return
        test_name = current_item.data(0, Qt.UserRole)
        if not test_name:
            return
        self._service.run_test(test_name)

    @Slot()
    def _on_run_all(self) -> None:
        if not self._current_fixture:
            return
        self._service.run_all_tests(self._current_fixture)

    @Slot(QTreeWidgetItem, QTreeWidgetItem)
    def _on_test_selected(self, current: QTreeWidgetItem, previous: QTreeWidgetItem) -> None:
        has_selection = current is not None and bool(current.data(0, Qt.UserRole))
        if not has_selection:
            self.run_selected_button.setEnabled(False)
            return
        item_status = current.text(1)
        self.run_selected_button.setEnabled(item_status != "Running…")

    @Slot(TestFixture)
    def _on_fixture_added(self, fixture: TestFixture) -> None:
        item = QListWidgetItem(fixture.name)
        item.setData(Qt.UserRole, fixture.name)
        self.fixture_list.addItem(item)
        self._test_items[fixture.name] = {}
        if self.fixture_list.count() == 1:
            self.fixture_list.setCurrentItem(item)

    @Slot(str)
    def _on_fixture_removed(self, name: str) -> None:
        for index in range(self.fixture_list.count()):
            item = self.fixture_list.item(index)
            if item.data(Qt.UserRole) == name:
                self.fixture_list.takeItem(index)
                break
        self._test_items.pop(name, None)
        if self._current_fixture == name:
            self._current_fixture = None
            self._clear_fixture_details()

    @Slot(TestFixture)
    def _on_fixture_updated(self, fixture: TestFixture) -> None:
        if fixture.name == self._current_fixture:
            self._populate_fixture_details(fixture)

    @Slot(str)
    def _on_session_started(self, fixture_name: str) -> None:
        if fixture_name != self._current_fixture:
            return
        self.start_session_button.setEnabled(False)
        self.stop_session_button.setEnabled(True)

    @Slot(str)
    def _on_session_stopped(self, fixture_name: str) -> None:
        if fixture_name != self._current_fixture:
            return
        self.start_session_button.setEnabled(True)
        self.stop_session_button.setEnabled(False)

    @Slot(str, str)
    def _on_log_received(self, fixture_name: str, message: str) -> None:
        if fixture_name != self._current_fixture:
            return
        self.log_view.append(message)

    @Slot(HILTestCase)
    def _on_test_registered(self, test: HILTestCase) -> None:
        if test.fixture_name not in self._test_items:
            self._test_items[test.fixture_name] = {}
        if test.fixture_name != self._current_fixture:
            return
        item = QTreeWidgetItem(self.test_tree)
        item.setText(0, test.name)
        item.setText(1, "Not run")
        item.setData(0, Qt.UserRole, test.name)
        self._test_items[test.fixture_name][test.name] = item
        self.run_all_button.setEnabled(True)

    @Slot(str, str)
    def _on_test_started(self, fixture_name: str, test_name: str) -> None:
        self._update_test_status(fixture_name, test_name, "Running…")

    @Slot(str, HILTestResult)
    def _on_test_finished(self, fixture_name: str, result: HILTestResult) -> None:
        status_text = "Passed" if result.passed else "Failed"
        timestamp = result.finished_at.strftime("%H:%M:%S")
        self._test_status[(fixture_name, result.test_name)] = status_text
        self._update_test_status(fixture_name, result.test_name, status_text, timestamp)
        if fixture_name == self._current_fixture:
            summary = f"Test {result.test_name} {status_text}"
            if not result.passed and result.failure_message:
                summary += f": {result.failure_message}"
            self.log_view.append(summary)

    @Slot(str, object)
    def _on_suite_finished(self, fixture_name: str, results) -> None:
        if fixture_name != self._current_fixture:
            return
        passed = sum(1 for result in results if result.passed)
        failed = len(results) - passed
        self.log_view.append(f"Suite finished: {passed} passed, {failed} failed")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _update_test_status(
        self,
        fixture_name: str,
        test_name: str,
        status: str,
        timestamp: Optional[str] = None,
    ) -> None:
        items_map = self._test_items.get(fixture_name, {})
        item = items_map.get(test_name)
        if not item:
            return
        item.setText(1, status)
        if timestamp:
            item.setText(2, timestamp)
        if fixture_name == self._current_fixture and self.test_tree.currentItem():
            self.run_selected_button.setEnabled(status != "Running…")

    def closeEvent(self, event):  # noqa: N802 (Qt API)
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
        super().closeEvent(event)


def json_template_fixture() -> str:
    """Return a starter JSON configuration for quick bootstrapping."""

    return """{\n  \"fixtures\": [\n    {\n      \"name\": \"DemoFixture\",\n      \"board\": \"arduino:avr:uno\",\n      \"port\": \"/dev/ttyUSB0\",\n      \"signals\": [\n        {\n          \"name\": \"button\",\n          \"pin\": 2,\n          \"type\": \"digital\",\n          \"direction\": \"input\"\n        },\n        {\n          \"name\": \"led\",\n          \"pin\": 13,\n          \"type\": \"digital\",\n          \"direction\": \"output\"\n        }\n      ],\n      \"tests\": [\n        {\n          \"name\": \"toggle_led\",\n          \"description\": \"Ensure the LED follows the button\",\n          \"steps\": [\n            {\n              \"description\": \"Set button HIGH\",\n              \"command\": {\"button\": 1},\n              \"expected\": {\"led\": 1},\n              \"wait_ms\": 50\n            },\n            {\n              \"description\": \"Set button LOW\",\n              \"command\": {\"button\": 0},\n              \"expected\": {\"led\": 0},\n              \"wait_ms\": 50\n            }\n          ]\n        }\n      ]\n    }\n  ]\n}\n"""
