"""
Main window for Arduino IDE Modern
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QTabWidget, QDockWidget,
    QComboBox, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, QSettings, QTimer, QWIDGETSIZE_MAX
from PySide6.QtGui import QAction, QKeySequence, QIcon, QTextCursor, QGuiApplication
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


class EditorContainer(QWidget):
    """Container widget that combines breadcrumb, editor, and minimap"""

    def __init__(self, filename="untitled.ino", project_name=None, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.project_name = project_name or self._derive_project_name(filename)
        self.setup_ui()

    def _derive_project_name(self, filename):
        """Derive project name from file path"""
        if filename and filename != "untitled.ino":
            # Get parent directory name as project name
            path = Path(filename)
            if path.is_absolute() and path.parent.name:
                return path.parent.name
        # Default to "My Project" for untitled or relative paths
        return "My Project"

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
        self.breadcrumb.update_breadcrumb(
            self.filename,
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

        # Ensure standard window chrome is available so desktop environments
        # show the minimize/maximize controls.  Some window managers (notably
        # GNOME on Wayland) will omit the maximize button unless the system
        # menu hint is explicitly enabled.
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setWindowFlag(Qt.WindowSystemMenuHint, True)

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

        # Current build configuration
        self.build_config = "Release"

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

        self.setCentralWidget(self.editor_tabs)

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
        """Create dockable panels"""
        # Quick Actions Panel (left)
        self.quick_actions_dock = QDockWidget("Quick Actions", self)
        self.quick_actions_dock.setObjectName("QuickActionsDock")
        self.quick_actions_panel = QuickActionsPanel()
        self.quick_actions_dock.setWidget(self.quick_actions_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.quick_actions_dock)

        # Project Explorer (left, tabbed with Quick Actions)
        self.project_dock = QDockWidget("Project Explorer", self)
        self.project_dock.setObjectName("ProjectExplorerDock")
        self.project_explorer = ProjectExplorer()
        self.project_dock.setWidget(self.project_explorer)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock)
        self.tabifyDockWidget(self.quick_actions_dock, self.project_dock)

        # Show Quick Actions by default
        self.quick_actions_dock.raise_()

        # Board Panel (right)
        self.board_dock = QDockWidget("Board Info", self)
        self.board_dock.setObjectName("BoardInfoDock")
        self.board_panel = BoardPanel()
        self.board_dock.setWidget(self.board_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.board_dock)

        # Variable Watch (right)
        self.watch_dock = QDockWidget("Variables", self)
        self.watch_dock.setObjectName("VariablesDock")
        self.variable_watch = VariableWatch()
        self.watch_dock.setWidget(self.variable_watch)
        self.addDockWidget(Qt.RightDockWidgetArea, self.watch_dock)

        # Status Display (right, tabbed with board panel)
        self.status_dock = QDockWidget("Real-time Status", self)
        self.status_dock.setObjectName("RealTimeStatusDock")
        self.status_display = StatusDisplay()
        self.status_dock.setWidget(self.status_display)
        self.addDockWidget(Qt.RightDockWidgetArea, self.status_dock)
        self.tabifyDockWidget(self.board_dock, self.status_dock)

        # Context Panel (right, tabbed with other panels)
        self.context_dock = QDockWidget("Context Help", self)
        self.context_dock.setObjectName("ContextHelpDock")
        self.context_panel = ContextPanel()
        self.context_dock.setWidget(self.context_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.context_dock)
        self.tabifyDockWidget(self.status_dock, self.context_dock)

        # Console Panel (bottom)
        self.console_dock = QDockWidget("Console", self)
        self.console_dock.setObjectName("ConsoleDock")
        self.console_panel = ConsolePanel()
        self.console_dock.setWidget(self.console_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.console_dock)

        # Serial Monitor (bottom, tabbed with console)
        self.serial_dock = QDockWidget("Serial Monitor", self)
        self.serial_dock.setObjectName("SerialMonitorDock")
        self.serial_monitor = SerialMonitor()
        self.serial_dock.setWidget(self.serial_monitor)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.serial_dock)
        self.tabifyDockWidget(self.console_dock, self.serial_dock)

        # Plotter (bottom, tabbed)
        self.plotter_dock = QDockWidget("Plotter", self)
        self.plotter_dock.setObjectName("PlotterDock")
        self.plotter_panel = PlotterPanel()
        self.plotter_dock.setWidget(self.plotter_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.plotter_dock)
        self.tabifyDockWidget(self.serial_dock, self.plotter_dock)

        # Connect serial monitor data to plotter
        self.serial_monitor.data_received.connect(self.plotter_panel.append_output)

        # Problems (bottom, tabbed)
        self.problems_dock = QDockWidget("Problems", self)
        self.problems_dock.setObjectName("ProblemsDock")
        self.problems_panel = ProblemsPanel()
        self.problems_dock.setWidget(self.problems_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.problems_dock)
        self.tabifyDockWidget(self.plotter_dock, self.problems_dock)

        # Output (bottom, tabbed)
        self.output_dock = QDockWidget("Output", self)
        self.output_dock.setObjectName("OutputDock")
        self.output_panel = OutputPanel()
        self.output_dock.setWidget(self.output_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.output_dock)
        self.tabifyDockWidget(self.problems_dock, self.output_dock)

        # Show console by default
        self.console_dock.raise_()

        bottom_docks = [
            self.console_dock,
            self.serial_dock,
            self.plotter_dock,
            self.problems_dock,
            self.output_dock,
        ]

        screen = QGuiApplication.primaryScreen()
        if screen:
            available_height = screen.availableGeometry().height()
            max_bottom_height = max(int(available_height * 0.4), 240)
            dock_min_height = max(100, int(max_bottom_height / len(bottom_docks)))
        else:
            max_bottom_height = 300
            dock_min_height = 120

        for dock in bottom_docks:
            dock.setMinimumHeight(dock_min_height)

        if screen:
            self.resizeDocks([self.console_dock], [max_bottom_height], Qt.Vertical)

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

    def create_new_editor(self, filename="untitled.ino"):
        """Create a new editor tab"""
        editor_container = EditorContainer(filename)

        # Set default Arduino template
        if filename.endswith(".ino"):
            editor_container.editor.setPlainText(self.get_arduino_template())

        # Connect editor changes to pin usage update and status display
        editor_container.editor.textChanged.connect(self.update_pin_usage)
        editor_container.editor.textChanged.connect(self.update_status_display)

        # Connect cursor position changes to status bar
        editor_container.editor.cursorPositionChanged.connect(self.update_cursor_position)

        # Connect function clicks to context panel
        editor_container.editor.function_clicked.connect(self.context_panel.update_context)

        index = self.editor_tabs.addTab(editor_container, filename)
        self.editor_tabs.setCurrentIndex(index)

        # Initial updates
        self.update_pin_usage()
        self.update_status_display()
        self.update_status_bar_for_file(filename)
        self.update_cursor_position()

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
        # TODO: Check if file is saved
        self.editor_tabs.removeTab(index)

    def new_file(self):
        """Create new file"""
        self.create_new_editor()

    def open_file(self):
        """Open file"""
        # TODO: Implement file dialog
        self.status_bar.set_status("Open file (not yet implemented)")
        # Reset to Ready after a moment
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def save_file(self):
        """Save current file"""
        # TODO: Implement save
        self.status_bar.set_status("Save file (not yet implemented)")
        # Reset to Ready after a moment
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def verify_sketch(self):
        """Verify/compile sketch"""
        self.console_panel.append_output("Verifying sketch...")
        # TODO: Implement compilation
        self.status_bar.set_status("Compiling...")
        # Reset to Ready after a moment (would normally be after compilation)
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def upload_sketch(self):
        """Upload sketch to board"""
        self.console_panel.append_output("Uploading sketch...")
        # TODO: Implement upload
        self.status_bar.set_status("Uploading...")
        # Reset to Ready after a moment (would normally be after upload)
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def toggle_serial_monitor(self):
        """Show/hide serial monitor"""
        if self.serial_dock.isVisible():
            self.serial_dock.hide()
        else:
            self.serial_dock.show()
            self.serial_dock.raise_()

    def toggle_status_display(self):
        """Show/hide real-time status display"""
        if self.status_dock.isVisible():
            self.status_dock.hide()
        else:
            self.status_dock.show()
            self.status_dock.raise_()

    def toggle_plotter(self):
        """Show/hide serial plotter"""
        if self.plotter_dock.isVisible():
            self.plotter_dock.hide()
        else:
            self.plotter_dock.show()
            self.plotter_dock.raise_()

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
        # TODO: Implement about dialog
        pass

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
            self.status_bar.set_status(f"Port changed to: {port_name}")
            self.console_panel.append_output(f"Selected port: {port_name}")
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
        self.upload_sketch()
        # Show serial monitor after upload
        if not self.serial_dock.isVisible():
            self.serial_dock.show()
        self.serial_dock.raise_()
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
        examples_menu.exec_(self.mapToGlobal(self.rect().center()))

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
        libraries_menu.exec_(self.mapToGlobal(self.rect().center()))

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
        example_code = examples.get(example_name, f"// {example_name} Example\n// TODO: Add example code\n\nvoid setup() {{\n  \n}}\n\nvoid loop() {{\n  \n}}\n")

        # Create new editor with example
        editor_container = self.create_new_editor(f"{example_name}.ino")
        editor_container.editor.setPlainText(example_code)

        # Update pin usage for the example
        self.update_pin_usage()

        # Reset to Ready after a moment
        QTimer.singleShot(2000, lambda: self.status_bar.set_status("Ready"))

    def load_library_example(self, library_name, example_name):
        """Load a library example sketch"""
        self.console_panel.append_output(f"Loading library example: {library_name}/{example_name}")
        self.status_bar.set_status(f"Loading example: {library_name}/{example_name}")
        # TODO: Implement library example loading
        editor_container = self.create_new_editor(f"{example_name}.ino")
        # Reset to Ready after a moment
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
        """Update real-time status display from current editor"""
        current_widget = self.editor_tabs.currentWidget()
        if current_widget and hasattr(current_widget, 'editor'):
            code_text = current_widget.editor.toPlainText()
            self.status_display.update_from_code(code_text)

    def on_tab_changed(self, index):
        """Handle tab change - update pin usage and status for new tab"""
        if index >= 0:
            self.update_pin_usage()
            self.update_status_display()
            # Update status bar for new tab
            current_widget = self.editor_tabs.currentWidget()
            if current_widget and hasattr(current_widget, 'filename'):
                self.update_status_bar_for_file(current_widget.filename)
            self.update_cursor_position()

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
