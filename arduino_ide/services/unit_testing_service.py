"""
Unit Testing Service for Arduino IDE Modern

This service provides comprehensive unit testing capabilities for Arduino projects,
supporting multiple testing frameworks including GoogleTest and Unity.

Features:
- GoogleTest and Unity framework support
- Test discovery and execution
- Test coverage reporting
- Mocking support for hardware functions
- Test result aggregation and reporting
- Host-based and on-device testing
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable
import json
import re
import subprocess
import time

from PySide6.QtCore import QObject, Signal, QProcess, QTimer


class TestFramework(Enum):
    """Supported test frameworks"""
    GOOGLETEST = "googletest"
    UNITY = "unity"
    AUNIT = "aunit"  # Arduino-specific unit testing
    CUSTOM = "custom"


class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestType(Enum):
    """Type of test"""
    UNIT = "unit"  # Unit tests for individual functions
    INTEGRATION = "integration"  # Integration tests
    FUNCTIONAL = "functional"  # Functional tests
    HARDWARE = "hardware"  # Hardware-in-loop tests


class AssertionType(Enum):
    """Types of test assertions"""
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    TRUE = "true"
    FALSE = "false"
    NULL = "null"
    NOT_NULL = "not_null"
    GREATER = "greater"
    LESS = "less"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    NEAR = "near"  # For floating point comparisons
    THROWS = "throws"  # For exception testing
    NO_THROW = "no_throw"


@dataclass
class TestAssertion:
    """Represents a single test assertion"""
    assertion_type: AssertionType
    expected: any
    actual: any
    passed: bool
    message: str = ""
    line_number: int = 0

    def __str__(self) -> str:
        status = "✓" if self.passed else "✗"
        return f"{status} {self.message}: expected {self.expected}, got {self.actual}"


@dataclass
class TestCase:
    """Represents a single test case"""
    name: str
    file_path: str
    line_number: int
    test_type: TestType
    status: TestStatus = TestStatus.PENDING
    duration_ms: float = 0.0
    assertions: List[TestAssertion] = field(default_factory=list)
    error_message: str = ""
    output: str = ""
    suite_name: str = ""

    def passed(self) -> bool:
        """Check if test passed"""
        return self.status == TestStatus.PASSED

    def failed(self) -> bool:
        """Check if test failed"""
        return self.status == TestStatus.FAILED

    def add_assertion(self, assertion: TestAssertion):
        """Add an assertion to this test"""
        self.assertions.append(assertion)


@dataclass
class TestSuite:
    """Represents a test suite (group of related tests)"""
    name: str
    file_path: str
    framework: TestFramework
    test_cases: List[TestCase] = field(default_factory=list)
    setup_code: str = ""
    teardown_code: str = ""

    def add_test(self, test_case: TestCase):
        """Add a test case to this suite"""
        test_case.suite_name = self.name
        self.test_cases.append(test_case)

    def total_tests(self) -> int:
        """Get total number of tests"""
        return len(self.test_cases)

    def passed_tests(self) -> int:
        """Get number of passed tests"""
        return sum(1 for test in self.test_cases if test.passed())

    def failed_tests(self) -> int:
        """Get number of failed tests"""
        return sum(1 for test in self.test_cases if test.failed())

    def total_duration_ms(self) -> float:
        """Get total duration of all tests"""
        return sum(test.duration_ms for test in self.test_cases)


@dataclass
class TestCoverage:
    """Test coverage information"""
    total_lines: int = 0
    covered_lines: int = 0
    total_functions: int = 0
    covered_functions: int = 0
    total_branches: int = 0
    covered_branches: int = 0
    file_coverage: Dict[str, float] = field(default_factory=dict)

    def line_coverage_percent(self) -> float:
        """Calculate line coverage percentage"""
        if self.total_lines == 0:
            return 0.0
        return (self.covered_lines / self.total_lines) * 100.0

    def function_coverage_percent(self) -> float:
        """Calculate function coverage percentage"""
        if self.total_functions == 0:
            return 0.0
        return (self.covered_functions / self.total_functions) * 100.0

    def branch_coverage_percent(self) -> float:
        """Calculate branch coverage percentage"""
        if self.total_branches == 0:
            return 0.0
        return (self.covered_branches / self.total_branches) * 100.0


@dataclass
class MockFunction:
    """Represents a mocked hardware function"""
    name: str
    return_type: str
    parameters: List[tuple]  # (type, name) tuples
    return_value: any = None
    call_count: int = 0
    call_history: List[Dict] = field(default_factory=list)
    side_effect: Optional[Callable] = None

    def record_call(self, args: Dict):
        """Record a function call"""
        self.call_count += 1
        self.call_history.append({
            'timestamp': datetime.now(),
            'args': args,
            'return_value': self.return_value
        })


@dataclass
class TestConfiguration:
    """Test execution configuration"""
    framework: TestFramework = TestFramework.GOOGLETEST
    test_directory: str = "test"
    include_patterns: List[str] = field(default_factory=lambda: ["test_*.cpp", "*_test.cpp"])
    exclude_patterns: List[str] = field(default_factory=list)
    run_on_device: bool = False  # Run on actual Arduino or on host
    board: str = "arduino:avr:uno"
    port: str = ""
    timeout_seconds: int = 30
    enable_coverage: bool = True
    enable_mocking: bool = True
    parallel_execution: bool = False
    repeat_count: int = 1
    shuffle_tests: bool = False


class UnitTestingService(QObject):
    """
    Service for managing unit tests in Arduino projects

    Signals:
        test_discovered: Emitted when tests are discovered
        test_started: Emitted when a test starts running
        test_finished: Emitted when a test finishes
        suite_finished: Emitted when a test suite finishes
        all_tests_finished: Emitted when all tests complete
        coverage_updated: Emitted when coverage data is updated
        mock_created: Emitted when a mock function is created
    """

    # Signals
    test_discovered = Signal(TestSuite)
    test_started = Signal(TestCase)
    test_finished = Signal(TestCase)
    suite_finished = Signal(TestSuite)
    all_tests_finished = Signal(int, int, int)  # passed, failed, skipped
    coverage_updated = Signal(TestCoverage)
    mock_created = Signal(MockFunction)

    def __init__(self, project_path: str = "", arduino_cli_path: str = "arduino-cli"):
        super().__init__()

        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.arduino_cli_path = arduino_cli_path

        # Test data
        self.test_suites: Dict[str, TestSuite] = {}
        self.test_cases: Dict[str, TestCase] = {}
        self.configuration = TestConfiguration()
        self.coverage = TestCoverage()
        self.mocks: Dict[str, MockFunction] = {}

        # Execution state
        self.running = False
        self.current_process: Optional[QProcess] = None
        self.test_output_buffer = ""

        # Framework-specific parsers
        self.framework_parsers = {
            TestFramework.GOOGLETEST: self._parse_googletest_output,
            TestFramework.UNITY: self._parse_unity_output,
            TestFramework.AUNIT: self._parse_aunit_output,
        }

    def set_project_path(self, path: str):
        """Set the project path"""
        self.project_path = Path(path)

    def set_configuration(self, config: TestConfiguration):
        """Set test configuration"""
        self.configuration = config

    def discover_tests(self) -> List[TestSuite]:
        """
        Discover all tests in the project

        Returns:
            List of discovered test suites
        """
        self.test_suites.clear()
        self.test_cases.clear()

        test_dir = self.project_path / self.configuration.test_directory
        if not test_dir.exists():
            return []

        # Find all test files
        test_files = []
        for pattern in self.configuration.include_patterns:
            test_files.extend(test_dir.glob(f"**/{pattern}"))

        # Parse each test file
        for test_file in test_files:
            # Check exclusions
            excluded = False
            for exclude_pattern in self.configuration.exclude_patterns:
                if test_file.match(exclude_pattern):
                    excluded = True
                    break

            if excluded:
                continue

            # Parse test file based on framework
            suite = self._parse_test_file(test_file)
            if suite and suite.test_cases:
                self.test_suites[suite.name] = suite
                self.test_discovered.emit(suite)

                # Add test cases to lookup dict
                for test_case in suite.test_cases:
                    test_id = f"{suite.name}.{test_case.name}"
                    self.test_cases[test_id] = test_case

        return list(self.test_suites.values())

    def _parse_test_file(self, file_path: Path) -> Optional[TestSuite]:
        """Parse a test file to extract test cases"""
        try:
            content = file_path.read_text()
        except Exception as e:
            print(f"Error reading test file {file_path}: {e}")
            return None

        framework = self.configuration.framework
        suite_name = file_path.stem

        suite = TestSuite(
            name=suite_name,
            file_path=str(file_path),
            framework=framework
        )

        if framework == TestFramework.GOOGLETEST:
            self._parse_googletest_file(content, suite, file_path)
        elif framework == TestFramework.UNITY:
            self._parse_unity_file(content, suite, file_path)
        elif framework == TestFramework.AUNIT:
            self._parse_aunit_file(content, suite, file_path)

        return suite

    def _parse_googletest_file(self, content: str, suite: TestSuite, file_path: Path):
        """Parse GoogleTest test file"""
        # Match TEST(SuiteName, TestName) or TEST_F(FixtureName, TestName)
        test_pattern = r'TEST(?:_F)?\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)'

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            match = re.search(test_pattern, line)
            if match:
                suite_name, test_name = match.groups()
                suite.name = suite_name

                test_case = TestCase(
                    name=test_name,
                    file_path=str(file_path),
                    line_number=i,
                    test_type=TestType.UNIT
                )
                suite.add_test(test_case)

    def _parse_unity_file(self, content: str, suite: TestSuite, file_path: Path):
        """Parse Unity test file"""
        # Match void test_FunctionName(void) pattern
        test_pattern = r'void\s+test_(\w+)\s*\(\s*void\s*\)'

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            match = re.search(test_pattern, line)
            if match:
                test_name = match.group(1)

                test_case = TestCase(
                    name=f"test_{test_name}",
                    file_path=str(file_path),
                    line_number=i,
                    test_type=TestType.UNIT
                )
                suite.add_test(test_case)

    def _parse_aunit_file(self, content: str, suite: TestSuite, file_path: Path):
        """Parse AUnit (Arduino) test file"""
        # Match test(SuiteName, TestName) or testing(TestName)
        test_pattern = r'(?:test|testing)\s*\(\s*(?:(\w+)\s*,\s*)?(\w+)\s*\)'

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            match = re.search(test_pattern, line)
            if match:
                suite_name, test_name = match.groups()
                if suite_name:
                    suite.name = suite_name

                test_case = TestCase(
                    name=test_name or "unnamed",
                    file_path=str(file_path),
                    line_number=i,
                    test_type=TestType.UNIT
                )
                suite.add_test(test_case)

    def run_all_tests(self) -> bool:
        """
        Run all discovered tests

        Returns:
            True if tests started successfully
        """
        if self.running:
            return False

        if not self.test_suites:
            self.discover_tests()

        if not self.test_suites:
            return False

        self.running = True

        # Reset test statuses
        for suite in self.test_suites.values():
            for test_case in suite.test_cases:
                test_case.status = TestStatus.PENDING
                test_case.assertions.clear()
                test_case.error_message = ""
                test_case.output = ""

        # Run tests
        if self.configuration.run_on_device:
            self._run_tests_on_device()
        else:
            self._run_tests_on_host()

        return True

    def run_test_suite(self, suite_name: str) -> bool:
        """Run a specific test suite"""
        if suite_name not in self.test_suites:
            return False

        suite = self.test_suites[suite_name]

        # Reset test statuses
        for test_case in suite.test_cases:
            test_case.status = TestStatus.PENDING

        self.running = True

        if self.configuration.run_on_device:
            self._run_suite_on_device(suite)
        else:
            self._run_suite_on_host(suite)

        return True

    def run_test_case(self, suite_name: str, test_name: str) -> bool:
        """Run a specific test case"""
        test_id = f"{suite_name}.{test_name}"
        if test_id not in self.test_cases:
            return False

        test_case = self.test_cases[test_id]
        test_case.status = TestStatus.PENDING

        self.running = True

        if self.configuration.run_on_device:
            self._run_test_on_device(test_case)
        else:
            self._run_test_on_host(test_case)

        return True

    def _run_tests_on_host(self):
        """Run tests on the host machine"""
        # Build test executable
        build_dir = self.project_path / "build" / "test"
        build_dir.mkdir(parents=True, exist_ok=True)

        # Compile tests
        compile_success = self._compile_tests_for_host(build_dir)
        if not compile_success:
            self._finish_all_tests_with_error("Compilation failed")
            return

        # Execute tests
        test_executable = build_dir / "test_runner"
        if not test_executable.exists():
            self._finish_all_tests_with_error("Test executable not found")
            return

        # Run test executable
        self.current_process = QProcess()
        self.current_process.readyReadStandardOutput.connect(self._on_test_output)
        self.current_process.readyReadStandardError.connect(self._on_test_error)
        self.current_process.finished.connect(self._on_test_process_finished)

        self.test_output_buffer = ""
        self.current_process.start(str(test_executable), [])

    def _run_suite_on_host(self, suite: TestSuite):
        """Run a specific test suite on host"""
        # Similar to _run_tests_on_host but with suite filter
        build_dir = self.project_path / "build" / "test"
        test_executable = build_dir / "test_runner"

        if not test_executable.exists():
            return

        self.current_process = QProcess()
        self.current_process.readyReadStandardOutput.connect(self._on_test_output)
        self.current_process.readyReadStandardError.connect(self._on_test_error)
        self.current_process.finished.connect(self._on_test_process_finished)

        # Add filter for specific suite
        args = [f"--gtest_filter={suite.name}.*"]

        self.test_output_buffer = ""
        self.current_process.start(str(test_executable), args)

    def _run_test_on_host(self, test_case: TestCase):
        """Run a specific test case on host"""
        build_dir = self.project_path / "build" / "test"
        test_executable = build_dir / "test_runner"

        if not test_executable.exists():
            return

        self.current_process = QProcess()
        self.current_process.readyReadStandardOutput.connect(self._on_test_output)
        self.current_process.readyReadStandardError.connect(self._on_test_error)
        self.current_process.finished.connect(self._on_test_process_finished)

        # Add filter for specific test
        args = [f"--gtest_filter={test_case.suite_name}.{test_case.name}"]

        self.test_output_buffer = ""
        self.current_process.start(str(test_executable), args)

    def _compile_tests_for_host(self, build_dir: Path) -> bool:
        """Compile tests for host execution"""
        try:
            # Create CMakeLists.txt for tests
            cmake_content = self._generate_cmake_for_tests()
            cmake_file = build_dir / "CMakeLists.txt"
            cmake_file.write_text(cmake_content)

            # Run CMake
            result = subprocess.run(
                ["cmake", ".."],
                cwd=str(build_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"CMake failed: {result.stderr}")
                return False

            # Run make
            result = subprocess.run(
                ["make", "-j4"],
                cwd=str(build_dir),
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                print(f"Make failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            print(f"Compilation error: {e}")
            return False

    def _generate_cmake_for_tests(self) -> str:
        """Generate CMakeLists.txt for test compilation"""
        framework = self.configuration.framework

        cmake_content = """cmake_minimum_required(VERSION 3.10)
project(ArduinoTests)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
"""

        if framework == TestFramework.GOOGLETEST:
            cmake_content += """
# GoogleTest
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})

# Test sources
file(GLOB TEST_SOURCES "../test/*.cpp" "../test/**/*.cpp")
file(GLOB SOURCES "../src/*.cpp" "../src/**/*.cpp")

# Test executable
add_executable(test_runner ${TEST_SOURCES} ${SOURCES})
target_link_libraries(test_runner ${GTEST_LIBRARIES} pthread)
"""
        elif framework == TestFramework.UNITY:
            cmake_content += """
# Unity
include_directories(../test/unity)

# Test sources
file(GLOB TEST_SOURCES "../test/*.c" "../test/**/*.c")
file(GLOB SOURCES "../src/*.c" "../src/**/*.c")

# Test executable
add_executable(test_runner ${TEST_SOURCES} ${SOURCES} ../test/unity/unity.c)
"""

        if self.configuration.enable_coverage:
            cmake_content += """
# Coverage flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g -O0 --coverage")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -g -O0 --coverage")
"""

        return cmake_content

    def _run_tests_on_device(self):
        """Run tests on actual Arduino hardware"""
        # Compile and upload test firmware
        upload_success = self._upload_test_firmware()
        if not upload_success:
            self._finish_all_tests_with_error("Upload failed")
            return

        # Connect to serial and capture output
        self._capture_serial_test_output()

    def _run_suite_on_device(self, suite: TestSuite):
        """Run test suite on device"""
        # Similar to _run_tests_on_device but with suite filter
        self._upload_test_firmware(suite_filter=suite.name)
        self._capture_serial_test_output()

    def _run_test_on_device(self, test_case: TestCase):
        """Run test case on device"""
        test_filter = f"{test_case.suite_name}.{test_case.name}"
        self._upload_test_firmware(test_filter=test_filter)
        self._capture_serial_test_output()

    def _upload_test_firmware(self, suite_filter: str = "", test_filter: str = "") -> bool:
        """Compile and upload test firmware to device"""
        try:
            # Generate test main file
            test_main = self._generate_test_main(suite_filter, test_filter)
            test_main_file = self.project_path / "test" / "test_main.ino"
            test_main_file.write_text(test_main)

            # Compile
            compile_cmd = [
                self.arduino_cli_path,
                "compile",
                "--fqbn", self.configuration.board,
                str(self.project_path / "test")
            ]

            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                print(f"Compile failed: {result.stderr}")
                return False

            # Upload
            upload_cmd = [
                self.arduino_cli_path,
                "upload",
                "--fqbn", self.configuration.board,
                "--port", self.configuration.port,
                str(self.project_path / "test")
            ]

            result = subprocess.run(
                upload_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                print(f"Upload failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            print(f"Upload error: {e}")
            return False

    def _generate_test_main(self, suite_filter: str = "", test_filter: str = "") -> str:
        """Generate test main file for Arduino"""
        framework = self.configuration.framework

        if framework == TestFramework.AUNIT:
            main_content = """#include <AUnit.h>

// Include test files
"""
            for suite in self.test_suites.values():
                if suite_filter and suite.name != suite_filter:
                    continue
                main_content += f'#include "{Path(suite.file_path).name}"\n'

            main_content += """
void setup() {
  Serial.begin(115200);
  while(!Serial);
"""

            if test_filter:
                main_content += f'  TestRunner::setFilter("{test_filter}");\n'
            elif suite_filter:
                main_content += f'  TestRunner::setFilter("{suite_filter}.*");\n'

            main_content += """
}

void loop() {
  TestRunner::run();
}
"""
        else:
            main_content = "// Custom test framework not fully supported for on-device testing\n"

        return main_content

    def _capture_serial_test_output(self):
        """Capture test output from serial port"""
        try:
            import serial

            ser = serial.Serial(
                self.configuration.port,
                115200,
                timeout=self.configuration.timeout_seconds
            )

            # Give device time to reset
            time.sleep(2)

            self.test_output_buffer = ""

            # Read until timeout or completion
            start_time = time.time()
            while time.time() - start_time < self.configuration.timeout_seconds:
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8', errors='ignore')
                    self.test_output_buffer += line

                    # Check for completion markers
                    if "TestRunner summary:" in line or "All tests complete" in line:
                        break

            ser.close()

            # Parse output
            self._parse_test_output(self.test_output_buffer)
            self._finish_all_tests()

        except Exception as e:
            print(f"Serial capture error: {e}")
            self._finish_all_tests_with_error(str(e))

    def _on_test_output(self):
        """Handle test process output"""
        if self.current_process:
            output = self.current_process.readAllStandardOutput().data().decode('utf-8')
            self.test_output_buffer += output

    def _on_test_error(self):
        """Handle test process error output"""
        if self.current_process:
            error = self.current_process.readAllStandardError().data().decode('utf-8')
            self.test_output_buffer += error

    def _on_test_process_finished(self, exit_code: int, exit_status):
        """Handle test process completion"""
        # Parse test output
        self._parse_test_output(self.test_output_buffer)

        # Generate coverage if enabled
        if self.configuration.enable_coverage:
            self._generate_coverage_report()

        self._finish_all_tests()

    def _parse_test_output(self, output: str):
        """Parse test output based on framework"""
        framework = self.configuration.framework
        parser = self.framework_parsers.get(framework)

        if parser:
            parser(output)

    def _parse_googletest_output(self, output: str):
        """Parse GoogleTest output"""
        lines = output.split('\n')

        current_test = None

        for line in lines:
            # Match test start: [ RUN      ] SuiteName.TestName
            run_match = re.search(r'\[\s*RUN\s*\]\s+(\w+)\.(\w+)', line)
            if run_match:
                suite_name, test_name = run_match.groups()
                test_id = f"{suite_name}.{test_name}"

                if test_id in self.test_cases:
                    current_test = self.test_cases[test_id]
                    current_test.status = TestStatus.RUNNING
                    current_test.output = ""
                    self.test_started.emit(current_test)

            # Match test result: [       OK ] SuiteName.TestName (X ms)
            ok_match = re.search(r'\[\s*OK\s*\]\s+(\w+)\.(\w+)\s+\((\d+)\s*ms\)', line)
            if ok_match:
                suite_name, test_name, duration = ok_match.groups()
                test_id = f"{suite_name}.{test_name}"

                if test_id in self.test_cases:
                    test_case = self.test_cases[test_id]
                    test_case.status = TestStatus.PASSED
                    test_case.duration_ms = float(duration)
                    self.test_finished.emit(test_case)
                    current_test = None

            # Match test failure: [  FAILED  ] SuiteName.TestName (X ms)
            failed_match = re.search(r'\[\s*FAILED\s*\]\s+(\w+)\.(\w+)\s+\((\d+)\s*ms\)', line)
            if failed_match:
                suite_name, test_name, duration = failed_match.groups()
                test_id = f"{suite_name}.{test_name}"

                if test_id in self.test_cases:
                    test_case = self.test_cases[test_id]
                    test_case.status = TestStatus.FAILED
                    test_case.duration_ms = float(duration)
                    self.test_finished.emit(test_case)
                    current_test = None

            # Collect output for current test
            if current_test:
                current_test.output += line + "\n"

                # Parse assertions
                assertion_match = re.search(r'(.*):(\d+):\s+Failure', line)
                if assertion_match:
                    file_path, line_num = assertion_match.groups()
                    current_test.error_message = line

    def _parse_unity_output(self, output: str):
        """Parse Unity test framework output"""
        lines = output.split('\n')

        for line in lines:
            # Match test result: test_FunctionName:PASS or test_FunctionName:FAIL
            match = re.search(r'(test_\w+):(PASS|FAIL)', line)
            if match:
                test_name, result = match.groups()

                # Find test case
                for test_case in self.test_cases.values():
                    if test_case.name == test_name:
                        test_case.status = TestStatus.PASSED if result == "PASS" else TestStatus.FAILED
                        self.test_finished.emit(test_case)
                        break

    def _parse_aunit_output(self, output: str):
        """Parse AUnit (Arduino) output"""
        lines = output.split('\n')

        for line in lines:
            # Match test result: TestRunner summary: X passed, Y failed, Z skipped
            summary_match = re.search(r'TestRunner summary:\s*(\d+)\s+passed,\s*(\d+)\s+failed,\s*(\d+)\s+skipped', line)
            if summary_match:
                passed, failed, skipped = map(int, summary_match.groups())
                # Update test statuses based on summary
                continue

            # Match individual test: Test SuiteName_TestName passed
            test_match = re.search(r'Test\s+(\w+)_(\w+)\s+(passed|failed)', line)
            if test_match:
                suite_name, test_name, result = test_match.groups()
                test_id = f"{suite_name}.{test_name}"

                if test_id in self.test_cases:
                    test_case = self.test_cases[test_id]
                    test_case.status = TestStatus.PASSED if result == "passed" else TestStatus.FAILED
                    self.test_finished.emit(test_case)

    def _generate_coverage_report(self):
        """Generate code coverage report"""
        try:
            build_dir = self.project_path / "build" / "test"

            # Run gcov to generate coverage
            result = subprocess.run(
                ["gcov", "-r", "-b", "*.gcno"],
                cwd=str(build_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse gcov output
            self._parse_coverage_output(result.stdout)

            self.coverage_updated.emit(self.coverage)

        except Exception as e:
            print(f"Coverage generation error: {e}")

    def _parse_coverage_output(self, output: str):
        """Parse gcov coverage output"""
        lines = output.split('\n')

        for line in lines:
            # Match coverage line: Lines executed:75.00% of 100
            line_match = re.search(r'Lines executed:(\d+\.\d+)%\s+of\s+(\d+)', line)
            if line_match:
                percent, total = line_match.groups()
                covered = int(float(percent) * int(total) / 100.0)
                self.coverage.covered_lines += covered
                self.coverage.total_lines += int(total)

            # Match function coverage
            func_match = re.search(r'Functions executed:(\d+\.\d+)%\s+of\s+(\d+)', line)
            if func_match:
                percent, total = func_match.groups()
                covered = int(float(percent) * int(total) / 100.0)
                self.coverage.covered_functions += covered
                self.coverage.total_functions += int(total)

            # Match branch coverage
            branch_match = re.search(r'Branches executed:(\d+\.\d+)%\s+of\s+(\d+)', line)
            if branch_match:
                percent, total = branch_match.groups()
                covered = int(float(percent) * int(total) / 100.0)
                self.coverage.covered_branches += covered
                self.coverage.total_branches += int(total)

    def _finish_all_tests(self):
        """Finish test execution"""
        self.running = False

        # Count results
        passed = sum(1 for test in self.test_cases.values() if test.status == TestStatus.PASSED)
        failed = sum(1 for test in self.test_cases.values() if test.status == TestStatus.FAILED)
        skipped = sum(1 for test in self.test_cases.values() if test.status == TestStatus.SKIPPED)

        # Emit suite finished for each suite
        for suite in self.test_suites.values():
            self.suite_finished.emit(suite)

        self.all_tests_finished.emit(passed, failed, skipped)

    def _finish_all_tests_with_error(self, error: str):
        """Finish tests with error"""
        self.running = False

        # Mark all pending tests as error
        for test in self.test_cases.values():
            if test.status == TestStatus.PENDING:
                test.status = TestStatus.ERROR
                test.error_message = error

        self.all_tests_finished.emit(0, 0, len(self.test_cases))

    def stop_tests(self):
        """Stop running tests"""
        if self.current_process and self.current_process.state() == QProcess.Running:
            self.current_process.kill()

        self.running = False

    # Mock functions

    def create_mock(self, function_name: str, return_type: str,
                   parameters: List[tuple], return_value: any = None) -> MockFunction:
        """
        Create a mock for a hardware function

        Args:
            function_name: Name of the function to mock
            return_type: Return type of the function
            parameters: List of (type, name) tuples for parameters
            return_value: Default return value

        Returns:
            MockFunction object
        """
        mock = MockFunction(
            name=function_name,
            return_type=return_type,
            parameters=parameters,
            return_value=return_value
        )

        self.mocks[function_name] = mock
        self.mock_created.emit(mock)

        return mock

    def set_mock_return_value(self, function_name: str, return_value: any):
        """Set the return value for a mocked function"""
        if function_name in self.mocks:
            self.mocks[function_name].return_value = return_value

    def set_mock_side_effect(self, function_name: str, side_effect: Callable):
        """Set a side effect function for a mock"""
        if function_name in self.mocks:
            self.mocks[function_name].side_effect = side_effect

    def get_mock_call_count(self, function_name: str) -> int:
        """Get the number of times a mock was called"""
        if function_name in self.mocks:
            return self.mocks[function_name].call_count
        return 0

    def get_mock_call_history(self, function_name: str) -> List[Dict]:
        """Get the call history of a mock"""
        if function_name in self.mocks:
            return self.mocks[function_name].call_history
        return []

    def reset_mock(self, function_name: str):
        """Reset a mock's call count and history"""
        if function_name in self.mocks:
            self.mocks[function_name].call_count = 0
            self.mocks[function_name].call_history.clear()

    def reset_all_mocks(self):
        """Reset all mocks"""
        for mock in self.mocks.values():
            mock.call_count = 0
            mock.call_history.clear()

    def generate_mock_header(self, output_file: str = "mocks.h") -> str:
        """
        Generate a header file with mock definitions

        Args:
            output_file: Output file path

        Returns:
            Path to generated file
        """
        header_content = """#ifndef ARDUINO_MOCKS_H
#define ARDUINO_MOCKS_H

// Auto-generated mock functions for Arduino IDE Modern

#include <stdint.h>

"""

        for mock in self.mocks.values():
            # Generate mock function declaration
            params = ", ".join(f"{ptype} {pname}" for ptype, pname in mock.parameters)
            header_content += f"{mock.return_type} {mock.name}_mock({params});\n"

            # Generate mock macro
            header_content += f"#define {mock.name} {mock.name}_mock\n\n"

        header_content += "#endif // ARDUINO_MOCKS_H\n"

        output_path = self.project_path / "test" / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(header_content)

        return str(output_path)

    # Test generation helpers

    def generate_test_template(self, suite_name: str, test_name: str,
                              framework: Optional[TestFramework] = None) -> str:
        """
        Generate a test template

        Args:
            suite_name: Name of the test suite
            test_name: Name of the test
            framework: Test framework (uses config if not specified)

        Returns:
            Test template code
        """
        if framework is None:
            framework = self.configuration.framework

        if framework == TestFramework.GOOGLETEST:
            return f"""TEST({suite_name}, {test_name}) {{
  // Arrange

  // Act

  // Assert
  EXPECT_EQ(expected, actual);
}}
"""
        elif framework == TestFramework.UNITY:
            return f"""void test_{test_name}(void) {{
  // Arrange

  // Act

  // Assert
  TEST_ASSERT_EQUAL(expected, actual);
}}
"""
        elif framework == TestFramework.AUNIT:
            return f"""test({suite_name}, {test_name}) {{
  // Arrange

  // Act

  // Assert
  assertEqual(expected, actual);
}}
"""

        return ""

    def get_test_statistics(self) -> Dict:
        """Get overall test statistics"""
        total = len(self.test_cases)
        passed = sum(1 for test in self.test_cases.values() if test.status == TestStatus.PASSED)
        failed = sum(1 for test in self.test_cases.values() if test.status == TestStatus.FAILED)
        skipped = sum(1 for test in self.test_cases.values() if test.status == TestStatus.SKIPPED)
        error = sum(1 for test in self.test_cases.values() if test.status == TestStatus.ERROR)

        total_duration = sum(test.duration_ms for test in self.test_cases.values())

        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'error': error,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'total_duration_ms': total_duration,
            'suites': len(self.test_suites)
        }

    def export_results_to_junit_xml(self, output_file: str = "test_results.xml") -> str:
        """
        Export test results to JUnit XML format

        Args:
            output_file: Output file path

        Returns:
            Path to generated file
        """
        import xml.etree.ElementTree as ET
        from xml.dom import minidom

        # Create XML structure
        testsuites = ET.Element('testsuites')

        stats = self.get_test_statistics()
        testsuites.set('tests', str(stats['total']))
        testsuites.set('failures', str(stats['failed']))
        testsuites.set('errors', str(stats['error']))
        testsuites.set('time', str(stats['total_duration_ms'] / 1000.0))

        for suite in self.test_suites.values():
            testsuite_elem = ET.SubElement(testsuites, 'testsuite')
            testsuite_elem.set('name', suite.name)
            testsuite_elem.set('tests', str(suite.total_tests()))
            testsuite_elem.set('failures', str(suite.failed_tests()))
            testsuite_elem.set('time', str(suite.total_duration_ms() / 1000.0))

            for test in suite.test_cases:
                testcase_elem = ET.SubElement(testsuite_elem, 'testcase')
                testcase_elem.set('name', test.name)
                testcase_elem.set('classname', suite.name)
                testcase_elem.set('time', str(test.duration_ms / 1000.0))

                if test.status == TestStatus.FAILED:
                    failure_elem = ET.SubElement(testcase_elem, 'failure')
                    failure_elem.set('message', test.error_message)
                    failure_elem.text = test.output
                elif test.status == TestStatus.ERROR:
                    error_elem = ET.SubElement(testcase_elem, 'error')
                    error_elem.set('message', test.error_message)
                    error_elem.text = test.output
                elif test.status == TestStatus.SKIPPED:
                    ET.SubElement(testcase_elem, 'skipped')

        # Pretty print XML
        xml_str = minidom.parseString(ET.tostring(testsuites)).toprettyxml(indent="  ")

        output_path = self.project_path / output_file
        output_path.write_text(xml_str)

        return str(output_path)
