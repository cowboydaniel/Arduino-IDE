"""Dialog wrapper for the CI/CD panel."""

from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout

from arduino_ide.services.cicd_service import CICDService
from arduino_ide.ui.cicd_panel import CICDPanel


class CICDDialog(QDialog):
    """Non-modal dialog hosting the CI/CD management panel."""

    def __init__(self, parent=None, cicd_service: Optional[CICDService] = None):
        super().__init__(parent)

        self.setWindowTitle("CI/CD")
        self.setWindowModality(Qt.NonModal)

        self.cicd_service = cicd_service or CICDService()
        self.cicd_panel = CICDPanel(self.cicd_service)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.cicd_panel)

        self._workspace_settings: Dict[str, str] = {}

    def update_context(
        self,
        project_path: Optional[str] = None,
        workspace_settings: Optional[Dict[str, str]] = None,
    ):
        """Apply project and workspace data to the embedded panel."""

        if project_path:
            self.cicd_service.set_project_path(project_path)

        if workspace_settings:
            self._workspace_settings = dict(workspace_settings)
            self.cicd_panel.apply_workspace_settings(self._workspace_settings)
        elif self._workspace_settings:
            # Re-apply any previously stored settings if none were provided.
            self.cicd_panel.apply_workspace_settings(self._workspace_settings)

    def refresh_now(self):
        """Trigger an immediate refresh of pipeline information."""

        self.cicd_panel.refresh_pipelines()
