"""
Main window for Arduino IDE Modern
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QTabWidget, QDockWidget
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence, QIcon

from arduino_ide.ui.code_editor import CodeEditor
from arduino_ide.ui.serial_monitor import SerialMonitor
from arduino_ide.ui.board_panel import BoardPanel
from arduino_ide.ui.project_explorer import ProjectExplorer
from arduino_ide.ui.console_panel import ConsolePanel
from arduino_ide.ui.variable_watch import VariableWatch
from arduino_ide.services.theme_manager import ThemeManager


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings()
        self.theme_manager = ThemeManager()

        self.init_ui()
        self.create_menus()
        self.create_toolbars()
        self.create_dock_widgets()
        self.restore_state()

        # Apply theme
        self.theme_manager.apply_theme("dark")

    def init_ui(self):
        """Initialize the main UI"""
        self.setWindowTitle("Arduino IDE Modern")
        self.setGeometry(100, 100, 1600, 900)

        # Central widget with editor tabs
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setMovable(True)
        self.editor_tabs.tabCloseRequested.connect(self.close_tab)

        # Create initial editor
        self.create_new_editor("sketch.ino")

        self.setCentralWidget(self.editor_tabs)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

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

        board_action = QAction("Board Manager...", self)
        tools_menu.addAction(board_action)

        library_action = QAction("Library Manager...", self)
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

    def create_toolbars(self):
        """Create toolbars"""
        # Main toolbar
        main_toolbar = QToolBar("Main")
        main_toolbar.setMovable(False)
        self.addToolBar(main_toolbar)

        verify_btn = QAction("✓ Verify", self)
        verify_btn.triggered.connect(self.verify_sketch)
        main_toolbar.addAction(verify_btn)

        upload_btn = QAction("→ Upload", self)
        upload_btn.triggered.connect(self.upload_sketch)
        main_toolbar.addAction(upload_btn)

        main_toolbar.addSeparator()

        new_btn = QAction("+ New", self)
        new_btn.triggered.connect(self.new_file)
        main_toolbar.addAction(new_btn)

        open_btn = QAction("📁 Open", self)
        open_btn.triggered.connect(self.open_file)
        main_toolbar.addAction(open_btn)

        save_btn = QAction("💾 Save", self)
        save_btn.triggered.connect(self.save_file)
        main_toolbar.addAction(save_btn)

        main_toolbar.addSeparator()

        serial_btn = QAction("📡 Serial Monitor", self)
        serial_btn.triggered.connect(self.toggle_serial_monitor)
        main_toolbar.addAction(serial_btn)

    def create_dock_widgets(self):
        """Create dockable panels"""
        # Project Explorer (left)
        self.project_dock = QDockWidget("Project Explorer", self)
        self.project_explorer = ProjectExplorer()
        self.project_dock.setWidget(self.project_explorer)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock)

        # Board Panel (right)
        self.board_dock = QDockWidget("Board Info", self)
        self.board_panel = BoardPanel()
        self.board_dock.setWidget(self.board_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.board_dock)

        # Variable Watch (right)
        self.watch_dock = QDockWidget("Variables", self)
        self.variable_watch = VariableWatch()
        self.watch_dock.setWidget(self.variable_watch)
        self.addDockWidget(Qt.RightDockWidgetArea, self.watch_dock)

        # Console Panel (bottom)
        self.console_dock = QDockWidget("Console", self)
        self.console_panel = ConsolePanel()
        self.console_dock.setWidget(self.console_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.console_dock)

        # Serial Monitor (bottom, tabbed with console)
        self.serial_dock = QDockWidget("Serial Monitor", self)
        self.serial_monitor = SerialMonitor()
        self.serial_dock.setWidget(self.serial_monitor)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.serial_dock)
        self.tabifyDockWidget(self.console_dock, self.serial_dock)

        # Show console by default
        self.console_dock.raise_()

    def create_new_editor(self, filename="untitled.ino"):
        """Create a new editor tab"""
        editor = CodeEditor()

        # Set default Arduino template
        if filename.endswith(".ino"):
            editor.setPlainText(self.get_arduino_template())

        index = self.editor_tabs.addTab(editor, filename)
        self.editor_tabs.setCurrentIndex(index)
        return editor

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
        self.status_bar.showMessage("Open file (not yet implemented)")

    def save_file(self):
        """Save current file"""
        # TODO: Implement save
        self.status_bar.showMessage("Save file (not yet implemented)")

    def verify_sketch(self):
        """Verify/compile sketch"""
        self.console_panel.append_output("Verifying sketch...")
        # TODO: Implement compilation
        self.status_bar.showMessage("Verifying...")

    def upload_sketch(self):
        """Upload sketch to board"""
        self.console_panel.append_output("Uploading sketch...")
        # TODO: Implement upload
        self.status_bar.showMessage("Uploading...")

    def toggle_serial_monitor(self):
        """Show/hide serial monitor"""
        if self.serial_dock.isVisible():
            self.serial_dock.hide()
        else:
            self.serial_dock.show()
            self.serial_dock.raise_()

    def show_about(self):
        """Show about dialog"""
        # TODO: Implement about dialog
        pass

    def save_state(self):
        """Save window state"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

    def restore_state(self):
        """Restore window state"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        """Handle window close"""
        self.save_state()
        event.accept()
