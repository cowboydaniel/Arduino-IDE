"""
Git Panel
UI for Git version control operations
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QPushButton, QLabel, QLineEdit, QTextEdit,
                               QListWidget, QListWidgetItem, QMessageBox,
                               QInputDialog, QSplitter)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor
import logging
from typing import Optional

from arduino_ide.services.git_service import GitService, GitCommit, GitFileStatus, GitBranch

logger = logging.getLogger(__name__)


class GitChangesWidget(QWidget):
    """Widget showing file changes and staging"""

    def __init__(self, git_service: GitService, parent=None):
        super().__init__(parent)

        self.git_service = git_service

        self._setup_ui()
        self._setup_connections()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.stage_all_btn = QPushButton("Stage All")
        self.commit_btn = QPushButton("Commit")
        self.commit_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
        """)

        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.stage_all_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.commit_btn)

        layout.addLayout(toolbar)

        # Changes table
        self.changes_table = QTableWidget()
        self.changes_table.setColumnCount(3)
        self.changes_table.setHorizontalHeaderLabels(["File", "Status", "Staged"])

        header = self.changes_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.changes_table.verticalHeader().setVisible(False)
        self.changes_table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(QLabel("Modified Files:"))
        layout.addWidget(self.changes_table)


    def _setup_connections(self):
        """Setup connections"""
        self.refresh_btn.clicked.connect(self.refresh_status)
        self.stage_all_btn.clicked.connect(self._on_stage_all)
        self.commit_btn.clicked.connect(self._on_commit)


    def refresh_status(self):
        """Refresh Git status"""
        self.changes_table.setRowCount(0)

        file_statuses = self.git_service.get_status()

        for status in file_statuses:
            row = self.changes_table.rowCount()
            self.changes_table.insertRow(row)

            # File path
            path_item = QTableWidgetItem(status.path)
            self.changes_table.setItem(row, 0, path_item)

            # Status
            status_text = {
                'M': 'Modified',
                'A': 'Added',
                'D': 'Deleted',
                '?': 'Untracked',
                'R': 'Renamed',
                'C': 'Copied'
            }.get(status.status, status.status)

            status_item = QTableWidgetItem(status_text)
            self.changes_table.setItem(row, 1, status_item)

            # Staged checkbox
            staged_item = QTableWidgetItem("Yes" if status.staged else "No")
            self.changes_table.setItem(row, 2, staged_item)


    @Slot()
    def _on_stage_all(self):
        """Stage all changes"""
        if self.git_service.add_all():
            self.refresh_status()


    @Slot()
    def _on_commit(self):
        """Create a commit"""
        message, ok = QInputDialog.getMultiLineText(
            self,
            "Commit Changes",
            "Commit message:"
        )

        if ok and message:
            commit_hash = self.git_service.commit(message)
            if commit_hash:
                QMessageBox.information(self, "Success", f"Created commit: {commit_hash[:7]}")
                self.refresh_status()


class GitHistoryWidget(QWidget):
    """Widget showing commit history"""

    def __init__(self, git_service: GitService, parent=None):
        super().__init__(parent)

        self.git_service = git_service

        self._setup_ui()
        self._setup_connections()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Hash", "Author", "Date", "Message"])

        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.history_table)


    def _setup_connections(self):
        """Setup connections"""
        self.refresh_btn.clicked.connect(self.refresh_history)


    def refresh_history(self):
        """Refresh commit history"""
        self.history_table.setRowCount(0)

        commits = self.git_service.get_commit_history(max_count=50)

        for commit in commits:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)

            # Hash
            hash_item = QTableWidgetItem(commit.short_hash)
            self.history_table.setItem(row, 0, hash_item)

            # Author
            author_item = QTableWidgetItem(commit.author)
            self.history_table.setItem(row, 1, author_item)

            # Date
            date_item = QTableWidgetItem(commit.date.strftime("%Y-%m-%d %H:%M"))
            self.history_table.setItem(row, 2, date_item)

            # Message
            message_item = QTableWidgetItem(commit.message)
            self.history_table.setItem(row, 3, message_item)


class GitBranchesWidget(QWidget):
    """Widget for branch management"""

    def __init__(self, git_service: GitService, parent=None):
        super().__init__(parent)

        self.git_service = git_service

        self._setup_ui()
        self._setup_connections()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.new_branch_btn = QPushButton("New Branch")
        self.checkout_btn = QPushButton("Checkout")
        self.delete_btn = QPushButton("Delete")

        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.new_branch_btn)
        toolbar.addWidget(self.checkout_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Branches list
        self.branches_list = QListWidget()
        layout.addWidget(self.branches_list)


    def _setup_connections(self):
        """Setup connections"""
        self.refresh_btn.clicked.connect(self.refresh_branches)
        self.new_branch_btn.clicked.connect(self._on_new_branch)
        self.checkout_btn.clicked.connect(self._on_checkout)
        self.delete_btn.clicked.connect(self._on_delete)


    def refresh_branches(self):
        """Refresh branches list"""
        self.branches_list.clear()

        branches = self.git_service.get_branches()

        for branch in branches:
            if branch.is_remote:
                continue

            item = QListWidgetItem(branch.name)

            if branch.is_current:
                font = QFont()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#4CAF50"))

            self.branches_list.addItem(item)


    @Slot()
    def _on_new_branch(self):
        """Create new branch"""
        name, ok = QInputDialog.getText(self, "New Branch", "Branch name:")

        if ok and name:
            if self.git_service.create_branch(name, checkout=True):
                QMessageBox.information(self, "Success", f"Created and checked out branch: {name}")
                self.refresh_branches()


    @Slot()
    def _on_checkout(self):
        """Checkout selected branch"""
        current_item = self.branches_list.currentItem()
        if not current_item:
            return

        branch_name = current_item.text()

        if self.git_service.checkout_branch(branch_name):
            self.refresh_branches()


    @Slot()
    def _on_delete(self):
        """Delete selected branch"""
        current_item = self.branches_list.currentItem()
        if not current_item:
            return

        branch_name = current_item.text()

        reply = QMessageBox.question(
            self,
            "Delete Branch",
            f"Delete branch '{branch_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.git_service.delete_branch(branch_name):
                self.refresh_branches()


class GitRemotesWidget(QWidget):
    """Widget for remote management"""

    def __init__(self, git_service: GitService, parent=None):
        super().__init__(parent)

        self.git_service = git_service

        self._setup_ui()
        self._setup_connections()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.fetch_btn = QPushButton("Fetch")
        self.pull_btn = QPushButton("Pull")
        self.push_btn = QPushButton("Push")
        self.push_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
            }
        """)

        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.fetch_btn)
        toolbar.addWidget(self.pull_btn)
        toolbar.addWidget(self.push_btn)

        layout.addLayout(toolbar)

        # Remotes list
        self.remotes_list = QListWidget()
        layout.addWidget(QLabel("Remotes:"))
        layout.addWidget(self.remotes_list)


    def _setup_connections(self):
        """Setup connections"""
        self.refresh_btn.clicked.connect(self.refresh_remotes)
        self.fetch_btn.clicked.connect(self._on_fetch)
        self.pull_btn.clicked.connect(self._on_pull)
        self.push_btn.clicked.connect(self._on_push)


    def refresh_remotes(self):
        """Refresh remotes list"""
        self.remotes_list.clear()

        remotes = self.git_service.get_remotes()

        for remote in remotes:
            item = QListWidgetItem(f"{remote.name}: {remote.url}")
            self.remotes_list.addItem(item)


    @Slot()
    def _on_fetch(self):
        """Fetch from remote"""
        if self.git_service.fetch():
            QMessageBox.information(self, "Success", "Fetched from origin")


    @Slot()
    def _on_pull(self):
        """Pull from remote"""
        if self.git_service.pull():
            QMessageBox.information(self, "Success", "Pulled from origin")


    @Slot()
    def _on_push(self):
        """Push to remote"""
        if self.git_service.push():
            QMessageBox.information(self, "Success", "Pushed to origin")


class GitPanel(QWidget):
    """
    Main Git panel with tabs for different operations
    """

    def __init__(self, git_service: Optional[GitService] = None, parent=None):
        super().__init__(parent)

        self.git_service = git_service or GitService()

        self._setup_ui()

        logger.info("Git panel initialized")


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title_layout = QHBoxLayout()
        title = QLabel("Git Version Control")
        title.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        title_layout.addWidget(title)

        # Current branch indicator
        self.branch_label = QLabel()
        self.branch_label.setStyleSheet("padding: 5px; color: #4CAF50; font-weight: bold;")
        title_layout.addWidget(self.branch_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # Tabs
        tabs = QTabWidget()

        # Changes tab
        self.changes_widget = GitChangesWidget(self.git_service)
        tabs.addTab(self.changes_widget, "Changes")

        # History tab
        self.history_widget = GitHistoryWidget(self.git_service)
        tabs.addTab(self.history_widget, "History")

        # Branches tab
        self.branches_widget = GitBranchesWidget(self.git_service)
        tabs.addTab(self.branches_widget, "Branches")

        # Remotes tab
        self.remotes_widget = GitRemotesWidget(self.git_service)
        tabs.addTab(self.remotes_widget, "Remotes")

        layout.addWidget(tabs)

        # Update current branch
        self._update_branch_label()


    def _update_branch_label(self):
        """Update current branch label"""
        if self.git_service.is_repository():
            current_branch = self.git_service.get_current_branch()
            if current_branch:
                self.branch_label.setText(f"📍 {current_branch}")
            else:
                self.branch_label.setText("📍 (detached)")
        else:
            self.branch_label.setText("Not a Git repository")


    def refresh_all(self):
        """Refresh all tabs"""
        self.changes_widget.refresh_status()
        self.history_widget.refresh_history()
        self.branches_widget.refresh_branches()
        self.remotes_widget.refresh_remotes()
        self._update_branch_label()


    def set_repository_path(self, path: str):
        """Set repository path"""
        self.git_service.set_repository_path(path)
        self.refresh_all()
