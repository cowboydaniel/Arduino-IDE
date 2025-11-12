"""
Unit Testing Panel for Arduino IDE Modern

This panel provides a comprehensive UI for running and managing unit tests.

Features:
- Test discovery and execution
- Test results display with tree view
- Test coverage visualization
- Mock function management
- Test configuration
- JUnit XML export
"""

from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QLabel, QComboBox, QSpinBox, QCheckBox,
    QGroupBox, QProgressBar, QTextEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QToolBar, QLineEdit,
    QFileDialog, QMessageBox
)
from PySide6.QtGui import QIcon, QColor, QBrush, QAction, QFont

from arduino_ide.services.unit_testing_service import (
    UnitTestingService, TestSuite, TestCase, TestStatus, TestFramework,
    TestConfiguration, TestType, MockFunction
)


class TestTreeWidget(QTreeWidget):
    """Tree widget for displaying test suites and cases"""

    test_selected = Signal(str, str)  # suite_name, test_name
    suite_selected = Signal(str)  # suite_name

    def __init__(self):
        super().__init__()

        self.setHeaderLabels(["Test", "Status", "Duration", "Location"])
        self.setColumnWidth(0, 250)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 100)
        self.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.setAlternatingRowColors(True)

        # Connect signals
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

        # Suite items mapping
        self.suite_items: Dict[str, QTreeWidgetItem] = {}
        self.test_items: Dict[str, QTreeWidgetItem] = {}

    def add_test_suite(self, suite: TestSuite):
        """Add a test suite to the tree"""
        suite_item = QTreeWidgetItem(self)
        suite_item.setText(0, f"📁 {suite.name}")
        suite_item.setText(1, f"0/{len(suite.test_cases)}")
        suite_item.setText(3, suite.file_path)
        suite_item.setData(0, Qt.UserRole, {"type": "suite", "name": suite.name})

        self.suite_items[suite.name] = suite_item

        # Add test cases
        for test_case in suite.test_cases:
            self.add_test_case(suite.name, test_case)

        suite_item.setExpanded(True)

    def add_test_case(self, suite_name: str, test_case: TestCase):
        """Add a test case to a suite"""
        if suite_name not in self.suite_items:
            return

        suite_item = self.suite_items[suite_name]

        test_item = QTreeWidgetItem(suite_item)
        test_item.setText(0, f"  {test_case.name}")
        test_item.setText(1, self._status_text(test_case.status))
        test_item.setText(2, f"{test_case.duration_ms:.1f} ms" if test_case.duration_ms > 0 else "")
        test_item.setText(3, f"{test_case.file_path}:{test_case.line_number}")
        test_item.setData(0, Qt.UserRole, {
            "type": "test",
            "suite": suite_name,
            "name": test_case.name
        })

        # Set color based on status
        self._update_test_item_color(test_item, test_case.status)

        test_id = f"{suite_name}.{test_case.name}"
        self.test_items[test_id] = test_item

    def update_test_status(self, suite_name: str, test_name: str, status: TestStatus, duration_ms: float = 0):
        """Update the status of a test"""
        test_id = f"{suite_name}.{test_name}"
        if test_id not in self.test_items:
            return

        test_item = self.test_items[test_id]
        test_item.setText(1, self._status_text(status))
        if duration_ms > 0:
            test_item.setText(2, f"{duration_ms:.1f} ms")

        self._update_test_item_color(test_item, status)

        # Update suite summary
        self._update_suite_summary(suite_name)

    def _update_suite_summary(self, suite_name: str):
        """Update the pass/total summary for a suite"""
        if suite_name not in self.suite_items:
            return

        suite_item = self.suite_items[suite_name]
        total_tests = suite_item.childCount()
        passed_tests = 0

        for i in range(total_tests):
            child = suite_item.child(i)
            status_text = child.text(1)
            if status_text == "✓ Passed":
                passed_tests += 1

        suite_item.setText(1, f"{passed_tests}/{total_tests}")

    def _status_text(self, status: TestStatus) -> str:
        """Get display text for status"""
        status_map = {
            TestStatus.PENDING: "○ Pending",
            TestStatus.RUNNING: "⟳ Running",
            TestStatus.PASSED: "✓ Passed",
            TestStatus.FAILED: "✗ Failed",
            TestStatus.SKIPPED: "⊘ Skipped",
            TestStatus.ERROR: "⚠ Error"
        }
        return status_map.get(status, "○ Pending")

    def _update_test_item_color(self, item: QTreeWidgetItem, status: TestStatus):
        """Update the color of a test item based on status"""
        color_map = {
            TestStatus.PASSED: QColor(0, 150, 0),
            TestStatus.FAILED: QColor(200, 0, 0),
            TestStatus.RUNNING: QColor(0, 100, 200),
            TestStatus.SKIPPED: QColor(150, 150, 0),
            TestStatus.ERROR: QColor(200, 100, 0),
            TestStatus.PENDING: QColor(100, 100, 100)
        }

        color = color_map.get(status, QColor(100, 100, 100))
        for col in range(4):
            item.setForeground(col, QBrush(color))

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        if data["type"] == "suite":
            self.suite_selected.emit(data["name"])
        elif data["type"] == "test":
            self.test_selected.emit(data["suite"], data["name"])

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item double click - navigate to test location"""
        location = item.text(3)
        if location and ':' in location:
            # Emit signal for navigation (to be handled by main window)
            pass

    def clear_tests(self):
        """Clear all tests"""
        self.clear()
        self.suite_items.clear()
        self.test_items.clear()


class TestOutputWidget(QWidget):
    """Widget for displaying test output"""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Test info
        self.info_label = QLabel("Select a test to view details")
        layout.addWidget(self.info_label)

        # Output text
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Monospace", 9))
        layout.addWidget(self.output_text)

        self.current_test: Optional[TestCase] = None

    def show_test_output(self, test_case: TestCase):
        """Show output for a test case"""
        self.current_test = test_case

        # Update info
        status_text = test_case.status.value.capitalize()
        self.info_label.setText(
            f"Test: {test_case.suite_name}.{test_case.name} | "
            f"Status: {status_text} | "
            f"Duration: {test_case.duration_ms:.1f} ms"
        )

        # Update output
        output = f"Test: {test_case.name}\n"
        output += f"File: {test_case.file_path}:{test_case.line_number}\n"
        output += f"Status: {status_text}\n"
        output += f"Duration: {test_case.duration_ms:.1f} ms\n"
        output += "\n"

        if test_case.error_message:
            output += f"Error: {test_case.error_message}\n\n"

        if test_case.assertions:
            output += "Assertions:\n"
            for assertion in test_case.assertions:
                output += f"  {assertion}\n"
            output += "\n"

        if test_case.output:
            output += "Output:\n"
            output += test_case.output

        self.output_text.setPlainText(output)

    def clear_output(self):
        """Clear output"""
        self.current_test = None
        self.info_label.setText("Select a test to view details")
        self.output_text.clear()


class TestCoverageWidget(QWidget):
    """Widget for displaying test coverage"""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # Overall coverage
        self.overall_group = QGroupBox("Overall Coverage")
        overall_layout = QVBoxLayout(self.overall_group)

        self.line_coverage_bar = QProgressBar()
        self.line_coverage_label = QLabel("Line Coverage: 0%")
        overall_layout.addWidget(self.line_coverage_label)
        overall_layout.addWidget(self.line_coverage_bar)

        self.function_coverage_bar = QProgressBar()
        self.function_coverage_label = QLabel("Function Coverage: 0%")
        overall_layout.addWidget(self.function_coverage_label)
        overall_layout.addWidget(self.function_coverage_bar)

        self.branch_coverage_bar = QProgressBar()
        self.branch_coverage_label = QLabel("Branch Coverage: 0%")
        overall_layout.addWidget(self.branch_coverage_label)
        overall_layout.addWidget(self.branch_coverage_bar)

        layout.addWidget(self.overall_group)

        # File coverage table
        self.file_coverage_table = QTableWidget()
        self.file_coverage_table.setColumnCount(4)
        self.file_coverage_table.setHorizontalHeaderLabels(["File", "Lines", "Functions", "Branches"])
        self.file_coverage_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(QLabel("File Coverage:"))
        layout.addWidget(self.file_coverage_table)

    def update_coverage(self, coverage):
        """Update coverage display"""
        # Overall coverage
        line_pct = coverage.line_coverage_percent()
        func_pct = coverage.function_coverage_percent()
        branch_pct = coverage.branch_coverage_percent()

        self.line_coverage_bar.setValue(int(line_pct))
        self.line_coverage_label.setText(
            f"Line Coverage: {line_pct:.1f}% ({coverage.covered_lines}/{coverage.total_lines})"
        )

        self.function_coverage_bar.setValue(int(func_pct))
        self.function_coverage_label.setText(
            f"Function Coverage: {func_pct:.1f}% ({coverage.covered_functions}/{coverage.total_functions})"
        )

        self.branch_coverage_bar.setValue(int(branch_pct))
        self.branch_coverage_label.setText(
            f"Branch Coverage: {branch_pct:.1f}% ({coverage.covered_branches}/{coverage.total_branches})"
        )

        # File coverage
        self.file_coverage_table.setRowCount(len(coverage.file_coverage))
        for row, (file_path, file_pct) in enumerate(coverage.file_coverage.items()):
            self.file_coverage_table.setItem(row, 0, QTableWidgetItem(file_path))
            self.file_coverage_table.setItem(row, 1, QTableWidgetItem(f"{file_pct:.1f}%"))


class MocksWidget(QWidget):
    """Widget for managing mock functions"""

    mock_created = Signal(str, str, list)  # name, return_type, params

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()
        self.create_mock_btn = QPushButton("Create Mock")
        self.create_mock_btn.clicked.connect(self._on_create_mock)
        self.reset_all_btn = QPushButton("Reset All")
        toolbar.addWidget(self.create_mock_btn)
        toolbar.addWidget(self.reset_all_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Mocks table
        self.mocks_table = QTableWidget()
        self.mocks_table.setColumnCount(5)
        self.mocks_table.setHorizontalHeaderLabels([
            "Function", "Return Type", "Parameters", "Call Count", "Return Value"
        ])
        self.mocks_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.mocks_table)

    def add_mock(self, mock: MockFunction):
        """Add a mock to the table"""
        row = self.mocks_table.rowCount()
        self.mocks_table.insertRow(row)

        self.mocks_table.setItem(row, 0, QTableWidgetItem(mock.name))
        self.mocks_table.setItem(row, 1, QTableWidgetItem(mock.return_type))

        params_str = ", ".join(f"{ptype} {pname}" for ptype, pname in mock.parameters)
        self.mocks_table.setItem(row, 2, QTableWidgetItem(params_str))
        self.mocks_table.setItem(row, 3, QTableWidgetItem(str(mock.call_count)))
        self.mocks_table.setItem(row, 4, QTableWidgetItem(str(mock.return_value)))

    def update_mock_call_count(self, function_name: str, call_count: int):
        """Update the call count for a mock"""
        for row in range(self.mocks_table.rowCount()):
            if self.mocks_table.item(row, 0).text() == function_name:
                self.mocks_table.item(row, 3).setText(str(call_count))
                break

    def _on_create_mock(self):
        """Handle create mock button"""
        # TODO: Show dialog for creating mock
        pass


class UnitTestingPanel(QWidget):
    """
    Main panel for unit testing

    Provides UI for:
    - Test discovery and execution
    - Test results display
    - Coverage visualization
    - Mock management
    """

    def __init__(self, testing_service: Optional[UnitTestingService] = None):
        super().__init__()

        self.testing_service = testing_service or UnitTestingService()

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QToolBar()

        self.discover_action = QAction("🔍 Discover Tests", self)
        self.discover_action.setToolTip("Discover all tests in project")
        self.discover_action.triggered.connect(self._on_discover_tests)
        toolbar.addAction(self.discover_action)

        self.run_all_action = QAction("▶ Run All", self)
        self.run_all_action.setToolTip("Run all tests (F5)")
        self.run_all_action.setShortcut("F5")
        self.run_all_action.triggered.connect(self._on_run_all_tests)
        toolbar.addAction(self.run_all_action)

        self.run_selected_action = QAction("▶ Run Selected", self)
        self.run_selected_action.setToolTip("Run selected test/suite")
        self.run_selected_action.triggered.connect(self._on_run_selected)
        toolbar.addAction(self.run_selected_action)

        self.stop_action = QAction("⏹ Stop", self)
        self.stop_action.setToolTip("Stop running tests")
        self.stop_action.setEnabled(False)
        self.stop_action.triggered.connect(self._on_stop_tests)
        toolbar.addAction(self.stop_action)

        toolbar.addSeparator()

        self.export_action = QAction("📄 Export Results", self)
        self.export_action.setToolTip("Export test results to JUnit XML")
        self.export_action.triggered.connect(self._on_export_results)
        toolbar.addAction(self.export_action)

        layout.addWidget(toolbar)

        # Configuration bar
        config_layout = QHBoxLayout()

        config_layout.addWidget(QLabel("Framework:"))
        self.framework_combo = QComboBox()
        self.framework_combo.addItems(["GoogleTest", "Unity", "AUnit"])
        self.framework_combo.currentTextChanged.connect(self._on_framework_changed)
        config_layout.addWidget(self.framework_combo)

        self.on_device_check = QCheckBox("Run on Device")
        self.on_device_check.stateChanged.connect(self._on_run_on_device_changed)
        config_layout.addWidget(self.on_device_check)

        self.coverage_check = QCheckBox("Enable Coverage")
        self.coverage_check.setChecked(True)
        config_layout.addWidget(self.coverage_check)

        config_layout.addStretch()

        layout.addLayout(config_layout)

        # Status bar
        status_layout = QHBoxLayout()

        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)

        layout.addLayout(status_layout)

        # Main splitter
        splitter = QSplitter(Qt.Vertical)

        # Test tree
        self.test_tree = TestTreeWidget()
        splitter.addWidget(self.test_tree)

        # Tab widget for output, coverage, mocks
        self.tab_widget = QTabWidget()

        self.output_widget = TestOutputWidget()
        self.tab_widget.addTab(self.output_widget, "Output")

        self.coverage_widget = TestCoverageWidget()
        self.tab_widget.addTab(self.coverage_widget, "Coverage")

        self.mocks_widget = MocksWidget()
        self.tab_widget.addTab(self.mocks_widget, "Mocks")

        splitter.addWidget(self.tab_widget)

        splitter.setSizes([400, 300])

        layout.addWidget(splitter)

    def _connect_signals(self):
        """Connect service signals"""
        self.testing_service.test_discovered.connect(self._on_test_discovered)
        self.testing_service.test_started.connect(self._on_test_started)
        self.testing_service.test_finished.connect(self._on_test_finished)
        self.testing_service.suite_finished.connect(self._on_suite_finished)
        self.testing_service.all_tests_finished.connect(self._on_all_tests_finished)
        self.testing_service.coverage_updated.connect(self._on_coverage_updated)
        self.testing_service.mock_created.connect(self._on_mock_created)

        # Tree signals
        self.test_tree.test_selected.connect(self._on_test_selected)
        self.test_tree.suite_selected.connect(self._on_suite_selected)

    @Slot()
    def _on_discover_tests(self):
        """Discover tests"""
        self.status_label.setText("Discovering tests...")
        self.test_tree.clear_tests()

        suites = self.testing_service.discover_tests()

        if suites:
            self.status_label.setText(f"Discovered {len(suites)} test suites")
        else:
            self.status_label.setText("No tests found")

    @Slot()
    def _on_run_all_tests(self):
        """Run all tests"""
        if not self.testing_service.test_suites:
            self._on_discover_tests()

        if not self.testing_service.test_suites:
            QMessageBox.warning(self, "No Tests", "No tests found in project")
            return

        self.status_label.setText("Running tests...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.run_all_action.setEnabled(False)
        self.stop_action.setEnabled(True)

        # Update configuration from UI
        self._update_configuration()

        self.testing_service.run_all_tests()

    @Slot()
    def _on_run_selected(self):
        """Run selected test/suite"""
        # Get selected item
        selected_items = self.test_tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        data = item.data(0, Qt.UserRole)

        if not data:
            return

        self._update_configuration()

        if data["type"] == "suite":
            self.testing_service.run_test_suite(data["name"])
        elif data["type"] == "test":
            self.testing_service.run_test_case(data["suite"], data["name"])

    @Slot()
    def _on_stop_tests(self):
        """Stop running tests"""
        self.testing_service.stop_tests()
        self.status_label.setText("Tests stopped")
        self.progress_bar.setVisible(False)
        self.run_all_action.setEnabled(True)
        self.stop_action.setEnabled(False)

    @Slot()
    def _on_export_results(self):
        """Export test results"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Test Results",
            "test_results.xml",
            "XML Files (*.xml)"
        )

        if file_path:
            output = self.testing_service.export_results_to_junit_xml(file_path)
            QMessageBox.information(
                self,
                "Export Complete",
                f"Test results exported to:\n{output}"
            )

    @Slot(TestSuite)
    def _on_test_discovered(self, suite: TestSuite):
        """Handle test suite discovered"""
        self.test_tree.add_test_suite(suite)

    @Slot(TestCase)
    def _on_test_started(self, test_case: TestCase):
        """Handle test started"""
        self.test_tree.update_test_status(
            test_case.suite_name,
            test_case.name,
            TestStatus.RUNNING
        )

    @Slot(TestCase)
    def _on_test_finished(self, test_case: TestCase):
        """Handle test finished"""
        self.test_tree.update_test_status(
            test_case.suite_name,
            test_case.name,
            test_case.status,
            test_case.duration_ms
        )

        # Update output if this test is selected
        if self.output_widget.current_test:
            if (self.output_widget.current_test.suite_name == test_case.suite_name and
                self.output_widget.current_test.name == test_case.name):
                self.output_widget.show_test_output(test_case)

    @Slot(TestSuite)
    def _on_suite_finished(self, suite: TestSuite):
        """Handle test suite finished"""
        pass

    @Slot(int, int, int)
    def _on_all_tests_finished(self, passed: int, failed: int, skipped: int):
        """Handle all tests finished"""
        total = passed + failed + skipped
        self.status_label.setText(
            f"Tests complete: {passed} passed, {failed} failed, {skipped} skipped"
        )
        self.progress_bar.setVisible(False)
        self.run_all_action.setEnabled(True)
        self.stop_action.setEnabled(False)

    @Slot()
    def _on_coverage_updated(self, coverage):
        """Handle coverage updated"""
        self.coverage_widget.update_coverage(coverage)

    @Slot(MockFunction)
    def _on_mock_created(self, mock: MockFunction):
        """Handle mock created"""
        self.mocks_widget.add_mock(mock)

    @Slot(str, str)
    def _on_test_selected(self, suite_name: str, test_name: str):
        """Handle test selected"""
        test_id = f"{suite_name}.{test_name}"
        if test_id in self.testing_service.test_cases:
            test_case = self.testing_service.test_cases[test_id]
            self.output_widget.show_test_output(test_case)

    @Slot(str)
    def _on_suite_selected(self, suite_name: str):
        """Handle suite selected"""
        self.output_widget.clear_output()

    @Slot(str)
    def _on_framework_changed(self, framework_name: str):
        """Handle framework changed"""
        framework_map = {
            "GoogleTest": TestFramework.GOOGLETEST,
            "Unity": TestFramework.UNITY,
            "AUnit": TestFramework.AUNIT
        }
        if framework_name in framework_map:
            config = self.testing_service.configuration
            config.framework = framework_map[framework_name]
            self.testing_service.set_configuration(config)

    @Slot(int)
    def _on_run_on_device_changed(self, state: int):
        """Handle run on device changed"""
        config = self.testing_service.configuration
        config.run_on_device = (state == Qt.Checked)
        self.testing_service.set_configuration(config)

    def _update_configuration(self):
        """Update test configuration from UI"""
        config = self.testing_service.configuration
        config.enable_coverage = self.coverage_check.isChecked()
        self.testing_service.set_configuration(config)

    def set_testing_service(self, service: UnitTestingService):
        """Set the testing service"""
        # Disconnect old signals
        if self.testing_service:
            self.testing_service.test_discovered.disconnect()
            self.testing_service.test_started.disconnect()
            self.testing_service.test_finished.disconnect()
            self.testing_service.suite_finished.disconnect()
            self.testing_service.all_tests_finished.disconnect()
            self.testing_service.coverage_updated.disconnect()
            self.testing_service.mock_created.disconnect()

        self.testing_service = service
        self._connect_signals()

    def set_project_path(self, path: str):
        """Set project path"""
        self.testing_service.set_project_path(path)
