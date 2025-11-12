"""
Performance Profiler Service for Arduino IDE Modern

This service provides comprehensive performance profiling capabilities for Arduino code.

Features:
- Execution time profiling
- Function call statistics
- Memory usage tracking over time
- CPU cycle counting
- Bottleneck identification
- Performance optimization suggestions
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import re
import subprocess
import time

from PySide6.QtCore import QObject, Signal, QProcess


class ProfileMode(Enum):
    """Profiling mode"""
    HOST_BASED = "host"  # Profile on host machine
    ON_DEVICE = "device"  # Profile on Arduino device
    SIMULATION = "simulation"  # Use simulator


@dataclass
class FunctionProfile:
    """Profile data for a single function"""
    name: str
    file_path: str
    line_number: int
    call_count: int = 0
    total_time_us: float = 0.0  # microseconds
    min_time_us: float = float('inf')
    max_time_us: float = 0.0
    avg_time_us: float = 0.0
    self_time_us: float = 0.0  # Time excluding child calls
    cpu_cycles: int = 0
    memory_allocated: int = 0  # bytes

    def update_stats(self):
        """Update calculated statistics"""
        if self.call_count > 0:
            self.avg_time_us = self.total_time_us / self.call_count

    def percentage_of_total(self, total_time: float) -> float:
        """Calculate percentage of total execution time"""
        if total_time == 0:
            return 0.0
        return (self.total_time_us / total_time) * 100.0


@dataclass
class CallStackEntry:
    """Call stack entry for profiling"""
    function_name: str
    timestamp_us: float
    parent: Optional['CallStackEntry'] = None
    children: List['CallStackEntry'] = field(default_factory=list)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: datetime
    heap_used: int
    heap_free: int
    stack_used: int
    global_variables: int
    fragmentation: float = 0.0


@dataclass
class Bottleneck:
    """Identified performance bottleneck"""
    function_name: str
    severity: str  # high, medium, low
    issue_type: str  # time, memory, calls
    description: str
    suggestion: str
    file_path: str
    line_number: int


@dataclass
class ProfilingSession:
    """Complete profiling session"""
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    mode: ProfileMode = ProfileMode.HOST_BASED
    function_profiles: Dict[str, FunctionProfile] = field(default_factory=dict)
    memory_snapshots: List[MemorySnapshot] = field(default_factory=list)
    bottlenecks: List[Bottleneck] = field(default_factory=list)
    total_execution_time_us: float = 0.0
    total_cpu_cycles: int = 0

    def duration_seconds(self) -> float:
        """Get session duration"""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return 0.0


class PerformanceProfilerService(QObject):
    """
    Service for performance profiling

    Signals:
        profiling_started: Emitted when profiling starts
        profiling_finished: Emitted when profiling finishes
        function_profiled: Emitted when a function is profiled
        memory_snapshot_taken: Emitted when memory snapshot is captured
        bottleneck_detected: Emitted when bottleneck is detected
    """

    # Signals
    profiling_started = Signal(str)  # session_id
    profiling_finished = Signal(str)  # session_id
    function_profiled = Signal(FunctionProfile)
    memory_snapshot_taken = Signal(MemorySnapshot)
    bottleneck_detected = Signal(Bottleneck)

    def __init__(self, project_path: str = "", arduino_cli_path: str = "arduino-cli"):
        super().__init__()

        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.arduino_cli_path = arduino_cli_path

        # Profiling state
        self.sessions: Dict[str, ProfilingSession] = {}
        self.current_session: Optional[ProfilingSession] = None
        self.profiling_active = False

        # Configuration
        self.profile_mode = ProfileMode.HOST_BASED
        self.target_board = "arduino:avr:uno"
        self.serial_port = ""
        self.enable_memory_profiling = True
        self.enable_cycle_counting = True
        self.sampling_interval_ms = 100

    def set_project_path(self, path: str):
        """Set project path"""
        self.project_path = Path(path)

    def start_profiling(self, mode: ProfileMode = ProfileMode.HOST_BASED) -> str:
        """
        Start a profiling session

        Args:
            mode: Profiling mode

        Returns:
            Session ID
        """
        if self.profiling_active:
            return ""

        session_id = f"profile_{int(time.time())}"
        session = ProfilingSession(
            session_id=session_id,
            started_at=datetime.now(),
            mode=mode
        )

        self.current_session = session
        self.sessions[session_id] = session
        self.profiling_active = True
        self.profile_mode = mode

        if mode == ProfileMode.HOST_BASED:
            self._start_host_profiling()
        elif mode == ProfileMode.ON_DEVICE:
            self._start_device_profiling()
        elif mode == ProfileMode.SIMULATION:
            self._start_simulation_profiling()

        self.profiling_started.emit(session_id)
        return session_id

    def stop_profiling(self) -> Optional[ProfilingSession]:
        """Stop current profiling session"""
        if not self.profiling_active or not self.current_session:
            return None

        self.current_session.ended_at = datetime.now()
        self.profiling_active = False

        # Analyze results
        self._analyze_profiling_results()

        self.profiling_finished.emit(self.current_session.session_id)

        session = self.current_session
        self.current_session = None

        return session

    def _start_host_profiling(self):
        """Start host-based profiling using gprof or similar"""
        # Compile with profiling flags
        build_dir = self.project_path / "build" / "profile"
        build_dir.mkdir(parents=True, exist_ok=True)

        # Generate instrumented code
        self._instrument_code_for_profiling()

        # Compile with profiling
        try:
            subprocess.run(
                ["g++", "-pg", "-O0", "-g",
                 "-o", str(build_dir / "profile_exe"),
                 *list((self.project_path / "src").glob("*.cpp"))],
                cwd=str(self.project_path),
                capture_output=True,
                timeout=60
            )

            # Run with profiling
            subprocess.run(
                [str(build_dir / "profile_exe")],
                cwd=str(build_dir),
                capture_output=True,
                timeout=30
            )

            # Generate profile data
            result = subprocess.run(
                ["gprof", str(build_dir / "profile_exe"), "gmon.out"],
                cwd=str(build_dir),
                capture_output=True,
                text=True,
                timeout=30
            )

            self._parse_gprof_output(result.stdout)

        except Exception as e:
            print(f"Host profiling error: {e}")

    def _start_device_profiling(self):
        """Start on-device profiling"""
        # Generate profiling firmware
        profile_code = self._generate_profiling_firmware()

        # Write to temporary sketch
        profile_sketch = self.project_path / "build" / "profile" / "profile.ino"
        profile_sketch.parent.mkdir(parents=True, exist_ok=True)
        profile_sketch.write_text(profile_code)

        # Compile and upload
        try:
            subprocess.run(
                [self.arduino_cli_path, "compile",
                 "--fqbn", self.target_board,
                 str(profile_sketch.parent)],
                capture_output=True,
                timeout=60
            )

            subprocess.run(
                [self.arduino_cli_path, "upload",
                 "--fqbn", self.target_board,
                 "--port", self.serial_port,
                 str(profile_sketch.parent)],
                capture_output=True,
                timeout=60
            )

            # Capture profiling data from serial
            self._capture_device_profiling_data()

        except Exception as e:
            print(f"Device profiling error: {e}")

    def _start_simulation_profiling(self):
        """Start simulation-based profiling"""
        # Use simavr or similar for simulation profiling
        pass

    def _instrument_code_for_profiling(self):
        """Instrument source code with profiling hooks"""
        src_dir = self.project_path / "src"
        profile_dir = self.project_path / "build" / "profile" / "src"
        profile_dir.mkdir(parents=True, exist_ok=True)

        for src_file in src_dir.glob("*.cpp"):
            content = src_file.read_text()

            # Add profiling includes
            instrumented = "#include <sys/time.h>\n"
            instrumented += "#include <unordered_map>\n"
            instrumented += "#include <string>\n\n"

            # Add profiling helpers
            instrumented += """
struct ProfileData {
    unsigned long calls = 0;
    unsigned long long total_us = 0;
    unsigned long long min_us = ULLONG_MAX;
    unsigned long long max_us = 0;
};

std::unordered_map<std::string, ProfileData> profile_data;

class ScopedProfiler {
    std::string func_name;
    unsigned long long start_us;
public:
    ScopedProfiler(const char* name) : func_name(name) {
        struct timeval tv;
        gettimeofday(&tv, nullptr);
        start_us = tv.tv_sec * 1000000ULL + tv.tv_usec;
    }

    ~ScopedProfiler() {
        struct timeval tv;
        gettimeofday(&tv, nullptr);
        unsigned long long end_us = tv.tv_sec * 1000000ULL + tv.tv_usec;
        unsigned long long elapsed = end_us - start_us;

        ProfileData& data = profile_data[func_name];
        data.calls++;
        data.total_us += elapsed;
        data.min_us = std::min(data.min_us, elapsed);
        data.max_us = std::max(data.max_us, elapsed);
    }
};

#define PROFILE_FUNCTION() ScopedProfiler __profiler__(__FUNCTION__)
"""

            # Instrument functions
            instrumented += content

            # Write instrumented file
            (profile_dir / src_file.name).write_text(instrumented)

    def _generate_profiling_firmware(self) -> str:
        """Generate Arduino firmware with profiling"""
        code = """
#include <Arduino.h>

// Profiling data structures
struct FunctionProfile {
    const char* name;
    unsigned long calls;
    unsigned long total_micros;
    unsigned long min_micros;
    unsigned long max_micros;
};

#define MAX_FUNCTIONS 50
FunctionProfile profiles[MAX_FUNCTIONS];
int profile_count = 0;

// Profiling macros
#define PROFILE_START(name) \\
    int __profile_idx_##name = -1; \\
    for(int i = 0; i < profile_count; i++) { \\
        if(strcmp(profiles[i].name, #name) == 0) { \\
            __profile_idx_##name = i; \\
            break; \\
        } \\
    } \\
    if(__profile_idx_##name == -1 && profile_count < MAX_FUNCTIONS) { \\
        __profile_idx_##name = profile_count++; \\
        profiles[__profile_idx_##name].name = #name; \\
        profiles[__profile_idx_##name].calls = 0; \\
        profiles[__profile_idx_##name].total_micros = 0; \\
        profiles[__profile_idx_##name].min_micros = ULONG_MAX; \\
        profiles[__profile_idx_##name].max_micros = 0; \\
    } \\
    unsigned long __start_##name = micros(); \\
    profiles[__profile_idx_##name].calls++;

#define PROFILE_END(name) \\
    unsigned long __elapsed_##name = micros() - __start_##name; \\
    profiles[__profile_idx_##name].total_micros += __elapsed_##name; \\
    if(__elapsed_##name < profiles[__profile_idx_##name].min_micros) \\
        profiles[__profile_idx_##name].min_micros = __elapsed_##name; \\
    if(__elapsed_##name > profiles[__profile_idx_##name].max_micros) \\
        profiles[__profile_idx_##name].max_micros = __elapsed_##name;

// Include your application code here
"""

        # Add user code with profiling
        main_sketch = self.project_path / (self.project_path.name + ".ino")
        if main_sketch.exists():
            user_code = main_sketch.read_text()
            code += user_code

        code += """
void printProfilingResults() {
    Serial.println("=== PROFILING RESULTS ===");
    for(int i = 0; i < profile_count; i++) {
        Serial.print("FUNC:");
        Serial.print(profiles[i].name);
        Serial.print(",CALLS:");
        Serial.print(profiles[i].calls);
        Serial.print(",TOTAL:");
        Serial.print(profiles[i].total_micros);
        Serial.print(",MIN:");
        Serial.print(profiles[i].min_micros);
        Serial.print(",MAX:");
        Serial.print(profiles[i].max_micros);
        Serial.print(",AVG:");
        Serial.println(profiles[i].total_micros / profiles[i].calls);
    }
    Serial.println("=== END PROFILING ===");
}
"""

        return code

    def _capture_device_profiling_data(self):
        """Capture profiling data from serial port"""
        try:
            import serial
            ser = serial.Serial(self.serial_port, 115200, timeout=10)

            time.sleep(2)  # Wait for device reset

            output = ""
            start_time = time.time()

            while time.time() - start_time < 30:
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8', errors='ignore')
                    output += line

                    if "=== END PROFILING ===" in line:
                        break

            ser.close()

            self._parse_device_profiling_output(output)

        except Exception as e:
            print(f"Serial capture error: {e}")

    def _parse_gprof_output(self, output: str):
        """Parse gprof profiling output"""
        if not self.current_session:
            return

        lines = output.split('\n')
        parsing_flat_profile = False

        for line in lines:
            if "Flat profile:" in line:
                parsing_flat_profile = True
                continue

            if parsing_flat_profile and line.strip():
                # Parse flat profile line
                # Format: % time   cumulative   self    calls  self  name
                match = re.search(r'\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+([\d.]+)\s+(.+)', line)
                if match:
                    _, cumulative, self_time, calls, _, name = match.groups()

                    profile = FunctionProfile(
                        name=name.strip(),
                        file_path="",
                        line_number=0,
                        call_count=int(calls),
                        total_time_us=float(self_time) * 1000000,
                        self_time_us=float(self_time) * 1000000
                    )
                    profile.update_stats()

                    self.current_session.function_profiles[name.strip()] = profile
                    self.function_profiled.emit(profile)

    def _parse_device_profiling_output(self, output: str):
        """Parse device profiling output"""
        if not self.current_session:
            return

        lines = output.split('\n')

        for line in lines:
            if line.startswith("FUNC:"):
                # Parse: FUNC:name,CALLS:X,TOTAL:Y,MIN:Z,MAX:W,AVG:A
                parts = line.split(',')
                func_name = parts[0].split(':')[1]

                profile = FunctionProfile(
                    name=func_name,
                    file_path="",
                    line_number=0
                )

                for part in parts[1:]:
                    key, value = part.split(':')
                    if key == "CALLS":
                        profile.call_count = int(value)
                    elif key == "TOTAL":
                        profile.total_time_us = float(value)
                    elif key == "MIN":
                        profile.min_time_us = float(value)
                    elif key == "MAX":
                        profile.max_time_us = float(value)
                    elif key == "AVG":
                        profile.avg_time_us = float(value)

                self.current_session.function_profiles[func_name] = profile
                self.function_profiled.emit(profile)

    def _analyze_profiling_results(self):
        """Analyze profiling results and identify bottlenecks"""
        if not self.current_session:
            return

        # Calculate total time
        total_time = sum(
            fp.total_time_us
            for fp in self.current_session.function_profiles.values()
        )
        self.current_session.total_execution_time_us = total_time

        # Identify bottlenecks
        for func_name, profile in self.current_session.function_profiles.items():
            percentage = profile.percentage_of_total(total_time)

            # High time consumption
            if percentage > 20:
                bottleneck = Bottleneck(
                    function_name=func_name,
                    severity="high",
                    issue_type="time",
                    description=f"Function consumes {percentage:.1f}% of total execution time",
                    suggestion="Consider optimizing this function or reducing call frequency",
                    file_path=profile.file_path,
                    line_number=profile.line_number
                )
                self.current_session.bottlenecks.append(bottleneck)
                self.bottleneck_detected.emit(bottleneck)

            # High call count
            if profile.call_count > 1000:
                bottleneck = Bottleneck(
                    function_name=func_name,
                    severity="medium",
                    issue_type="calls",
                    description=f"Function called {profile.call_count} times",
                    suggestion="Consider caching results or reducing call frequency",
                    file_path=profile.file_path,
                    line_number=profile.line_number
                )
                self.current_session.bottlenecks.append(bottleneck)
                self.bottleneck_detected.emit(bottleneck)

            # High variance
            if profile.max_time_us > profile.avg_time_us * 10:
                bottleneck = Bottleneck(
                    function_name=func_name,
                    severity="low",
                    issue_type="time",
                    description=f"Function has inconsistent execution time (max/avg ratio: {profile.max_time_us/profile.avg_time_us:.1f})",
                    suggestion="Investigate causes of execution time variance",
                    file_path=profile.file_path,
                    line_number=profile.line_number
                )
                self.current_session.bottlenecks.append(bottleneck)
                self.bottleneck_detected.emit(bottleneck)

    def get_session(self, session_id: str) -> Optional[ProfilingSession]:
        """Get a profiling session"""
        return self.sessions.get(session_id)

    def get_hot_functions(self, session_id: str, limit: int = 10) -> List[FunctionProfile]:
        """Get the most time-consuming functions"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        sorted_funcs = sorted(
            session.function_profiles.values(),
            key=lambda f: f.total_time_us,
            reverse=True
        )

        return sorted_funcs[:limit]

    def export_profiling_report(self, session_id: str, output_file: str = "profile_report.json") -> str:
        """Export profiling report to JSON"""
        session = self.sessions.get(session_id)
        if not session:
            return ""

        report = {
            'session_id': session.session_id,
            'started_at': session.started_at.isoformat(),
            'ended_at': session.ended_at.isoformat() if session.ended_at else None,
            'duration_seconds': session.duration_seconds(),
            'mode': session.mode.value,
            'total_execution_time_us': session.total_execution_time_us,
            'functions': []
        }

        for func_name, profile in session.function_profiles.items():
            report['functions'].append({
                'name': profile.name,
                'file': profile.file_path,
                'line': profile.line_number,
                'calls': profile.call_count,
                'total_time_us': profile.total_time_us,
                'avg_time_us': profile.avg_time_us,
                'min_time_us': profile.min_time_us,
                'max_time_us': profile.max_time_us,
                'percentage': profile.percentage_of_total(session.total_execution_time_us)
            })

        report['bottlenecks'] = [
            {
                'function': b.function_name,
                'severity': b.severity,
                'type': b.issue_type,
                'description': b.description,
                'suggestion': b.suggestion
            }
            for b in session.bottlenecks
        ]

        output_path = self.project_path / output_file
        output_path.write_text(json.dumps(report, indent=2))

        return str(output_path)

    def get_optimization_suggestions(self, session_id: str) -> List[str]:
        """Get optimization suggestions based on profiling"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        suggestions = []

        # High call count functions
        high_call_funcs = [
            f for f in session.function_profiles.values()
            if f.call_count > 500
        ]
        if high_call_funcs:
            suggestions.append(
                f"Consider caching or memoization for frequently called functions: "
                f"{', '.join(f.name for f in high_call_funcs[:3])}"
            )

        # Time-consuming functions
        total_time = session.total_execution_time_us
        slow_funcs = [
            f for f in session.function_profiles.values()
            if f.percentage_of_total(total_time) > 15
        ]
        if slow_funcs:
            suggestions.append(
                f"Optimize time-consuming functions: "
                f"{', '.join(f.name for f in slow_funcs[:3])}"
            )

        # Add general suggestions
        suggestions.extend([
            "Use const references for function parameters to avoid copying",
            "Consider using inline for small frequently-called functions",
            "Avoid dynamic memory allocation in tight loops",
            "Use bit operations instead of multiplication/division by powers of 2"
        ])

        return suggestions
