"""Dialog wrapper for the collaboration panel."""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout

from arduino_ide.services.collaboration_service import CollaborationService
from arduino_ide.ui.collaboration_panel import CollaborationPanel


class CollaborationDialog(QDialog):
    """Non-modal dialog hosting the collaboration UI."""

    def __init__(
        self,
        parent=None,
        collaboration_service: Optional[CollaborationService] = None,
    ):
        super().__init__(parent)

        self.setWindowTitle("Collaboration")
        self.setWindowModality(Qt.NonModal)

        self.collaboration_service = collaboration_service or CollaborationService(self)
        self.collaboration_panel = CollaborationPanel(self.collaboration_service, parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.collaboration_panel)

    # ------------------------------------------------------------------
    # Context synchronization helpers
    # ------------------------------------------------------------------

    def set_current_user(self, user_id: str, username: str) -> None:
        """Ensure the collaboration service tracks the active user."""

        if not user_id or not username:
            return

        current = self.collaboration_service.get_current_user()
        if current and current.user_id == user_id and current.username == username:
            return

        self.collaboration_panel.set_current_user(user_id, username)
        self.collaboration_panel.collaborators_widget.refresh_collaborators()

    def set_project(
        self,
        project_path: Optional[str],
        project_name: Optional[str] = None,
    ) -> None:
        """Update the active project context for collaboration."""

        self.collaboration_panel.set_project(project_path, project_name)

    def initialize_session(self) -> None:
        """Refresh panel data to reflect the current collaboration context."""

        self.collaboration_panel.refresh_all()

    def get_session_context(self) -> Tuple[Optional[str], Optional[str]]:
        """Return the currently configured collaboration project context."""

        return self.collaboration_service.get_active_project()
