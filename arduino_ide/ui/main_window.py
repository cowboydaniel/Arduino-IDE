"""
Main window for Arduino IDE Modern
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QTabWidget, QDockWidget,
    QComboBox, QLabel, QSizePolicy, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QSettings, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QIcon, QTextCursor, QGuiApplication, QCursor
import serial.tools.list_ports
from pathlib import Path

from arduino_ide.ui.code_editor import CodeEditor, BreadcrumbBar, CodeMinimap
from arduino_ide.ui.serial_monitor import SerialMonitor
from arduino_ide.ui.board_panel import BoardPanel
from arduino_ide.ui.project_explorer import ProjectExplorer
from arduino_ide.ui.console_panel import ConsolePanel
from arduino_ide.ui.variable_watch import VariableWatch
from arduino_ide.ui.status_display import StatusDisplay
from arduino_ide.ui.context_panel import ContextPanel
from arduino_ide.ui.plotter_panel import PlotterPanel
from arduino_ide.ui.problems_panel import ProblemsPanel
from arduino_ide.ui.output_panel import OutputPanel
from arduino_ide.ui.status_bar import StatusBar
from arduino_ide.ui.quick_actions_panel import QuickActionsPanel
from arduino_ide.ui.library_manager_dialog import LibraryManagerDialog
from arduino_ide.ui.board_manager_dialog import BoardManagerDialog
from arduino_ide.services.theme_manager import ThemeManager
from arduino_ide.services.library_manager import LibraryManager
from arduino_ide.services.board_manager import BoardManager
from arduino_ide.services.project_manager import ProjectManager
from arduino_ide.ui.example_templates import build_missing_example_template
from arduino_ide.services import ArduinoCliService
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

        # Initialize package managers
        self.library_manager = LibraryManager()
        self.board_manager = BoardManager()
        self.project_manager = ProjectManager(
            library_manager=self.library_manager,
            board_manager=self.board_manager
        )

        self.cli_service = ArduinoCliService(self)
        self.cli_service.output_received.connect(self._handle_cli_output)
        self.cli_service.error_received.connect(self._handle_cli_error)
        self.cli_service.finished.connect(self._handle_cli_finished)
        self._cli_current_operation = None
        self._last_cli_error = ""
        self._open_monitor_after_upload = False
        self._last_selected_port = None
        self._compilation_output = ""  # Store compilation output for parsing
        self._upload_after_compile = False  # Flag to trigger upload after successful compilation
        self._is_background_compile = False  # Flag to distinguish background vs user-initiated compile

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

        # Apply theme
        self.theme_manager.apply_theme("dark")

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

        # Left column (Quick Actions + Project Explorer)
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
        self.bottom_tabs.setMinimumHeight(150)
        left_area_layout.addWidget(self.bottom_tabs)

        # Add left area to main splitter
        central.addWidget(left_area)

        # Right column (Board/Watch/Status/Context) - full height
        self.right_column = QWidget()
        self.right_column_layout = QVBoxLayout(self.right_column)
        self.right_column_layout.setContentsMargins(0, 0, 0, 0)
        self.right_column_layout.setSpacing(0)
        self.right_column.setFixedWidth(300)

        # Add right column to main splitter
        central.addWidget(self.right_column)

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

        # View Menu
        view_menu = menubar.addMenu("&View")

        theme_menu = view_menu.addMenu("Theme")

        light_theme = QAction("Light", self)
        light_theme.triggered.connect(lambda: self.theme_manager.apply_theme("light"))
        theme_menu.addAction(light_theme)

        dark_theme = QAction("Dark", self)
        dark_theme.triggered.connect(lambda: self.theme_manager.apply_theme("dark"))
        theme_menu.addAction(dark_theme)

        high_contrast = QAction("High Contrast", self)
        high_contrast.triggered.connect(lambda: self.theme_manager.apply_theme("high_contrast"))
        theme_menu.addAction(high_contrast)

        # Debug Menu
        debug_menu = menubar.addMenu("&Debug")

        start_debug = QAction("Start Debugging", self)
        start_debug.setShortcut(Qt.Key_F5)
        debug_menu.addAction(start_debug)

        toggle_breakpoint = QAction("Toggle Breakpoint", self)
        toggle_breakpoint.setShortcut(Qt.Key_F9)
        debug_menu.addAction(toggle_breakpoint)

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        docs_action = QAction("Documentation", self)
        docs_action.setShortcut(Qt.Key_F1)
        help_menu.addAction(docs_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

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

        # Board selector
        main_toolbar.addWidget(QLabel("Board: "))
        self.board_selector = QComboBox()
        self.board_selector.setMinimumWidth(200)
        self.board_selector.addItems([
            "Arduino Uno",
            "Arduino Mega 2560",
            "Arduino Nano",
            "Arduino Leonardo",
            "Arduino Pro Mini",
            "ESP32 Dev Module",
            "ESP8266 NodeMCU",
            "Arduino Due"
        ])
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

    def create_dock_widgets(self):
        """Create panels (no dock widgets)"""
        # --- LEFT COLUMN (Normal widgets, NOT docks) ---
        # Create left-side panel widgets
        self.quick_actions_panel = QuickActionsPanel()
        self.project_explorer = ProjectExplorer()

        # Add widgets to left column layout (NOT as dock widgets)
        self.left_column_layout.addWidget(self.quick_actions_panel)
        self.left_column_layout.addWidget(self.project_explorer)
        self.project_explorer.file_open_requested.connect(self.open_file_from_project_explorer)

        # --- RIGHT COLUMN (Normal widgets, NOT docks) ---
        # Create right-side panel widgets
        self.board_panel = BoardPanel()
        self.variable_watch = VariableWatch()
        self.status_display = StatusDisplay()
        self.context_panel = ContextPanel()

        # Add widgets to right column layout (NOT as dock widgets)
        self.right_column_layout.addWidget(self.board_panel)
        self.right_column_layout.addWidget(self.variable_watch)
        self.right_column_layout.addWidget(self.status_display)
        self.right_column_layout.addWidget(self.context_panel)
        self.right_column_layout.addStretch()

        # --- BOTTOM TABS (Normal widgets in tabs, NOT docks) ---
        # Create bottom panels
        self.console_panel = ConsolePanel()
        self.serial_monitor = SerialMonitor()
        self.plotter_panel = PlotterPanel()
        self.problems_panel = ProblemsPanel()
        self.output_panel = OutputPanel()

        # Connect serial monitor data to plotter
        self.serial_monitor.data_received.connect(self.plotter_panel.append_output)

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

        editor_container.dirtyChanged.connect(
            lambda dirty, container=editor_container: self.on_editor_dirty_changed(container)
        )

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
        editor_container.mark_clean()
        self.update_tab_title(index)
        self.add_recent_file(path)
        self.update_status_bar_for_file(editor_container.filename)

    def open_file_from_project_explorer(self, file_path: str):
        """Open a file from the project explorer tree."""
        self._open_file_path(Path(file_path))

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

        self.add_recent_file(path)
        self.status_bar.set_status(f"Opened {path.name}")
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

        self.status_bar.set_status(f"Saved {path.name}")
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

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

    def _handle_cli_output(self, text):
        # Only show output for non-background compiles
        if not self._is_background_compile:
            self._append_console_stream(text)
        # Store compilation output for parsing memory usage
        if self._cli_current_operation == "compile":
            self._compilation_output += text

    def _handle_cli_error(self, text):
        if not text:
            return
        self._last_cli_error += text
        # Only show errors for non-background compiles
        if not self._is_background_compile:
            self._append_console_stream(text, color="#F48771")

    def _handle_cli_finished(self, exit_code):
        operation = self._cli_current_operation
        is_background = self._is_background_compile
        self._cli_current_operation = None
        self._is_background_compile = False

        if exit_code == 0:
            if operation == "compile":
                # Always parse and update memory usage on successful compile
                self._parse_and_update_memory_usage(self._compilation_output)

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
            else:
                if not is_background:
                    self.status_bar.set_status("Ready")
        else:
            # For background compiles, ALWAYS try to parse memory even with errors
            # This allows the memory monitor to update even when code has compilation errors
            if is_background and operation == "compile":
                self._parse_and_update_memory_usage(self._compilation_output)

            # Only show error dialogs and messages for non-background compiles
            if not is_background:
                detail = self._last_cli_error.strip() or "Check the console for details."
                if operation == "compile":
                    self.console_panel.append_output("✗ Compilation failed.", color="#F48771")
                    self.status_bar.set_status("Compilation Failed")
                    QMessageBox.critical(self, "Compilation Failed", detail)
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

            # Run silent compilation
            self.cli_service.run_compile(str(temp_sketch), board.fqbn, config=build_config)

        except Exception as exc:
            # Silently ignore any errors in background compile
            self._is_background_compile = False
            self._cli_current_operation = None
            self.status_bar.set_status(f"Background compile error: {exc}")
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def _get_selected_board(self):
        board_name = self.board_selector.currentText().strip() if hasattr(self, "board_selector") else ""
        if not board_name:
            return None
        boards = self.board_manager.search_boards(query=board_name)
        for board in boards:
            if board.name == board_name or board.fqbn == board_name:
                return board
        return self.board_manager.get_board(board_name)

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

        try:
            self.cli_service.run_compile(str(sketch_path), board.fqbn, config=build_config)
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

        self.console_panel.append_output(
            f"Step 1: Compiling {sketch_path.name} for {board.name}...",
            color="#6A9955"
        )
        if build_config:
            self.console_panel.append_output(f"Using configuration: {build_config}")
        self.status_bar.set_status("Compiling (before upload)...")
        self._cli_current_operation = "compile"
        self._last_cli_error = ""
        self._upload_after_compile = True  # Flag to trigger upload after compile

        try:
            self.cli_service.run_compile(str(sketch_path), board.fqbn, config=build_config)
        except (RuntimeError, FileNotFoundError) as exc:
            self._cli_current_operation = None
            self._upload_after_compile = False
            self.console_panel.append_output(f"✗ {exc}", color="#F48771")
            self.status_bar.set_status("Compilation Failed")
            QMessageBox.critical(self, "Upload Sketch", f"Compilation failed: {exc}")
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

        try:
            self.cli_service.run_upload(str(sketch_path), board.fqbn, port)
        except (RuntimeError, FileNotFoundError) as exc:
            self._cli_current_operation = None
            self.console_panel.append_output(f"✗ {exc}", color="#F48771")
            self.status_bar.set_status("Upload Failed")
            QMessageBox.critical(self, "Upload Sketch", str(exc))
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

    def show_find_dialog(self):
        """Show find/replace dialog"""
        # Get current editor
        current_widget = self.editor_tabs.currentWidget()
        if current_widget:
            editor = current_widget.editor
            # Show find dialog using Qt's built-in find functionality
            from PySide6.QtWidgets import QInputDialog, QMessageBox
            text, ok = QInputDialog.getText(self, "Find", "Find text:")
            if ok and text:
                # Search for text in the editor
                if not editor.find(text):
                    # If not found, try from the beginning
                    cursor = editor.textCursor()
                    cursor.movePosition(cursor.Start)
                    editor.setTextCursor(cursor)
                    if not editor.find(text):
                        QMessageBox.information(self, "Find", f"Text '{text}' not found.")

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

    def on_board_changed(self, board_name):
        """Handle board selection change"""
        self.status_bar.set_status(f"Board changed to: {board_name}")
        self.console_panel.append_output(f"Selected board: {board_name}")
        # Update board panel
        self.board_panel.update_board_info(board_name)
        # Update status display with new board specs
        self.status_display.update_board(board_name)
        # Update status bar
        self.status_bar.set_board(board_name)
        # Reset to Ready after a moment
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def on_port_changed(self, port_name):
        """Handle port selection change"""
        if port_name:
            # Only log to console if port actually changed
            if port_name != self._last_selected_port:
                self.status_bar.set_status(f"Port changed to: {port_name}")
                self.console_panel.append_output(f"Selected port: {port_name}")
                self._last_selected_port = port_name
            # Update status bar
            self.status_bar.set_port(port_name)
            # Check if port is actually available (not "No ports available")
            is_connected = port_name != "No ports available" and " - " in port_name
            self.status_bar.set_connection_status(is_connected)
            # Reset to Ready after a moment
            QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def on_config_changed(self, config):
        """Handle build configuration change"""
        self.build_config = config
        self.status_bar.set_status(f"Build configuration: {config}")
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

        # Popular libraries
        libraries_menu.addAction("Manage Libraries...").triggered.connect(self.open_library_manager)
        libraries_menu.addSeparator()

        # Quick access to common libraries
        servo_menu = libraries_menu.addMenu("Servo")
        servo_menu.addAction("Sweep Example").triggered.connect(lambda: self.load_library_example("Servo", "Sweep"))
        servo_menu.addAction("Knob Example").triggered.connect(lambda: self.load_library_example("Servo", "Knob"))

        stepper_menu = libraries_menu.addMenu("Stepper")
        stepper_menu.addAction("stepper_oneRevolution").triggered.connect(lambda: self.load_library_example("Stepper", "stepper_oneRevolution"))

        wifi_menu = libraries_menu.addMenu("WiFi")
        wifi_menu.addAction("WiFiScan").triggered.connect(lambda: self.load_library_example("WiFi", "WiFiScan"))
        wifi_menu.addAction("WiFiWebServer").triggered.connect(lambda: self.load_library_example("WiFi", "WiFiWebServer"))

        # Show menu at cursor position
        libraries_menu.exec_(QCursor.pos())

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

    def open_board_manager(self):
        """Open board manager dialog"""
        self.console_panel.append_output("Opening Board Manager...")
        self.status_bar.set_status("Board Manager")

        dialog = BoardManagerDialog(self.board_manager, self)

        # Connect board selection signal
        dialog.board_selected.connect(self.on_board_selected_from_manager)

        dialog.exec_()

        self.status_bar.set_status("Ready")

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

    def update_pin_usage(self):
        """Update pin usage overview from current editor"""
        current_widget = self.editor_tabs.currentWidget()
        if current_widget and hasattr(current_widget, 'editor'):
            code_text = current_widget.editor.toPlainText()
            self.board_panel.update_pin_usage(code_text)

    def update_status_display(self):
        """DEPRECATED: Now uses background compilation instead of estimates.

        This method is kept for backwards compatibility but does nothing.
        Memory usage is updated automatically via background compilation.
        """
        # No longer using estimation - background compilation updates memory
        pass

    def on_tab_changed(self, index):
        """Handle tab change - update pin usage and status for new tab"""
        if index >= 0:
            self.update_pin_usage()
            # Update status bar for new tab
            current_widget = self.editor_tabs.currentWidget()
            if current_widget and hasattr(current_widget, 'filename'):
                self.update_status_bar_for_file(current_widget.filename)
            self.update_cursor_position()

            # Trigger background compile for new tab (after a short delay)
            QTimer.singleShot(500, self._do_background_compile)

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
