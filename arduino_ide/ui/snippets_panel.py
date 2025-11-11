"""
Snippets panel for browsing and inserting code snippets
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QPushButton, QLineEdit, QLabel, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from arduino_ide.services.snippets_manager import SnippetsManager


class SnippetsPanel(QWidget):
    """Panel for browsing and inserting code snippets"""

    snippet_insert_requested = Signal(object)  # Emits Snippet object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.snippets_manager = SnippetsManager()
        self.setup_ui()
        self.populate_snippets()

    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Title
        title_label = QLabel("Code Snippets")
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                padding: 8px;
                background-color: #2D2D30;
                color: #FFFFFF;
                border-bottom: 1px solid #3E3E42;
            }
        """)
        layout.addWidget(title_label)

        # Search box
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(5, 5, 5, 5)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search snippets...")
        self.search_input.textChanged.connect(self.filter_snippets)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #3E3E42;
                border-radius: 3px;
                background-color: #2D2D30;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #007ACC;
            }
        """)
        search_layout.addWidget(self.search_input)

        layout.addLayout(search_layout)

        # Splitter for tree and preview
        splitter = QSplitter(Qt.Vertical)

        # Tree widget for categories and snippets
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Available Snippets")
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #3E3E42;
                outline: none;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #094771;
            }
            QTreeWidget::item:hover {
                background-color: #2A2D2E;
            }
            QHeaderView::section {
                background-color: #2D2D30;
                color: #FFFFFF;
                padding: 5px;
                border: none;
                border-bottom: 1px solid #3E3E42;
            }
        """)
        self.tree.itemSelectionChanged.connect(self.on_selection_changed)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        splitter.addWidget(self.tree)

        # Preview area
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(5, 5, 5, 5)

        preview_label = QLabel("Preview:")
        preview_label.setStyleSheet("QLabel { color: #CCCCCC; font-weight: bold; }")
        preview_layout.addWidget(preview_label)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas, Monaco, Courier New", 10))
        self.preview.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3E3E42;
                padding: 5px;
            }
        """)
        preview_layout.addWidget(self.preview)

        # Description label
        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("""
            QLabel {
                color: #858585;
                padding: 5px;
                font-style: italic;
            }
        """)
        preview_layout.addWidget(self.description_label)

        splitter.addWidget(preview_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # Insert button
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 5, 5, 5)

        self.insert_button = QPushButton("Insert Snippet")
        self.insert_button.clicked.connect(self.insert_selected_snippet)
        self.insert_button.setEnabled(False)
        self.insert_button.setStyleSheet("""
            QPushButton {
                background-color: #0E639C;
                color: #FFFFFF;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #0D5A8F;
            }
            QPushButton:disabled {
                background-color: #3E3E42;
                color: #858585;
            }
        """)
        button_layout.addWidget(self.insert_button)

        layout.addLayout(button_layout)

    def populate_snippets(self):
        """Populate the tree with snippets"""
        self.tree.clear()

        categories = self.snippets_manager.get_categories()

        for category in categories:
            category_item = QTreeWidgetItem(self.tree)
            category_item.setText(0, f"📁 {category}")
            category_item.setExpanded(True)

            snippets = self.snippets_manager.get_snippets_by_category(category)
            for snippet in snippets:
                snippet_item = QTreeWidgetItem(category_item)
                snippet_item.setText(0, f"📄 {snippet.name}")
                snippet_item.setData(0, Qt.UserRole, snippet)

    def filter_snippets(self, query: str):
        """Filter snippets based on search query"""
        if not query:
            # Show all snippets
            self.populate_snippets()
            return

        self.tree.clear()

        # Search snippets
        results = self.snippets_manager.search_snippets(query)

        # Group by category
        categories = {}
        for snippet in results:
            if snippet.category not in categories:
                categories[snippet.category] = []
            categories[snippet.category].append(snippet)

        # Populate tree with results
        for category, snippets in categories.items():
            category_item = QTreeWidgetItem(self.tree)
            category_item.setText(0, f"📁 {category}")
            category_item.setExpanded(True)

            for snippet in snippets:
                snippet_item = QTreeWidgetItem(category_item)
                snippet_item.setText(0, f"📄 {snippet.name}")
                snippet_item.setData(0, Qt.UserRole, snippet)

    def on_selection_changed(self):
        """Handle selection change in tree"""
        selected_items = self.tree.selectedItems()

        if not selected_items:
            self.preview.clear()
            self.description_label.clear()
            self.insert_button.setEnabled(False)
            return

        item = selected_items[0]
        snippet = item.data(0, Qt.UserRole)

        if snippet:
            # Show snippet preview
            self.preview.setPlainText(snippet.get_body_text())
            self.description_label.setText(f"Prefix: {snippet.prefix} - {snippet.description}")
            self.insert_button.setEnabled(True)
        else:
            # Category selected
            self.preview.clear()
            self.description_label.clear()
            self.insert_button.setEnabled(False)

    def on_item_double_clicked(self, item, column):
        """Handle double-click on snippet"""
        snippet = item.data(0, Qt.UserRole)
        if snippet:
            self.insert_selected_snippet()

    def insert_selected_snippet(self):
        """Insert the selected snippet"""
        selected_items = self.tree.selectedItems()

        if not selected_items:
            return

        item = selected_items[0]
        snippet = item.data(0, Qt.UserRole)

        if snippet:
            self.snippet_insert_requested.emit(snippet)

    def get_selected_snippet(self):
        """Get the currently selected snippet"""
        selected_items = self.tree.selectedItems()

        if not selected_items:
            return None

        item = selected_items[0]
        return item.data(0, Qt.UserRole)
