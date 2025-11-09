"""Unit tests for the RAM estimation logic."""

import importlib.util
import pathlib
import sys
import textwrap
import types

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Provide lightweight PySide6 stubs so the UI module can be imported without
# the real Qt libraries (which are unavailable in the test environment).
class _QtStub:
    def __init__(self, *args, **kwargs):
        pass


qt_widgets = types.ModuleType("PySide6.QtWidgets")
qt_widgets.QWidget = _QtStub
qt_widgets.QVBoxLayout = _QtStub
qt_widgets.QHBoxLayout = _QtStub
qt_widgets.QLabel = _QtStub
qt_widgets.QProgressBar = _QtStub
qt_widgets.QGroupBox = _QtStub
qt_widgets.QFrame = _QtStub

qt_core = types.ModuleType("PySide6.QtCore")
qt_core.Qt = types.SimpleNamespace(AlignCenter=0)
qt_core.QTimer = _QtStub

qt_gui = types.ModuleType("PySide6.QtGui")
qt_gui.QFont = _QtStub

pyside6 = types.ModuleType("PySide6")
pyside6.QtWidgets = qt_widgets
pyside6.QtCore = qt_core
pyside6.QtGui = qt_gui

sys.modules.setdefault("PySide6", pyside6)
sys.modules["PySide6.QtWidgets"] = qt_widgets
sys.modules["PySide6.QtCore"] = qt_core
sys.modules["PySide6.QtGui"] = qt_gui

status_display_path = PROJECT_ROOT / "arduino_ide" / "ui" / "status_display.py"
spec = importlib.util.spec_from_file_location(
    "arduino_ide.ui.status_display", status_display_path
)
status_display = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(status_display)

CodeAnalyzer = status_display.CodeAnalyzer


def normalize(code: str) -> str:
    """Utility helper to normalize test sketches."""

    return textwrap.dedent(code).strip() + "\n"


def test_avr_estimation_uses_16_bit_ints():
    sketch = normalize(
        """
        int counter = 42;
        float analogValue = 0.5;
        int *ptr;

        void setup() {}
        void loop() {}
        """
    )

    estimated = CodeAnalyzer.estimate_ram_usage(sketch, "Arduino Uno")

    # 9 base + 2 (int) + 4 (float) + 2 (pointer)
    assert estimated == 17


def test_arm_estimation_promotes_int_and_double_sizes():
    sketch = normalize(
        """
        int samples = 10;
        double weight = 1.0;
        int *buffer;

        void setup() {}
        void loop() {}
        """
    )

    estimated = CodeAnalyzer.estimate_ram_usage(sketch, "Arduino Uno R4 WiFi")

    # 100 base + 4 (int) + 8 (double) + 4 (pointer)
    assert estimated == 116


def test_esp32_includes_wifi_buffers_and_32_bit_types():
    sketch = normalize(
        """
        String message;
        double reading = 3.14;
        int *heapPtr;

        void setup() {
            WiFi.begin();
        }

        void loop() {}
        """
    )

    estimated = CodeAnalyzer.estimate_ram_usage(sketch, "ESP32 Dev Module")

    # 25600 base + 6 (String) + 8 (double) + 4 (pointer) + 1024 (WiFi)
    assert estimated == 26642
