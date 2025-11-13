"""
Main window for Arduino IDE Modern
"""

from functools import partial
from typing import Dict, List, Optional, Set

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QTabWidget,
    QComboBox, QLabel, QSizePolicy, QFileDialog, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QSettings, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QIcon, QTextCursor, QGuiApplication, QCursor
import serial.tools.list_ports
from pathlib import Path

from arduino_ide.ui.code_editor import CodeEditor, BreadcrumbBar, CodeMinimap
from arduino_ide.ui.serial_monitor import SerialMonitor
from arduino_ide.ui.board_panel import BoardPanel
from arduino_ide.ui.pin_usage_panel import PinUsagePanel
from arduino_ide.ui.console_panel import ConsolePanel
from arduino_ide.ui.status_display import StatusDisplay
from arduino_ide.ui.context_panel import ContextPanel
from arduino_ide.ui.plotter_panel import PlotterPanel
from arduino_ide.ui.problems_panel import ProblemsPanel
from arduino_ide.ui.output_panel import OutputPanel
from arduino_ide.ui.status_bar import StatusBar
from arduino_ide.ui.quick_actions_panel import QuickActionsPanel
from arduino_ide.ui.code_quality_panel import CodeQualityPanel
from arduino_ide.ui.library_manager_dialog import LibraryManagerDialog
from arduino_ide.ui.board_manager_dialog import BoardManagerDialog
from arduino_ide.ui.find_replace_dialog import FindReplaceDialog
from arduino_ide.ui.snippets_panel import SnippetsLibraryDialog
from arduino_ide.ui.circuit_editor import CircuitDesignerWindow
from arduino_ide.ui.onboarding_wizard import OnboardingWizard
from arduino_ide.ui.git_panel import GitPanel
from arduino_ide.ui.cicd_dialog import CICDDialog
from arduino_ide.ui.breakpoint_gutter import BreakpointGutter, install_breakpoint_gutter
from arduino_ide.ui.debug_workspace_dialog import DebugWorkspaceDialog
from arduino_ide.services.theme_manager import ThemeManager
from arduino_ide.services.library_manager import LibraryManager
from arduino_ide.services.board_manager import BoardManager
from arduino_ide.services.project_manager import ProjectManager
from arduino_ide.services.circuit_service import CircuitService
from arduino_ide.ui.example_templates import build_missing_example_template
from arduino_ide.services import ArduinoCliService
from arduino_ide.services.visual_programming_service import VisualProgrammingService
from arduino_ide.ui.visual_programming_editor import VisualProgrammingEditor
from arduino_ide.services.error_recovery import SmartErrorRecovery
from arduino_ide.services.unit_testing_service import UnitTestingService
from arduino_ide.services.hil_testing_service import HILTestingService
from arduino_ide.ui.preferences_dialog import PreferencesDialog
from arduino_ide.ui.unit_testing_panel import UnitTestingDialog
from arduino_ide.ui.hil_testing_dialog import HILTestingDialog
from arduino_ide.ui.plugin_manager import PluginManagerWidget
from arduino_ide.ui.performance_profiler_dialog import PerformanceProfilerDialog
from arduino_ide.services.plugin_system import PluginManager, PluginType, PluginStatus
from arduino_ide.services.debug_service import Breakpoint, DebugService, DebugState
from arduino_ide.services.power_analyzer_service import (
    PowerAnalyzerService,
    PowerSessionPhase,
    PowerSessionStage,
)
from arduino_ide.ui.power_analyzer_dialog import PowerAnalyzerDialog
from arduino_ide.services.performance_profiler_service import (
    PerformanceProfilerService,
    ProfileMode,
)
import re


class EditorContainer(QWidget):
    """Container widget that combines breadcrumb, editor, and minimap"""

    dirtyChanged = Signal(bool)

    def __init__(self, filename="untitled.ino", project_name=None, parent=None, file_path=None):
        super().__init__(parent)
        self.suggested_name = filename or "untitled.ino"
        self.file_path = str(Path(file_path).resolve()) if file_path else None
        if self.file_path:
            self.suggested_name = Path(self.file_path).name
        self.filename = self.file_path or self.suggested_name
        self.project_name = project_name or self._derive_project_name(self.filename)
        self.dirty = False
        self.setup_ui()
        self.editor.document().modificationChanged.connect(self._on_modification_changed)
        self.set_dirty(self.editor.document().isModified())

    def _derive_project_name(self, filename):
        """Derive project name from file path"""
        if filename and filename != "untitled.ino":
            # Get parent directory name as project name
            path = Path(filename)
            if path.is_absolute() and path.parent.name:
                return path.parent.name
        # Default to "My Project" for untitled or relative paths
        return "My Project"

    def current_display_name(self):
        """Return the name that should be shown in tab titles"""
        if self.file_path:
            return Path(self.file_path).name
        return self.suggested_name

    def set_file_path(self, path):
        """Update the current file path after saving/opening"""
        self.file_path = str(Path(path).resolve()) if path else None
        if self.file_path:
            self.suggested_name = Path(self.file_path).name
        self.filename = self.file_path or self.suggested_name
        self.project_name = self._derive_project_name(self.filename)
        self.editor.file_path = self.file_path
        self.update_breadcrumb()

    def set_content(self, text, mark_clean=False):
        """Replace the editor contents"""
        self.editor.setPlainText(text)
        if mark_clean:
            self.editor.document().setModified(False)
        self.sync_minimap()
        self.update_breadcrumb()

    def mark_clean(self):
        """Mark the document as saved"""
        self.editor.document().setModified(False)

    def set_dirty(self, dirty):
        """Update dirty flag and emit change signal"""
        if self.dirty == dirty:
            return
        self.dirty = dirty
        self.dirtyChanged.emit(dirty)

    def _on_modification_changed(self, modified):
        """Handle modification changes from the document"""
        self.set_dirty(modified)

    def setup_ui(self):
        """Setup the editor container layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Breadcrumb bar at top
        self.breadcrumb = BreadcrumbBar()
        layout.addWidget(self.breadcrumb)

        # Horizontal layout for editor and minimap
        editor_layout = QHBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        # Code editor
        self.editor = CodeEditor(file_path=self.filename)
        editor_layout.addWidget(self.editor)

        # Minimap on the right
        self.minimap = CodeMinimap()
        editor_layout.addWidget(self.minimap)

        layout.addLayout(editor_layout)

        # Connect signals
        self.editor.textChanged.connect(self.sync_minimap)
        self.editor.cursorPositionChanged.connect(self.update_breadcrumb)
        self.minimap.clicked.connect(self.jump_to_line)

        # Initial sync
        self.sync_minimap()
        self.update_breadcrumb()

    def sync_minimap(self):
        """Sync minimap content with editor"""
        self.minimap.setPlainText(self.editor.toPlainText())

    def update_breadcrumb(self):
        """Update breadcrumb with current location"""
        cursor = self.editor.textCursor()
        line_num = cursor.blockNumber() + 1
        function_name = self.editor.get_current_function()
        current_name = self.file_path or self.suggested_name
        self.breadcrumb.update_breadcrumb(
            current_name,
            function_name,
            line_num,
            self.project_name
        )

    def jump_to_line(self, line_number):
        """Jump to a specific line from minimap click"""
        cursor = QTextCursor(self.editor.document().findBlockByNumber(line_number))
        self.editor.setTextCursor(cursor)
        self.editor.centerCursor()


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings()
        self.theme_manager = ThemeManager()
        self.recent_files = self._load_recent_files()
        self._compile_verbose_enabled = self._load_compile_verbose_preference()
        self.view_menu = None
        self.theme_menu = None
        self.code_quality_panel = None
        self._cli_boards = []
        self.board_panel = None
        self.pin_usage_panel = None
        self.status_display = None
        self.console_panel = None
        self.unit_testing_service = UnitTestingService()
        self.hil_testing_service = HILTestingService(unit_testing_service=self.unit_testing_service)
        self.power_analyzer_service = PowerAnalyzerService(self)
        self.performance_profiler_service = PerformanceProfilerService()
        self.unit_testing_panel = None
        self.unit_testing_dialog = None
        self.hil_testing_dialog: Optional[HILTestingDialog] = None
        self.power_analyzer_dialog: Optional[PowerAnalyzerDialog] = None
        self.performance_profiler_dialog: Optional[PerformanceProfilerDialog] = None
        self._last_completed_profiling_session_id: Optional[str] = None
        self._last_selected_profiler_session_id: Optional[str] = None
        self._unit_testing_project_root: Optional[str] = None
        self._unit_testing_actions_linked = False
        self._hil_sessions_active: Set[str] = set()
        self._hil_tests_running: Set[str] = set()
        self.main_toolbar = None
        self.extensions_toolbar_action = None
        self.extensions_action = None
        self.plugin_manager_dialog = None
        self.git_panel = None
        self.git_dialog = None
        self.cicd_dialog: Optional[CICDDialog] = None
        self._latest_cicd_context: Dict[str, str] = {}
        self._cicd_refresh_timer = QTimer(self)
        self._cicd_refresh_timer.setSingleShot(True)
        self._cicd_refresh_timer.timeout.connect(self._refresh_cicd_context)

        # Debugger integration
        self.debug_service = DebugService(self)
        self.debug_service.state_changed.connect(self._on_debug_state_changed)
        self.debug_service.error_occurred.connect(self._on_debug_error)
        self.debug_service.breakpoint_added.connect(self._on_service_breakpoint_added)
        self.debug_service.breakpoint_removed.connect(self._on_service_breakpoint_removed)
        self.debug_service.breakpoint_updated.connect(self._on_service_breakpoint_updated)
        self.debug_workspace_dialog: Optional[DebugWorkspaceDialog] = None
        self._breakpoint_gutters: Dict[EditorContainer, BreakpointGutter] = {}
        self._gutters_by_path: Dict[str, Set[BreakpointGutter]] = {}
        self._create_debug_actions()

        # Ensure standard window chrome is available so desktop environments
        # show the minimize/maximize controls.  Some window managers (notably
        # GNOME on Wayland) will omit the maximize button unless the window
        # advertises both the system menu and maximize hints together.
        window_flags = (
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowSystemMenuHint
        )
        self.setWindowFlags(window_flags)

        # Guarantee the window advertises a resizable geometry so window
        # managers keep the maximize control visible.
        self.setMinimumSize(640, 480)
        self.resize(1280, 800)

        # Track initial maximize attempts so we can retry until the window is
        # actually maximized when first shown.
        self._initial_maximize_done = False
        self._initial_maximize_attempts = 0
        self._max_initial_maximize_attempts = 5

        # Initialize CLI service first (needed by managers)
        self.cli_service = ArduinoCliService(self)
        self.cli_service.output_received.connect(self._handle_cli_output)
        self.cli_service.error_received.connect(self._handle_cli_error)
        self.cli_service.finished.connect(self._handle_cli_finished)
        self.error_recovery = SmartErrorRecovery()

        # Initialize package managers
        self.library_manager = LibraryManager()
        self.board_manager = BoardManager(cli_runner=self.cli_service)
        self.project_manager = ProjectManager(
            library_manager=self.library_manager,
            board_manager=self.board_manager
        )
        self.project_manager.project_loaded.connect(self._handle_project_loaded)
        self.project_manager.project_saved.connect(self._handle_project_saved)
        self.project_manager.dependencies_changed.connect(self._handle_project_dependencies_changed)

        self.performance_profiler_service.profiling_started.connect(self._on_profiler_session_started)
        self.performance_profiler_service.profiling_finished.connect(self._on_profiler_session_finished)

        # Unit testing global actions (menus, toolbars, shortcuts)
        self.discover_tests_action = QAction("Discover Tests", self)
        self.discover_tests_action.setShortcut(QKeySequence("Ctrl+Shift+D"))
        self.discover_tests_action.setToolTip("Discover unit tests in the active sketch directory")
        self.discover_tests_action.setEnabled(False)
        self.discover_tests_action.triggered.connect(self._discover_unit_tests)

        self.run_all_tests_action = QAction("Run All Tests", self)
        self.run_all_tests_action.setShortcut(QKeySequence("Ctrl+Shift+T"))
        self.run_all_tests_action.setToolTip("Run all discovered unit tests")
        self.run_all_tests_action.setEnabled(False)
        self.run_all_tests_action.triggered.connect(self._run_all_unit_tests)

        self.run_selected_tests_action = QAction("Run Selected Test", self)
        self.run_selected_tests_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        self.run_selected_tests_action.setToolTip("Run the selected test or suite in the Unit Testing panel")
        self.run_selected_tests_action.setEnabled(False)
        self.run_selected_tests_action.triggered.connect(self._run_selected_unit_tests)

        self.stop_tests_action = QAction("Stop Tests", self)
        self.stop_tests_action.setShortcut(QKeySequence("Ctrl+Shift+X"))
        self.stop_tests_action.setToolTip("Stop running unit tests")
        self.stop_tests_action.setEnabled(False)
        self.stop_tests_action.triggered.connect(self._stop_unit_tests)

        self.open_unit_testing_action = QAction("Unit Testing...", self)
        self.open_unit_testing_action.setShortcut(QKeySequence("Ctrl+Shift+U"))
        self.open_unit_testing_action.setToolTip("Open the Unit Testing dialog")
        self.open_unit_testing_action.triggered.connect(self._show_unit_testing_dialog)

        self.open_hil_testing_action = QAction("Hardware-in-the-Loop...", self)
        self.open_hil_testing_action.setShortcut(QKeySequence("Ctrl+Shift+H"))
        self.open_hil_testing_action.setToolTip("Configure fixtures and run HIL test suites")
        self.open_hil_testing_action.triggered.connect(self._show_hil_testing_dialog)

        self.performance_profiler_action = QAction("Performance Profiler...", self)
        self.performance_profiler_action.setStatusTip("Open the Performance Profiler dashboard")
        self.performance_profiler_action.triggered.connect(self.show_performance_profiler_dialog)

        self.start_profiling_action = QAction("Start Profiling", self)
        self.start_profiling_action.setShortcut(QKeySequence("Ctrl+Alt+P"))
        self.start_profiling_action.setStatusTip("Start a performance profiling run for the active sketch")
        self.start_profiling_action.triggered.connect(self.start_performance_profiling)

        self.stop_profiling_action = QAction("Stop Profiling", self)
        self.stop_profiling_action.setShortcut(QKeySequence("Ctrl+Alt+Shift+P"))
        self.stop_profiling_action.setStatusTip("Stop the current performance profiling session")
        self.stop_profiling_action.setEnabled(False)
        self.stop_profiling_action.triggered.connect(self.stop_performance_profiling)

        self.export_profiling_action = QAction("Export Profiling Report...", self)
        self.export_profiling_action.setShortcut(QKeySequence("Ctrl+Alt+E"))
        self.export_profiling_action.setStatusTip("Export profiling metrics to a JSON report")
        self.export_profiling_action.setEnabled(False)
        self.export_profiling_action.triggered.connect(self.export_current_profiling_session)

        for action in (
            self.discover_tests_action,
            self.run_all_tests_action,
            self.run_selected_tests_action,
            self.stop_tests_action,
            self.open_unit_testing_action,
            self.open_hil_testing_action,
        ):
            self.addAction(action)

        self.hil_testing_service.session_started.connect(self._on_hil_session_started)
        self.hil_testing_service.session_stopped.connect(self._on_hil_session_stopped)
        self.hil_testing_service.test_started.connect(self._on_hil_test_started)
        self.hil_testing_service.test_finished.connect(self._on_hil_test_finished)

        # Initialize plugin manager and UI integration
        self.plugin_manager = PluginManager(parent=self)
        self.plugin_manager.api.ide = self
        self.plugin_manager_widget = PluginManagerWidget(self.plugin_manager, parent=self)
        self.plugin_manager.plugin_loaded.connect(self._on_plugin_state_changed)
        self.plugin_manager.plugin_activated.connect(self._on_plugin_state_changed)
        self.plugin_manager.plugin_deactivated.connect(self._on_plugin_state_changed)
        self.plugin_manager.plugin_error.connect(self._on_plugin_error)
        if hasattr(self.project_manager, "project_loaded"):
            self.project_manager.project_loaded.connect(self._on_project_loaded)
            self.project_manager.project_loaded.connect(self._schedule_cicd_refresh)
        if hasattr(self.project_manager, "project_saved"):
            self.project_manager.project_saved.connect(self._on_project_saved)
            self.project_manager.project_saved.connect(self._schedule_cicd_refresh)
        if hasattr(self.project_manager, "dependencies_changed"):
            self.project_manager.dependencies_changed.connect(self._schedule_cicd_refresh)

        self._update_cli_library_paths()

        if hasattr(self.library_manager, "library_installed"):
            self.library_manager.library_installed.connect(self._update_cli_library_paths)
        if hasattr(self.library_manager, "library_uninstalled"):
            self.library_manager.library_uninstalled.connect(self._update_cli_library_paths)

        # Track pending board list refreshes triggered by package changes.
        self._board_list_refresh_reason = ""
        self._board_list_refresh_pending = False
        self._board_list_refresh_timer = QTimer(self)
        self._board_list_refresh_timer.setSingleShot(True)
        self._board_list_refresh_timer.timeout.connect(self._perform_board_list_refresh)

        # Keep the board selector synchronized with board package operations.
        if hasattr(self.board_manager, "package_installed"):
            self.board_manager.package_installed.connect(self._on_board_package_installed)
        if hasattr(self.board_manager, "package_uninstalled"):
            self.board_manager.package_uninstalled.connect(self._on_board_package_uninstalled)
        if hasattr(self.board_manager, "package_updated"):
            self.board_manager.package_updated.connect(self._on_board_package_updated)
        if hasattr(self.board_manager, "index_updated"):
            self.board_manager.index_updated.connect(self._on_board_index_updated)

        # Initialize visual programming service
        self.visual_programming_service = VisualProgrammingService()
        self.visual_programming_window = None  # Will be created when opened
        # Initialize circuit service
        self.circuit_service = CircuitService()
        self.circuit_designer_window = None  # Will be created on demand
        self.onboarding_wizard = None

        self._cli_current_operation = None
        self._last_cli_error = ""
        self._open_monitor_after_upload = False
        self._serial_monitor_open = False
        self._last_selected_port = None
        self._compilation_output = ""  # Store compilation output for parsing
        self._upload_after_compile = False  # Flag to trigger upload after successful compilation
        self._is_background_compile = False  # Flag to distinguish background vs user-initiated compile
        self._pending_board_memory_refresh = False  # Force refresh once CLI becomes idle

        # Current build configuration
        self.build_config = "Release"

        # Background compilation timer for real-time memory updates
        self._background_compile_timer = QTimer(self)
        self._background_compile_timer.setSingleShot(True)
        self._background_compile_timer.timeout.connect(self._do_background_compile)
        self._background_compile_delay = 2000  # 2 seconds after user stops typing

        self.init_ui()
        self.create_menus()
        self.create_toolbars()
        self.create_dock_widgets()

        # Don't restore window geometry, always start maximized
        # Only restore dock widget positions
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

        # Always open maximized regardless of any previous geometry by kicking
        # off the maximize retry loop.
        self._enforce_initial_maximize()

        # Create initial editor (after dock widgets are created)
        self.create_new_editor("sketch.ino")

        # Setup port auto-refresh timer
        self.setup_port_refresh()

        # Initialize status bar with current values
        self.initialize_status_bar()

        self._sync_profiler_context()
        self._update_profiler_actions_state()

        # Apply theme
        self.theme_manager.apply_theme("dark")

    def _update_cli_library_paths(self, *_args):
        """Synchronize the CLI's library search paths with the manager."""

        try:
            paths = self.library_manager.get_library_search_paths()
        except Exception:
            paths = []

        self.cli_service.set_library_search_paths(paths)

    def _on_project_loaded(self, _project_name):
        """Handle project load events from the project manager."""
        self._update_git_repository()

    def _on_project_saved(self, _project_name):
        """Refresh Git information after a project save."""
        self._refresh_git_panel()

    def _update_git_repository(self):
        """Update the Git panel with the current project repository."""
        if not self.git_panel:
            return

        project_path = getattr(self.project_manager, "project_path", None)
        if project_path:
            self.git_panel.set_repository_path(str(Path(project_path)))
            self.git_panel.refresh_all()

    def _refresh_git_panel(self):
        """Refresh Git panel data if available."""
        if self.git_panel:
            self.git_panel.refresh_all()

    def _ensure_git_dialog(self):
        """Ensure the Git dialog and panel are created."""
        if self.git_panel is None:
            self.git_panel = GitPanel()

        if self.git_dialog is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Git")
            layout = QVBoxLayout(dialog)
            layout.addWidget(self.git_panel)
            self.git_dialog = dialog

    def open_git_dialog(self):
        """Display the Git dialog and refresh its contents."""
        self._ensure_git_dialog()
        self._update_git_repository()
        self.git_dialog.show()
        self.git_dialog.raise_()
        self.git_dialog.activateWindow()

    def _collect_cicd_workspace_settings(self) -> Dict[str, str]:
        """Gather project and workspace details for the CI/CD dialog."""

        context: Dict[str, str] = {}

        project_path = getattr(self.project_manager, "project_path", None)
        if project_path:
            context["project_path"] = str(Path(project_path))

        project = getattr(self.project_manager, "current_project", None)
        project_name = getattr(project, "name", "") if project else ""
        if project_name:
            context["project_name"] = str(project_name)

        board = self._get_selected_board() if hasattr(self, "_get_selected_board") else None
        if board:
            board_fqbn = getattr(board, "fqbn", "")
            if board_fqbn:
                context["board_fqbn"] = str(board_fqbn)
            board_name = getattr(board, "name", "")
            if board_name:
                context["board_name"] = str(board_name)

        return context

    def _schedule_cicd_refresh(self, *_args):
        """Update stored CI/CD context and schedule a refresh if needed."""

        self._latest_cicd_context = self._collect_cicd_workspace_settings()

        if not self.cicd_dialog:
            return

        if self._cicd_refresh_timer.isActive():
            self._cicd_refresh_timer.stop()
        self._cicd_refresh_timer.start(250)

    def _refresh_cicd_context(self):
        """Apply stored context changes and refresh the CI/CD dialog."""

        self._apply_cicd_context(refresh=True)

    def _apply_cicd_context(self, refresh: bool = False):
        """Push the latest workspace context into the CI/CD dialog."""

        if not self.cicd_dialog:
            return

        context = dict(self._latest_cicd_context)
        project_path = context.pop("project_path", None)
        workspace_settings = context or None

        self.cicd_dialog.update_context(project_path, workspace_settings)

        if refresh:
            self.cicd_dialog.refresh_now()

    def _ensure_cicd_dialog(self):
        """Ensure the CI/CD dialog exists and is configured."""

        if self.cicd_dialog is None:
            self.cicd_dialog = CICDDialog(self)
            if self._latest_cicd_context:
                self._apply_cicd_context(refresh=False)

    def open_cicd_dialog(self):
        """Open the CI/CD dialog and refresh pipeline information."""

        self._schedule_cicd_refresh()
        self._ensure_cicd_dialog()
        self._apply_cicd_context(refresh=False)

        self.cicd_dialog.show()
        self.cicd_dialog.raise_()
        self.cicd_dialog.activateWindow()
        self.cicd_dialog.refresh_now()

    def init_ui(self):
        """Initialize the main UI"""
        self.setWindowTitle("Arduino IDE Modern")

        # Central widget with editor tabs
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setMovable(True)
        self.editor_tabs.tabCloseRequested.connect(self.close_tab)
        self.editor_tabs.currentChanged.connect(self.on_tab_changed)

        # Main horizontal splitter: [left area (with bottom tabs)] | [right column (full height)]
        central = QSplitter(Qt.Horizontal)
        central.setHandleWidth(4)

        # Left area: vertical layout for top row and bottom tabs
        left_area = QWidget()
        left_area_layout = QVBoxLayout(left_area)
        left_area_layout.setContentsMargins(0, 0, 0, 0)
        left_area_layout.setSpacing(0)

        # Top row: horizontal splitter with left column | editor
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setHandleWidth(4)

        # Left column (Quick Actions)
        self.left_column = QWidget()
        self.left_column_layout = QVBoxLayout(self.left_column)
        self.left_column_layout.setContentsMargins(0, 0, 0, 0)
        self.left_column_layout.setSpacing(0)
        self.left_column.setFixedWidth(260)

        top_splitter.addWidget(self.left_column)
        top_splitter.addWidget(self.editor_tabs)

        # Add top splitter to left area
        left_area_layout.addWidget(top_splitter)

        # Bottom tab widget (only under left area, NOT under right column)
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setMinimumHeight(50)
        self.bottom_tabs.setMaximumHeight(150)
        self.bottom_tabs.currentChanged.connect(self._on_bottom_tab_changed)
        left_area_layout.addWidget(self.bottom_tabs)

        # Add left area to main splitter
        central.addWidget(left_area)

        # Right column 1 (Board/Status) - full height
        self.right_column = QWidget()
        self.right_column_layout = QVBoxLayout(self.right_column)
        self.right_column_layout.setContentsMargins(0, 0, 0, 0)
        self.right_column_layout.setSpacing(0)
        self.right_column.setFixedWidth(300)

        # Add first right column to main splitter
        central.addWidget(self.right_column)

        # Right column 2 (Pin Usage/Context Help) - full height
        self.right_column_2 = QWidget()
        self.right_column_2_layout = QVBoxLayout(self.right_column_2)
        self.right_column_2_layout.setContentsMargins(0, 0, 0, 0)
        self.right_column_2_layout.setSpacing(0)
        self.right_column_2.setFixedWidth(300)

        # Add second right column to main splitter
        central.addWidget(self.right_column_2)

        self.setCentralWidget(central)

        # Enhanced status bar
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)

        # Connect status bar click signals
        self.status_bar.board_clicked.connect(self.on_status_bar_board_clicked)
        self.status_bar.port_clicked.connect(self.on_status_bar_port_clicked)

    def create_menus(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        find_action = QAction("&Find...", self)
        find_action.setShortcut(QKeySequence.Find)
        edit_menu.addAction(find_action)

        # Sketch Menu
        sketch_menu = menubar.addMenu("&Sketch")

        verify_action = QAction("Verify/Compile", self)
        verify_action.setShortcut(Qt.CTRL | Qt.Key_R)
        verify_action.triggered.connect(self.verify_sketch)
        sketch_menu.addAction(verify_action)

        upload_action = QAction("Upload", self)
        upload_action.setShortcut(Qt.CTRL | Qt.Key_U)
        upload_action.triggered.connect(self.upload_sketch)
        sketch_menu.addAction(upload_action)

        # Tools Menu
        tools_menu = menubar.addMenu("&Tools")

        serial_action = QAction("Serial Monitor", self)
        serial_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_M)
        serial_action.triggered.connect(self.toggle_serial_monitor)
        tools_menu.addAction(serial_action)

        status_action = QAction("Real-time Status", self)
        status_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_S)
        status_action.triggered.connect(self.toggle_status_display)
        tools_menu.addAction(status_action)

        tools_menu.addSeparator()

        board_action = QAction("Board Manager...", self)
        board_action.triggered.connect(self.open_board_manager)
        tools_menu.addAction(board_action)

        library_action = QAction("Library Manager...", self)
        library_action.triggered.connect(self.open_library_manager)
        tools_menu.addAction(library_action)

        preferences_action = QAction("Preferences...", self)
        preferences_action.setShortcut(Qt.CTRL | Qt.Key_Comma)
        preferences_action.triggered.connect(self.open_preferences)
        tools_menu.addAction(preferences_action)

        tools_menu.addSeparator()

        snippets_action = QAction("Code Snippets...", self)
        snippets_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_K)
        snippets_action.triggered.connect(self.show_snippets_library)
        tools_menu.addAction(snippets_action)
        tools_menu.addSeparator()

        block_code_action = QAction("Block Code Editor...", self)
        block_code_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_B)
        block_code_action.triggered.connect(self.show_block_code_editor)
        tools_menu.addAction(block_code_action)
        tools_menu.addSeparator()

        git_action = QAction("Git...", self)
        git_action.triggered.connect(self.open_git_dialog)
        tools_menu.addAction(git_action)
        self.cicd_action = QAction("CI/CD...", self)
        self.cicd_action.triggered.connect(self.open_cicd_dialog)
        tools_menu.addAction(self.cicd_action)
        self.debugger_action = QAction("Debugger...", self)
        self.debugger_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_D)
        self.debugger_action.triggered.connect(self.show_debugger_dialog)
        tools_menu.addAction(self.debugger_action)
        tools_menu.addSeparator()

        circuit_designer_action = QAction("Circuit Designer...", self)
        circuit_designer_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_C)
        circuit_designer_action.triggered.connect(self.open_circuit_designer)
        tools_menu.addAction(circuit_designer_action)

        tools_menu.addSeparator()

        code_quality_action = QAction("Code Quality...", self)
        code_quality_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_Q)
        code_quality_action.triggered.connect(self.open_code_quality)
        tools_menu.addAction(code_quality_action)

        self.power_analyzer_action = QAction("Power Consumption Analyzer...", self)
        self.power_analyzer_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_P)
        self.power_analyzer_action.setStatusTip(
            "Open the Power Consumption Analyzer to review power metrics"
        )
        self.power_analyzer_action.triggered.connect(self.show_power_analyzer_dialog)
        tools_menu.addAction(self.power_analyzer_action)

        tools_menu.addAction(self.performance_profiler_action)

        profiler_controls_menu = tools_menu.addMenu("Performance Profiling Controls")
        profiler_controls_menu.addAction(self.start_profiling_action)
        profiler_controls_menu.addAction(self.stop_profiling_action)
        profiler_controls_menu.addAction(self.export_profiling_action)

        unit_testing_action = self.open_unit_testing_action
        tools_menu.addAction(unit_testing_action)

        hil_testing_action = self.open_hil_testing_action
        tools_menu.addAction(hil_testing_action)

        # Tests Menu
        tests_menu = menubar.addMenu("&Tests")
        tests_menu.addAction(self.discover_tests_action)
        tests_menu.addAction(self.run_all_tests_action)
        tests_menu.addAction(self.run_selected_tests_action)
        tests_menu.addAction(self.stop_tests_action)

        tools_menu.addSeparator()
        self.extensions_action = QAction("Extensions Manager...", self)
        self.extensions_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_E)
        self.extensions_action.setStatusTip("Open the Extensions Manager dialog to manage plugins")
        self.extensions_action.triggered.connect(self.open_plugin_manager)
        tools_menu.addAction(self.extensions_action)

        # View Menu
        self.view_menu = menubar.addMenu("&View")

        self.theme_menu = self.view_menu.addMenu("Theme")
        self._populate_theme_menu()

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        docs_action = QAction("Documentation", self)
        docs_action.setShortcut(Qt.Key_F1)
        help_menu.addAction(docs_action)

        onboarding_action = QAction("Getting Started Tour...", self)
        onboarding_action.triggered.connect(self.show_onboarding_wizard)
        help_menu.addAction(onboarding_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        self._refresh_plugin_integrations()

    def showEvent(self, event):
        """Ensure the window is maximized the first time it is shown"""
        super().showEvent(event)
        if not self._initial_maximize_done:
            self._enforce_initial_maximize()

    def create_toolbars(self):
        """Create toolbars"""
        # Main toolbar
        main_toolbar = QToolBar("Main")
        main_toolbar.setObjectName("MainToolBar")
        main_toolbar.setMovable(False)
        self.addToolBar(main_toolbar)
        self.main_toolbar = main_toolbar

        # Board selector
        main_toolbar.addWidget(QLabel("Board: "))
        self.board_selector = QComboBox()
        self.board_selector.setMinimumWidth(200)
        # Boards are populated dynamically from arduino-cli
        self._populate_boards()
        self.board_selector.currentTextChanged.connect(self.on_board_changed)
        main_toolbar.addWidget(self.board_selector)

        main_toolbar.addSeparator()

        # Port selector
        main_toolbar.addWidget(QLabel("Port: "))
        self.port_selector = QComboBox()
        self.port_selector.setMinimumWidth(150)
        self.refresh_ports()
        self.port_selector.currentTextChanged.connect(self.on_port_changed)
        main_toolbar.addWidget(self.port_selector)

        # Port refresh button
        refresh_port_btn = QAction("🔄", self)
        refresh_port_btn.setToolTip("Refresh Ports")
        refresh_port_btn.triggered.connect(self.refresh_ports)
        main_toolbar.addAction(refresh_port_btn)

        main_toolbar.addSeparator()

        # Build configuration selector
        main_toolbar.addWidget(QLabel("Config: "))
        self.config_selector = QComboBox()
        self.config_selector.setMinimumWidth(100)
        self.config_selector.addItems(["Release", "Debug"])
        self.config_selector.currentTextChanged.connect(self.on_config_changed)
        main_toolbar.addWidget(self.config_selector)

        main_toolbar.addSeparator()

        # Verify and Upload buttons
        verify_btn = QAction("✓ Verify", self)
        verify_btn.setToolTip("Verify/Compile Sketch")
        verify_btn.triggered.connect(self.verify_sketch)
        main_toolbar.addAction(verify_btn)

        upload_btn = QAction("→ Upload", self)
        upload_btn.setToolTip("Upload Sketch to Board")
        upload_btn.triggered.connect(self.upload_sketch)
        main_toolbar.addAction(upload_btn)

        # Upload & Monitor combo button
        upload_monitor_btn = QAction("⬆️📡 Upload & Monitor", self)
        upload_monitor_btn.setToolTip("Upload and Open Serial Monitor")
        upload_monitor_btn.triggered.connect(self.upload_and_monitor)
        main_toolbar.addAction(upload_monitor_btn)

        main_toolbar.addSeparator()
        self.start_profiling_action.setIconText("🕒 Start Profiling")
        main_toolbar.addAction(self.start_profiling_action)
        self.stop_profiling_action.setIconText("⏹ Stop Profiling")
        main_toolbar.addAction(self.stop_profiling_action)
        profiler_open_action = QAction("📈 Profiler", self)
        profiler_open_action.setToolTip("Open the Performance Profiler dashboard")
        profiler_open_action.triggered.connect(self.show_performance_profiler_dialog)
        main_toolbar.addAction(profiler_open_action)

        main_toolbar.addSeparator()

        # File operations
        new_btn = QAction("+ New", self)
        new_btn.setToolTip("New Sketch")
        new_btn.triggered.connect(self.new_file)
        main_toolbar.addAction(new_btn)

        open_btn = QAction("📁 Open", self)
        open_btn.setToolTip("Open Sketch")
        open_btn.triggered.connect(self.open_file)
        main_toolbar.addAction(open_btn)

        save_btn = QAction("💾 Save", self)
        save_btn.setToolTip("Save Sketch")
        save_btn.triggered.connect(self.save_file)
        main_toolbar.addAction(save_btn)

        main_toolbar.addSeparator()

        # Quick access to Examples
        examples_btn = QAction("📚 Examples", self)
        examples_btn.setToolTip("Open Example Sketches")
        examples_btn.triggered.connect(self.show_examples)
        main_toolbar.addAction(examples_btn)

        # Quick access to Libraries
        libraries_btn = QAction("📦 Libraries", self)
        libraries_btn.setToolTip("Manage Libraries")
        libraries_btn.triggered.connect(self.show_libraries)
        main_toolbar.addAction(libraries_btn)

        # Extensions / Plugin manager button
        self.extensions_toolbar_action = QAction("🧩 Extensions", self)
        self.extensions_toolbar_action.setToolTip("Open Extensions Manager dialog")
        self.extensions_toolbar_action.triggered.connect(self.open_plugin_manager)
        main_toolbar.addAction(self.extensions_toolbar_action)

        main_toolbar.addSeparator()

        # Serial Monitor
        serial_btn = QAction("📡 Serial Monitor", self)
        serial_btn.setToolTip("Toggle Serial Monitor")
        serial_btn.triggered.connect(self.toggle_serial_monitor)
        main_toolbar.addAction(serial_btn)

        # Real-time Status
        status_btn = QAction("⚡ Status", self)
        status_btn.setToolTip("Toggle Real-time Status Display")
        status_btn.triggered.connect(self.toggle_status_display)
        main_toolbar.addAction(status_btn)

        main_toolbar.addSeparator()

        # Circuit Designer
        circuit_btn = QAction("🔌 Circuit Designer", self)
        circuit_btn.setToolTip("Open Circuit Designer")
        circuit_btn.triggered.connect(self.open_circuit_designer)
        main_toolbar.addAction(circuit_btn)

        main_toolbar.addSeparator()
        self.run_all_tests_action.setIconText("🧪 Run Tests")
        main_toolbar.addAction(self.run_all_tests_action)
        self._refresh_toolbar_plugins()

    def create_dock_widgets(self):
        """Create panels and dockable widgets."""
        # --- LEFT COLUMN (Normal widgets, NOT docks) ---
        # Create left-side panel widgets
        self.quick_actions_panel = QuickActionsPanel()

        # Add widgets to left column layout (NOT as dock widgets)
        self.left_column_layout.addWidget(self.quick_actions_panel)

        # --- RIGHT COLUMN 1 (Normal widgets, NOT docks) ---
        # Create first right column widgets (Board/Status)
        self.board_panel = BoardPanel(board_manager=self.board_manager)
        self.board_panel.board_selected.connect(self._on_board_panel_board_selected)
        self.status_display = StatusDisplay()

        # Add widgets to first right column layout
        self.right_column_layout.addWidget(self.board_panel)
        self.right_column_layout.addWidget(self.status_display)
        self.right_column_layout.addStretch()

        if self._cli_boards:
            self.board_panel.set_boards(self._cli_boards)
            selected_board = self._get_selected_board()
            if selected_board:
                self.board_panel.select_board(selected_board)
            else:
                self.board_panel.update_board_info(None)
        else:
            self.board_panel.set_boards([])

        # --- RIGHT COLUMN 2 (Normal widgets, NOT docks) ---
        # Create second right column widgets (Pin Usage/Context)
        self.pin_usage_panel = PinUsagePanel()
        self.context_panel = ContextPanel()

        # Add widgets to second right column layout
        self.right_column_2_layout.addWidget(self.pin_usage_panel)
        self.right_column_2_layout.addWidget(self.context_panel)
        self.right_column_2_layout.setStretch(0, 1)
        self.right_column_2_layout.setStretch(1, 1)

        # --- BOTTOM TABS (Normal widgets in tabs, NOT docks) ---
        # Create bottom panels
        self.console_panel = ConsolePanel()
        self.serial_monitor = SerialMonitor()
        self.plotter_panel = PlotterPanel()
        self.problems_panel = ProblemsPanel()
        self.output_panel = OutputPanel()

        # Connect serial monitor data to plotter
        self.serial_monitor.data_received.connect(self.plotter_panel.append_output)
        self.serial_monitor.data_received.connect(self._on_serial_monitor_data)

        # Add panels to bottom tabs (created in init_ui)
        self.bottom_tabs.addTab(self.console_panel, "Console")
        self.bottom_tabs.addTab(self.serial_monitor, "Serial Monitor")
        self.bottom_tabs.addTab(self.plotter_panel, "Plotter")
        self.bottom_tabs.addTab(self.problems_panel, "Problems")
        self.bottom_tabs.addTab(self.output_panel, "Output")

        # Connect Quick Actions Panel signals
        self.quick_actions_panel.upload_clicked.connect(self.upload_sketch)
        self.quick_actions_panel.verify_clicked.connect(self.verify_sketch)
        self.quick_actions_panel.find_clicked.connect(self.show_find_dialog)
        self.quick_actions_panel.libraries_clicked.connect(self.show_libraries)
        self.quick_actions_panel.examples_clicked.connect(self.show_examples)
        self.quick_actions_panel.board_clicked.connect(self.on_status_bar_board_clicked)
        self.quick_actions_panel.new_sketch_clicked.connect(self.new_file)
        self.quick_actions_panel.open_sketch_clicked.connect(self.open_file)
        self.quick_actions_panel.save_sketch_clicked.connect(self.save_file)
        self.quick_actions_panel.serial_monitor_clicked.connect(self.toggle_serial_monitor)
        self.quick_actions_panel.serial_plotter_clicked.connect(self.toggle_plotter)

        # --- UNIT TESTING DIALOG (Non-modal dialog) ---
        if not self.unit_testing_dialog:
            self.unit_testing_dialog = UnitTestingDialog(self.unit_testing_service, parent=self)
            self.unit_testing_panel = self.unit_testing_dialog.panel
        self._sync_unit_testing_actions()

        # Sync contextual help state with the initial Serial Monitor visibility
        self._broadcast_serial_monitor_state(self._is_serial_monitor_active())

        # Prime unit testing service with the current sketch/project context
        self._update_unit_testing_target(force_discover=True)
    def _ensure_plugin_manager_dialog(self):
        """Create the plugin manager dialog if it hasn't been added yet."""
        if getattr(self, "plugin_manager_widget", None) is None:
            return
        if self.plugin_manager_dialog is not None:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Extensions Manager")
        dialog.setModal(False)
        dialog.setWindowModality(Qt.NonModal)
        dialog.setAttribute(Qt.WA_DeleteOnClose, False)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plugin_manager_widget)
        self.plugin_manager_widget.setParent(dialog)

        self.plugin_manager_dialog = dialog

    def open_plugin_manager(self):
        """Show the plugin manager dialog and refresh its contents."""
        if getattr(self, "plugin_manager_widget", None) is None:
            return

        self._ensure_plugin_manager_dialog()

        if self.plugin_manager_widget is not None:
            self.plugin_manager_widget.refresh_plugins()
            self._refresh_plugin_integrations()

        if self.plugin_manager_dialog is not None:
            self.plugin_manager_dialog.show()
            self.plugin_manager_dialog.raise_()
            self.plugin_manager_dialog.activateWindow()
            self.plugin_manager_widget.setFocus()

    def _populate_theme_menu(self):
        """Populate the theme menu with built-in and plugin-provided themes."""
        if self.theme_menu is None:
            return

        self.theme_menu.clear()

        built_in_themes = [
            ("Light", "light"),
            ("Dark", "dark"),
            ("High Contrast", "high_contrast"),
        ]

        for label, theme_key in built_in_themes:
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, key=theme_key: self.theme_manager.apply_theme(key))
            self.theme_menu.addAction(action)

        if getattr(self, "plugin_manager", None) is None:
            return

        theme_plugins = self.plugin_manager.get_plugins_by_type(PluginType.THEME)
        if not theme_plugins:
            return

        self.theme_menu.addSeparator()

        for plugin_info in theme_plugins:
            action = QAction(plugin_info.metadata.name, self)
            action.setCheckable(True)
            action.setChecked(plugin_info.status == PluginStatus.ACTIVE)
            action.triggered.connect(partial(self._on_theme_plugin_action_triggered, plugin_info.metadata.id))
            self.theme_menu.addAction(action)

    def _on_theme_plugin_action_triggered(self, plugin_id: str, checked=False):
        """Toggle activation for a theme plugin when selected from the menu."""
        if getattr(self, "plugin_manager", None) is None:
            return

        plugin_info = self.plugin_manager.get_plugin_info(plugin_id)
        if plugin_info is None:
            return

        if plugin_info.status != PluginStatus.ACTIVE:
            self.plugin_manager.activate_plugin(plugin_id)
        else:
            self.plugin_manager.deactivate_plugin(plugin_id)

    def _refresh_theme_menu_from_plugins(self):
        """Rebuild the theme menu to reflect current plugin state."""
        self._populate_theme_menu()

    def _refresh_toolbar_plugins(self):
        """Update toolbar and menu metadata to reflect plugin counts."""
        if getattr(self, "plugin_manager", None) is None:
            return

        total_plugins = len(self.plugin_manager.get_all_plugins())
        active_plugins = len(self.plugin_manager.get_active_plugins())

        suffix = ""
        if total_plugins:
            suffix = f" ({active_plugins} active / {total_plugins} installed)"

        if self.extensions_toolbar_action is not None:
            tooltip = "Open Extensions Manager dialog"
            if suffix:
                tooltip += suffix
            self.extensions_toolbar_action.setToolTip(tooltip)

        if self.extensions_action is not None:
            status_tip = "Open the Extensions Manager dialog to manage plugins"
            if suffix:
                status_tip += f" — {active_plugins} active of {total_plugins} installed"
            self.extensions_action.setStatusTip(status_tip)
            self.extensions_action.setToolTip(status_tip)

    def _refresh_plugin_integrations(self):
        """Refresh UI elements that depend on plugin availability."""
        self._refresh_theme_menu_from_plugins()
        self._refresh_toolbar_plugins()

    def _on_plugin_state_changed(self, plugin_id: str):
        """Handle plugin load/unload/activation changes."""
        self._refresh_plugin_integrations()

        if getattr(self, "status_bar", None) is not None:
            self.status_bar.set_status(f"Plugin updated: {plugin_id}")

    def _on_plugin_error(self, plugin_id: str, error_message: str):
        """Surface plugin errors in the status bar."""
        if getattr(self, "status_bar", None) is not None:
            self.status_bar.set_status(f"Plugin error: {plugin_id}")
        # --- GIT PANEL DIALOG ---
        self._ensure_git_dialog()
        self._update_git_repository()

    def create_new_editor(self, filename="untitled.ino", *, file_path=None, content=None, mark_clean=False):
        """Create a new editor tab"""
        editor_container = EditorContainer(filename, file_path=file_path)

        # Set content either from provided text or default template
        if content is not None:
            editor_container.set_content(content, mark_clean=mark_clean)
        elif filename.endswith(".ino"):
            editor_container.set_content(self.get_arduino_template(), mark_clean=mark_clean)

        # Newly created sketches without saved content should be considered dirty
        if content is None and not mark_clean:
            editor_container.editor.document().setModified(True)

        # Connect editor changes to pin usage update and background compilation
        editor_container.editor.textChanged.connect(self.update_pin_usage)
        editor_container.editor.textChanged.connect(self._on_code_changed)  # Triggers background compile for memory

        # Connect cursor position changes to status bar
        editor_container.editor.cursorPositionChanged.connect(self.update_cursor_position)

        # Connect function clicks to context panel
        editor_container.editor.function_clicked.connect(self.context_panel.update_context)

        # Keep contextual help aware of Serial Monitor visibility
        editor_container.editor.set_serial_monitor_open(self._serial_monitor_open)

        editor_container.dirtyChanged.connect(
            lambda dirty, container=editor_container: self.on_editor_dirty_changed(container)
        )

        self._attach_debugger_to_editor(editor_container)

        display_name = editor_container.current_display_name()
        index = self.editor_tabs.addTab(editor_container, display_name)
        self.editor_tabs.setTabToolTip(index, editor_container.filename)
        self.editor_tabs.setCurrentIndex(index)

        # Initial updates
        self.update_pin_usage()
        self.update_status_bar_for_file(editor_container.filename)
        self.update_cursor_position()
        self.update_tab_title(index)

        # Trigger initial background compile for memory usage (after a short delay to ensure setup is complete)
        QTimer.singleShot(500, self._do_background_compile)
        self._update_code_quality_panel()

        self._update_unit_testing_target()

        return editor_container

    def get_arduino_template(self):
        """Get default Arduino sketch template"""
        return """// Arduino Sketch
// Modern Arduino IDE

void setup() {
  // Initialize serial communication
  Serial.begin(9600);

  // Your setup code here

}

void loop() {
  // Your main code here

}
"""

    def close_tab(self, index):
        """Close editor tab"""
        widget = self.editor_tabs.widget(index)
        if not widget:
            return

        if getattr(widget, "dirty", False):
            choice = self.prompt_unsaved_changes(widget)
            if choice == QMessageBox.Cancel:
                return
            if choice == QMessageBox.Save:
                if not self.save_file(index=index):
                    return

        self._detach_debugger_from_editor(widget)
        self.editor_tabs.removeTab(index)

    def prompt_unsaved_changes(self, editor_container):
        """Ask the user how to handle unsaved changes"""
        file_name = editor_container.current_display_name()
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Warning)
        message.setWindowTitle("Unsaved Changes")
        message.setText(f"Do you want to save changes to {file_name}?")
        message.setInformativeText("Your changes will be lost if you don't save them.")
        message.setStandardButtons(
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        message.setDefaultButton(QMessageBox.Save)
        return message.exec()

    def on_editor_dirty_changed(self, editor_container):
        """Update tab title when dirty state changes"""
        index = self.editor_tabs.indexOf(editor_container)
        if index >= 0:
            self.update_tab_title(index)

    def update_tab_title(self, index):
        """Refresh the tab title and tooltip for the given index"""
        editor_container = self.editor_tabs.widget(index)
        if not editor_container:
            return
        title = editor_container.current_display_name()
        if getattr(editor_container, "dirty", False):
            title += "*"
        self.editor_tabs.setTabText(index, title)
        tooltip = editor_container.file_path or editor_container.suggested_name
        self.editor_tabs.setTabToolTip(index, tooltip)

    def find_editor_by_path(self, path):
        """Return the index and container for a given file path"""
        if not path:
            return -1, None
        normalized = str(Path(path).resolve())
        for i in range(self.editor_tabs.count()):
            widget = self.editor_tabs.widget(i)
            if getattr(widget, "file_path", None) == normalized:
                return i, widget
        return -1, None

    def add_recent_file(self, path):
        """Track a recently opened or saved file"""
        normalized = str(Path(path).resolve())
        files = [normalized]
        files.extend(f for f in getattr(self, "recent_files", []) if f != normalized)
        self.recent_files = files[:10]
        self.settings.setValue("recentFiles", self.recent_files)

    def _load_recent_files(self):
        """Load recent files from persistent settings"""
        stored = self.settings.value("recentFiles", [])
        if isinstance(stored, str):
            return [stored]
        if isinstance(stored, (list, tuple)):
            return [str(Path(item).resolve()) for item in stored]
        return []

    def _load_compile_verbose_preference(self) -> bool:
        """Retrieve the persisted compile verbosity preference."""

        stored = self.settings.value("cli/verboseCompile", False)
        if isinstance(stored, bool):
            return stored
        if isinstance(stored, str):
            return stored.lower() in {"1", "true", "yes", "on"}
        if isinstance(stored, int):
            return stored != 0
        return False

    def _is_compile_verbose_enabled(self) -> bool:
        """Return True when verbose compilation output is enabled."""

        return bool(getattr(self, "_compile_verbose_enabled", False))

    # ------------------------------------------------------------------
    # Debugger integration helpers

    def _create_debug_actions(self) -> None:
        """Create global debugger shortcuts and initial state."""

        self.start_debug_action = QAction("Start/Continue Debugging", self)
        self.start_debug_action.setShortcut(QKeySequence(Qt.Key_F5))
        self.start_debug_action.triggered.connect(self._start_or_continue_debugging)

        self.stop_debug_action = QAction("Stop Debugging", self)
        self.stop_debug_action.setShortcut(QKeySequence(Qt.SHIFT | Qt.Key_F5))
        self.stop_debug_action.triggered.connect(self.debug_service.stop_debugging)

        self.pause_debug_action = QAction("Pause Debugging", self)
        self.pause_debug_action.setShortcut(QKeySequence(Qt.Key_F6))
        self.pause_debug_action.triggered.connect(self.debug_service.pause_execution)

        self.step_over_action = QAction("Step Over", self)
        self.step_over_action.setShortcut(QKeySequence(Qt.Key_F10))
        self.step_over_action.triggered.connect(self.debug_service.step_over)

        self.step_into_action = QAction("Step Into", self)
        self.step_into_action.setShortcut(QKeySequence(Qt.Key_F11))
        self.step_into_action.triggered.connect(self.debug_service.step_into)

        self.step_out_action = QAction("Step Out", self)
        self.step_out_action.setShortcut(QKeySequence(Qt.SHIFT | Qt.Key_F11))
        self.step_out_action.triggered.connect(self.debug_service.step_out)

        self.toggle_breakpoint_action = QAction("Toggle Breakpoint", self)
        self.toggle_breakpoint_action.setShortcut(QKeySequence(Qt.Key_F9))
        self.toggle_breakpoint_action.triggered.connect(self._toggle_breakpoint_at_cursor)

        for action in (
            self.start_debug_action,
            self.stop_debug_action,
            self.pause_debug_action,
            self.step_over_action,
            self.step_into_action,
            self.step_out_action,
            self.toggle_breakpoint_action,
        ):
            self.addAction(action)

        self._update_debug_action_states(self.debug_service.state)

    def _start_or_continue_debugging(self) -> None:
        """Handle the Start/Continue shortcut."""

        self.debug_service.start_debugging()

    def _toggle_breakpoint_at_cursor(self) -> None:
        """Toggle breakpoint at the current cursor line in the active editor."""

        container = self.editor_tabs.currentWidget()
        if not container:
            return

        gutter = self._breakpoint_gutters.get(container)
        if not gutter:
            return

        file_path = container.file_path
        if not file_path:
            if getattr(self, "status_bar", None) is not None:
                self.status_bar.set_status("Save the sketch before adding breakpoints.")
            return

        line_number = container.editor.textCursor().blockNumber() + 1
        if gutter.has_breakpoint(line_number):
            gutter.remove_breakpoint(line_number)
        else:
            gutter.add_breakpoint(line_number)

    def _update_debug_action_states(self, state: DebugState) -> None:
        """Enable or disable debugger shortcuts based on current state."""

        start_enabled = state in (DebugState.IDLE, DebugState.DISCONNECTED, DebugState.CONNECTED)
        stop_enabled = state not in (DebugState.IDLE, DebugState.DISCONNECTED)
        pause_enabled = state == DebugState.RUNNING
        stepping_enabled = state == DebugState.PAUSED

        self.start_debug_action.setEnabled(start_enabled)
        self.stop_debug_action.setEnabled(stop_enabled)
        self.pause_debug_action.setEnabled(pause_enabled)
        self.step_over_action.setEnabled(stepping_enabled)
        self.step_into_action.setEnabled(stepping_enabled)
        self.step_out_action.setEnabled(stepping_enabled)

    def _on_debug_state_changed(self, state: DebugState) -> None:
        self._update_debug_action_states(state)

    def _on_debug_error(self, message: str) -> None:
        if getattr(self, "status_bar", None) is not None:
            self.status_bar.set_status(message)

    def _on_service_breakpoint_added(self, breakpoint: Breakpoint) -> None:
        self._refresh_gutters_for_path(breakpoint.file_path)

    def _on_service_breakpoint_updated(self, breakpoint: Breakpoint) -> None:
        self._refresh_gutters_for_path(breakpoint.file_path)

    def _on_service_breakpoint_removed(self, breakpoint_id: int) -> None:  # noqa: ARG002
        self._refresh_all_gutters()

    def _refresh_gutters_for_path(self, file_path: Optional[str]) -> None:
        if not file_path:
            return

        gutters = self._gutters_by_path.get(file_path)
        if not gutters:
            return

        for gutter in list(gutters):
            gutter.sync_with_debug_service(self.debug_service)

    def _refresh_all_gutters(self) -> None:
        for gutter in list(self._breakpoint_gutters.values()):
            if getattr(gutter, "file_path", None):
                gutter.sync_with_debug_service(self.debug_service)

    def _attach_debugger_to_editor(self, editor_container: EditorContainer) -> None:
        if editor_container in self._breakpoint_gutters:
            return

        gutter = install_breakpoint_gutter(editor_container.editor, self.debug_service)
        gutter.breakpoint_added.connect(self._on_editor_breakpoint_added)
        gutter.breakpoint_removed.connect(self._on_editor_breakpoint_removed)

        self._breakpoint_gutters[editor_container] = gutter
        self._sync_editor_breakpoints(editor_container)

    def _detach_debugger_from_editor(self, editor_container: EditorContainer) -> None:
        gutter = self._breakpoint_gutters.pop(editor_container, None)
        if not gutter:
            return

        try:
            gutter.breakpoint_added.disconnect(self._on_editor_breakpoint_added)
        except Exception:
            pass
        try:
            gutter.breakpoint_removed.disconnect(self._on_editor_breakpoint_removed)
        except Exception:
            pass

        self._unregister_gutter(gutter)

    def _unregister_gutter(self, gutter: BreakpointGutter) -> None:
        existing_key = getattr(gutter, "_file_key", None)
        if existing_key and existing_key in self._gutters_by_path:
            gutters = self._gutters_by_path[existing_key]
            gutters.discard(gutter)
            if not gutters:
                self._gutters_by_path.pop(existing_key, None)

    def _sync_editor_breakpoints(self, editor_container: EditorContainer) -> None:
        gutter = self._breakpoint_gutters.get(editor_container)
        if not gutter:
            return

        # Remove previous registration
        self._unregister_gutter(gutter)

        file_path = editor_container.file_path
        if file_path:
            gutter.set_file_path(file_path)
            gutter._file_key = file_path  # type: ignore[attr-defined]
            self._gutters_by_path.setdefault(file_path, set()).add(gutter)
            gutter.sync_with_debug_service(self.debug_service)
        else:
            gutter.set_file_path(None)
            gutter._file_key = None  # type: ignore[attr-defined]

    def _on_editor_breakpoint_added(self, file_path: str, line: int) -> None:
        if not file_path:
            return
        self.debug_service.add_breakpoint(file_path, line)

    def _on_editor_breakpoint_removed(self, file_path: str, line: int) -> None:
        if not file_path:
            return
        breakpoint = self.debug_service.get_breakpoint_at_line(file_path, line)
        if breakpoint:
            self.debug_service.remove_breakpoint(breakpoint.id)

    def _navigate_to_source(self, file_path: str, line: int) -> None:
        if not file_path:
            return

        path = Path(file_path)
        _, existing_container = self.find_editor_by_path(path)
        if not existing_container:
            self._open_file_path(path)
            _, existing_container = self.find_editor_by_path(path)

        if not existing_container:
            return

        self.editor_tabs.setCurrentWidget(existing_container)
        editor = existing_container.editor
        cursor = editor.textCursor()
        block = editor.document().findBlockByNumber(max(line - 1, 0))
        cursor.setPosition(block.position())
        editor.setTextCursor(cursor)
        editor.centerCursor()

    def show_debugger_dialog(self, checked=False):  # noqa: ARG002
        """Open (or focus) the debugger workspace dialog."""

        if self.debug_workspace_dialog is None:
            self.debug_workspace_dialog = DebugWorkspaceDialog(self.debug_service, self)
            self.debug_workspace_dialog.breakpoints_panel.breakpoint_activated.connect(self._navigate_to_source)
            self.debug_workspace_dialog.call_stack_panel.location_activated.connect(self._navigate_to_source)

        self.debug_workspace_dialog.show()
        self.debug_workspace_dialog.raise_()
        self.debug_workspace_dialog.activateWindow()

    def new_file(self, checked=False):
        """Create new file"""
        self.create_new_editor()

    def open_file(self, checked=False):
        """Open file"""
        start_dir = self.settings.value("lastOpenDir", str(Path.home()))
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Sketch",
            start_dir,
            "Arduino Sketches (*.ino *.pde *.cpp *.c *.h);;All Files (*)"
        )

        if not file_path:
            return

        path = Path(file_path)
        self.settings.setValue("lastOpenDir", str(path.parent))

        self._open_file_path(path)

    def save_file(self, checked=False, *, index=None, save_as=False):
        """Save current file"""
        if index is None:
            index = self.editor_tabs.currentIndex()

        if index < 0:
            return False

        editor_container = self.editor_tabs.widget(index)
        if not editor_container:
            return False

        current_path = editor_container.file_path
        needs_dialog = save_as or not current_path

        if needs_dialog:
            suggested_dir = self.settings.value("lastSaveDir", str(Path.home()))
            if current_path:
                suggested_dir = str(Path(current_path).parent)
                default_name = Path(current_path).name
            else:
                default_name = editor_container.suggested_name
            initial_path = str(Path(suggested_dir) / default_name)
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Sketch As" if save_as or not current_path else "Save Sketch",
                initial_path,
                "Arduino Sketches (*.ino *.pde *.cpp *.c *.h);;All Files (*)"
            )
            if not file_path:
                return False
            current_path = file_path

        path = Path(current_path)

        try:
            path.write_text(editor_container.editor.toPlainText(), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Save Sketch",
                f"Failed to save {path.name}: {exc}"
            )
            self.status_bar.set_status("Ready")
            return False

        self.settings.setValue("lastSaveDir", str(path.parent))
        editor_container.set_file_path(path)
        self._sync_editor_breakpoints(editor_container)
        editor_container.mark_clean()
        self.update_tab_title(index)
        self.add_recent_file(path)
        self.update_status_bar_for_file(editor_container.filename)
        self._update_unit_testing_target(force_discover=True)

        self._refresh_git_panel()

        return True

    def _open_file_path(self, path: Path):
        try:
            contents = path.read_text(encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Open Sketch",
                f"Failed to open {path.name}: {exc}"
            )
            self.status_bar.set_status("Ready")
            return

        existing_index, existing_container = self.find_editor_by_path(path)
        if existing_container:
            existing_container.set_file_path(path)
            self._sync_editor_breakpoints(existing_container)
            existing_container.set_content(contents, mark_clean=True)
            self.editor_tabs.setCurrentIndex(existing_index)
            self.update_status_bar_for_file(existing_container.filename)
            self.update_tab_title(existing_index)
        else:
            editor_container = self.create_new_editor(
                filename=path.name,
                file_path=str(path),
                content=contents,
                mark_clean=True
            )
            editor_container.set_file_path(path)
            self._sync_editor_breakpoints(editor_container)

        self.add_recent_file(path)
        self.status_bar.set_status(f"Opened {path.name}")
        # Explicitly update pin usage after opening file
        self.update_pin_usage()
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

        self.status_bar.set_status(f"Saved {path.name}")
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

        self._update_unit_testing_target(force_discover=True)

        return True

    def save_file_as(self, checked=False):
        """Save the current file with a new name"""
        return self.save_file(index=None, save_as=True)

    def _append_console_stream(self, chunk, *, color=None):
        """Stream CLI output to the console panel line-by-line."""
        if not chunk:
            return
        lines = chunk.splitlines()
        if chunk.endswith(("\n", "\r")):
            lines.append("")
        for line in lines:
            self.console_panel.append_output(line, color=color)

    def _show_error_recovery_hints(self, compiler_output):
        """Display smart recovery hints for the most recent compiler error."""

        if not compiler_output or not compiler_output.strip():
            return

        suggestions = self.error_recovery.analyze_compile_error(compiler_output)
        if not suggestions:
            return

        highlight = "#CCA700"
        self.console_panel.append_output("💡 Potential fixes:", color=highlight)

        for suggestion in suggestions:
            if suggestion.issue == "unknown":
                title = "General guidance"
                confidence = ""
            else:
                title = suggestion.issue.capitalize()
                confidence = (
                    f" ({int(round(suggestion.confidence * 100))}% match)"
                    if suggestion.confidence
                    else ""
                )
            self.console_panel.append_output(f"  • {title}{confidence}", color=highlight)
            for fix in suggestion.suggestions:
                self.console_panel.append_output(f"      - {fix}", color=highlight)

    def _handle_cli_output(self, text):
        # Only show output for non-background compiles
        if not self._is_background_compile:
            self._append_console_stream(text)
        # Store compilation output for parsing memory usage
        if self._cli_current_operation == "compile":
            self._compilation_output += text
        self.power_analyzer_service.ingest_cli_output(self._cli_current_operation, text)

    def _handle_cli_error(self, text):
        if not text:
            return
        self._last_cli_error += text
        # Only show errors for non-background compiles
        if not self._is_background_compile:
            self._append_console_stream(text, color="#F48771")

    def _on_serial_monitor_data(self, payload: str):
        """Forward serial telemetry to the power analyzer service."""

        if not payload:
            return

        board = self._get_selected_board()
        port = self._get_selected_port() or ""
        self.power_analyzer_service.ingest_serial_stream(payload, board=board, port=port)

    def _handle_cli_finished(self, exit_code):
        operation = self._cli_current_operation
        is_background = self._is_background_compile
        self._cli_current_operation = None
        self._is_background_compile = False

        if exit_code == 0:
            if operation == "compile":
                # Always parse and update memory usage on successful compile
                self._parse_and_update_memory_usage(self._compilation_output)

                # Parse compiler output for problems (warnings, etc.)
                self.problems_panel.parse_compiler_output(self._compilation_output)

                # Only show messages and handle UI for non-background compiles
                if not is_background:
                    self.console_panel.append_output("✔ Compilation completed successfully.", color="#6A9955")
                    self.status_bar.set_status("Compilation Succeeded")
                    QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))
                else:
                    # Background compile succeeded - show brief status
                    self.status_bar.set_status("Memory updated")
                    QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

                # If this was a compile before upload, trigger the upload now
                if self._upload_after_compile:
                    self._upload_after_compile = False
                    QTimer.singleShot(500, self._do_upload)

            elif operation == "upload":
                self.console_panel.append_output("✔ Upload completed successfully.", color="#6A9955")
                self.status_bar.set_status("Upload Succeeded")
                if self._open_monitor_after_upload:
                    self.toggle_serial_monitor()
                self._open_monitor_after_upload = False
                QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))
                self._refresh_git_panel()
            else:
                if not is_background:
                    self.status_bar.set_status("Ready")
        else:
            # For background compiles, ALWAYS try to parse memory even with errors
            # This allows the memory monitor to update even when code has compilation errors
            if is_background and operation == "compile":
                self._parse_and_update_memory_usage(self._compilation_output)

            # Parse compiler output for problems (errors, warnings)
            if operation == "compile":
                # Combine both stdout and stderr for complete error information
                full_output = self._compilation_output + self._last_cli_error
                self.problems_panel.parse_compiler_output(full_output)

            # Only show error dialogs and messages for non-background compiles
            if not is_background:
                detail = self._last_cli_error.strip() or "Check the console for details."
                if operation == "compile":
                    self.console_panel.append_output("✗ Compilation failed.", color="#F48771")
                    self.status_bar.set_status("Compilation Failed")
                    QMessageBox.critical(self, "Compilation Failed", detail)
                    self._show_error_recovery_hints(full_output)
                    # Cancel upload if compilation failed
                    self._upload_after_compile = False
                elif operation == "upload":
                    self.console_panel.append_output("✗ Upload failed.", color="#F48771")
                    self.status_bar.set_status("Upload Failed")
                    QMessageBox.critical(self, "Upload Failed", detail)
                else:
                    self.status_bar.set_status("Error")
                    QMessageBox.critical(self, "Command Failed", detail)
                self._open_monitor_after_upload = False
                QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))
            else:
                # Background compile failed - silently ignore errors
                # Cancel upload if this was a background compile before upload
                self._upload_after_compile = False
                self._open_monitor_after_upload = False

        # Clear compilation output buffer
        self._compilation_output = ""
        self._last_cli_error = ""

        self.power_analyzer_service.handle_cli_finished(operation, exit_code, is_background=is_background)

        if self._pending_board_memory_refresh and not self.cli_service.is_running():
            self._pending_board_memory_refresh = False
            QTimer.singleShot(0, self._do_background_compile)

        if self._board_list_refresh_pending and not self.cli_service.is_running():
            self._start_board_list_refresh_timer()

    def _parse_and_update_memory_usage(self, output_text):
        """Parse memory usage from compilation output and update status display

        Parses lines like:
        Sketch uses 1438 bytes (4%) of program storage space. Maximum is 30720 bytes.
        Global variables use 184 bytes (8%) of dynamic memory, leaving 1864 bytes for local variables. Maximum is 2048 bytes.
        """
        if not output_text:
            return

        # Parse flash/program storage
        # Pattern: "Sketch uses X bytes (Y%) of program storage space. Maximum is Z bytes."
        flash_pattern = r'Sketch uses (\d+) bytes.*?Maximum is (\d+) bytes'
        flash_match = re.search(flash_pattern, output_text)

        # Parse RAM/dynamic memory
        # Pattern: "Global variables use X bytes (Y%) of dynamic memory... Maximum is Z bytes."
        ram_pattern = r'Global variables use (\d+) bytes.*?Maximum is (\d+) bytes'
        ram_match = re.search(ram_pattern, output_text)

        if flash_match and ram_match:
            flash_used = int(flash_match.group(1))
            flash_max = int(flash_match.group(2))
            ram_used = int(ram_match.group(1))
            ram_max = int(ram_match.group(2))

            # Update the status display with actual compilation results
            self.status_display.update_from_compilation(
                flash_used, flash_max, ram_used, ram_max
            )

            # Log to console (only for non-background compiles)
            if not self._is_background_compile:
                self.console_panel.append_output(
                    f"✓ Memory updated: Flash {flash_used}/{flash_max} bytes, RAM {ram_used}/{ram_max} bytes",
                    color="#6A9955"
                )

    def _trigger_board_memory_refresh(self):
        """Ensure memory usage is recalculated immediately after a board change."""
        if self._background_compile_timer.isActive():
            self._background_compile_timer.stop()

        if self.cli_service.is_running():
            # Try again once the CLI is idle
            self._pending_board_memory_refresh = True
            return

        self._pending_board_memory_refresh = False
        QTimer.singleShot(0, self._do_background_compile)

    def _on_code_changed(self):
        """Called when code changes - restart background compile timer"""
        # Cancel any pending background compile
        if self._background_compile_timer.isActive():
            self._background_compile_timer.stop()

        # Don't start background compile if CLI is already running
        if self.cli_service.is_running():
            return

        # Schedule a new background compile after delay
        self._background_compile_timer.start(self._background_compile_delay)
        self._update_code_quality_panel()

    def _do_background_compile(self):
        """Perform a silent background compilation to update memory usage"""
        # Don't run if CLI is busy
        if self.cli_service.is_running():
            return

        current_widget = self.editor_tabs.currentWidget()
        if not current_widget or not hasattr(current_widget, "editor"):
            return

        board = self._get_selected_board()
        if not board:
            # Show why background compile isn't running
            self.status_bar.set_status("Background compile: No board selected")
            return

        # Get current code content
        temp_content = current_widget.editor.toPlainText()

        # Skip if content is empty
        if not temp_content or not temp_content.strip():
            return

        try:
            # Write to temp file for compilation
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "arduino-ide-bg-compile"
            temp_dir.mkdir(exist_ok=True)

            # Use filename from saved file if available, otherwise use generic name
            if getattr(current_widget, "file_path", None) and Path(current_widget.file_path).exists():
                temp_filename = Path(current_widget.file_path).name
            else:
                # For unsaved files, use a generic name
                temp_filename = "sketch.ino"

            temp_sketch = temp_dir / temp_filename
            temp_sketch.write_text(temp_content, encoding="utf-8")

            build_config = self.config_selector.currentText() if hasattr(self, "config_selector") else None

            # Show status that background compile is starting
            self.status_bar.set_status("⚡ Updating memory usage...")

            # Mark this as a background compile
            self._is_background_compile = True
            self._cli_current_operation = "compile"
            self._last_cli_error = ""
            self._compilation_output = ""
            # Clear previous problems before starting new compilation
            self.problems_panel.clear_problems()

            # Run silent background compilation (no verbose output, no export)
            self.cli_service.run_compile(
                str(temp_sketch),
                board.fqbn,
                config=build_config,
                verbose=False,
                export_binaries=False
            )

        except Exception as exc:
            # Silently ignore any errors in background compile
            self._is_background_compile = False
            self._cli_current_operation = None
            self.status_bar.set_status(f"Background compile error: {exc}")
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def _enrich_board_list(self, boards):
        """Replace lightweight CLI board stubs with full definitions when possible."""

        if not boards:
            return []

        enriched_boards = []
        cached_results = {}
        missing_definitions = []

        for board in boards:
            if not board:
                continue

            fqbn = getattr(board, "fqbn", "")
            if not fqbn:
                missing_definitions.append(getattr(board, "name", "<unknown>"))
                continue

            enriched_board = cached_results.get(fqbn)
            if enriched_board is None:
                enriched_board = self.board_manager.get_board(fqbn)
                if enriched_board:
                    cached_results[fqbn] = enriched_board
                else:
                    missing_definitions.append(fqbn)
                    continue

            enriched_boards.append(enriched_board)

        if missing_definitions:
            print(
                "DEBUG: Missing board definitions for: "
                + ", ".join(sorted(set(missing_definitions)))
            )

        return enriched_boards

    def _populate_boards(self):
        """Populate board selector with boards from arduino-cli.

        This method dynamically discovers boards from installed platforms using
        arduino-cli. Requires arduino-cli to be properly configured.
        """
        current_selection = (
            self.board_selector.currentText().strip()
            if hasattr(self, "board_selector") and self.board_selector.count() > 0
            else ""
        )

        self.board_selector.blockSignals(True)
        self.board_selector.clear()
        board_panel = getattr(self, "board_panel", None)

        # Get boards from arduino-cli (installed platforms only)
        boards = []
        try:
            boards = self.board_manager.get_boards_from_cli()
            print(f"DEBUG: get_boards_from_cli() returned {len(boards)} boards")
        except Exception as e:
            print(f"DEBUG: get_boards_from_cli() raised exception: {e}")

        # ``arduino-cli board list`` only reports connected hardware.  When the
        # IDE starts with no devices attached (the common case right after a
        # fresh platform install) we still need to populate the selector with
        # every board provided by the installed cores.  Fall back to parsing the
        # installed ``boards.txt`` files so the toolbar updates immediately.
        if not boards:
            try:
                boards = self.board_manager.get_all_boards()
                print(
                    "DEBUG: Falling back to get_all_boards(), "
                    f"discovered {len(boards)} boards"
                )
            except Exception as e:
                print(f"DEBUG: get_all_boards() raised exception: {e}")

        boards = self._enrich_board_list(boards)

        if boards:
            # Sort boards by name for better UX
            boards.sort(key=lambda b: b.name)

            self._cli_boards = boards
            if board_panel:
                board_panel.set_boards(self._cli_boards)

            # Add boards to selector
            for board in boards:
                self.board_selector.addItem(board.name)

            preferred_board_name = "Arduino Uno"
            preferred_index = self.board_selector.findText(preferred_board_name)

            # Try to restore previous selection when possible, but prefer Arduino Uno
            selected_board_name = current_selection if current_selection else boards[0].name
            index = preferred_index if preferred_index >= 0 else self.board_selector.findText(selected_board_name)
            if index < 0:
                index = 0
            self.board_selector.setCurrentIndex(index)

            self.status_bar.set_status(f"Loaded {len(boards)} boards from installed platforms")
        else:
            self._cli_boards = []
            if board_panel:
                board_panel.set_boards(self._cli_boards)
            # No installed platforms - show helpful message
            self.board_selector.addItem("No boards available - Install a platform first")
            self.status_bar.set_status("No boards found. Install a platform via Tools > Board Manager")

        self.board_selector.blockSignals(False)

        if boards:
            self.on_board_changed(self.board_selector.currentText())
        elif board_panel:
            board_panel.update_board_info(None)

    def _log_board_package_event(self, message: str, *, color: Optional[str] = None):
        """Write a message to the console if it is available."""

        if hasattr(self, "console_panel") and self.console_panel:
            self.console_panel.append_output(message, color=color)

    # ------------------------------------------------------------------
    # Board package change handling
    # ------------------------------------------------------------------
    def _on_board_package_installed(self, package_name: str, version: str):
        version_display = version or "latest"
        reason = f"{package_name} {version_display} installed"
        self._log_board_package_event(
            f"⬇️ Installed board package: {package_name} {version_display}"
        )
        self._schedule_board_list_refresh(reason)

    def _on_board_package_uninstalled(self, package_name: str):
        self._log_board_package_event(f"🗑️ Removed board package: {package_name}")
        self._schedule_board_list_refresh(f"{package_name} removed")

    def _on_board_package_updated(self, package_name: str, old_version: str, new_version: str):
        reason = f"{package_name} updated to {new_version}" if new_version else f"{package_name} updated"
        old_display = old_version or "?"
        new_display = new_version or "latest"
        self._log_board_package_event(
            f"🔄 Updated board package: {package_name} {old_display} → {new_display}"
        )
        self._schedule_board_list_refresh(reason)

    def _on_board_index_updated(self):
        self._schedule_board_list_refresh("index updated")

    def _schedule_board_list_refresh(self, reason: str):
        """Queue a refresh of the board selector after package changes."""

        self._board_list_refresh_reason = reason

        if self.cli_service.is_running():
            self._board_list_refresh_pending = True
            return

        self._start_board_list_refresh_timer()

    def _start_board_list_refresh_timer(self):
        """Start (or restart) the timer that performs the actual refresh."""

        self._board_list_refresh_pending = False
        if self._board_list_refresh_timer.isActive():
            self._board_list_refresh_timer.stop()
        self._board_list_refresh_timer.start(300)

    def _perform_board_list_refresh(self):
        """Refresh the board selector and related panels after package changes."""

        reason = self._board_list_refresh_reason or "package change"

        if not hasattr(self, "board_selector"):
            self._board_list_refresh_pending = True
            QTimer.singleShot(300, self._start_board_list_refresh_timer)
            return

        self.status_bar.set_status(f"Refreshing boards ({reason})")

        try:
            self._populate_boards()
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))
        except Exception as exc:
            self._log_board_package_event(
                f"⚠️ Failed to refresh boards after {reason}: {exc}",
                color="#F48771"
            )
            self.status_bar.set_status("Board refresh failed")
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def _get_selected_board(self):
        """Get the currently selected board object from arduino-cli.

        Only boards from installed platforms (via arduino-cli) are supported.
        """
        board_name = self.board_selector.currentText().strip() if hasattr(self, "board_selector") else ""
        if not board_name:
            return None

        cli_boards = self._cli_boards
        if not cli_boards:
            try:
                cli_boards = self.board_manager.get_boards_from_cli()
            except Exception:
                cli_boards = []
            else:
                cli_boards = self._enrich_board_list(cli_boards)
            self._cli_boards = cli_boards

        for board in cli_boards:
            if board.name == board_name or board.fqbn == board_name:
                enriched_board = None
                fqbn = getattr(board, "fqbn", "")

                if fqbn:
                    try:
                        enriched_board = self.board_manager.get_board(fqbn)
                    except Exception:
                        enriched_board = None

                if enriched_board:
                    # Update cache so downstream consumers reuse enriched metadata
                    try:
                        index = cli_boards.index(board)
                        cli_boards[index] = enriched_board
                        self._cli_boards = cli_boards
                    except ValueError:
                        # Board might have been duplicated; append enriched definition
                        cli_boards.append(enriched_board)
                        self._cli_boards = cli_boards
                    return enriched_board

                return board

        return None

    def _on_board_panel_board_selected(self, board):
        """Synchronize toolbar selector when the side panel changes."""
        if not board or not hasattr(self, "board_selector") or not self.board_selector:
            return

        self.board_selector.blockSignals(True)
        try:
            index = self.board_selector.findText(board.name)
            if index < 0:
                self.board_selector.addItem(board.name)
                index = self.board_selector.count() - 1
            self.board_selector.setCurrentIndex(index)
        finally:
            self.board_selector.blockSignals(False)

        self.on_board_changed(board.name)

    def _get_selected_port(self):
        if not hasattr(self, "port_selector"):
            return None
        port_text = self.port_selector.currentText().strip()
        if not port_text or port_text == "No ports available":
            return None
        if " - " in port_text:
            return port_text.split(" - ", 1)[0].strip()
        return port_text

    def verify_sketch(self):
        """Verify/compile sketch"""
        current_widget = self.editor_tabs.currentWidget()
        if not current_widget or not hasattr(current_widget, "editor"):
            QMessageBox.warning(self, "Verify Sketch", "No sketch is currently open.")
            return

        if self.cli_service.is_running():
            QMessageBox.information(self, "Arduino CLI Busy", "Another command is currently running. Please wait for it to finish.")
            return

        index = self.editor_tabs.currentIndex()
        if current_widget.editor.document().isModified():
            choice = QMessageBox.question(
                self,
                "Save Sketch",
                "The sketch has unsaved changes. Save before verifying?",
                QMessageBox.Save | QMessageBox.Cancel,
                QMessageBox.Save
            )
            if choice == QMessageBox.Save:
                if not self.save_file(index=index):
                    return
            else:
                return

        if not getattr(current_widget, "file_path", None):
            if not self.save_file(index=index, save_as=True):
                return

        sketch_path = Path(current_widget.file_path)
        if not sketch_path.exists():
            QMessageBox.critical(self, "Verify Sketch", f"Sketch file not found: {sketch_path}")
            return

        board = self._get_selected_board()
        if not board:
            QMessageBox.warning(self, "Verify Sketch", "Please select a board before compiling.")
            return

        build_config = self.config_selector.currentText() if hasattr(self, "config_selector") else None

        self.console_panel.append_output(
            f"Compiling {sketch_path.name} for {board.name} ({board.fqbn})..."
        )
        if build_config:
            self.console_panel.append_output(f"Using configuration: {build_config}")
        self.status_bar.set_status("Compiling...")
        self._cli_current_operation = "compile"
        self._last_cli_error = ""
        self._compilation_output = ""
        # Clear previous problems before starting new compilation
        self.problems_panel.clear_problems()

        try:
            # User-initiated verify: optional verbose output controlled by preferences
            self.cli_service.run_compile(
                str(sketch_path),
                board.fqbn,
                config=build_config,
                verbose=self._is_compile_verbose_enabled(),
                export_binaries=True  # Export binaries to sketch folder like official IDE
            )
        except (RuntimeError, FileNotFoundError) as exc:
            self._cli_current_operation = None
            self.console_panel.append_output(f"✗ {exc}", color="#F48771")
            self.status_bar.set_status("Compilation Failed")
            QMessageBox.critical(self, "Verify Sketch", str(exc))
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def upload_sketch(self):
        """Upload sketch to board (compiles first, then uploads)"""
        current_widget = self.editor_tabs.currentWidget()
        if not current_widget or not hasattr(current_widget, "editor"):
            QMessageBox.warning(self, "Upload Sketch", "No sketch is currently open.")
            self._open_monitor_after_upload = False
            return

        if self.cli_service.is_running():
            QMessageBox.information(self, "Arduino CLI Busy", "Another command is currently running. Please wait for it to finish.")
            self._open_monitor_after_upload = False
            return

        index = self.editor_tabs.currentIndex()
        if current_widget.editor.document().isModified():
            choice = QMessageBox.question(
                self,
                "Save Sketch",
                "The sketch has unsaved changes. Save before uploading?",
                QMessageBox.Save | QMessageBox.Cancel,
                QMessageBox.Save
            )
            if choice == QMessageBox.Save:
                if not self.save_file(index=index):
                    self._open_monitor_after_upload = False
                    return
            else:
                self._open_monitor_after_upload = False
                return

        if not getattr(current_widget, "file_path", None):
            if not self.save_file(index=index, save_as=True):
                self._open_monitor_after_upload = False
                return

        sketch_path = Path(current_widget.file_path)
        if not sketch_path.exists():
            QMessageBox.critical(self, "Upload Sketch", f"Sketch file not found: {sketch_path}")
            self._open_monitor_after_upload = False
            return

        board = self._get_selected_board()
        if not board:
            QMessageBox.warning(self, "Upload Sketch", "Please select a board before uploading.")
            self._open_monitor_after_upload = False
            return

        port = self._get_selected_port()
        if not port:
            QMessageBox.warning(self, "Upload Sketch", "Please select a serial port before uploading.")
            self._open_monitor_after_upload = False
            return

        # Step 1: Compile first (verify)
        build_config = self.config_selector.currentText() if hasattr(self, "config_selector") else None

        self.power_analyzer_service.start_upload_session(
            board=board,
            port=port,
            sketch_path=str(sketch_path),
            metadata={"trigger": "manual_upload"},
        )
        self.power_analyzer_service.update_stage(PowerSessionStage.COMPILE)

        self.console_panel.append_output(
            f"Step 1: Compiling {sketch_path.name} for {board.name}...",
            color="#6A9955"
        )
        if build_config:
            self.console_panel.append_output(f"Using configuration: {build_config}")
        self.status_bar.set_status("Compiling (before upload)...")
        self._cli_current_operation = "compile"
        self._last_cli_error = ""
        self._compilation_output = ""
        self._upload_after_compile = True  # Flag to trigger upload after compile
        # Clear previous problems before starting new compilation
        self.problems_panel.clear_problems()

        try:
            # Upload requires compilation first: export binaries for upload
            self.cli_service.run_compile(
                str(sketch_path),
                board.fqbn,
                config=build_config,
                verbose=self._is_compile_verbose_enabled(),
                export_binaries=True  # Export binaries for upload
            )
        except (RuntimeError, FileNotFoundError) as exc:
            self._cli_current_operation = None
            self._upload_after_compile = False
            self.console_panel.append_output(f"✗ {exc}", color="#F48771")
            self.status_bar.set_status("Compilation Failed")
            QMessageBox.critical(self, "Upload Sketch", f"Compilation failed: {exc}")
            self.power_analyzer_service.abort_active_session("compile_exception")
            self._open_monitor_after_upload = False
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def _do_upload(self):
        """Perform the actual upload after successful compilation"""
        current_widget = self.editor_tabs.currentWidget()
        if not current_widget or not hasattr(current_widget, "file_path"):
            return

        sketch_path = Path(current_widget.file_path)
        board = self._get_selected_board()
        port = self._get_selected_port()

        if not sketch_path.exists() or not board or not port:
            self.console_panel.append_output(
                "✗ Upload cancelled: missing sketch, board, or port",
                color="#F48771"
            )
            self.power_analyzer_service.abort_active_session("upload_prerequisite_missing")
            self._open_monitor_after_upload = False
            return

        # Step 2: Upload
        self.console_panel.append_output(
            f"Step 2: Uploading {sketch_path.name} to {board.name} via {port}...",
            color="#6A9955"
        )
        self.status_bar.set_status("Uploading...")
        self._cli_current_operation = "upload"
        self._last_cli_error = ""

        self.power_analyzer_service.update_stage(PowerSessionStage.UPLOAD)

        try:
            self.cli_service.run_upload(str(sketch_path), board.fqbn, port)
        except (RuntimeError, FileNotFoundError) as exc:
            self._cli_current_operation = None
            self.console_panel.append_output(f"✗ {exc}", color="#F48771")
            self.status_bar.set_status("Upload Failed")
            QMessageBox.critical(self, "Upload Sketch", str(exc))
            self.power_analyzer_service.abort_active_session("upload_exception")
            self._open_monitor_after_upload = False
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def toggle_serial_monitor(self):
        """Show/hide serial monitor"""
        # Switch to Serial Monitor tab
        serial_index = self.bottom_tabs.indexOf(self.serial_monitor)
        if serial_index >= 0:
            self.bottom_tabs.setCurrentIndex(serial_index)

    def toggle_status_display(self):
        """Show/hide real-time status display"""
        if self.status_display.isVisible():
            self.status_display.hide()
        else:
            self.status_display.show()

    def toggle_plotter(self):
        """Show/hide serial plotter"""
        # Switch to Plotter tab
        plotter_index = self.bottom_tabs.indexOf(self.plotter_panel)
        if plotter_index >= 0:
            self.bottom_tabs.setCurrentIndex(plotter_index)

    def _on_bottom_tab_changed(self, index):
        """Update contextual help when the bottom tab selection changes."""

        if not hasattr(self, "serial_monitor"):
            return

        widget = self.bottom_tabs.widget(index) if index >= 0 else None
        self._broadcast_serial_monitor_state(widget is self.serial_monitor)

    def _broadcast_serial_monitor_state(self, is_open: bool):
        """Notify all editors about the Serial Monitor visibility."""

        self._serial_monitor_open = bool(is_open)
        for i in range(self.editor_tabs.count()):
            container = self.editor_tabs.widget(i)
            if not container:
                continue

            editor = getattr(container, "editor", None)
            if editor:
                editor.set_serial_monitor_open(self._serial_monitor_open)

    def _is_serial_monitor_active(self) -> bool:
        """Return True if the Serial Monitor tab is currently selected."""

        return (
            hasattr(self, "serial_monitor")
            and self.bottom_tabs.currentWidget() is self.serial_monitor
        )

    def show_find_dialog(self):
        """Show find/replace dialog"""
        # Get current editor
        current_widget = self.editor_tabs.currentWidget()
        if current_widget:
            editor = current_widget.editor

            # Create find/replace dialog if it doesn't exist
            if not hasattr(self, 'find_replace_dialog') or self.find_replace_dialog is None:
                self.find_replace_dialog = FindReplaceDialog(editor, self)
            else:
                # Update the editor reference
                self.find_replace_dialog.editor = editor

            # If text is selected, use it as the find text
            cursor = editor.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText()
                self.find_replace_dialog.set_find_text(selected_text)

            # Show the dialog
            self.find_replace_dialog.show()
            self.find_replace_dialog.raise_()
            self.find_replace_dialog.activateWindow()

    def insert_snippet(self, snippet):
        """Insert a code snippet into the current editor"""
        current_widget = self.editor_tabs.currentWidget()
        if not current_widget:
            return

        editor = current_widget.editor
        cursor = editor.textCursor()

        # Get snippet text and cursor position
        text, cursor_offset = snippet.insert_text()

        # Insert the snippet
        cursor.insertText(text)

        # Position cursor at the placeholder location
        if cursor_offset > 0:
            # Move cursor back by offset
            for _ in range(cursor_offset):
                cursor.movePosition(QTextCursor.Left)
            editor.setTextCursor(cursor)

    def show_about(self):
        """Show about dialog"""
        from PySide6.QtCore import Qt, QUrl
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtWidgets import QLabel, QMessageBox

        from arduino_ide.config import (
            ABOUT_CREDITS,
            APP_AUTHORS,
            APP_DESCRIPTION,
            APP_NAME,
            APP_SOURCE_REPO,
            APP_VERSION,
            APP_WEBSITE,
        )

        about_dialog = QMessageBox(self)
        about_dialog.setIcon(QMessageBox.Information)
        about_dialog.setWindowTitle(f"About {APP_NAME}")
        about_dialog.setStandardButtons(QMessageBox.Close)
        about_dialog.setDefaultButton(QMessageBox.Close)
        about_dialog.setTextFormat(Qt.RichText)

        credits_html = "".join(f"<li>{credit}</li>" for credit in ABOUT_CREDITS)
        authors = ", ".join(APP_AUTHORS)
        about_dialog.setText(
            """
            <div style="min-width: 320px;">
                <h2 style="margin-bottom: 4px;">{name}</h2>
                <p style="margin: 0 0 8px 0;"><strong>Version:</strong> {version}</p>
                <p style="margin: 0 0 12px 0;">{description}</p>
                <p style="margin: 0 0 8px 0;"><strong>Credits</strong></p>
                <ul style="margin-top: 0; padding-left: 18px;">{credits}</ul>
                <p style="margin: 12px 0 4px 0;">
                    <strong>Project Links</strong><br>
                    <a href="{website}">Official website</a><br>
                    <a href="{repository}">Source repository</a>
                </p>
                <p style="margin: 12px 0 0 0;">Maintained by {authors}</p>
            </div>
            """.format(
                name=APP_NAME,
                version=APP_VERSION,
                description=APP_DESCRIPTION,
                credits=credits_html or "<li>No credits listed.</li>",
                website=APP_WEBSITE,
                repository=APP_SOURCE_REPO,
                authors=authors,
            )
        )

        about_dialog.setTextInteractionFlags(
            Qt.TextBrowserInteraction
            | Qt.LinksAccessibleByMouse
            | Qt.TextSelectableByMouse
        )

        label = about_dialog.findChild(QLabel, "qt_msgbox_label")
        if label is not None:
            label.setOpenExternalLinks(True)
            label.setTextInteractionFlags(
                Qt.TextBrowserInteraction
                | Qt.LinksAccessibleByMouse
                | Qt.TextSelectableByMouse
            )

        def open_link(url: str) -> None:
            QDesktopServices.openUrl(QUrl(url))

        about_dialog.linkActivated.connect(open_link)
        about_dialog.exec()

    def show_onboarding_wizard(self):
        """Launch the onboarding wizard dialog."""
        if self.onboarding_wizard is None:
            self.onboarding_wizard = OnboardingWizard(self)
        self.onboarding_wizard.show()
        self.onboarding_wizard.raise_()
        self.onboarding_wizard.activateWindow()

    def on_board_changed(self, board_name):
        """Handle board selection change"""
        if not board_name:
            return

        self.status_bar.set_status(f"Board changed to: {board_name}")
        if self.console_panel:
            self.console_panel.append_output(f"Selected board: {board_name}")

        board = self._get_selected_board()
        if board:
            if self.board_panel:
                self.board_panel.select_board(board)
            if self.pin_usage_panel:
                self.pin_usage_panel.set_board(board)
                self.update_pin_usage()

        # Update board panel with Board object
        if self.board_panel:
            self.board_panel.update_board_info(board)
        # Update status display with new board specs
        if self.status_display:
            self.status_display.update_board(board_name)
            self._trigger_board_memory_refresh()
        # Update status bar
        self.status_bar.set_board(board_name)
        # Reset to Ready after a moment
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

        self._sync_profiler_context()
        self._schedule_cicd_refresh()

    def on_port_changed(self, port_name):
        """Handle port selection change"""
        if port_name:
            # Only log to console if port actually changed
            if port_name != self._last_selected_port:
                self.status_bar.set_status(f"Port changed to: {port_name}")
                if self.console_panel:
                    self.console_panel.append_output(f"Selected port: {port_name}")
                self._last_selected_port = port_name
            # Update status bar
            self.status_bar.set_port(port_name)
            # Check if port is actually available (not "No ports available")
            is_connected = port_name != "No ports available" and " - " in port_name
            self.status_bar.set_connection_status(is_connected)
            # Reset to Ready after a moment
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

        self._sync_profiler_context()

    def on_config_changed(self, config):
        """Handle build configuration change"""
        self.build_config = config
        self.status_bar.set_status(f"Build configuration: {config}")
        if self.console_panel:
            self.console_panel.append_output(f"Build configuration changed to: {config}")
        # Reset to Ready after a moment
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def refresh_ports(self):
        """Refresh available serial ports"""
        current_port = self.port_selector.currentText() if hasattr(self, 'port_selector') else None

        # Get list of available ports
        ports = serial.tools.list_ports.comports()
        port_list = [f"{port.device} - {port.description}" for port in ports]

        # Update combo box
        if hasattr(self, 'port_selector'):
            self.port_selector.clear()
            if port_list:
                self.port_selector.addItems(port_list)
                # Try to restore previous selection
                if current_port:
                    index = self.port_selector.findText(current_port)
                    if index >= 0:
                        self.port_selector.setCurrentIndex(index)
            else:
                self.port_selector.addItem("No ports available")

        return port_list

    def setup_port_refresh(self):
        """Setup automatic port refresh timer"""
        self.port_refresh_timer = QTimer(self)
        self.port_refresh_timer.timeout.connect(self.refresh_ports)
        # Refresh ports every 3 seconds
        self.port_refresh_timer.start(3000)

    def upload_and_monitor(self):
        """Upload sketch and open serial monitor"""
        self.console_panel.append_output("Uploading sketch and opening serial monitor...")
        self._open_monitor_after_upload = True
        self.upload_sketch()
        # Serial monitor will be shown after a successful upload
        serial_index = self.bottom_tabs.indexOf(self.serial_monitor)
        if serial_index >= 0:
            self.bottom_tabs.setCurrentIndex(serial_index)
        self.status_bar.set_status("Upload complete - Serial monitor opened")
        # Reset to Ready after a moment
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def show_examples(self):
        """Show examples menu/dialog"""
        examples_menu = QMenu(self)

        # Basic examples
        basic_menu = examples_menu.addMenu("01.Basics")
        basic_menu.addAction("Blink").triggered.connect(lambda: self.load_example("Blink"))
        basic_menu.addAction("AnalogReadSerial").triggered.connect(lambda: self.load_example("AnalogReadSerial"))
        basic_menu.addAction("DigitalReadSerial").triggered.connect(lambda: self.load_example("DigitalReadSerial"))

        # Digital examples
        digital_menu = examples_menu.addMenu("02.Digital")
        digital_menu.addAction("Button").triggered.connect(lambda: self.load_example("Button"))
        digital_menu.addAction("Debounce").triggered.connect(lambda: self.load_example("Debounce"))
        digital_menu.addAction("StateChangeDetection").triggered.connect(lambda: self.load_example("StateChangeDetection"))

        # Analog examples
        analog_menu = examples_menu.addMenu("03.Analog")
        analog_menu.addAction("AnalogInput").triggered.connect(lambda: self.load_example("AnalogInput"))
        analog_menu.addAction("Fading").triggered.connect(lambda: self.load_example("Fading"))
        analog_menu.addAction("Smoothing").triggered.connect(lambda: self.load_example("Smoothing"))

        # Communication examples
        comm_menu = examples_menu.addMenu("04.Communication")
        comm_menu.addAction("SerialEvent").triggered.connect(lambda: self.load_example("SerialEvent"))
        comm_menu.addAction("SerialPassthrough").triggered.connect(lambda: self.load_example("SerialPassthrough"))

        # Show menu at cursor position
        examples_menu.exec_(QCursor.pos())

    def show_libraries(self):
        """Show libraries menu/dialog"""
        libraries_menu = QMenu(self)

        manage_action = libraries_menu.addAction("Manage Libraries...")
        manage_action.triggered.connect(self.open_library_manager)

        library_examples = self.library_manager.get_installed_library_examples()
        if library_examples:
            separator_action = libraries_menu.addSeparator()
            has_examples = False

            for library_name, example_ids in library_examples.items():
                submenu = libraries_menu.addMenu(library_name)
                if self._populate_library_examples_menu(submenu, library_name, example_ids):
                    has_examples = True
                else:
                    libraries_menu.removeAction(submenu.menuAction())

            if not has_examples:
                libraries_menu.removeAction(separator_action)
                placeholder = libraries_menu.addAction("No library examples found")
                placeholder.setEnabled(False)
        else:
            placeholder = libraries_menu.addAction("No library examples found")
            placeholder.setEnabled(False)

        # Show menu at cursor position
        libraries_menu.exec_(QCursor.pos())

    def _populate_library_examples_menu(
        self,
        menu: QMenu,
        library_name: str,
        example_ids: List[str],
    ) -> bool:
        """Populate ``menu`` with the examples belonging to ``library_name``."""

        tree: Dict[str, Dict] = {}
        for identifier in example_ids:
            parts = [part for part in identifier.split("/") if part]
            if not parts:
                continue

            node = tree
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node.setdefault("__examples__", set()).add(parts[-1])

        return self._build_example_menu_tree(menu, library_name, tree, [])

    def _build_example_menu_tree(
        self,
        menu: QMenu,
        library_name: str,
        node: Dict[str, Dict],
        prefix: List[str],
    ) -> bool:
        """Recursively convert ``node`` into nested menus and actions."""

        has_entries = False

        child_folders = [key for key in node.keys() if key != "__examples__"]
        for folder_name in sorted(child_folders, key=str.lower):
            submenu = menu.addMenu(folder_name)
            if self._build_example_menu_tree(submenu, library_name, node[folder_name], prefix + [folder_name]):
                has_entries = True
            else:
                menu.removeAction(submenu.menuAction())

        for example_name in sorted(node.get("__examples__", []), key=str.lower):
            request_parts = prefix + [example_name]
            request = "/".join(request_parts)
            action = menu.addAction(example_name)
            action.triggered.connect(partial(self.load_library_example, library_name, request))
            has_entries = True

        return has_entries

    def load_example(self, example_name):
        """Load an example sketch"""
        self.console_panel.append_output(f"Loading example: {example_name}")
        self.status_bar.set_status(f"Loading example: {example_name}")

        # Create example templates
        examples = {
            "Blink": """// Blink Example
// Turns an LED on for one second, then off for one second, repeatedly

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(1000);
  digitalWrite(LED_BUILTIN, LOW);
  delay(1000);
}
""",
            "AnalogReadSerial": """// AnalogReadSerial Example
// Reads an analog input and prints the value to the serial monitor

void setup() {
  Serial.begin(9600);
}

void loop() {
  int sensorValue = analogRead(A0);
  Serial.println(sensorValue);
  delay(1);
}
""",
            "DigitalReadSerial": """// DigitalReadSerial Example
// Reads a digital input and prints "H" or "L" to the serial monitor

int pushButton = 2;

void setup() {
  Serial.begin(9600);
  pinMode(pushButton, INPUT);
}

void loop() {
  int buttonState = digitalRead(pushButton);
  Serial.println(buttonState);
  delay(1);
}
""",
            "Button": """// Button Example
// Turns on an LED when pressing a button

const int buttonPin = 2;
const int ledPin = 13;

int buttonState = 0;

void setup() {
  pinMode(ledPin, OUTPUT);
  pinMode(buttonPin, INPUT);
}

void loop() {
  buttonState = digitalRead(buttonPin);

  if (buttonState == HIGH) {
    digitalWrite(ledPin, HIGH);
  } else {
    digitalWrite(ledPin, LOW);
  }
}
"""
        }

        # Get example code or use default
        board_name = "Unknown board"
        if hasattr(self, "board_selector") and self.board_selector:
            current_text = self.board_selector.currentText().strip()
            if current_text:
                board_name = current_text

        example_code = examples.get(
            example_name,
            build_missing_example_template(example_name, board_name),
        )

        # Create new editor with example
        editor_container = self.create_new_editor(f"{example_name}.ino")
        editor_container.set_content(example_code)

        # Update pin usage for the example
        self.update_pin_usage()

        # Reset to Ready after a moment
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def load_library_example(self, library_name, example_name):
        """Load a library example sketch"""
        message = f"Loading library example: {library_name}/{example_name}"
        self.console_panel.append_output(message)
        self.status_bar.set_status(f"Loading example: {library_name}/{example_name}")

        example_path = self.library_manager.get_example_sketch_path(library_name, example_name)
        if not example_path:
            error_msg = (
                f"Example '{example_name}' not found in library '{library_name}'."
            )
            self.console_panel.append_output(error_msg, color="#F48771")
            self.status_bar.set_status(
                f"Error loading {library_name}/{example_name}"
            )
            QMessageBox.warning(self, "Example Not Found", error_msg)
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))
            return

        try:
            with open(example_path, "r", encoding="utf-8") as sketch_file:
                example_code = sketch_file.read()
        except OSError as exc:
            error_msg = (
                f"Failed to read example '{library_name}/{example_name}': {exc}"
            )
            self.console_panel.append_output(error_msg, color="#F48771")
            self.status_bar.set_status(
                f"Error loading {library_name}/{example_name}"
            )
            QMessageBox.critical(self, "Error Loading Example", error_msg)
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))
            return

        self.create_new_editor(
            example_path.name,
            file_path=str(example_path),
            content=example_code,
            mark_clean=True,
        )

        success_message = f"Loaded library example from {example_path}"
        self.console_panel.append_output(success_message)
        self.status_bar.set_status(f"Loaded: {library_name}/{example_name}")
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def open_library_manager(self):
        """Open library manager dialog"""
        self.console_panel.append_output("Opening Library Manager...")
        self.status_bar.set_status("Library Manager")

        dialog = LibraryManagerDialog(self.library_manager, self)
        dialog.exec_()

        self.status_bar.set_status("Ready")

    def open_preferences(self):
        """Open the preferences dialog and apply any changes."""

        self.console_panel.append_output("Opening Preferences...")
        self.status_bar.set_status("Preferences")
        previous = self._is_compile_verbose_enabled()
        dialog = PreferencesDialog(self.settings, self)
        if dialog.exec_():
            self._compile_verbose_enabled = dialog.verbose_compile_enabled
            if previous != self._compile_verbose_enabled:
                state = "enabled" if self._compile_verbose_enabled else "disabled"
                self.console_panel.append_output(
                    f"Verbose compilation output {state}."
                )
        self.status_bar.set_status("Ready")

    def open_board_manager(self):
        """Open board manager dialog"""
        self.console_panel.append_output("Opening Board Manager...")
        self.status_bar.set_status("Board Manager")

        dialog = BoardManagerDialog(self.board_manager, self)

        # Connect board selection signal
        dialog.board_selected.connect(self.on_board_selected_from_manager)

        dialog.exec_()

        self.status_bar.set_status("Ready")

    def open_code_quality(self):
        """Open code quality analysis dialog"""
        self.status_bar.set_status("Code Quality")

        # Create dialog if it doesn't exist or was closed
        if not self.code_quality_panel:
            self.code_quality_panel = CodeQualityPanel(self)

        # Get current code and analyze
        current_widget = self.editor_tabs.currentWidget()
        if current_widget and hasattr(current_widget, 'editor'):
            code_text = current_widget.editor.toPlainText()
        else:
            code_text = ""

        self.code_quality_panel.analyze_code(code_text)

        # Show the dialog (non-modal)
        self.code_quality_panel.show()
        self.code_quality_panel.raise_()
        self.code_quality_panel.activateWindow()

        self.status_bar.set_status("Ready")

    def show_power_analyzer_dialog(self):
        """Open the power consumption analyzer dialog."""

        self.status_bar.set_status("Power Analyzer")

        if not self.power_analyzer_dialog:
            self.power_analyzer_dialog = PowerAnalyzerDialog(self.power_analyzer_service, parent=self)

        active_session = self.power_analyzer_service.active_session
        if active_session and active_session.phase == PowerSessionPhase.UPLOAD:
            # An upload session is currently running; let it continue feeding data.
            pass
        elif not active_session:
            board = self._get_selected_board()
            port = self._get_selected_port() or ""
            metadata = {"source": "tools_menu"}
            self.power_analyzer_service.ensure_runtime_session(
                board=board,
                port=port,
                metadata=metadata,
                enable_estimation=True,
            )
            self.power_analyzer_service.update_stage(PowerSessionStage.RUNNING)

        self.power_analyzer_dialog.show()
        self.power_analyzer_dialog.raise_()
        self.power_analyzer_dialog.activateWindow()
        self.status_bar.set_status("Ready")

    def show_performance_profiler_dialog(self):
        """Open or focus the performance profiler dashboard."""

        self.status_bar.set_status("Performance Profiler")
        dialog = self._ensure_profiler_dialog()
        self._sync_profiler_context()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self.status_bar.set_status("Ready")

    def start_performance_profiling(self, mode: Optional[ProfileMode] = None):
        """Start a profiling session using the requested mode."""

        if getattr(self.performance_profiler_service, "profiling_active", False):
            QMessageBox.information(self, "Performance Profiler", "Profiling is already running.")
            return

        self._sync_profiler_context()
        profile_mode = mode or ProfileMode.HOST_BASED
        session_id = self.performance_profiler_service.start_profiling(profile_mode)
        if not session_id:
            QMessageBox.warning(
                self,
                "Performance Profiler",
                "Unable to start profiling. Verify that another session is not already active.",
            )
            return

        self._update_profiler_actions_state()

    def stop_performance_profiling(self):
        """Stop the currently running profiling session."""

        if not getattr(self.performance_profiler_service, "profiling_active", False):
            return

        session = self.performance_profiler_service.stop_profiling()
        if session and self.performance_profiler_dialog:
            self.performance_profiler_dialog.focus_session(session.session_id)

        self._update_profiler_actions_state()

    def export_current_profiling_session(self):
        """Export profiling metrics for the selected session."""

        if not self.performance_profiler_service.sessions:
            QMessageBox.information(self, "Performance Profiler", "No profiling sessions available to export.")
            return

        session_id: Optional[str] = None
        if self.performance_profiler_dialog and self.performance_profiler_dialog.current_session_id:
            session_id = self.performance_profiler_dialog.current_session_id
        elif getattr(self.performance_profiler_service, "current_session", None):
            session_id = self.performance_profiler_service.current_session.session_id
        elif self._last_completed_profiling_session_id:
            session_id = self._last_completed_profiling_session_id
        elif self._last_selected_profiler_session_id:
            session_id = self._last_selected_profiler_session_id
        else:
            session_id = next(iter(self.performance_profiler_service.sessions.keys()), None)

        if not session_id:
            QMessageBox.warning(
                self,
                "Performance Profiler",
                "No profiling session is selected for export.",
            )
            return

        default_name = f"{session_id}_profile.json"
        default_path = (self.performance_profiler_service.project_path / default_name).resolve()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profiling Report",
            str(default_path),
            "JSON Files (*.json)",
        )
        if not file_path:
            return

        output_path = self.performance_profiler_service.export_profiling_report(session_id, file_path)
        if not output_path:
            QMessageBox.warning(
                self,
                "Performance Profiler",
                "Failed to export profiling report for the selected session.",
            )
            return

        QMessageBox.information(
            self,
            "Performance Profiler",
            f"Profiling report saved to {output_path}",
        )

    def show_snippets_library(self):
        """Show code snippets library dialog"""
        # Create snippets dialog if it doesn't exist
        if not hasattr(self, 'snippets_dialog') or self.snippets_dialog is None:
            self.snippets_dialog = SnippetsLibraryDialog(self)
            # Connect snippet insert signal
            self.snippets_dialog.snippet_insert_requested.connect(self.insert_snippet)

        # Show the dialog
        self.snippets_dialog.show()
        self.snippets_dialog.raise_()
        self.snippets_dialog.activateWindow()

    def show_block_code_editor(self):
        """Show block code editor in standalone window"""
        # Create window if it doesn't exist
        if self.visual_programming_window is None:
            from PySide6.QtWidgets import QMainWindow

            # Create a standalone window
            self.visual_programming_window = QMainWindow(self)
            self.visual_programming_window.setWindowTitle("Block Code Editor")
            self.visual_programming_window.resize(1200, 800)

            # Create the visual programming editor
            editor = VisualProgrammingEditor(self.visual_programming_service)

            # Connect code generation signal to insert code into sketch
            editor.code_generated.connect(self.insert_generated_code)

            # Set as central widget
            self.visual_programming_window.setCentralWidget(editor)

        # Show the window
        self.visual_programming_window.show()
        self.visual_programming_window.raise_()
        self.visual_programming_window.activateWindow()

    def insert_generated_code(self, code: str):
        """Insert generated code from block editor into current sketch"""
        current_widget = self.editor_tabs.currentWidget()
        if not current_widget or not hasattr(current_widget, 'editor'):
            QMessageBox.warning(
                self,
                "No Sketch Open",
                "Please open or create a sketch to insert the generated code."
            )
            return

        # Get the editor and insert the code
        editor = current_widget.editor
        cursor = editor.textCursor()

        # Insert the generated code at cursor position
        cursor.insertText(code)

        # Set the cursor to the editor
        editor.setTextCursor(cursor)

        # Mark the document as modified
        editor.document().setModified(True)

        # Show confirmation
        self.status_bar.set_status("Block code inserted into sketch")
        self.console_panel.append_output("Generated code inserted from Block Code Editor", color="#6A9955")
    def open_circuit_designer(self):
        """Open circuit designer window"""
        self.console_panel.append_output("Opening Circuit Designer...")
        self.status_bar.set_status("Circuit Designer")

        # Create window if it doesn't exist or was closed
        if self.circuit_designer_window is None or not self.circuit_designer_window.isVisible():
            self.circuit_designer_window = CircuitDesignerWindow(self.circuit_service, self)

        # Show and raise the window
        self.circuit_designer_window.show()
        self.circuit_designer_window.raise_()
        self.circuit_designer_window.activateWindow()

        self.status_bar.set_status("Circuit Designer Opened")
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def on_board_selected_from_manager(self, fqbn: str):
        """Handle board selection from board manager"""
        # Get board object
        board = self.board_manager.get_board(fqbn)
        if board:
            # Update board selector in toolbar
            # Find the board in the combo box or add it
            index = self.board_selector.findText(board.name)
            if index >= 0:
                self.board_selector.setCurrentIndex(index)
            else:
                self.board_selector.addItem(board.name)
                self.board_selector.setCurrentText(board.name)

            self.console_panel.append_output(f"Selected board: {board.name}")
            self.status_bar.update_board(board.name)

    def save_state(self):
        """Save window state (dock widgets only, not window geometry)"""
        # Don't save geometry - we always want to start maximized
        self.settings.setValue("windowState", self.saveState())

    def restore_state(self):
        """Restore window state (dock widgets only, not window geometry)"""
        # Clear any old saved geometry to prevent issues
        self.settings.remove("geometry")

        # Only restore dock widget state
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def _enforce_initial_maximize(self):
        """Force the main window to launch maximized on all platforms"""
        if self._initial_maximize_done:
            return

        if self._initial_maximize_attempts >= self._max_initial_maximize_attempts:
            self._initial_maximize_done = True
            return

        self._initial_maximize_attempts += 1
        self.showMaximized()

        if self.isMaximized():
            self._initial_maximize_done = True
        else:
            # Keep retrying briefly - some window managers ignore the request
            # the first few times while the window is still being constructed.
            QTimer.singleShot(100, self._enforce_initial_maximize)

    def closeEvent(self, event):
        """Handle window close"""
        self.save_state()
        event.accept()

    def _update_code_quality_panel(self):
        """Run static analysis on the current editor and refresh the panel."""
        # Only update if the dialog exists and is visible
        if not self.code_quality_panel or not self.code_quality_panel.isVisible():
            return

        current_widget = self.editor_tabs.currentWidget()
        if current_widget and hasattr(current_widget, 'editor'):
            code_text = current_widget.editor.toPlainText()
        else:
            code_text = ""
        self.code_quality_panel.analyze_code(code_text)

    def update_pin_usage(self):
        """Update pin usage overview from current editor"""
        current_widget = self.editor_tabs.currentWidget()
        if current_widget and hasattr(current_widget, 'editor'):
            code_text = current_widget.editor.toPlainText()
            self.pin_usage_panel.update_pin_usage(code_text)

    def update_status_display(self):
        """DEPRECATED: Now uses background compilation instead of estimates.

        This method is kept for backwards compatibility but does nothing.
        Memory usage is updated automatically via background compilation.
        """
        # No longer using estimation - background compilation updates memory
        pass

    # ------------------------------------------------------------------
    # Unit testing integration helpers
    # ------------------------------------------------------------------
    def _discover_unit_tests(self):
        if not self.unit_testing_panel:
            return
        self._update_unit_testing_target(force_discover=True)
        self.unit_testing_panel.discover_tests()

    def _run_all_unit_tests(self):
        if not self.unit_testing_panel:
            return
        self._update_unit_testing_target()
        self.unit_testing_panel.run_all_tests()

    def _run_selected_unit_tests(self):
        if not self.unit_testing_panel:
            return
        self._update_unit_testing_target()
        self.unit_testing_panel.run_selected()

    def _stop_unit_tests(self):
        if not self.unit_testing_panel:
            return
        self.unit_testing_panel.stop_tests()

    def _show_unit_testing_dialog(self):
        if not self.unit_testing_panel:
            return
        if not self.unit_testing_dialog:
            self.unit_testing_dialog = UnitTestingDialog(self.unit_testing_service, parent=self)
            self.unit_testing_panel = self.unit_testing_dialog.panel
            self._unit_testing_actions_linked = False
            self._sync_unit_testing_actions()
        self._update_unit_testing_target()
        self.unit_testing_dialog.show()
        self.unit_testing_dialog.raise_()
        self.unit_testing_dialog.activateWindow()

    def _show_hil_testing_dialog(self):
        if not self.hil_testing_dialog:
            self.hil_testing_dialog = HILTestingDialog(self.hil_testing_service, parent=self)
        self._update_hil_testing_project_path()
        self.hil_testing_dialog.show()
        self.hil_testing_dialog.raise_()
        self.hil_testing_dialog.activateWindow()

    def _determine_active_project_root(self) -> Optional[Path]:
        project_path = getattr(self.project_manager, "project_path", None)
        if project_path:
            return Path(project_path).resolve()

        current_widget = self.editor_tabs.currentWidget()
        file_path = getattr(current_widget, "file_path", None) if current_widget else None
        if file_path:
            return Path(file_path).resolve().parent

        return None

    def _determine_unit_testing_root(self) -> Optional[Path]:
        return self._determine_active_project_root()

    def _sync_profiler_context(self) -> None:
        root = self._determine_active_project_root()
        project_path = str(root) if root else ""
        if project_path:
            if str(self.performance_profiler_service.project_path) != project_path:
                self.performance_profiler_service.set_project_path(project_path)
        board_obj = self._get_selected_board()
        board_label = ""
        target_board = ""
        if board_obj:
            board_label = getattr(board_obj, "name", "") or getattr(board_obj, "fqbn", "")
            target_board = getattr(board_obj, "fqbn", "") or board_label
        elif hasattr(self, "board_selector"):
            board_label = self.board_selector.currentText().strip()
            target_board = board_label
        if target_board:
            self.performance_profiler_service.target_board = target_board

        port = self._get_selected_port() or ""
        self.performance_profiler_service.serial_port = port

        if self.performance_profiler_dialog:
            self.performance_profiler_dialog.update_context(project_path, board_label, port)

    def _ensure_profiler_dialog(self) -> PerformanceProfilerDialog:
        if not self.performance_profiler_dialog:
            self.performance_profiler_dialog = PerformanceProfilerDialog(
                self.performance_profiler_service,
                parent=self,
            )
            self.performance_profiler_dialog.start_requested.connect(self._on_profiler_start_requested)
            self.performance_profiler_dialog.stop_requested.connect(self._on_profiler_stop_requested)
            self.performance_profiler_dialog.export_requested.connect(self._on_profiler_export_requested)
            self.performance_profiler_dialog.location_requested.connect(self._navigate_to_source)
            self.performance_profiler_dialog.session_changed.connect(self._on_profiler_session_changed)
            self.performance_profiler_dialog.update_context(
                str(self.performance_profiler_service.project_path),
                getattr(self.board_selector, "currentText", lambda: "")(),
                self._get_selected_port() or "",
            )
            self.performance_profiler_dialog.set_profiling_active(
                getattr(self.performance_profiler_service, "profiling_active", False)
            )
        return self.performance_profiler_dialog

    def _on_profiler_start_requested(self, mode: ProfileMode) -> None:
        self.start_performance_profiling(mode)

    def _on_profiler_stop_requested(self) -> None:
        self.stop_performance_profiling()

    def _on_profiler_export_requested(self) -> None:
        self.export_current_profiling_session()

    def _on_profiler_session_changed(self, session_id: str) -> None:
        self._last_selected_profiler_session_id = session_id or None
        self._update_profiler_actions_state()

    def _on_profiler_session_started(self, session_id: str) -> None:
        self.status_bar.set_status("Profiling…")
        self._update_profiler_actions_state()
        if self.performance_profiler_dialog:
            self.performance_profiler_dialog.set_profiling_active(True)
            self.performance_profiler_dialog.focus_session(session_id)

    def _on_profiler_session_finished(self, session_id: str) -> None:
        self._last_completed_profiling_session_id = session_id
        self._last_selected_profiler_session_id = session_id
        self.status_bar.set_status("Profiling complete")
        self._update_profiler_actions_state()
        if self.performance_profiler_dialog:
            self.performance_profiler_dialog.set_profiling_active(False)
            self.performance_profiler_dialog.focus_session(session_id)
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def _update_profiler_actions_state(self) -> None:
        is_running = getattr(self.performance_profiler_service, "profiling_active", False)
        self.start_profiling_action.setEnabled(not is_running)
        self.stop_profiling_action.setEnabled(is_running)
        has_sessions = bool(self.performance_profiler_service.sessions or self._last_selected_profiler_session_id)
        self.export_profiling_action.setEnabled(has_sessions and not is_running)
        if self.performance_profiler_dialog:
            self.performance_profiler_dialog.set_profiling_active(is_running)

    def _update_unit_testing_target(self, *, force_discover=False):
        root = self._determine_unit_testing_root()
        if root:
            normalized = str(root)
            if str(self.hil_testing_service.project_path) != normalized:
                self.hil_testing_service.set_project_path(normalized)
        if not self.unit_testing_panel or not root:
            return

        normalized = str(root)
        path_changed = normalized != self._unit_testing_project_root

        if path_changed:
            self._unit_testing_project_root = normalized
            self.unit_testing_panel.set_project_path(normalized)

        if force_discover or path_changed:
            if getattr(self.unit_testing_service, "running", False):
                return
            self.unit_testing_panel.discover_tests()

    def _update_hil_testing_project_path(self):
        root = self._determine_unit_testing_root()
        if not root:
            return
        normalized = str(root)
        if str(self.hil_testing_service.project_path) != normalized:
            self.hil_testing_service.set_project_path(normalized)

    def _on_hil_session_started(self, fixture_name: str):
        self._hil_sessions_active.add(fixture_name)
        self._update_hil_unit_lock()

    def _on_hil_session_stopped(self, fixture_name: str):
        self._hil_sessions_active.discard(fixture_name)
        self._update_hil_unit_lock()

    def _on_hil_test_started(self, fixture_name: str, test_name: str):
        self._hil_tests_running.add(f"{fixture_name}:{test_name}")
        self._update_hil_unit_lock()
        if getattr(self, "status_bar", None) is not None:
            self.status_bar.set_status(f"HIL: Running {test_name} on {fixture_name}")

    def _on_hil_test_finished(self, fixture_name: str, result):
        key = f"{fixture_name}:{getattr(result, 'test_name', '')}"
        self._hil_tests_running.discard(key)
        passed = getattr(result, "passed", False)
        test_name = getattr(result, "test_name", "")
        failure_message = getattr(result, "failure_message", "")
        if getattr(self, "status_bar", None) is not None and test_name:
            summary = f"HIL: {test_name} {'passed' if passed else 'failed'}"
            if not passed and failure_message:
                summary += f" — {failure_message}"
            self.status_bar.set_status(summary)
            QTimer.singleShot(3000, lambda: self.status_bar.set_status("Ready"))
        self._update_hil_unit_lock()

    def _update_hil_unit_lock(self):
        self._lock_unit_testing_actions_from_hil(bool(self._hil_sessions_active or self._hil_tests_running))

    def _lock_unit_testing_actions_from_hil(self, locked: bool) -> None:
        actions = [
            self.discover_tests_action,
            self.run_all_tests_action,
            self.run_selected_tests_action,
        ]
        if self.unit_testing_panel:
            actions.extend(
                [
                    self.unit_testing_panel.discover_action,
                    self.unit_testing_panel.run_all_action,
                    self.unit_testing_panel.run_selected_action,
                ]
            )

        for action in actions:
            if not action:
                continue
            if locked:
                if not action.property("hil_locked"):
                    action.setProperty("hil_locked", True)
                    action.setProperty("hil_prev_enabled", action.isEnabled())
                    action.setEnabled(False)
            else:
                if action.property("hil_locked"):
                    prev_enabled = action.property("hil_prev_enabled")
                    action.setProperty("hil_locked", False)
                    action.setProperty("hil_prev_enabled", None)
                    if prev_enabled is None:
                        prev_enabled = action.isEnabled()
                    action.setEnabled(bool(prev_enabled))

        if not locked and self.unit_testing_panel:
            # Re-sync global actions with panel actions in case their state changed.
            self.discover_tests_action.setEnabled(self.unit_testing_panel.discover_action.isEnabled())
            self.run_all_tests_action.setEnabled(self.unit_testing_panel.run_all_action.isEnabled())
            self.run_selected_tests_action.setEnabled(self.unit_testing_panel.run_selected_action.isEnabled())

    def _sync_unit_testing_actions(self):
        if self._unit_testing_actions_linked or not self.unit_testing_panel:
            return

        def bind(source_action: QAction, target_action: QAction):
            if not source_action or not target_action:
                return
            target_action.setEnabled(source_action.isEnabled())
            source_action.changed.connect(
                lambda *, s=source_action, t=target_action: t.setEnabled(s.isEnabled())
            )

        bind(self.unit_testing_panel.discover_action, self.discover_tests_action)
        bind(self.unit_testing_panel.run_all_action, self.run_all_tests_action)
        bind(self.unit_testing_panel.run_selected_action, self.run_selected_tests_action)
        bind(self.unit_testing_panel.stop_action, self.stop_tests_action)

        self._unit_testing_actions_linked = True

        if self._hil_sessions_active or self._hil_tests_running:
            self._lock_unit_testing_actions_from_hil(True)

    def _handle_project_loaded(self, _project_name):
        self._update_unit_testing_target(force_discover=True)
        self._sync_profiler_context()

    def _handle_project_saved(self, _project_name):
        self._update_unit_testing_target(force_discover=True)
        self._sync_profiler_context()

    def _handle_project_dependencies_changed(self):
        self._update_unit_testing_target(force_discover=True)
        self._sync_profiler_context()

    def on_tab_changed(self, index):
        """Handle tab change - update pin usage and status for new tab"""
        if index >= 0:
            self.update_pin_usage()
            # Update status bar for new tab
            current_widget = self.editor_tabs.currentWidget()
            if current_widget and hasattr(current_widget, 'filename'):
                self.update_status_bar_for_file(current_widget.filename)
            self.update_cursor_position()
            self._update_code_quality_panel()

            # Trigger background compile for new tab (after a short delay)
            QTimer.singleShot(500, self._do_background_compile)
            self._update_unit_testing_target()
            self._sync_profiler_context()

    def update_cursor_position(self):
        """Update cursor position in status bar"""
        current_widget = self.editor_tabs.currentWidget()
        if current_widget and hasattr(current_widget, 'editor'):
            cursor = current_widget.editor.textCursor()
            line = cursor.blockNumber() + 1  # 1-based
            column = cursor.columnNumber() + 1  # 1-based
            self.status_bar.set_cursor_position(line, column)

    def update_status_bar_for_file(self, filename):
        """Update status bar language based on filename"""
        language = self.status_bar.detect_language_from_filename(filename)
        self.status_bar.set_language(language)

    def on_status_bar_board_clicked(self):
        """Handle clicks on the board section in status bar"""
        # Focus the board selector in the toolbar
        self.board_selector.setFocus()
        self.board_selector.showPopup()

    def on_status_bar_port_clicked(self):
        """Handle clicks on the port section in status bar"""
        # Refresh ports and focus the port selector
        self.refresh_ports()
        self.port_selector.setFocus()
        self.port_selector.showPopup()

    def initialize_status_bar(self):
        """Initialize status bar with default values"""
        # Set initial board
        self.status_bar.set_board(self.board_selector.currentText())
        # Set initial board for pin widget
        board = self._get_selected_board()
        if board:
            self.pin_usage_panel.set_board(board)

        # Set initial port
        current_port = self.port_selector.currentText()
        self.status_bar.set_port(current_port)

        # Set connection status
        is_connected = current_port != "No ports available" and " - " in current_port
        self.status_bar.set_connection_status(is_connected)

        # Set initial encoding
        self.status_bar.set_encoding("UTF-8")

        # Set initial language (will be updated when file is loaded)
        self.status_bar.set_language("C++")

        # Set initial status
        self.status_bar.set_status("Ready")
