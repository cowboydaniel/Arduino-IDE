"""
CI/CD Panel for Arduino IDE Modern

This panel provides a comprehensive UI for managing CI/CD pipelines.

Features:
- Pipeline status monitoring
- Build history
- Configuration generation
- Deployment management
- Build artifact access
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QComboBox, QCheckBox, QLineEdit, QTextEdit, QGroupBox,
    QToolBar, QSplitter, QProgressBar, QMessageBox, QFileDialog,
    QListWidget, QListWidgetItem
)
from PySide6.QtGui import QAction, QColor, QBrush, QIcon

from arduino_ide.services.cicd_service import (
    CICDService, Pipeline, BuildJob, BuildStatus, CICDPlatform,
    PipelineConfiguration, DeploymentEnvironment, Deployment
)


class PipelineTableWidget(QTableWidget):
    """Table widget for displaying pipelines"""

    pipeline_selected = Signal(str)  # pipeline_id

    def __init__(self):
        super().__init__()

        self.setColumnCount(7)
        self.setHorizontalHeaderLabels([
            "ID", "Name", "Branch", "Status", "Duration", "Started", "URL"
        ])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setAlternatingRowColors(True)

        self.itemSelectionChanged.connect(self._on_selection_changed)

        self.pipeline_rows: Dict[str, int] = {}

    def add_pipeline(self, pipeline: Pipeline):
        """Add a pipeline to the table"""
        row = self.rowCount()
        self.insertRow(row)

        # ID
        id_item = QTableWidgetItem(pipeline.id)
        id_item.setData(Qt.UserRole, pipeline.id)
        self.setItem(row, 0, id_item)

        # Name
        self.setItem(row, 1, QTableWidgetItem(pipeline.name))

        # Branch
        self.setItem(row, 2, QTableWidgetItem(pipeline.branch))

        # Status
        status_item = QTableWidgetItem(self._status_text(pipeline.status))
        self._update_status_color(status_item, pipeline.status)
        self.setItem(row, 3, status_item)

        # Duration
        duration_text = f"{pipeline.total_duration_seconds():.0f}s" if pipeline.total_duration_seconds() > 0 else ""
        self.setItem(row, 4, QTableWidgetItem(duration_text))

        # Started
        started_text = pipeline.started_at.strftime("%Y-%m-%d %H:%M") if pipeline.started_at else ""
        self.setItem(row, 5, QTableWidgetItem(started_text))

        # URL
        self.setItem(row, 6, QTableWidgetItem(pipeline.web_url))

        self.pipeline_rows[pipeline.id] = row

    def update_pipeline(self, pipeline: Pipeline):
        """Update pipeline in table"""
        if pipeline.id not in self.pipeline_rows:
            self.add_pipeline(pipeline)
            return

        row = self.pipeline_rows[pipeline.id]

        # Status
        status_item = self.item(row, 3)
        status_item.setText(self._status_text(pipeline.status))
        self._update_status_color(status_item, pipeline.status)

        # Duration
        duration_text = f"{pipeline.total_duration_seconds():.0f}s" if pipeline.total_duration_seconds() > 0 else ""
        self.item(row, 4).setText(duration_text)

    def _status_text(self, status: BuildStatus) -> str:
        """Get display text for status"""
        status_map = {
            BuildStatus.PENDING: "⏳ Pending",
            BuildStatus.RUNNING: "▶ Running",
            BuildStatus.SUCCESS: "✓ Success",
            BuildStatus.FAILED: "✗ Failed",
            BuildStatus.CANCELLED: "⊗ Cancelled",
            BuildStatus.SKIPPED: "⊘ Skipped"
        }
        return status_map.get(status, "⏳ Pending")

    def _update_status_color(self, item: QTableWidgetItem, status: BuildStatus):
        """Update status color"""
        color_map = {
            BuildStatus.SUCCESS: QColor(0, 150, 0),
            BuildStatus.FAILED: QColor(200, 0, 0),
            BuildStatus.RUNNING: QColor(0, 100, 200),
            BuildStatus.CANCELLED: QColor(150, 150, 0),
            BuildStatus.SKIPPED: QColor(100, 100, 100),
            BuildStatus.PENDING: QColor(100, 100, 100)
        }
        color = color_map.get(status, QColor(100, 100, 100))
        item.setForeground(QBrush(color))

    def _on_selection_changed(self):
        """Handle selection change"""
        selected_items = self.selectedItems()
        if selected_items:
            pipeline_id = selected_items[0].data(Qt.UserRole)
            if pipeline_id:
                self.pipeline_selected.emit(pipeline_id)

    def clear_pipelines(self):
        """Clear all pipelines"""
        self.setRowCount(0)
        self.pipeline_rows.clear()


class ConfigurationWidget(QWidget):
    """Widget for pipeline configuration"""

    config_changed = Signal()

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # Platform selection
        platform_group = QGroupBox("Platform")
        platform_layout = QVBoxLayout(platform_group)

        self.platform_combo = QComboBox()
        self.platform_combo.addItems([
            "GitHub Actions",
            "GitLab CI",
            "Jenkins",
            "Travis CI",
            "CircleCI",
            "Azure Pipelines"
        ])
        self.platform_combo.currentTextChanged.connect(self._on_config_changed)
        platform_layout.addWidget(self.platform_combo)

        layout.addWidget(platform_group)

        # Triggers
        triggers_group = QGroupBox("Triggers")
        triggers_layout = QVBoxLayout(triggers_group)

        self.push_trigger = QCheckBox("Push")
        self.push_trigger.setChecked(True)
        self.push_trigger.stateChanged.connect(self._on_config_changed)
        triggers_layout.addWidget(self.push_trigger)

        self.pr_trigger = QCheckBox("Pull Request")
        self.pr_trigger.setChecked(True)
        self.pr_trigger.stateChanged.connect(self._on_config_changed)
        triggers_layout.addWidget(self.pr_trigger)

        layout.addWidget(triggers_group)

        # Branches
        branches_group = QGroupBox("Branches")
        branches_layout = QVBoxLayout(branches_group)

        branches_layout.addWidget(QLabel("Trigger on branches (comma-separated):"))
        self.branches_input = QLineEdit("main,develop")
        self.branches_input.textChanged.connect(self._on_config_changed)
        branches_layout.addWidget(self.branches_input)

        layout.addWidget(branches_group)

        # Boards
        boards_group = QGroupBox("Target Boards")
        boards_layout = QVBoxLayout(boards_group)

        boards_layout.addWidget(QLabel("Boards to build for (comma-separated):"))
        self.boards_input = QLineEdit("arduino:avr:uno,arduino:avr:mega")
        self.boards_input.textChanged.connect(self._on_config_changed)
        boards_layout.addWidget(self.boards_input)

        layout.addWidget(boards_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.testing_check = QCheckBox("Enable Testing")
        self.testing_check.setChecked(True)
        self.testing_check.stateChanged.connect(self._on_config_changed)
        options_layout.addWidget(self.testing_check)

        self.linting_check = QCheckBox("Enable Linting")
        self.linting_check.setChecked(True)
        self.linting_check.stateChanged.connect(self._on_config_changed)
        options_layout.addWidget(self.linting_check)

        self.deployment_check = QCheckBox("Enable Deployment")
        self.deployment_check.stateChanged.connect(self._on_config_changed)
        options_layout.addWidget(self.deployment_check)

        layout.addWidget(options_group)

        # Generate button
        self.generate_btn = QPushButton("Generate Configuration")
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        layout.addWidget(self.generate_btn)

        layout.addStretch()

    def get_configuration(self) -> PipelineConfiguration:
        """Get current configuration"""
        platform_map = {
            "GitHub Actions": CICDPlatform.GITHUB_ACTIONS,
            "GitLab CI": CICDPlatform.GITLAB_CI,
            "Jenkins": CICDPlatform.JENKINS,
            "Travis CI": CICDPlatform.TRAVIS_CI,
            "CircleCI": CICDPlatform.CIRCLE_CI,
            "Azure Pipelines": CICDPlatform.AZURE_PIPELINES
        }

        config = PipelineConfiguration(
            platform=platform_map[self.platform_combo.currentText()]
        )

        # Triggers
        config.triggers = []
        if self.push_trigger.isChecked():
            config.triggers.append("push")
        if self.pr_trigger.isChecked():
            config.triggers.append("pull_request")

        # Branches
        branches_text = self.branches_input.text().strip()
        if branches_text:
            config.branches = [b.strip() for b in branches_text.split(',')]

        # Boards
        boards_text = self.boards_input.text().strip()
        if boards_text:
            config.boards = [b.strip() for b in boards_text.split(',')]

        # Options
        config.enable_testing = self.testing_check.isChecked()
        config.enable_linting = self.linting_check.isChecked()
        config.enable_deployment = self.deployment_check.isChecked()

        return config

    def _on_config_changed(self):
        """Handle configuration change"""
        self.config_changed.emit()

    def _on_generate_clicked(self):
        """Handle generate button click"""
        pass  # Handled by parent


class PipelineDetailsWidget(QWidget):
    """Widget for displaying pipeline details"""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # Info section
        self.info_label = QLabel("Select a pipeline to view details")
        layout.addWidget(self.info_label)

        # Jobs table
        layout.addWidget(QLabel("Jobs:"))
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(4)
        self.jobs_table.setHorizontalHeaderLabels(["Name", "Status", "Duration", "Artifacts"])
        self.jobs_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.jobs_table)

        # Logs
        layout.addWidget(QLabel("Logs:"))
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        layout.addWidget(self.logs_text)

        self.current_pipeline: Optional[Pipeline] = None

    def show_pipeline(self, pipeline: Pipeline):
        """Show pipeline details"""
        self.current_pipeline = pipeline

        # Update info
        status_text = pipeline.status.value.capitalize()
        duration = pipeline.total_duration_seconds()
        success_rate = pipeline.success_rate()

        info = f"Pipeline: {pipeline.name}\n"
        info += f"Branch: {pipeline.branch}\n"
        info += f"Status: {status_text}\n"
        info += f"Duration: {duration:.0f}s\n"
        info += f"Success Rate: {success_rate:.1f}%\n"
        if pipeline.triggered_by:
            info += f"Triggered by: {pipeline.triggered_by}\n"

        self.info_label.setText(info)

        # Update jobs table
        self.jobs_table.setRowCount(len(pipeline.jobs))
        for row, job in enumerate(pipeline.jobs):
            self.jobs_table.setItem(row, 0, QTableWidgetItem(job.name))
            self.jobs_table.setItem(row, 1, QTableWidgetItem(job.status.value.capitalize()))
            self.jobs_table.setItem(row, 2, QTableWidgetItem(f"{job.duration_seconds:.0f}s"))
            self.jobs_table.setItem(row, 3, QTableWidgetItem(str(len(job.artifacts))))

        # Clear logs (would be fetched from API)
        self.logs_text.setPlainText("Logs not available (would be fetched from API)")

    def clear_details(self):
        """Clear details"""
        self.current_pipeline = None
        self.info_label.setText("Select a pipeline to view details")
        self.jobs_table.setRowCount(0)
        self.logs_text.clear()


class CICDPanel(QWidget):
    """
    Main panel for CI/CD management

    Provides UI for:
    - Pipeline monitoring
    - Build history
    - Configuration generation
    - Deployment management
    """

    def __init__(self, cicd_service: Optional[CICDService] = None):
        super().__init__()

        self.cicd_service = cicd_service or CICDService()

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QToolBar()

        self.refresh_action = QAction("🔄 Refresh", self)
        self.refresh_action.setToolTip("Refresh pipeline list")
        self.refresh_action.triggered.connect(self._on_refresh)
        toolbar.addAction(self.refresh_action)

        self.trigger_action = QAction("▶ Trigger Pipeline", self)
        self.trigger_action.setToolTip("Trigger a new pipeline")
        self.trigger_action.triggered.connect(self._on_trigger_pipeline)
        toolbar.addAction(self.trigger_action)

        self.cancel_action = QAction("⏹ Cancel", self)
        self.cancel_action.setToolTip("Cancel selected pipeline")
        self.cancel_action.setEnabled(False)
        self.cancel_action.triggered.connect(self._on_cancel_pipeline)
        toolbar.addAction(self.cancel_action)

        toolbar.addSeparator()

        self.monitor_action = QAction("👁 Start Monitoring", self)
        self.monitor_action.setToolTip("Start monitoring pipelines")
        self.monitor_action.setCheckable(True)
        self.monitor_action.toggled.connect(self._on_monitor_toggled)
        toolbar.addAction(self.monitor_action)

        layout.addWidget(toolbar)

        # Status bar
        status_layout = QHBoxLayout()

        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        layout.addLayout(status_layout)

        # Tab widget
        self.tab_widget = QTabWidget()

        # Pipelines tab
        pipelines_widget = QWidget()
        pipelines_layout = QVBoxLayout(pipelines_widget)

        # Splitter for table and details
        splitter = QSplitter(Qt.Vertical)

        self.pipeline_table = PipelineTableWidget()
        splitter.addWidget(self.pipeline_table)

        self.details_widget = PipelineDetailsWidget()
        splitter.addWidget(self.details_widget)

        splitter.setSizes([400, 300])

        pipelines_layout.addWidget(splitter)

        self.tab_widget.addTab(pipelines_widget, "Pipelines")

        # Configuration tab
        self.config_widget = ConfigurationWidget()
        self.tab_widget.addTab(self.config_widget, "Configuration")

        # Credentials tab
        credentials_widget = QWidget()
        credentials_layout = QVBoxLayout(credentials_widget)

        # GitHub
        github_group = QGroupBox("GitHub")
        github_layout = QVBoxLayout(github_group)
        github_layout.addWidget(QLabel("Personal Access Token:"))
        self.github_token_input = QLineEdit()
        self.github_token_input.setEchoMode(QLineEdit.Password)
        github_layout.addWidget(self.github_token_input)
        credentials_layout.addWidget(github_group)

        # GitLab
        gitlab_group = QGroupBox("GitLab")
        gitlab_layout = QVBoxLayout(gitlab_group)
        gitlab_layout.addWidget(QLabel("Personal Access Token:"))
        self.gitlab_token_input = QLineEdit()
        self.gitlab_token_input.setEchoMode(QLineEdit.Password)
        gitlab_layout.addWidget(self.gitlab_token_input)
        credentials_layout.addWidget(gitlab_group)

        # Jenkins
        jenkins_group = QGroupBox("Jenkins")
        jenkins_layout = QVBoxLayout(jenkins_group)
        jenkins_layout.addWidget(QLabel("URL:"))
        self.jenkins_url_input = QLineEdit()
        jenkins_layout.addWidget(self.jenkins_url_input)
        jenkins_layout.addWidget(QLabel("Username:"))
        self.jenkins_username_input = QLineEdit()
        jenkins_layout.addWidget(self.jenkins_username_input)
        jenkins_layout.addWidget(QLabel("API Token:"))
        self.jenkins_token_input = QLineEdit()
        self.jenkins_token_input.setEchoMode(QLineEdit.Password)
        jenkins_layout.addWidget(self.jenkins_token_input)
        credentials_layout.addWidget(jenkins_group)

        credentials_layout.addStretch()

        save_creds_btn = QPushButton("Save Credentials")
        save_creds_btn.clicked.connect(self._on_save_credentials)
        credentials_layout.addWidget(save_creds_btn)

        self.tab_widget.addTab(credentials_widget, "Credentials")

        layout.addWidget(self.tab_widget)

    def _connect_signals(self):
        """Connect service signals"""
        self.cicd_service.pipeline_created.connect(self._on_pipeline_created)
        self.cicd_service.pipeline_started.connect(self._on_pipeline_started)
        self.cicd_service.pipeline_finished.connect(self._on_pipeline_finished)
        self.cicd_service.job_started.connect(self._on_job_started)
        self.cicd_service.job_finished.connect(self._on_job_finished)

        # UI signals
        self.pipeline_table.pipeline_selected.connect(self._on_pipeline_selected)
        self.config_widget.generate_btn.clicked.connect(self._on_generate_config)

    @Slot()
    def _on_refresh(self):
        """Refresh pipeline list"""
        self.status_label.setText("Fetching pipelines...")
        self.pipeline_table.clear_pipelines()

        pipelines = self.cicd_service.fetch_pipelines(limit=20)

        for pipeline in pipelines:
            self.pipeline_table.add_pipeline(pipeline)

        self.status_label.setText(f"Loaded {len(pipelines)} pipelines")

    @Slot()
    def _on_trigger_pipeline(self):
        """Trigger a new pipeline"""
        pipeline = self.cicd_service.trigger_pipeline("main")

        if pipeline:
            self.status_label.setText(f"Pipeline {pipeline.id} triggered")
            self.pipeline_table.add_pipeline(pipeline)
        else:
            QMessageBox.warning(
                self,
                "Trigger Failed",
                "Failed to trigger pipeline. Check credentials and configuration."
            )

    @Slot()
    def _on_cancel_pipeline(self):
        """Cancel selected pipeline"""
        selected_items = self.pipeline_table.selectedItems()
        if not selected_items:
            return

        pipeline_id = selected_items[0].data(Qt.UserRole)
        success = self.cicd_service.cancel_pipeline(pipeline_id)

        if success:
            self.status_label.setText(f"Pipeline {pipeline_id} cancelled")
        else:
            QMessageBox.warning(self, "Cancel Failed", "Failed to cancel pipeline")

    @Slot(bool)
    def _on_monitor_toggled(self, checked: bool):
        """Toggle pipeline monitoring"""
        if checked:
            self.cicd_service.start_monitoring(interval_seconds=30)
            self.monitor_action.setText("👁 Stop Monitoring")
            self.status_label.setText("Monitoring pipelines...")
        else:
            self.cicd_service.stop_monitoring()
            self.monitor_action.setText("👁 Start Monitoring")
            self.status_label.setText("Monitoring stopped")

    @Slot()
    def _on_generate_config(self):
        """Generate pipeline configuration"""
        config = self.config_widget.get_configuration()
        self.cicd_service.set_configuration(config)

        config_file = self.cicd_service.generate_pipeline_config()

        if config_file:
            QMessageBox.information(
                self,
                "Configuration Generated",
                f"Pipeline configuration generated:\n{config_file}"
            )
            self.status_label.setText(f"Generated: {config_file}")
        else:
            QMessageBox.warning(
                self,
                "Generation Failed",
                "Failed to generate configuration"
            )

    @Slot()
    def _on_save_credentials(self):
        """Save credentials"""
        github_token = self.github_token_input.text().strip()
        if github_token:
            self.cicd_service.set_github_token(github_token)

        gitlab_token = self.gitlab_token_input.text().strip()
        if gitlab_token:
            self.cicd_service.set_gitlab_token(gitlab_token)

        jenkins_url = self.jenkins_url_input.text().strip()
        jenkins_username = self.jenkins_username_input.text().strip()
        jenkins_token = self.jenkins_token_input.text().strip()
        if jenkins_url and jenkins_username and jenkins_token:
            self.cicd_service.set_jenkins_credentials(
                jenkins_username,
                jenkins_token,
                jenkins_url
            )

        QMessageBox.information(self, "Credentials Saved", "Credentials saved successfully")
        self.status_label.setText("Credentials updated")

    @Slot(Pipeline)
    def _on_pipeline_created(self, pipeline: Pipeline):
        """Handle pipeline created"""
        self.pipeline_table.add_pipeline(pipeline)

    @Slot(Pipeline)
    def _on_pipeline_started(self, pipeline: Pipeline):
        """Handle pipeline started"""
        self.pipeline_table.update_pipeline(pipeline)

    @Slot(Pipeline)
    def _on_pipeline_finished(self, pipeline: Pipeline):
        """Handle pipeline finished"""
        self.pipeline_table.update_pipeline(pipeline)
        self.status_label.setText(f"Pipeline {pipeline.id} finished: {pipeline.status.value}")

    @Slot(BuildJob)
    def _on_job_started(self, job: BuildJob):
        """Handle job started"""
        pass

    @Slot(BuildJob)
    def _on_job_finished(self, job: BuildJob):
        """Handle job finished"""
        pass

    @Slot(str)
    def _on_pipeline_selected(self, pipeline_id: str):
        """Handle pipeline selected"""
        if pipeline_id in self.cicd_service.pipelines:
            pipeline = self.cicd_service.pipelines[pipeline_id]
            self.details_widget.show_pipeline(pipeline)
            self.cancel_action.setEnabled(pipeline.status == BuildStatus.RUNNING)
        else:
            self.details_widget.clear_details()
            self.cancel_action.setEnabled(False)

    def set_cicd_service(self, service: CICDService):
        """Set the CI/CD service"""
        # Disconnect old signals
        if self.cicd_service:
            self.cicd_service.pipeline_created.disconnect()
            self.cicd_service.pipeline_started.disconnect()
            self.cicd_service.pipeline_finished.disconnect()
            self.cicd_service.job_started.disconnect()
            self.cicd_service.job_finished.disconnect()

        self.cicd_service = service
        self._connect_signals()

    def set_project_path(self, path: str):
        """Set project path"""
        self.cicd_service.set_project_path(path)
