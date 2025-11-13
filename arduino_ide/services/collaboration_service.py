"""
Collaboration Service
Enables real-time collaboration, project sharing, and team features
"""

import json
import logging
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtNetwork import QTcpSocket, QHostAddress

logger = logging.getLogger(__name__)


class CollaborationMode(Enum):
    """Collaboration modes"""
    OFFLINE = "offline"
    PEER_TO_PEER = "peer_to_peer"
    SERVER_BASED = "server_based"


class UserRole(Enum):
    """User roles in collaboration"""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


@dataclass
class CollaboratorInfo:
    """Information about a collaborator"""
    user_id: str
    username: str
    role: UserRole
    online: bool = False
    cursor_position: Optional[tuple] = None  # (line, column)
    last_active: datetime = field(default_factory=datetime.now)
    color: str = "#3498DB"  # Display color for cursor/highlights


@dataclass
class TextChange:
    """Represents a text change in collaborative editing"""
    change_id: str
    user_id: str
    timestamp: float
    file_path: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    operation: str  # 'insert', 'delete', 'replace'
    text: str = ""
    version: int = 0


@dataclass
class SharedProject:
    """Represents a shared project"""
    project_id: str
    name: str
    owner_id: str
    collaborators: List[CollaboratorInfo] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    description: str = ""
    public: bool = False


@dataclass
class ChatMessage:
    """Chat message in collaboration session"""
    message_id: str
    user_id: str
    username: str
    text: str
    timestamp: datetime = field(default_factory=datetime.now)


class CollaborationService(QObject):
    """
    Service for real-time collaboration features
    Supports peer-to-peer and server-based collaboration
    """

    # Signals
    collaboration_started = Signal(str)  # session_id
    collaboration_ended = Signal()
    collaborator_joined = Signal(CollaboratorInfo)
    collaborator_left = Signal(str)  # user_id
    collaborator_updated = Signal(CollaboratorInfo)

    text_change_received = Signal(TextChange)
    cursor_updated = Signal(str, int, int)  # user_id, line, column

    chat_message_received = Signal(ChatMessage)

    project_shared = Signal(SharedProject)
    project_unshared = Signal(str)  # project_id

    sync_completed = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_user: Optional[CollaboratorInfo] = None
        self._session_id: Optional[str] = None
        self._mode = CollaborationMode.OFFLINE

        # Collaboration state
        self._collaborators: Dict[str, CollaboratorInfo] = {}
        self._shared_projects: Dict[str, SharedProject] = {}

        # Change tracking
        self._pending_changes: List[TextChange] = []
        self._change_history: List[TextChange] = []
        self._document_version = 0

        # Chat
        self._chat_history: List[ChatMessage] = []

        # Active project context
        self._active_project_path: Optional[str] = None
        self._active_project_name: Optional[str] = None

        # Network (for future implementation)
        self._socket: Optional[QTcpSocket] = None
        self._server_address = ""
        self._server_port = 0

        # Heartbeat timer
        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)
        self._heartbeat_interval = 30000  # 30 seconds

        logger.info("Collaboration service initialized")


    def set_current_user(self, user_id: str, username: str):
        """Set current user information"""
        self._current_user = CollaboratorInfo(
            user_id=user_id,
            username=username,
            role=UserRole.OWNER,
            online=True
        )

        logger.info(f"Current user set: {username} ({user_id})")


    def get_current_user(self) -> Optional[CollaboratorInfo]:
        """Get current user"""
        return self._current_user


    # ===== Session Management =====

    def start_collaboration_session(self, mode: CollaborationMode = CollaborationMode.PEER_TO_PEER) -> str:
        """
        Start a new collaboration session
        Returns session_id
        """
        if not self._current_user:
            logger.error("Cannot start session: No user set")
            self.error_occurred.emit("No user configured")
            return ""

        # Generate session ID
        self._session_id = hashlib.sha256(
            f"{self._current_user.user_id}_{time.time()}".encode()
        ).hexdigest()[:16]

        self._mode = mode
        self._collaborators = {self._current_user.user_id: self._current_user}

        # Start heartbeat
        self._heartbeat_timer.start(self._heartbeat_interval)

        self.collaboration_started.emit(self._session_id)
        logger.info(f"Collaboration session started: {self._session_id} ({mode.value})")

        return self._session_id


    def end_collaboration_session(self):
        """End current collaboration session"""
        if not self._session_id:
            return

        # Stop heartbeat
        self._heartbeat_timer.stop()

        # Notify collaborators
        self._broadcast_event("session_ended", {})

        # Clear state
        self._session_id = None
        self._mode = CollaborationMode.OFFLINE
        self._collaborators.clear()

        self.collaboration_ended.emit()
        logger.info("Collaboration session ended")


    def join_session(self, session_id: str, server_address: str = "", port: int = 0) -> bool:
        """Join an existing collaboration session"""
        if not self._current_user:
            logger.error("Cannot join session: No user set")
            return False

        self._session_id = session_id
        self._server_address = server_address
        self._server_port = port

        # Connect to server/peer
        if server_address and port:
            success = self._connect_to_server(server_address, port)
            if not success:
                return False

        # Send join request
        self._send_event("join_session", {
            "user_id": self._current_user.user_id,
            "username": self._current_user.username
        })

        self.collaboration_started.emit(session_id)
        logger.info(f"Joined collaboration session: {session_id}")

        return True


    def leave_session(self):
        """Leave current collaboration session"""
        if not self._session_id:
            return

        # Notify other collaborators
        self._send_event("leave_session", {
            "user_id": self._current_user.user_id
        })

        self.end_collaboration_session()


    # ===== Collaborator Management =====

    def get_collaborators(self) -> List[CollaboratorInfo]:
        """Get list of active collaborators"""
        return list(self._collaborators.values())


    def add_collaborator(self, collaborator: CollaboratorInfo):
        """Add a collaborator to the session"""
        self._collaborators[collaborator.user_id] = collaborator
        self.collaborator_joined.emit(collaborator)

        logger.info(f"Collaborator joined: {collaborator.username} ({collaborator.user_id})")


    def remove_collaborator(self, user_id: str):
        """Remove a collaborator from the session"""
        if user_id in self._collaborators:
            del self._collaborators[user_id]
            self.collaborator_left.emit(user_id)

            logger.info(f"Collaborator left: {user_id}")


    def update_collaborator_cursor(self, user_id: str, line: int, column: int):
        """Update collaborator cursor position"""
        if user_id in self._collaborators:
            collaborator = self._collaborators[user_id]
            collaborator.cursor_position = (line, column)
            collaborator.last_active = datetime.now()

            self.collaborator_updated.emit(collaborator)
            self.cursor_updated.emit(user_id, line, column)


    # ===== Real-time Editing =====

    def create_text_change(self, file_path: str, start_line: int, start_column: int,
                          end_line: int, end_column: int, operation: str, text: str = "") -> TextChange:
        """Create a text change event"""
        if not self._current_user:
            raise ValueError("No current user set")

        change_id = hashlib.sha256(
            f"{self._current_user.user_id}_{time.time()}_{file_path}".encode()
        ).hexdigest()[:16]

        change = TextChange(
            change_id=change_id,
            user_id=self._current_user.user_id,
            timestamp=time.time(),
            file_path=file_path,
            start_line=start_line,
            start_column=start_column,
            end_line=end_line,
            end_column=end_column,
            operation=operation,
            text=text,
            version=self._document_version
        )

        self._document_version += 1

        return change


    def apply_text_change(self, change: TextChange):
        """Apply a text change locally"""
        self._pending_changes.append(change)
        self._change_history.append(change)

        # Broadcast to collaborators
        if self._session_id:
            self._broadcast_text_change(change)


    def _broadcast_text_change(self, change: TextChange):
        """Broadcast text change to collaborators"""
        data = {
            "change_id": change.change_id,
            "user_id": change.user_id,
            "timestamp": change.timestamp,
            "file_path": change.file_path,
            "start_line": change.start_line,
            "start_column": change.start_column,
            "end_line": change.end_line,
            "end_column": change.end_column,
            "operation": change.operation,
            "text": change.text,
            "version": change.version
        }

        self._broadcast_event("text_change", data)


    def handle_received_text_change(self, data: Dict):
        """Handle received text change from collaborator"""
        change = TextChange(
            change_id=data["change_id"],
            user_id=data["user_id"],
            timestamp=data["timestamp"],
            file_path=data["file_path"],
            start_line=data["start_line"],
            start_column=data["start_column"],
            end_line=data["end_line"],
            end_column=data["end_column"],
            operation=data["operation"],
            text=data.get("text", ""),
            version=data["version"]
        )

        self._change_history.append(change)
        self.text_change_received.emit(change)


    # ===== Chat =====

    def send_chat_message(self, text: str):
        """Send a chat message"""
        if not self._current_user or not self._session_id:
            return

        message_id = hashlib.sha256(
            f"{self._current_user.user_id}_{time.time()}".encode()
        ).hexdigest()[:16]

        message = ChatMessage(
            message_id=message_id,
            user_id=self._current_user.user_id,
            username=self._current_user.username,
            text=text
        )

        self._chat_history.append(message)
        self.chat_message_received.emit(message)

        # Broadcast to collaborators
        self._broadcast_event("chat_message", {
            "message_id": message.message_id,
            "user_id": message.user_id,
            "username": message.username,
            "text": text,
            "timestamp": message.timestamp.isoformat()
        })

        logger.debug(f"Chat message sent: {text[:50]}")


    def get_chat_history(self) -> List[ChatMessage]:
        """Get chat message history"""
        return self._chat_history.copy()


    # ===== Project Context =====

    def set_project(self, project_path: Optional[str], project_name: Optional[str] = None):
        """Set or clear the active project for collaboration features."""

        normalized_path: Optional[str]
        if project_path:
            try:
                normalized_path = str(Path(project_path).resolve())
            except Exception:  # pragma: no cover - guard against invalid paths
                normalized_path = str(project_path)
        else:
            normalized_path = None

        resolved_name: Optional[str] = project_name
        if not resolved_name and normalized_path:
            resolved_name = Path(normalized_path).name

        state_changed = (
            normalized_path != self._active_project_path
            or resolved_name != self._active_project_name
        )

        self._active_project_path = normalized_path
        self._active_project_name = resolved_name

        if state_changed:
            if normalized_path:
                logger.info(
                    "Active collaboration project set: %s (%s)",
                    resolved_name or "",
                    normalized_path,
                )
            else:
                logger.info("Cleared active collaboration project context")

    def get_active_project(self) -> tuple[Optional[str], Optional[str]]:
        """Return the active project path and name."""

        return self._active_project_path, self._active_project_name

    def get_active_project_path(self) -> Optional[str]:
        """Return the active project path if available."""

        return self._active_project_path

    def get_active_project_name(self) -> Optional[str]:
        """Return the active project name if available."""

        return self._active_project_name


    # ===== Project Sharing =====

    def share_project(
        self,
        project_name: Optional[str] = None,
        description: str = "",
        public: bool = False,
    ) -> SharedProject:
        """Share a project for collaboration"""
        if not self._current_user:
            raise ValueError("No current user set")

        if not project_name:
            project_name = self._active_project_name or "Untitled Project"

        project_id = hashlib.sha256(
            f"{self._current_user.user_id}_{project_name}_{time.time()}".encode()
        ).hexdigest()[:16]

        project = SharedProject(
            project_id=project_id,
            name=project_name,
            owner_id=self._current_user.user_id,
            collaborators=[self._current_user],
            description=description,
            public=public
        )

        self._shared_projects[project_id] = project
        self.project_shared.emit(project)

        logger.info(f"Project shared: {project_name} ({project_id})")

        return project


    def unshare_project(self, project_id: str):
        """Stop sharing a project"""
        if project_id in self._shared_projects:
            del self._shared_projects[project_id]
            self.project_unshared.emit(project_id)

            logger.info(f"Project unshared: {project_id}")


    def get_shared_projects(self) -> List[SharedProject]:
        """Get list of shared projects"""
        return list(self._shared_projects.values())


    def invite_to_project(self, project_id: str, user_id: str, role: UserRole = UserRole.EDITOR):
        """Invite a user to a shared project"""
        if project_id not in self._shared_projects:
            logger.error(f"Project not found: {project_id}")
            return

        project = self._shared_projects[project_id]

        # Check if user is already a collaborator
        if any(c.user_id == user_id for c in project.collaborators):
            logger.warning(f"User already invited: {user_id}")
            return

        # Create invitation (simplified - actual implementation would send invite)
        logger.info(f"Invited user {user_id} to project {project.name} as {role.value}")


    # ===== Network Communication =====

    def _connect_to_server(self, address: str, port: int) -> bool:
        """Connect to collaboration server"""
        # Simplified implementation
        # In production, this would establish WebSocket or TCP connection
        logger.info(f"Connecting to server: {address}:{port}")

        # For now, just simulate success
        return True


    def _send_event(self, event_type: str, data: Dict):
        """Send an event to server/peers"""
        message = {
            "type": event_type,
            "session_id": self._session_id,
            "user_id": self._current_user.user_id if self._current_user else None,
            "timestamp": time.time(),
            "data": data
        }

        # In production, send via WebSocket or TCP
        logger.debug(f"Sending event: {event_type}")


    def _broadcast_event(self, event_type: str, data: Dict):
        """Broadcast an event to all collaborators"""
        self._send_event(event_type, data)


    def _send_heartbeat(self):
        """Send heartbeat to keep connection alive"""
        if self._session_id and self._current_user:
            self._send_event("heartbeat", {
                "user_id": self._current_user.user_id
            })


    # ===== Synchronization =====

    def sync_with_server(self):
        """Synchronize local changes with server"""
        if not self._session_id:
            return

        # Send pending changes
        for change in self._pending_changes:
            self._broadcast_text_change(change)

        self._pending_changes.clear()
        self.sync_completed.emit()

        logger.info("Synchronized with server")


    def request_full_sync(self):
        """Request full document sync from server"""
        if not self._session_id:
            return

        self._send_event("request_sync", {})
        logger.info("Requested full sync")


    # ===== Export/Import =====

    def export_session_data(self) -> Dict:
        """Export session data for backup"""
        return {
            "session_id": self._session_id,
            "collaborators": [
                {
                    "user_id": c.user_id,
                    "username": c.username,
                    "role": c.role.value
                }
                for c in self._collaborators.values()
            ],
            "change_history": len(self._change_history),
            "chat_messages": len(self._chat_history)
        }


    def get_session_statistics(self) -> Dict:
        """Get statistics about current session"""
        return {
            "session_id": self._session_id,
            "mode": self._mode.value if self._mode else "offline",
            "collaborators_count": len(self._collaborators),
            "total_changes": len(self._change_history),
            "pending_changes": len(self._pending_changes),
            "chat_messages": len(self._chat_history),
            "document_version": self._document_version
        }
