import sys
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from services_mobile.build_service import (  # noqa: E402
    BoardManager,
    BuildRequest,
    BuildResult,
    BuildService,
    LibraryManager,
)
from services_mobile.storage_service import StorageService  # noqa: E402
from ui_mobile.board_library_dialogs import BoardSelectionDialog, LibraryManagerDialog  # noqa: E402
from ui_mobile.build_console import BuildConsole  # noqa: E402
from ui_mobile.gesture_handler import GestureHandler  # noqa: E402
from ui_mobile.mobile_toolbar import KeyboardToolbar  # noqa: E402
from ui_mobile.touch_editor import TouchEditor  # noqa: E402


class BuildWorker(QtCore.QThread):
    """Runs compilation in a background thread to avoid UI freezes."""

    progress = QtCore.Signal(str)
    finished_with_result = QtCore.Signal(BuildResult)

    def __init__(self, service: BuildService, request: BuildRequest) -> None:
        super().__init__()
        self.service = service
        self.request = request

    def run(self) -> None:  # noqa: D401
        self.progress.emit("Starting build...")
        result = self.service.verify_sketch(self.request)
        self.finished_with_result.emit(result)


class MainWindow(QtWidgets.QMainWindow):
    """Main window for the Android code editor."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Arduino IDE Modern - Android")
        self.resize(1200, 800)

        self.storage = StorageService()
        self.board_manager = BoardManager()
        self.library_manager = LibraryManager()
        self.build_service = BuildService()
        self.build_worker: BuildWorker | None = None
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)

        self.editor_toolbar = self._build_editor_toolbar()
        self.keyboard_toolbar = KeyboardToolbar()
        self.keyboard_toolbar.symbol_pressed.connect(self.insert_symbol)

        self.build_console = BuildConsole()
        self.build_console.error_selected.connect(self._jump_to_error)
        self.build_dock = QtWidgets.QDockWidget("Build Console", self)
        self.build_dock.setWidget(self.build_console)
        self.build_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable)

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.editor_toolbar)
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.keyboard_toolbar)
        self.setCentralWidget(container)

        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.build_dock)
        self._init_status_bar()

        self._apply_theme("dark")

    def _init_status_bar(self) -> None:
        status_bar = self.statusBar()
        status_bar.setSizeGripEnabled(False)
        self.board_label = QtWidgets.QLabel()
        self.build_status_label = QtWidgets.QLabel("Ready")
        status_bar.addPermanentWidget(self.board_label)
        status_bar.addPermanentWidget(self.build_status_label)
        self._refresh_board_label()

    # region UI builders
    def _build_editor_toolbar(self) -> QtWidgets.QToolBar:
        toolbar = QtWidgets.QToolBar("Editor Toolbar")
        toolbar.setMovable(False)

        new_action = QtGui.QAction("New", self)
        new_action.triggered.connect(self.create_new_tab)
        toolbar.addAction(new_action)

        open_action = QtGui.QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        save_action = QtGui.QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)

        delete_action = QtGui.QAction("Delete", self)
        delete_action.triggered.connect(self.delete_file)
        toolbar.addAction(delete_action)

        toolbar.addSeparator()

        verify_action = QtGui.QAction("Verify", self)
        verify_action.setShortcut(QtGui.QKeySequence("Ctrl+B"))
        verify_action.triggered.connect(self.verify_sketch)
        toolbar.addAction(verify_action)

        board_action = QtGui.QAction("Select Board", self)
        board_action.triggered.connect(self.select_board)
        toolbar.addAction(board_action)

        core_action = QtGui.QAction("Manage Cores", self)
        core_action.triggered.connect(self.manage_cores)
        toolbar.addAction(core_action)

        library_action = QtGui.QAction("Manage Libraries", self)
        library_action.triggered.connect(self.manage_libraries)
        toolbar.addAction(library_action)

        toolbar.addSeparator()

        theme_toggle = QtGui.QAction("Toggle Theme", self)
        theme_toggle.triggered.connect(self.toggle_theme)
        toolbar.addAction(theme_toggle)

        return toolbar

    # endregion

    # region Tabs & editors
    def create_new_tab(self, file_path: Optional[Path] = None, content: str | None = None) -> None:
        editor = TouchEditor()
        gesture_handler = GestureHandler(editor)
        editor.installEventFilter(gesture_handler)
        editor.apply_touch_preferences()
        editor.enable_keyboard_shortcuts()
        editor.set_theme(getattr(self, "current_theme", "dark"))
        editor.textChanged.connect(self._refresh_current_tab_title)

        if file_path:
            editor.load_file(file_path, content)
        else:
            editor.setPlaceholderText("Untitled sketch")

        index = self.tab_widget.addTab(editor, self._tab_title(file_path))
        self.tab_widget.setCurrentIndex(index)

    def current_editor(self) -> Optional[TouchEditor]:
        widget = self.tab_widget.currentWidget()
        if isinstance(widget, TouchEditor):
            return widget
        return None

    def _tab_title(self, path: Optional[Path]) -> str:
        if path:
            return path.name
        return "Untitled"

    def _refresh_current_tab_title(self) -> None:
        editor = self.current_editor()
        if not editor:
            return
        title = editor.tab_title()
        self.tab_widget.setTabText(self.tab_widget.currentIndex(), title)

    def close_tab(self, index: int) -> None:
        widget = self.tab_widget.widget(index)
        widget.deleteLater()
        self.tab_widget.removeTab(index)

    # endregion

    # region File actions
    def open_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Arduino Sketch", str(self.storage.base_dir), "Arduino Sketches (*.ino *.cpp *.h);;All Files (*)")
        if not path:
            return
        file_path = Path(path)
        content = self.storage.read_file(file_path)
        self.create_new_tab(file_path, content)

    def save_file(self) -> None:
        editor = self.current_editor()
        if not editor:
            return

        file_path = editor.file_path
        if not file_path:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Arduino Sketch", str(self.storage.base_dir / "sketch.ino"), "Arduino Sketches (*.ino *.cpp *.h);;All Files (*)")
            if not path:
                return
            file_path = Path(path)
            editor.file_path = file_path

        self.storage.write_file(file_path, editor.toPlainText())
        self.tab_widget.setTabText(self.tab_widget.currentIndex(), self._tab_title(file_path))

    def delete_file(self) -> None:
        editor = self.current_editor()
        if not editor:
            return

        file_path = editor.file_path
        if not file_path:
            QtWidgets.QMessageBox.information(self, "Delete", "Current file has not been saved yet.")
            return

        reply = QtWidgets.QMessageBox.question(self, "Delete", f"Delete {file_path.name}?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.storage.delete_file(file_path)
            self.close_tab(self.tab_widget.currentIndex())

    # endregion

    # region Build system
    def verify_sketch(self) -> None:
        editor = self.current_editor()
        if not editor:
            return

        if not editor.file_path:
            QtWidgets.QMessageBox.information(self, "Save sketch", "Please save the sketch before building.")
            self.save_file()
            if not editor.file_path:
                return

        request = BuildRequest(
            sketch_path=editor.file_path,
            fqbn=self.board_manager.selected_board()["fqbn"],
            libraries=[lib["name"] for lib in self.library_manager.installed()],
        )
        self.build_status_label.setText("Verifying...")
        self.build_console.append_output(f"Verifying {editor.file_path.name} for {request.fqbn}")
        if self.build_worker and self.build_worker.isRunning():
            QtWidgets.QMessageBox.information(self, "Build in progress", "Please wait for the current build to finish.")
            return

        self.build_worker = BuildWorker(self.build_service, request)
        self.build_worker.progress.connect(self.build_console.append_output)
        self.build_worker.finished_with_result.connect(self._handle_build_result)
        self.build_worker.start()

    def _handle_build_result(self, result: BuildResult) -> None:
        self.build_console.show_result(result)
        self.build_status_label.setText("Success" if result.success else "Failed")
        self.build_worker = None
        if not result.success:
            QtWidgets.QMessageBox.warning(self, "Build failed", "Check the build console for compiler output.")
        else:
            QtWidgets.QMessageBox.information(self, "Build succeeded", "Sketch compiled successfully.")

    def _jump_to_error(self, error: object) -> None:
        if not hasattr(error, "line"):
            return
        editor = self.current_editor()
        if not editor:
            return
        if editor.file_path and Path(getattr(error, "file", "")).name != editor.file_path.name:
            return
        block = editor.document().findBlockByNumber(getattr(error, "line", 1) - 1)
        cursor = editor.textCursor()
        cursor.setPosition(block.position() + getattr(error, "column", 1) - 1)
        editor.setTextCursor(cursor)
        editor.setFocus()

    def select_board(self) -> None:
        dialog = BoardSelectionDialog(self.board_manager, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            board = dialog.selected_board()
            if board:
                self.board_manager.select_board(board)
                self._refresh_board_label()

    def manage_cores(self) -> None:
        board = self.board_manager.selected_board()
        fqbn = board["fqbn"]
        output = self.board_manager.install_core(fqbn)
        QtWidgets.QMessageBox.information(self, "Board Core", output)
        self._refresh_board_label()

    def manage_libraries(self) -> None:
        dialog = LibraryManagerDialog(self.library_manager, self)
        dialog.exec()

    def _refresh_board_label(self) -> None:
        board = self.board_manager.selected_board()
        self.board_label.setText(f"Board: {board['name']} ({board['fqbn']})")

    # endregion

    # region Keyboard toolbar
    def insert_symbol(self, symbol: str) -> None:
        editor = self.current_editor()
        if editor:
            editor.insert_symbol(symbol)

    # endregion

    # region Theme
    def _apply_theme(self, mode: str) -> None:
        palette = QtGui.QPalette()
        if mode == "dark":
            palette.setColor(QtGui.QPalette.Window, QtGui.QColor(25, 25, 25))
            palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.Base, QtGui.QColor(18, 18, 18))
            palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.Button, QtGui.QColor(45, 45, 45))
            palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(75, 110, 175))
            palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        else:
            palette = QtWidgets.QApplication.style().standardPalette()
        QtWidgets.QApplication.instance().setPalette(palette)
        self.current_theme = mode

    def toggle_theme(self) -> None:
        next_theme = "light" if getattr(self, "current_theme", "dark") == "dark" else "dark"
        self._apply_theme(next_theme)

    # endregion


def main() -> int:
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.create_new_tab()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
