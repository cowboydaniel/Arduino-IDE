"""UI components for Arduino IDE Modern"""

from .main_window import MainWindow
from .code_editor import CodeEditor
from .console_panel import ConsolePanel
from .serial_monitor import SerialMonitor
from .board_panel import BoardPanel
from .project_explorer import ProjectExplorer
from .variable_watch import VariableWatch
from .status_display import StatusDisplay
from .plotter_panel import PlotterPanel
from .problems_panel import ProblemsPanel
from .output_panel import OutputPanel
from .status_bar import StatusBar
from .library_manager_dialog import LibraryManagerDialog
from .board_manager_dialog import BoardManagerDialog

__all__ = [
    'MainWindow',
    'CodeEditor',
    'ConsolePanel',
    'SerialMonitor',
    'BoardPanel',
    'ProjectExplorer',
    'VariableWatch',
    'StatusDisplay',
    'PlotterPanel',
    'ProblemsPanel',
    'OutputPanel',
    'StatusBar',
    'LibraryManagerDialog',
    'BoardManagerDialog',
]
