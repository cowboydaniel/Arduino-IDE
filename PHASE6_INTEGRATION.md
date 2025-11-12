# Phase 6: Professional Tools - Integration Guide

This document provides comprehensive integration instructions for all Phase 6 professional development tools in Arduino IDE Modern.

## Table of Contents

1. [Overview](#overview)
2. [Unit Testing Framework](#unit-testing-framework)
3. [CI/CD Integration](#cicd-integration)
4. [Performance Profiler](#performance-profiler)
5. [Power Consumption Analyzer](#power-consumption-analyzer)
6. [Hardware-in-Loop Testing](#hardware-in-loop-testing)
7. [Integration with Main Window](#integration-with-main-window)
8. [Best Practices](#best-practices)

---

## Overview

Phase 6 introduces professional-grade development tools that enable enterprise-level Arduino development workflows:

- **Unit Testing Framework**: Comprehensive testing with GoogleTest, Unity, and AUnit support
- **CI/CD Integration**: Automated builds and deployments with GitHub Actions, GitLab CI, Jenkins
- **Performance Profiler**: Execution time analysis and bottleneck identification
- **Power Consumption Analyzer**: Battery life estimation and power optimization
- **Hardware-in-Loop Testing**: Automated hardware testing and validation

All services follow a consistent architecture with Qt signals/slots for event-driven communication.

---

## Unit Testing Framework

### Features

- **Multiple Framework Support**: GoogleTest, Unity, AUnit
- **Test Discovery**: Automatic test detection in project
- **Host and Device Testing**: Run tests on PC or Arduino hardware
- **Code Coverage**: Line, function, and branch coverage reporting
- **Mock Functions**: Hardware function mocking for isolated testing
- **JUnit XML Export**: Integration with CI/CD pipelines

### Service Integration

```python
from arduino_ide.services.unit_testing_service import (
    UnitTestingService, TestFramework, TestConfiguration
)

# Create service
testing_service = UnitTestingService(
    project_path="/path/to/project",
    arduino_cli_path="arduino-cli"
)

# Configure testing
config = TestConfiguration(
    framework=TestFramework.GOOGLETEST,
    test_directory="test",
    run_on_device=False,
    enable_coverage=True
)
testing_service.set_configuration(config)

# Connect signals
testing_service.test_discovered.connect(on_test_discovered)
testing_service.test_finished.connect(on_test_finished)
testing_service.all_tests_finished.connect(on_all_tests_finished)

# Discover and run tests
testing_service.discover_tests()
testing_service.run_all_tests()
```

### UI Integration

```python
from arduino_ide.ui.unit_testing_panel import UnitTestingPanel

# Create panel
testing_panel = UnitTestingPanel(testing_service)

# Add to main window
self.addDockWidget(Qt.BottomDockWidgetArea, testing_panel)
```

### Project Structure

```
project/
├── src/
│   ├── main.cpp
│   └── utilities.cpp
├── test/
│   ├── test_main.cpp
│   ├── test_utilities.cpp
│   └── mocks.h
└── CMakeLists.txt  # For host-based testing
```

### Example Test (GoogleTest)

```cpp
// test/test_utilities.cpp
#include <gtest/gtest.h>
#include "../src/utilities.h"

TEST(UtilitiesTest, CalculateSum) {
    EXPECT_EQ(5, calculate_sum(2, 3));
    EXPECT_EQ(0, calculate_sum(-5, 5));
}

TEST(UtilitiesTest, ValidateInput) {
    EXPECT_TRUE(validate_input(100));
    EXPECT_FALSE(validate_input(-1));
}
```

### Example Test (Unity)

```c
// test/test_utilities.c
#include "unity.h"
#include "../src/utilities.h"

void test_calculate_sum(void) {
    TEST_ASSERT_EQUAL(5, calculate_sum(2, 3));
    TEST_ASSERT_EQUAL(0, calculate_sum(-5, 5));
}

void test_validate_input(void) {
    TEST_ASSERT_TRUE(validate_input(100));
    TEST_ASSERT_FALSE(validate_input(-1));
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_calculate_sum);
    RUN_TEST(test_validate_input);
    return UNITY_END();
}
```

### Mock Functions

```python
# Create mock for digitalRead
mock = testing_service.create_mock(
    function_name="digitalRead",
    return_type="int",
    parameters=[("int", "pin")],
    return_value=HIGH
)

# Set return value for specific test
testing_service.set_mock_return_value("digitalRead", LOW)

# Generate mock header
testing_service.generate_mock_header("test/mocks.h")
```

### Coverage Reporting

```python
# Enable coverage in configuration
config.enable_coverage = True

# After tests run, get coverage data
coverage = testing_service.coverage

print(f"Line Coverage: {coverage.line_coverage_percent():.1f}%")
print(f"Function Coverage: {coverage.function_coverage_percent():.1f}%")
print(f"Branch Coverage: {coverage.branch_coverage_percent():.1f}%")
```

---

## CI/CD Integration

### Features

- **Multi-Platform Support**: GitHub Actions, GitLab CI, Jenkins, Travis CI, CircleCI, Azure Pipelines
- **Configuration Generation**: Automatic pipeline config file generation
- **Build Monitoring**: Real-time pipeline status tracking
- **Artifact Management**: Build artifact collection and storage
- **Deployment Workflows**: Automated deployment to staging/production

### Service Integration

```python
from arduino_ide.services.cicd_service import (
    CICDService, CICDPlatform, PipelineConfiguration
)

# Create service
cicd_service = CICDService(project_path="/path/to/project")

# Set credentials
cicd_service.set_github_token("ghp_xxxxxxxxxxxxx")
cicd_service.set_gitlab_token("glpat-xxxxxxxxxxxxx")

# Configure pipeline
config = PipelineConfiguration(
    platform=CICDPlatform.GITHUB_ACTIONS,
    name="Arduino CI/CD",
    triggers=["push", "pull_request"],
    branches=["main", "develop"],
    boards=["arduino:avr:uno", "arduino:avr:mega"],
    enable_testing=True,
    enable_linting=True,
    enable_deployment=False
)
cicd_service.set_configuration(config)

# Generate configuration file
config_file = cicd_service.generate_pipeline_config()
print(f"Generated: {config_file}")

# Monitor pipelines
cicd_service.start_monitoring(interval_seconds=30)
cicd_service.pipeline_finished.connect(on_pipeline_finished)
```

### UI Integration

```python
from arduino_ide.ui.cicd_panel import CICDPanel

# Create panel
cicd_panel = CICDPanel(cicd_service)

# Add to main window
self.addDockWidget(Qt.RightDockWidgetArea, cicd_panel)
```

### Generated GitHub Actions Workflow

```yaml
# .github/workflows/arduino-ci.yml
name: Arduino CI/CD
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Arduino CLI
        uses: arduino/setup-arduino-cli@v1
        with:
          version: latest

      - name: Update board index
        run: arduino-cli core update-index

      - name: Install arduino:avr:uno
        run: arduino-cli core install arduino:avr

      - name: Compile for arduino:avr:uno
        run: arduino-cli compile --fqbn arduino:avr:uno .

      - name: Run tests
        run: make test || echo "No tests configured"

      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: firmware
          path: build/**/*.hex
          retention-days: 7
```

### Fetching Pipeline Status

```python
# Fetch recent pipelines
pipelines = cicd_service.fetch_pipelines(limit=10)

for pipeline in pipelines:
    print(f"Pipeline: {pipeline.name}")
    print(f"Branch: {pipeline.branch}")
    print(f"Status: {pipeline.status.value}")
    print(f"Duration: {pipeline.total_duration_seconds()}s")
    print(f"Success Rate: {pipeline.success_rate()}%")
```

---

## Performance Profiler

### Features

- **Multiple Profiling Modes**: Host-based, on-device, simulation
- **Function Profiling**: Execution time per function
- **Call Statistics**: Call count and average time
- **Bottleneck Detection**: Automatic identification of performance issues
- **Memory Profiling**: Memory allocation tracking
- **Optimization Suggestions**: AI-powered optimization recommendations

### Service Integration

```python
from arduino_ide.services.performance_profiler_service import (
    PerformanceProfilerService, ProfileMode
)

# Create service
profiler_service = PerformanceProfilerService(
    project_path="/path/to/project"
)

# Configure
profiler_service.target_board = "arduino:avr:uno"
profiler_service.serial_port = "/dev/ttyUSB0"
profiler_service.enable_memory_profiling = True

# Connect signals
profiler_service.profiling_finished.connect(on_profiling_finished)
profiler_service.bottleneck_detected.connect(on_bottleneck_detected)

# Start profiling
session_id = profiler_service.start_profiling(ProfileMode.HOST_BASED)

# ... run your code ...

# Stop profiling
session = profiler_service.stop_profiling()

# Get hot functions
hot_funcs = profiler_service.get_hot_functions(session_id, limit=10)
for func in hot_funcs:
    print(f"{func.name}: {func.total_time_us:.0f}μs ({func.call_count} calls)")
```

### Profiling Firmware

For on-device profiling, the service generates instrumented firmware:

```cpp
// Auto-generated profiling code
void myFunction() {
    PROFILE_START(myFunction);

    // Your code here
    digitalWrite(LED_PIN, HIGH);
    delay(100);

    PROFILE_END(myFunction);
}

void loop() {
    myFunction();

    // Print profiling results every 10 seconds
    static unsigned long lastPrint = 0;
    if (millis() - lastPrint > 10000) {
        printProfilingResults();
        lastPrint = millis();
    }
}
```

### Analyzing Results

```python
# Get bottlenecks
session = profiler_service.get_session(session_id)

for bottleneck in session.bottlenecks:
    print(f"Bottleneck: {bottleneck.function_name}")
    print(f"Severity: {bottleneck.severity}")
    print(f"Issue: {bottleneck.description}")
    print(f"Suggestion: {bottleneck.suggestion}")

# Get optimization suggestions
suggestions = profiler_service.get_optimization_suggestions(session_id)
for suggestion in suggestions:
    print(f"- {suggestion}")

# Export report
report_file = profiler_service.export_profiling_report(
    session_id,
    "profile_report.json"
)
```

---

## Power Consumption Analyzer

### Features

- **Current Measurement**: Real-time current monitoring via INA219/INA260
- **Power Profiling**: Voltage, current, and power tracking
- **Sleep Mode Analysis**: Power consumption in different sleep modes
- **Battery Life Estimation**: Estimate runtime with different batteries
- **Optimization Suggestions**: Power-saving recommendations

### Service Integration

```python
from arduino_ide.services.power_analyzer_service import (
    PowerAnalyzerService, PowerMode
)

# Create service
power_service = PowerAnalyzerService(project_path="/path/to/project")

# Configure current sensor
power_service.sensor_port = "/dev/ttyUSB0"
power_service.sensor_type = "INA219"
power_service.sampling_rate_hz = 100

# Start monitoring
session_id = power_service.start_monitoring()

# ... run your code ...

# Stop monitoring
session = power_service.stop_monitoring()

# Get power statistics
stats = power_service.get_power_statistics(session_id)
print(f"Average Current: {stats['avg_current_ma']:.2f} mA")
print(f"Peak Current: {stats['peak_current_ma']:.2f} mA")
print(f"Average Power: {stats['avg_power_mw']:.2f} mW")
print(f"Energy Consumed: {stats['energy_mwh']:.4f} mWh")

# Estimate battery life
battery_life = power_service.estimate_battery_life(
    session_id,
    battery_capacity_mah=2000
)
print(f"Estimated Battery Life: {battery_life:.1f} hours")
```

### Power Optimization

```python
# Analyze power modes
modes = power_service.analyze_power_modes(session_id)

for mode, data in modes.items():
    print(f"{mode}: {data['avg_current_ma']:.2f} mA")

# Get optimization suggestions
suggestions = power_service.get_optimization_suggestions(session_id)
for suggestion in suggestions:
    print(f"- {suggestion}")

# Example suggestions:
# - Use sleep mode during idle periods (can save 90% power)
# - Reduce LED brightness or disable when not needed
# - Use external interrupts instead of polling
# - Optimize sensor reading frequency
# - Consider using power-efficient components
```

---

## Hardware-in-Loop Testing

### Features

- **Automated Testing**: Programmatic control of hardware tests
- **Test Fixture Management**: Multiple fixture configurations
- **Signal Generation**: Generate test signals (PWM, analog, digital)
- **Signal Capture**: Capture and validate hardware responses
- **Automated Flashing**: Automatic firmware upload for tests
- **Result Validation**: Expected vs actual comparison

### Service Integration

```python
from arduino_ide.services.hil_testing_service import (
    HILTestingService, TestFixture, SignalType
)

# Create service
hil_service = HILTestingService(project_path="/path/to/project")

# Define test fixture
fixture = TestFixture(
    name="LED_Test_Fixture",
    board="arduino:avr:uno",
    port="/dev/ttyUSB0"
)

# Add test signals
fixture.add_input_signal("button", 2, SignalType.DIGITAL)
fixture.add_output_signal("led", 13, SignalType.DIGITAL)

hil_service.add_fixture(fixture)

# Create test
test = hil_service.create_test(
    name="test_led_button",
    fixture_name="LED_Test_Fixture",
    description="Test LED toggles when button pressed"
)

# Add test steps
test.add_step("Set button HIGH", {"button": 1})
test.add_step("Wait 100ms", {"delay": 100})
test.add_step("Check LED is HIGH", {"led": 1}, expected=True)
test.add_step("Set button LOW", {"button": 0})
test.add_step("Wait 100ms", {"delay": 100})
test.add_step("Check LED is LOW", {"led": 0}, expected=True)

# Run test
result = hil_service.run_test("test_led_button")

if result.passed:
    print("Test PASSED")
else:
    print(f"Test FAILED: {result.failure_message}")
```

### Test Automation

```python
# Run all tests in fixture
results = hil_service.run_all_tests("LED_Test_Fixture")

passed = sum(1 for r in results if r.passed)
failed = sum(1 for r in results if not r.passed)

print(f"Results: {passed} passed, {failed} failed")

# Generate test report
report = hil_service.generate_test_report(
    fixture_name="LED_Test_Fixture",
    output_format="html"
)
```

---

## Integration with Main Window

### Complete Integration Example

```python
# main_window.py

from PySide6.QtWidgets import QMainWindow, QDockWidget
from PySide6.QtCore import Qt

from arduino_ide.services.unit_testing_service import UnitTestingService
from arduino_ide.services.cicd_service import CICDService
from arduino_ide.services.performance_profiler_service import PerformanceProfilerService
from arduino_ide.services.power_analyzer_service import PowerAnalyzerService
from arduino_ide.services.hil_testing_service import HILTestingService

from arduino_ide.ui.unit_testing_panel import UnitTestingPanel
from arduino_ide.ui.cicd_panel import CICDPanel
from arduino_ide.ui.performance_profiler_panel import PerformanceProfilerPanel
from arduino_ide.ui.power_analyzer_panel import PowerAnalyzerPanel
from arduino_ide.ui.hil_testing_panel import HILTestingPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.project_path = ""

        # Initialize services
        self._init_services()

        # Initialize UI
        self._init_ui()

        # Create menu
        self._create_menus()

    def _init_services(self):
        """Initialize all Phase 6 services"""
        self.testing_service = UnitTestingService()
        self.cicd_service = CICDService()
        self.profiler_service = PerformanceProfilerService()
        self.power_service = PowerAnalyzerService()
        self.hil_service = HILTestingService()

    def _init_ui(self):
        """Initialize UI panels"""
        # Unit Testing Panel
        self.testing_panel = UnitTestingPanel(self.testing_service)
        self.testing_dock = QDockWidget("Unit Tests", self)
        self.testing_dock.setWidget(self.testing_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.testing_dock)
        self.testing_dock.setVisible(False)

        # CI/CD Panel
        self.cicd_panel = CICDPanel(self.cicd_service)
        self.cicd_dock = QDockWidget("CI/CD", self)
        self.cicd_dock.setWidget(self.cicd_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.cicd_dock)
        self.cicd_dock.setVisible(False)

        # Performance Profiler Panel
        self.profiler_panel = PerformanceProfilerPanel(self.profiler_service)
        self.profiler_dock = QDockWidget("Performance Profiler", self)
        self.profiler_dock.setWidget(self.profiler_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.profiler_dock)
        self.profiler_dock.setVisible(False)

        # Power Analyzer Panel
        self.power_panel = PowerAnalyzerPanel(self.power_service)
        self.power_dock = QDockWidget("Power Analyzer", self)
        self.power_dock.setWidget(self.power_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.power_dock)
        self.power_dock.setVisible(False)

        # HIL Testing Panel
        self.hil_panel = HILTestingPanel(self.hil_service)
        self.hil_dock = QDockWidget("Hardware-in-Loop Testing", self)
        self.hil_dock.setWidget(self.hil_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.hil_dock)
        self.hil_dock.setVisible(False)

    def _create_menus(self):
        """Create menus for Phase 6 tools"""
        tools_menu = self.menuBar().addMenu("&Professional Tools")

        # Unit Testing
        testing_action = tools_menu.addAction("&Unit Testing")
        testing_action.triggered.connect(
            lambda: self.testing_dock.setVisible(not self.testing_dock.isVisible())
        )

        # CI/CD
        cicd_action = tools_menu.addAction("&CI/CD Integration")
        cicd_action.triggered.connect(
            lambda: self.cicd_dock.setVisible(not self.cicd_dock.isVisible())
        )

        # Performance Profiler
        profiler_action = tools_menu.addAction("&Performance Profiler")
        profiler_action.triggered.connect(
            lambda: self.profiler_dock.setVisible(not self.profiler_dock.isVisible())
        )

        # Power Analyzer
        power_action = tools_menu.addAction("Po&wer Analyzer")
        power_action.triggered.connect(
            lambda: self.power_dock.setVisible(not self.power_dock.isVisible())
        )

        # HIL Testing
        hil_action = tools_menu.addAction("&Hardware-in-Loop Testing")
        hil_action.triggered.connect(
            lambda: self.hil_dock.setVisible(not self.hil_dock.isVisible())
        )

    def set_project_path(self, path: str):
        """Set project path for all services"""
        self.project_path = path

        self.testing_service.set_project_path(path)
        self.cicd_service.set_project_path(path)
        self.profiler_service.set_project_path(path)
        self.power_service.set_project_path(path)
        self.hil_service.set_project_path(path)
```

---

## Best Practices

### Unit Testing

1. **Write tests first**: Follow TDD (Test-Driven Development)
2. **Mock hardware functions**: Use mocks for pinMode, digitalRead, etc.
3. **Test on host when possible**: Faster feedback loop
4. **Aim for 80%+ coverage**: Good indicator of test quality
5. **Run tests in CI/CD**: Catch regressions early

### CI/CD

1. **Test on multiple boards**: Ensure compatibility
2. **Enable code linting**: Maintain code quality
3. **Cache dependencies**: Speed up builds
4. **Use matrix builds**: Test multiple configurations
5. **Monitor build status**: Set up notifications

### Performance Profiling

1. **Profile regularly**: Catch performance regressions
2. **Focus on hot spots**: Optimize high-impact functions
3. **Measure before/after**: Validate optimizations
4. **Consider trade-offs**: Speed vs memory vs power
5. **Profile on target**: Host profiling may differ

### Power Optimization

1. **Use sleep modes**: Idle time = sleep time
2. **Minimize active time**: Do work quickly, sleep often
3. **Reduce clock speed**: If performance allows
4. **Disable unused peripherals**: Turn off what you don't need
5. **Measure real consumption**: Don't rely on estimates

### HIL Testing

1. **Automate everything**: Manual testing doesn't scale
2. **Design for testability**: Add test points, headers
3. **Use good fixtures**: Reliable hardware is critical
4. **Test edge cases**: Not just happy path
5. **Maintain test equipment**: Calibrate, verify regularly

---

## Performance Considerations

### Testing Overhead

- Host-based tests: Minimal overhead (< 1s per test)
- Device tests: Upload time + execution (5-30s per test)
- Coverage collection: Adds 10-20% overhead
- Mock functions: < 1% overhead

### Profiling Overhead

- Host profiling: 5-10% slowdown
- Device profiling: 10-30% slowdown (instrumentation)
- Memory profiling: Minimal overhead
- Continuous profiling: Not recommended for production

### CI/CD Performance

- GitHub Actions: Free for public repos, 2000 min/month private
- GitLab CI: 400 min/month free tier
- Caching: Can reduce build time by 50-80%
- Matrix builds: Parallel execution speeds up multi-board testing

---

## Troubleshooting

### Unit Testing

**Issue**: Tests not discovered
- Check test file naming matches patterns (test_*.cpp)
- Verify test directory exists
- Ensure test framework is properly installed

**Issue**: Coverage not generated
- Install gcov/lcov: `sudo apt-get install lcov`
- Compile with coverage flags (-g --coverage)
- Run tests before generating coverage

### CI/CD

**Issue**: Pipeline fails with permission error
- Check GitHub/GitLab token has correct permissions
- Verify repository access
- Check branch protection rules

**Issue**: Build succeeds locally but fails in CI
- Check Arduino CLI version matches
- Verify all dependencies are installed in CI
- Check for platform-specific issues

### Profiling

**Issue**: No profiling data collected
- Verify gprof is installed for host profiling
- Check serial connection for device profiling
- Ensure profiling code is instrumented

**Issue**: Profiling results inconsistent
- Run multiple iterations
- Disable other background tasks
- Use consistent test conditions

---

## Future Enhancements

Potential improvements for Phase 6 tools:

1. **Unit Testing**
   - Parameterized tests
   - Test fixtures and suites
   - Parallel test execution
   - Visual test runner

2. **CI/CD**
   - More platform support (Drone, Buildkite)
   - Deployment to OTA servers
   - Security scanning integration
   - Performance regression detection

3. **Profiler**
   - Flame graphs
   - Call graph visualization
   - Comparative profiling
   - Real-time profiling

4. **Power Analyzer**
   - Multiple sensor support
   - Power state machine analysis
   - A/B testing for optimizations
   - Power budget tracking

5. **HIL Testing**
   - Distributed test execution
   - Test case generation
   - Hardware fault injection
   - Video capture integration

---

## Additional Resources

- **GoogleTest Documentation**: https://google.github.io/googletest/
- **Unity Testing Framework**: http://www.throwtheswitch.org/unity
- **AUnit**: https://github.com/bxparks/AUnit
- **GitHub Actions**: https://docs.github.com/en/actions
- **GitLab CI**: https://docs.gitlab.com/ee/ci/
- **gprof Manual**: https://sourceware.org/binutils/docs/gprof/
- **INA219 Sensor**: https://www.ti.com/product/INA219

---

## Support

For questions or issues with Phase 6 integration:

1. Check this documentation first
2. Review example code in `examples/` directory
3. Search existing GitHub issues
4. Open a new issue with detailed description

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Phase Status**: ✅ Completed
