"""
Theme management system
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt


class ThemeManager:
    """Manage application themes"""

    def __init__(self):
        self.current_theme = "dark"

    def apply_theme(self, theme_name):
        """Apply a theme to the application"""
        self.current_theme = theme_name

        app = QApplication.instance()
        if not app:
            return

        if theme_name == "dark":
            self._apply_dark_theme(app)
        elif theme_name == "light":
            self._apply_light_theme(app)
        elif theme_name == "high_contrast":
            self._apply_high_contrast_theme(app)

    def _apply_dark_theme(self, app):
        """Apply dark theme"""
        stylesheet = """
        QMainWindow {
            background-color: #1E1E1E;
            color: #FFFFFF;
        }

        QWidget {
            background-color: #1E1E1E;
            color: #CCCCCC;
        }

        QTextEdit, QPlainTextEdit {
            background-color: #1E1E1E;
            color: #D4D4D4;
            border: 1px solid #3E3E42;
            selection-background-color: #264F78;
        }

        QLineEdit {
            background-color: #2D2D30;
            color: #CCCCCC;
            border: 1px solid #3E3E42;
            padding: 5px;
            border-radius: 3px;
        }

        QPushButton {
            background-color: #0E639C;
            color: #FFFFFF;
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        }

        QPushButton:hover {
            background-color: #1177BB;
        }

        QPushButton:pressed {
            background-color: #005A9E;
        }

        QComboBox {
            background-color: #2D2D30;
            color: #CCCCCC;
            border: 1px solid #3E3E42;
            padding: 5px;
            border-radius: 3px;
        }

        QComboBox:drop-down {
            border: none;
        }

        QComboBox QAbstractItemView {
            background-color: #252526;
            color: #CCCCCC;
            selection-background-color: #094771;
        }

        QMenuBar {
            background-color: #2D2D30;
            color: #CCCCCC;
        }

        QMenuBar::item:selected {
            background-color: #3E3E42;
        }

        QMenu {
            background-color: #252526;
            color: #CCCCCC;
            border: 1px solid #3E3E42;
        }

        QMenu::item:selected {
            background-color: #094771;
        }

        QToolBar {
            background-color: #2D2D30;
            border: none;
            spacing: 5px;
            padding: 3px;
        }

        QStatusBar {
            background-color: #007ACC;
            color: #FFFFFF;
        }

        QTabWidget::pane {
            border: 1px solid #3E3E42;
            background-color: #1E1E1E;
        }

        QTabBar::tab {
            background-color: #2D2D30;
            color: #969696;
            padding: 8px 16px;
            border: 1px solid #3E3E42;
            border-bottom: none;
        }

        QTabBar::tab:selected {
            background-color: #1E1E1E;
            color: #FFFFFF;
        }

        QTabBar::tab:hover {
            background-color: #3E3E42;
        }

        QDockWidget {
            color: #CCCCCC;
            titlebar-close-icon: url(close.png);
            titlebar-normal-icon: url(undock.png);
        }

        QDockWidget::title {
            background-color: #2D2D30;
            padding: 5px;
        }

        QTreeView, QTableWidget {
            background-color: #1E1E1E;
            color: #CCCCCC;
            border: 1px solid #3E3E42;
            alternate-background-color: #252526;
        }

        QTreeView::item:selected, QTableWidget::item:selected {
            background-color: #094771;
        }

        QTreeView::item:hover, QTableWidget::item:hover {
            background-color: #2A2D2E;
        }

        QHeaderView::section {
            background-color: #2D2D30;
            color: #CCCCCC;
            padding: 5px;
            border: 1px solid #3E3E42;
        }

        QScrollBar:vertical {
            background-color: #1E1E1E;
            width: 14px;
            border: none;
        }

        QScrollBar::handle:vertical {
            background-color: #424242;
            min-height: 20px;
            border-radius: 7px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #4E4E4E;
        }

        QScrollBar:horizontal {
            background-color: #1E1E1E;
            height: 14px;
            border: none;
        }

        QScrollBar::handle:horizontal {
            background-color: #424242;
            min-width: 20px;
            border-radius: 7px;
        }

        QScrollBar::handle:horizontal:hover {
            background-color: #4E4E4E;
        }

        QScrollBar::add-line, QScrollBar::sub-line {
            border: none;
            background: none;
        }

        QGroupBox {
            border: 1px solid #3E3E42;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: #CCCCCC;
        }

        QLabel {
            color: #CCCCCC;
        }

        QCheckBox {
            color: #CCCCCC;
        }

        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 1px solid #3E3E42;
            border-radius: 3px;
            background-color: #2D2D30;
        }

        QCheckBox::indicator:checked {
            background-color: #0E639C;
            border-color: #0E639C;
        }
        """

        app.setStyleSheet(stylesheet)

    def _apply_light_theme(self, app):
        """Apply light theme"""
        stylesheet = """
        QMainWindow {
            background-color: #F3F3F3;
            color: #000000;
        }

        QWidget {
            background-color: #F3F3F3;
            color: #333333;
        }

        QTextEdit, QPlainTextEdit {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #CCCCCC;
            selection-background-color: #ADD6FF;
        }

        QLineEdit {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #CCCCCC;
            padding: 5px;
            border-radius: 3px;
        }

        QPushButton {
            background-color: #0078D4;
            color: #FFFFFF;
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        }

        QPushButton:hover {
            background-color: #106EBE;
        }

        QPushButton:pressed {
            background-color: #005A9E;
        }

        QComboBox {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #CCCCCC;
            padding: 5px;
            border-radius: 3px;
        }

        QMenuBar {
            background-color: #F3F3F3;
            color: #000000;
        }

        QMenuBar::item:selected {
            background-color: #E5E5E5;
        }

        QMenu {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #CCCCCC;
        }

        QMenu::item:selected {
            background-color: #E5F3FF;
        }

        QToolBar {
            background-color: #F3F3F3;
            border: none;
            spacing: 5px;
            padding: 3px;
        }

        QStatusBar {
            background-color: #0078D4;
            color: #FFFFFF;
        }

        QTabWidget::pane {
            border: 1px solid #CCCCCC;
            background-color: #FFFFFF;
        }

        QTabBar::tab {
            background-color: #E5E5E5;
            color: #666666;
            padding: 8px 16px;
            border: 1px solid #CCCCCC;
            border-bottom: none;
        }

        QTabBar::tab:selected {
            background-color: #FFFFFF;
            color: #000000;
        }

        QDockWidget::title {
            background-color: #F3F3F3;
            padding: 5px;
        }

        QTreeView, QTableWidget {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #CCCCCC;
        }

        QHeaderView::section {
            background-color: #F3F3F3;
            color: #000000;
            padding: 5px;
            border: 1px solid #CCCCCC;
        }
        """

        app.setStyleSheet(stylesheet)

    def _apply_high_contrast_theme(self, app):
        """Apply high contrast theme for accessibility"""
        stylesheet = """
        QMainWindow, QWidget {
            background-color: #000000;
            color: #FFFFFF;
        }

        QTextEdit, QPlainTextEdit, QLineEdit {
            background-color: #000000;
            color: #FFFF00;
            border: 2px solid #FFFFFF;
        }

        QPushButton {
            background-color: #000000;
            color: #FFFF00;
            border: 2px solid #FFFFFF;
            padding: 8px 16px;
        }

        QPushButton:hover {
            background-color: #FFFFFF;
            color: #000000;
        }

        QMenuBar, QMenu, QToolBar {
            background-color: #000000;
            color: #FFFFFF;
        }

        QMenuBar::item:selected, QMenu::item:selected {
            background-color: #FFFFFF;
            color: #000000;
        }

        QTabBar::tab {
            background-color: #000000;
            color: #FFFFFF;
            border: 2px solid #FFFFFF;
        }

        QTabBar::tab:selected {
            background-color: #FFFFFF;
            color: #000000;
        }
        """

        app.setStyleSheet(stylesheet)
