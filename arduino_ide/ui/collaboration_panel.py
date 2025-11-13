"""
Collaboration Panel
UI for real-time collaboration features
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QListWidget, QListWidgetItem, QPushButton, QLabel,
                               QLineEdit, QTextEdit, QInputDialog, QMessageBox,
                               QGroupBox, QCheckBox, QComboBox)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor
import logging
from typing import Optional

from arduino_ide.services.collaboration_service import (
    CollaborationService, CollaboratorInfo, ChatMessage,
    SharedProject, UserRole, CollaborationMode
)

logger = logging.getLogger(__name__)


class CollaboratorsWidget(QWidget):
    """Widget showing active collaborators"""

    def __init__(self, service: CollaborationService, parent=None):
        super().__init__(parent)

        self.service = service

        self._setup_ui()
        self._setup_connections()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Title
        layout.addWidget(QLabel("Active Collaborators:"))

        # Collaborators list
        self.collaborators_list = QListWidget()
        layout.addWidget(self.collaborators_list)


    def _setup_connections(self):
        """Setup connections"""
        self.service.collaborator_joined.connect(self._on_collaborator_joined)
        self.service.collaborator_left.connect(self._on_collaborator_left)


    def refresh_collaborators(self):
        """Refresh collaborators list"""
        self.collaborators_list.clear()

        for collaborator in self.service.get_collaborators():
            text = f"{collaborator.username} ({collaborator.role.value})"
            if not collaborator.online:
                text += " [Offline]"

            item = QListWidgetItem(text)

            # Color based on role
            if collaborator.role == UserRole.OWNER:
                item.setForeground(QColor("#E74C3C"))
            elif collaborator.role == UserRole.EDITOR:
                item.setForeground(QColor("#3498DB"))
            else:
                item.setForeground(QColor("#95A5A6"))

            self.collaborators_list.addItem(item)


    @Slot(CollaboratorInfo)
    def _on_collaborator_joined(self, collaborator: CollaboratorInfo):
        """Handle collaborator joined"""
        self.refresh_collaborators()


    @Slot(str)
    def _on_collaborator_left(self, user_id: str):
        """Handle collaborator left"""
        self.refresh_collaborators()


class ChatWidget(QWidget):
    """Chat widget for collaboration"""

    def __init__(self, service: CollaborationService, parent=None):
        super().__init__(parent)

        self.service = service

        self._setup_ui()
        self._setup_connections()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        layout.addWidget(self.chat_history)

        # Message input
        input_layout = QHBoxLayout()

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")

        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
        """)

        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)


    def _setup_connections(self):
        """Setup connections"""
        self.send_btn.clicked.connect(self._on_send_message)
        self.message_input.returnPressed.connect(self._on_send_message)

        self.service.chat_message_received.connect(self._on_message_received)


    @Slot()
    def _on_send_message(self):
        """Send chat message"""
        text = self.message_input.text().strip()
        if text:
            self.service.send_chat_message(text)
            self.message_input.clear()


    @Slot(ChatMessage)
    def _on_message_received(self, message: ChatMessage):
        """Display received message"""
        timestamp = message.timestamp.strftime("%H:%M")
        self.chat_history.append(f"[{timestamp}] {message.username}: {message.text}")


class SharedProjectsWidget(QWidget):
    """Widget for managing shared projects"""

    def __init__(self, service: CollaborationService, parent=None):
        super().__init__(parent)

        self.service = service

        self._setup_ui()
        self._setup_connections()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        self.share_btn = QPushButton("Share Project")
        self.unshare_btn = QPushButton("Unshare")
        self.refresh_btn = QPushButton("Refresh")

        toolbar.addWidget(self.share_btn)
        toolbar.addWidget(self.unshare_btn)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Projects list
        layout.addWidget(QLabel("Shared Projects:"))
        self.projects_list = QListWidget()
        layout.addWidget(self.projects_list)


    def _setup_connections(self):
        """Setup connections"""
        self.share_btn.clicked.connect(self._on_share_project)
        self.unshare_btn.clicked.connect(self._on_unshare_project)
        self.refresh_btn.clicked.connect(self.refresh_projects)

        self.service.project_shared.connect(self._on_project_shared)
        self.service.project_unshared.connect(self._on_project_unshared)


    def refresh_projects(self):
        """Refresh projects list"""
        self.projects_list.clear()

        for project in self.service.get_shared_projects():
            text = f"{project.name} (Owner: {project.owner_id})"
            if project.public:
                text += " [Public]"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, project.project_id)

            self.projects_list.addItem(item)


    @Slot()
    def _on_share_project(self):
        """Share current project"""
        default_name = self.service.get_active_project_name() or ""
        name, ok = QInputDialog.getText(
            self,
            "Share Project",
            "Project name:",
            text=default_name,
        )

        if ok and name:
            description, ok = QInputDialog.getText(self, "Share Project", "Description (optional):")

            if ok:
                self.service.share_project(name, description or "", public=False)


    @Slot()
    def _on_unshare_project(self):
        """Unshare selected project"""
        current_item = self.projects_list.currentItem()
        if not current_item:
            return

        project_id = current_item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Unshare Project",
            "Stop sharing this project?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.service.unshare_project(project_id)


    @Slot(SharedProject)
    def _on_project_shared(self, project: SharedProject):
        """Handle project shared"""
        self.refresh_projects()


    @Slot(str)
    def _on_project_unshared(self, project_id: str):
        """Handle project unshared"""
        self.refresh_projects()


class SessionControlWidget(QWidget):
    """Widget for starting/stopping collaboration sessions"""

    def __init__(self, service: CollaborationService, parent=None):
        super().__init__(parent)

        self.service = service

        self._session_active = False

        self._setup_ui()
        self._setup_connections()


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)

        # Session controls
        group_box = QGroupBox("Collaboration Session")
        group_layout = QVBoxLayout(group_box)

        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Peer-to-Peer", CollaborationMode.PEER_TO_PEER)
        self.mode_combo.addItem("Server-Based", CollaborationMode.SERVER_BASED)

        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()

        group_layout.addLayout(mode_layout)

        # Start/Stop buttons
        buttons_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Session")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
        """)

        self.stop_btn = QPushButton("End Session")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
        """)
        self.stop_btn.setEnabled(False)

        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)

        group_layout.addLayout(buttons_layout)

        # Session info
        self.session_label = QLabel("No active session")
        self.session_label.setStyleSheet("padding: 5px; font-style: italic;")
        group_layout.addWidget(self.session_label)

        layout.addWidget(group_box)

        # Join session
        join_group = QGroupBox("Join Session")
        join_layout = QVBoxLayout(join_group)

        session_id_layout = QHBoxLayout()
        session_id_layout.addWidget(QLabel("Session ID:"))

        self.session_id_input = QLineEdit()
        self.session_id_input.setPlaceholderText("Enter session ID...")

        session_id_layout.addWidget(self.session_id_input)

        join_layout.addLayout(session_id_layout)

        self.join_btn = QPushButton("Join Session")
        join_layout.addWidget(self.join_btn)

        layout.addWidget(join_group)

        layout.addStretch()


    def _setup_connections(self):
        """Setup connections"""
        self.start_btn.clicked.connect(self._on_start_session)
        self.stop_btn.clicked.connect(self._on_stop_session)
        self.join_btn.clicked.connect(self._on_join_session)

        self.service.collaboration_started.connect(self._on_session_started)
        self.service.collaboration_ended.connect(self._on_session_ended)


    @Slot()
    def _on_start_session(self):
        """Start collaboration session"""
        mode_data = self.mode_combo.currentData()

        session_id = self.service.start_collaboration_session(mode_data)

        if session_id:
            QMessageBox.information(
                self,
                "Session Started",
                f"Collaboration session started!\n\nSession ID: {session_id}\n\nShare this ID with collaborators."
            )


    @Slot()
    def _on_stop_session(self):
        """Stop collaboration session"""
        reply = QMessageBox.question(
            self,
            "End Session",
            "End collaboration session?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.service.end_collaboration_session()


    @Slot()
    def _on_join_session(self):
        """Join a collaboration session"""
        session_id = self.session_id_input.text().strip()

        if not session_id:
            QMessageBox.warning(self, "Error", "Please enter a session ID")
            return

        if self.service.join_session(session_id):
            QMessageBox.information(self, "Success", "Joined collaboration session!")
            self.session_id_input.clear()


    @Slot(str)
    def _on_session_started(self, session_id: str):
        """Handle session started"""
        self._session_active = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.join_btn.setEnabled(False)
        self.mode_combo.setEnabled(False)

        self.session_label.setText(f"Active session: {session_id}")
        self.session_label.setStyleSheet("padding: 5px; color: #4CAF50; font-weight: bold;")


    @Slot()
    def _on_session_ended(self):
        """Handle session ended"""
        self._session_active = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.join_btn.setEnabled(True)
        self.mode_combo.setEnabled(True)

        self.session_label.setText("No active session")
        self.session_label.setStyleSheet("padding: 5px; font-style: italic; color: #888;")


class CollaborationPanel(QWidget):
    """
    Main collaboration panel
    """

    def __init__(self, service: Optional[CollaborationService] = None, parent=None):
        super().__init__(parent)

        self.service = service or CollaborationService()

        self._setup_ui()

        logger.info("Collaboration panel initialized")


    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Collaboration")
        title.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        layout.addWidget(title)

        # Tabs
        tabs = QTabWidget()

        # Session tab
        self.session_widget = SessionControlWidget(self.service)
        tabs.addTab(self.session_widget, "Session")

        # Collaborators tab
        self.collaborators_widget = CollaboratorsWidget(self.service)
        tabs.addTab(self.collaborators_widget, "Collaborators")

        # Chat tab
        self.chat_widget = ChatWidget(self.service)
        tabs.addTab(self.chat_widget, "Chat")

        # Projects tab
        self.projects_widget = SharedProjectsWidget(self.service)
        tabs.addTab(self.projects_widget, "Projects")

        layout.addWidget(tabs)


    def set_current_user(self, user_id: str, username: str):
        """Set current user"""
        self.service.set_current_user(user_id, username)


    def set_project(self, project_path: Optional[str], project_name: Optional[str] = None):
        """Update the active project used by collaboration features."""

        self.service.set_project(project_path, project_name)


    def refresh_all(self):
        """Refresh all widgets"""
        self.collaborators_widget.refresh_collaborators()
        self.projects_widget.refresh_projects()
