"""
Context-Aware Panel
Shows contextual information about Arduino functions when clicked
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QGroupBox, QTextBrowser, QDockWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextCursor

from arduino_ide.data.arduino_api_reference import get_api_info


class ContextPanel(QDockWidget):
    """Panel that displays contextual information about Arduino code elements"""

    def __init__(self, parent=None):
        super().__init__("Context Help", parent)
        self.setObjectName("ContextPanel")
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea
        )
        self.current_context = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(10)

        # Title
        self.title_label = QLabel("Context Help")
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.title_label)

        # Category badge
        self.category_label = QLabel("")
        self.category_label.setFont(QFont("Arial", 9))
        self.category_label.setAlignment(Qt.AlignCenter)
        self.category_label.setStyleSheet("""
            QLabel {
                background-color: #264f78;
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
            }
        """)
        self.category_label.hide()
        self.content_layout.addWidget(self.category_label)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.content_layout.addWidget(line)

        # Description
        self.description_label = QLabel("")
        self.description_label.setFont(QFont("Arial", 10))
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #CCCCCC; padding: 5px;")
        self.content_layout.addWidget(self.description_label)

        # Syntax section
        self.syntax_group = QGroupBox("Syntax")
        self.syntax_group.setFont(QFont("Arial", 9, QFont.Bold))
        syntax_layout = QVBoxLayout()
        self.syntax_label = QLabel("")
        self.syntax_label.setFont(QFont("Consolas", 9))
        self.syntax_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #4EC9B0;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #3E3E42;
            }
        """)
        self.syntax_label.setWordWrap(True)
        syntax_layout.addWidget(self.syntax_label)
        self.syntax_group.setLayout(syntax_layout)
        self.syntax_group.hide()
        self.content_layout.addWidget(self.syntax_group)

        # Parameters section
        self.params_group = QGroupBox("Parameters")
        self.params_group.setFont(QFont("Arial", 9, QFont.Bold))
        self.params_layout = QVBoxLayout()
        self.params_group.setLayout(self.params_layout)
        self.params_group.hide()
        self.content_layout.addWidget(self.params_group)

        # Common values section
        self.values_group = QGroupBox("Common Values")
        self.values_group.setFont(QFont("Arial", 9, QFont.Bold))
        self.values_layout = QVBoxLayout()
        self.values_group.setLayout(self.values_layout)
        self.values_group.hide()
        self.content_layout.addWidget(self.values_group)

        # Warnings section
        self.warnings_group = QGroupBox("Warnings")
        self.warnings_group.setFont(QFont("Arial", 9, QFont.Bold))
        self.warnings_layout = QVBoxLayout()
        self.warnings_group.setLayout(self.warnings_layout)
        self.warnings_group.hide()
        self.content_layout.addWidget(self.warnings_group)

        # Tips section
        self.tips_group = QGroupBox("Tips")
        self.tips_group.setFont(QFont("Arial", 9, QFont.Bold))
        self.tips_layout = QVBoxLayout()
        self.tips_group.setLayout(self.tips_layout)
        self.tips_group.hide()
        self.content_layout.addWidget(self.tips_group)

        # Example section
        self.example_group = QGroupBox("Example")
        self.example_group.setFont(QFont("Arial", 9, QFont.Bold))
        example_layout = QVBoxLayout()
        self.example_label = QTextBrowser()
        self.example_label.setFont(QFont("Consolas", 9))
        self.example_label.setStyleSheet("""
            QTextBrowser {
                background-color: #1e1e1e;
                color: #D4D4D4;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #3E3E42;
            }
        """)
        self.example_label.setMaximumHeight(150)
        example_layout.addWidget(self.example_label)
        self.example_group.setLayout(example_layout)
        self.example_group.hide()
        self.content_layout.addWidget(self.example_group)

        # Default message
        self.default_message = QLabel(
            "💡 Click on code elements to see contextual help\n\n"
            "Supported:\n"
            "• Arduino functions (Serial.begin, pinMode, etc.)\n"
            "• C++ keywords (if, for, while, switch, etc.)\n"
            "• Data types (int, float, char, bool, etc.)\n"
            "• Operators (+, -, ==, &&, ||, etc.)\n"
            "• Control flow (break, continue, return, etc.)\n"
            "• Preprocessor (#include, #define, etc.)\n"
            "• And much more!"
        )
        self.default_message.setFont(QFont("Arial", 10))
        self.default_message.setStyleSheet("color: #888; padding: 20px;")
        self.default_message.setAlignment(Qt.AlignCenter)
        self.default_message.setWordWrap(True)
        self.content_layout.addWidget(self.default_message)

        self.content_layout.addStretch()

        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)

        self.setWidget(container)

    def update_context(self, word_under_cursor, full_context=None):
        """Update panel with context information for the word under cursor

        Args:
            word_under_cursor: The function name clicked (e.g., "Serial.begin")
            full_context: Full context string from code (e.g., "Serial.begin(9600)")
        """
        if not word_under_cursor:
            self.show_default_message()
            return

        # Get API information
        api_info = get_api_info(word_under_cursor)

        if not api_info:
            self.show_not_found(word_under_cursor)
            return

        # Hide default message
        self.default_message.hide()

        # Update title
        self.title_label.setText(api_info.get("title", word_under_cursor))
        self.title_label.show()

        # Update category
        category = api_info.get("category", "")
        if category:
            self.category_label.setText(category)
            self.category_label.show()
        else:
            self.category_label.hide()

        # Update description
        description = api_info.get("description", "")
        if description:
            self.description_label.setText(description)
            self.description_label.show()
        else:
            self.description_label.hide()

        # Update syntax
        syntax = api_info.get("syntax", "")
        if syntax:
            self.syntax_label.setText(syntax)
            self.syntax_group.show()
        else:
            self.syntax_group.hide()

        # Update parameters
        self.clear_layout(self.params_layout)
        parameters = api_info.get("parameters", [])
        if parameters:
            for param in parameters:
                param_label = QLabel(
                    f"<b>{param['name']}</b> ({param['type']})<br/>"
                    f"<span style='color: #CCCCCC;'>{param['description']}</span>"
                )
                param_label.setFont(QFont("Arial", 9))
                param_label.setWordWrap(True)
                param_label.setStyleSheet("padding: 5px; margin-bottom: 5px;")
                self.params_layout.addWidget(param_label)
            self.params_group.show()
        else:
            self.params_group.hide()

        # Update common values
        self.clear_layout(self.values_layout)
        common_values = api_info.get("common_values", [])
        if common_values:
            for val in common_values:
                val_label = QLabel(
                    f"<b>{val['value']}</b><br/>"
                    f"<span style='color: #AAAAAA;'>{val['description']}</span>"
                )
                val_label.setFont(QFont("Arial", 9))
                val_label.setWordWrap(True)
                val_label.setStyleSheet("""
                    padding: 6px;
                    margin-bottom: 5px;
                    background-color: #2D2D30;
                    border-left: 3px solid #4EC9B0;
                    border-radius: 3px;
                """)
                self.values_layout.addWidget(val_label)
            self.values_group.show()
        else:
            self.values_group.hide()

        # Update warnings
        self.clear_layout(self.warnings_layout)
        warnings = api_info.get("warnings", [])
        if warnings:
            for warning in warnings:
                warn_label = QLabel(warning)
                warn_label.setFont(QFont("Arial", 9))
                warn_label.setWordWrap(True)
                warn_label.setStyleSheet("""
                    padding: 6px;
                    margin-bottom: 5px;
                    background-color: #3D2817;
                    border-left: 3px solid #FFA500;
                    border-radius: 3px;
                    color: #FFD700;
                """)
                self.warnings_layout.addWidget(warn_label)
            self.warnings_group.show()
        else:
            self.warnings_group.hide()

        # Update tips
        self.clear_layout(self.tips_layout)
        tips = api_info.get("tips", [])
        if tips:
            for tip in tips:
                tip_label = QLabel(tip)
                tip_label.setFont(QFont("Arial", 9))
                tip_label.setWordWrap(True)
                tip_label.setStyleSheet("""
                    padding: 6px;
                    margin-bottom: 5px;
                    background-color: #1E3A1E;
                    border-left: 3px solid #4CAF50;
                    border-radius: 3px;
                    color: #90EE90;
                """)
                self.tips_layout.addWidget(tip_label)
            self.tips_group.show()
        else:
            self.tips_group.hide()

        # Update example
        example = api_info.get("example", "")
        if example:
            self.example_label.setPlainText(example)
            self.example_group.show()
        else:
            self.example_group.hide()

        self.current_context = word_under_cursor

    def show_default_message(self):
        """Show default message when no context is available"""
        # Hide all sections
        self.title_label.hide()
        self.category_label.hide()
        self.description_label.hide()
        self.syntax_group.hide()
        self.params_group.hide()
        self.values_group.hide()
        self.warnings_group.hide()
        self.tips_group.hide()
        self.example_group.hide()

        # Show default message
        self.default_message.show()
        self.current_context = None

    def show_not_found(self, word):
        """Show message when function is not in the database"""
        self.default_message.hide()

        self.title_label.setText(f"'{word}'")
        self.title_label.show()

        self.category_label.hide()

        self.description_label.setText(
            f"No contextual information available for '{word}'.\n\n"
            "This might be:\n"
            "• A user-defined function or variable\n"
            "• A library function not yet documented\n"
            "• A custom type or constant\n\n"
            "Documentation is available for:\n"
            "• Arduino functions (Serial.begin, pinMode, etc.)\n"
            "• C++ keywords and types (if, for, int, float, etc.)\n"
            "• Operators and control flow statements"
        )
        self.description_label.show()

        # Hide all other sections
        self.syntax_group.hide()
        self.params_group.hide()
        self.values_group.hide()
        self.warnings_group.hide()
        self.tips_group.hide()
        self.example_group.hide()

    def clear_layout(self, layout):
        """Clear all widgets from a layout"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def hide_content(self):
        """Hide all content and show default message"""
        self.show_default_message()
