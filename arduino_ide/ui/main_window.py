"""
Main window for Arduino IDE Modern
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QTabWidget, QDockWidget,
    QComboBox, QLabel
)
from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QAction, QKeySequence, QIcon, QTextCursor
import serial.tools.list_ports

from arduino_ide.ui.code_editor import CodeEditor, BreadcrumbBar, CodeMinimap
from arduino_ide.ui.serial_monitor import SerialMonitor
from arduino_ide.ui.board_panel import BoardPanel
from arduino_ide.ui.project_explorer import ProjectExplorer
from arduino_ide.ui.console_panel import ConsolePanel
from arduino_ide.ui.variable_watch import VariableWatch
from arduino_ide.ui.status_display import StatusDisplay
from arduino_ide.services.theme_manager import ThemeManager


class EditorContainer(QWidget):
    """Container widget that combines breadcrumb, editor, and minimap"""

    def __init__(self, filename="untitled.ino", parent=None):
        super().__init__(parent)
        self.filename = filename
        self.setup_ui()

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
        self.breadcrumb.update_breadcrumb(self.filename, function_name, line_num)

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

        # Current build configuration
        self.build_config = "Release"

        self.init_ui()
        self.create_menus()
        self.create_toolbars()
        self.create_dock_widgets()
        self.restore_state()

        # Setup port auto-refresh timer
        self.setup_port_refresh()

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
        self.editor_tabs.currentChanged.connect(self.on_tab_changed)

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

        status_action = QAction("Real-time Status", self)
        status_action.setShortcut(Qt.CTRL | Qt.SHIFT | Qt.Key_S)
        status_action.triggered.connect(self.toggle_status_display)
        tools_menu.addAction(status_action)

        tools_menu.addSeparator()

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

        # Status Display (right, tabbed with board panel)
        self.status_dock = QDockWidget("Real-time Status", self)
        self.status_display = StatusDisplay()
        self.status_dock.setWidget(self.status_display)
        self.addDockWidget(Qt.RightDockWidgetArea, self.status_dock)
        self.tabifyDockWidget(self.board_dock, self.status_dock)

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
        editor_container = EditorContainer(filename)

        # Set default Arduino template
        if filename.endswith(".ino"):
            editor_container.editor.setPlainText(self.get_arduino_template())

        # Connect editor changes to pin usage update and status display
        editor_container.editor.textChanged.connect(self.update_pin_usage)
        editor_container.editor.textChanged.connect(self.update_status_display)

        index = self.editor_tabs.addTab(editor_container, filename)
        self.editor_tabs.setCurrentIndex(index)

        # Initial updates
        self.update_pin_usage()
        self.update_status_display()

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

    def toggle_status_display(self):
        """Show/hide real-time status display"""
        if self.status_dock.isVisible():
            self.status_dock.hide()
        else:
            self.status_dock.show()
            self.status_dock.raise_()

    def show_about(self):
        """Show about dialog"""
        # TODO: Implement about dialog
        pass

    def on_board_changed(self, board_name):
        """Handle board selection change"""
        self.status_bar.showMessage(f"Board changed to: {board_name}")
        self.console_panel.append_output(f"Selected board: {board_name}")
        # Update board panel
        self.board_panel.update_board_info(board_name)
        # Update status display with new board specs
        self.status_display.update_board(board_name)

    def on_port_changed(self, port_name):
        """Handle port selection change"""
        if port_name:
            self.status_bar.showMessage(f"Port changed to: {port_name}")
            self.console_panel.append_output(f"Selected port: {port_name}")

    def on_config_changed(self, config):
        """Handle build configuration change"""
        self.build_config = config
        self.status_bar.showMessage(f"Build configuration: {config}")
        self.console_panel.append_output(f"Build configuration changed to: {config}")

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
        self.status_bar.showMessage("Upload complete - Serial monitor opened")

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
        self.status_bar.showMessage(f"Loading example: {example_name}")

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

    def load_library_example(self, library_name, example_name):
        """Load a library example sketch"""
        self.console_panel.append_output(f"Loading library example: {library_name}/{example_name}")
        self.status_bar.showMessage(f"Loading example: {library_name}/{example_name}")
        # TODO: Implement library example loading
        editor_container = self.create_new_editor(f"{example_name}.ino")

    def open_library_manager(self):
        """Open library manager dialog"""
        self.console_panel.append_output("Opening Library Manager...")
        self.status_bar.showMessage("Library Manager (not yet implemented)")
        # TODO: Implement library manager dialog

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
