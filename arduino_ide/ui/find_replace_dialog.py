"""
Find and Replace dialog for code editor
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QCheckBox, QLabel, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor, QTextDocument


class FindReplaceDialog(QDialog):
    """
    Find and Replace dialog with advanced search options
    """

    find_next_signal = Signal(str, bool, bool, bool)  # text, case_sensitive, whole_word, regex
    replace_signal = Signal(str, str, bool, bool, bool)  # find_text, replace_text, case_sensitive, whole_word, regex
    replace_all_signal = Signal(str, str, bool, bool, bool)

    def __init__(self, editor=None, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Find and Replace")
        self.setModal(False)
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.resize(500, 300)
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Find group
        find_group = QGroupBox("Find")
        find_layout = QVBoxLayout()

        find_input_layout = QHBoxLayout()
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Enter text to find...")
        self.find_input.returnPressed.connect(self.find_next)
        find_input_layout.addWidget(QLabel("Find:"))
        find_input_layout.addWidget(self.find_input)
        find_layout.addLayout(find_input_layout)

        find_group.setLayout(find_layout)
        layout.addWidget(find_group)

        # Replace group
        replace_group = QGroupBox("Replace")
        replace_layout = QVBoxLayout()

        replace_input_layout = QHBoxLayout()
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Enter replacement text...")
        replace_input_layout.addWidget(QLabel("Replace:"))
        replace_input_layout.addWidget(self.replace_input)
        replace_layout.addLayout(replace_input_layout)

        replace_group.setLayout(replace_layout)
        layout.addWidget(replace_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.case_sensitive_cb = QCheckBox("Case sensitive")
        self.whole_word_cb = QCheckBox("Whole words only")
        self.regex_cb = QCheckBox("Regular expression")
        self.wrap_around_cb = QCheckBox("Wrap around")
        self.wrap_around_cb.setChecked(True)

        options_layout.addWidget(self.case_sensitive_cb)
        options_layout.addWidget(self.whole_word_cb)
        options_layout.addWidget(self.regex_cb)
        options_layout.addWidget(self.wrap_around_cb)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.find_next_btn = QPushButton("Find Next")
        self.find_next_btn.clicked.connect(self.find_next)
        self.find_next_btn.setDefault(True)
        button_layout.addWidget(self.find_next_btn)

        self.find_prev_btn = QPushButton("Find Previous")
        self.find_prev_btn.clicked.connect(self.find_previous)
        button_layout.addWidget(self.find_prev_btn)

        self.replace_btn = QPushButton("Replace")
        self.replace_btn.clicked.connect(self.replace_current)
        button_layout.addWidget(self.replace_btn)

        self.replace_all_btn = QPushButton("Replace All")
        self.replace_all_btn.clicked.connect(self.replace_all)
        button_layout.addWidget(self.replace_all_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("QLabel { color: #858585; padding: 5px; }")
        layout.addWidget(self.status_label)

        # Apply styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #FFFFFF;
            }
            QGroupBox {
                border: 1px solid #3E3E42;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                color: #FFFFFF;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit {
                background-color: #2D2D30;
                border: 1px solid #3E3E42;
                color: #FFFFFF;
                padding: 5px;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #007ACC;
            }
            QPushButton {
                background-color: #0E639C;
                color: #FFFFFF;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #0D5A8F;
            }
            QCheckBox {
                color: #FFFFFF;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #3E3E42;
                border-radius: 3px;
                background-color: #2D2D30;
            }
            QCheckBox::indicator:checked {
                background-color: #007ACC;
                border-color: #007ACC;
            }
            QLabel {
                color: #CCCCCC;
            }
        """)

    def find_next(self):
        """Find next occurrence"""
        if not self.editor or not self.find_input.text():
            return

        find_text = self.find_input.text()
        flags = self.get_search_flags()

        cursor = self.editor.textCursor()
        original_position = cursor.position()

        # Try to find from current position
        found = self.search_from_position(cursor.position(), flags, find_text)

        # If wrap around is enabled and not found, search from beginning
        if not found and self.wrap_around_cb.isChecked():
            found = self.search_from_position(0, flags, find_text)

        if found:
            self.status_label.setText("")
        else:
            self.status_label.setText("No matches found")

    def find_previous(self):
        """Find previous occurrence"""
        if not self.editor or not self.find_input.text():
            return

        find_text = self.find_input.text()
        flags = self.get_search_flags() | QTextDocument.FindBackward

        cursor = self.editor.textCursor()
        original_position = cursor.position()

        # Try to find backwards from current position
        found = self.search_from_position(cursor.position(), flags, find_text)

        # If wrap around is enabled and not found, search from end
        if not found and self.wrap_around_cb.isChecked():
            found = self.search_from_position(len(self.editor.toPlainText()), flags, find_text)

        if found:
            self.status_label.setText("")
        else:
            self.status_label.setText("No matches found")

    def search_from_position(self, position, flags, find_text):
        """Search for text from a specific position"""
        cursor = self.editor.textCursor()
        cursor.setPosition(position)

        if self.regex_cb.isChecked():
            import re
            pattern = find_text
            regex_flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE

            try:
                regex = re.compile(pattern, regex_flags)
            except re.error as e:
                self.status_label.setText(f"Invalid regex: {e}")
                return False

            text = self.editor.toPlainText()

            if flags & QTextDocument.FindBackward:
                # Search backwards
                text_before = text[:position]
                matches = list(regex.finditer(text_before))
                if matches:
                    match = matches[-1]
                    cursor.setPosition(match.start())
                    cursor.setPosition(match.end(), QTextCursor.KeepAnchor)
                    self.editor.setTextCursor(cursor)
                    return True
            else:
                # Search forwards
                text_after = text[position:]
                match = regex.search(text_after)
                if match:
                    cursor.setPosition(position + match.start())
                    cursor.setPosition(position + match.end(), QTextCursor.KeepAnchor)
                    self.editor.setTextCursor(cursor)
                    return True

            return False
        else:
            # Use Qt's find method
            found_cursor = self.editor.document().find(find_text, cursor, flags)
            if not found_cursor.isNull():
                self.editor.setTextCursor(found_cursor)
                return True
            return False

    def replace_current(self):
        """Replace current selection"""
        if not self.editor or not self.find_input.text():
            return

        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            # Check if selection matches find text
            selected_text = cursor.selectedText()
            find_text = self.find_input.text()

            matches = False
            if self.case_sensitive_cb.isChecked():
                matches = selected_text == find_text
            else:
                matches = selected_text.lower() == find_text.lower()

            if matches:
                cursor.insertText(self.replace_input.text())
                self.status_label.setText("Replaced 1 occurrence")
                # Find next after replacing
                self.find_next()
            else:
                # Selection doesn't match, just find next
                self.find_next()
        else:
            # No selection, just find next
            self.find_next()

    def replace_all(self):
        """Replace all occurrences"""
        if not self.editor or not self.find_input.text():
            return

        find_text = self.find_input.text()
        replace_text = self.replace_input.text()

        # Save cursor position
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()

        count = 0
        # Start from beginning
        cursor.movePosition(QTextCursor.Start)
        self.editor.setTextCursor(cursor)

        flags = self.get_search_flags()

        if self.regex_cb.isChecked():
            import re
            pattern = find_text
            regex_flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE

            try:
                regex = re.compile(pattern, regex_flags)
                text = self.editor.toPlainText()
                new_text = regex.sub(replace_text, text)
                count = len(regex.findall(text))

                if count > 0:
                    cursor.select(QTextCursor.Document)
                    cursor.insertText(new_text)
            except re.error as e:
                self.status_label.setText(f"Invalid regex: {e}")
                cursor.endEditBlock()
                return
        else:
            # Replace using Qt's find
            while True:
                found_cursor = self.editor.document().find(find_text, cursor, flags)
                if found_cursor.isNull():
                    break

                found_cursor.insertText(replace_text)
                cursor = found_cursor
                count += 1

        cursor.endEditBlock()

        if count > 0:
            self.status_label.setText(f"Replaced {count} occurrence{'s' if count != 1 else ''}")
        else:
            self.status_label.setText("No matches found")

    def get_search_flags(self):
        """Get search flags based on checkboxes"""
        flags = QTextDocument.FindFlags()

        if self.case_sensitive_cb.isChecked():
            flags |= QTextDocument.FindCaseSensitively

        if self.whole_word_cb.isChecked():
            flags |= QTextDocument.FindWholeWords

        return flags

    def set_find_text(self, text):
        """Set the find text and select it"""
        self.find_input.setText(text)
        self.find_input.selectAll()
        self.find_input.setFocus()

    def showEvent(self, event):
        """When dialog is shown, focus the find input"""
        super().showEvent(event)
        self.find_input.setFocus()
        self.find_input.selectAll()
