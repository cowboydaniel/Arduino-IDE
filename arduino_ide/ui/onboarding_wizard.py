"""Onboarding wizard that guides new users through the IDE basics."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Qt


class StepIndicator(QFrame):
    """Pill-shaped indicator used to show onboarding progress."""

    def __init__(self, index, title, parent=None):
        super().__init__(parent)
        self.index = index
        self.title = title
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self.badge = QLabel(str(self.index + 1))
        self.badge.setObjectName("badge")
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setFixedWidth(28)
        layout.addWidget(self.badge)

        self.title_label = QLabel(self.title)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label, 1)

        self.setObjectName("stepIndicator")

    def set_state(self, state):
        """Update the indicator style based on the state."""

        # States: "pending", "active", "done"
        self.setProperty("state", state)
        self.badge.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)


class OnboardingWizard(QDialog):
    """Guide new users through the IDE with actionable steps."""

    steps = [
        {
            "title": "Connect your Arduino",
            "description": (
                "Plug in your board via USB and select the detected board/port from "
                "the toolbar. If drivers are missing, open Tools → Board Manager to "
                "install the right core."
            ),
            "actions": [
                "Use the board dropdown to pick the connected hardware.",
                "Refresh available ports if your device does not appear immediately.",
            ],
        },
        {
            "title": "Try an example (Blink)",
            "description": (
                "Open File → Examples → 01.Basics → Blink to load the classic sketch. "
                "The template includes comments that describe what each section does."
            ),
            "actions": [
                "Browse curated templates from the Examples panel or menu.",
                "Use the Quick Actions panel to jump directly to Examples.",
            ],
        },
        {
            "title": "Modify and upload",
            "description": (
                "Customize the sketch (for example, change the delay) and click Upload. "
                "The build output appears in the console so you can monitor progress."
            ),
            "actions": [
                "Use Verify first if you only want to compile without flashing.",
                "Keep an eye on status messages in the bottom bar while uploading.",
            ],
        },
        {
            "title": "Open Serial Monitor",
            "description": (
                "View the board's output by opening the Serial Monitor. Matching the "
                "baud rate with your sketch ensures readable logs and sensor data."
            ),
            "actions": [
                "Toggle the Serial Monitor from the toolbar or the Tools menu.",
                "Switch to the Serial Plotter if you want to visualize sensor streams.",
            ],
        },
        {
            "title": "Create your first project",
            "description": (
                "Organize sketches by creating a project folder. The Project Explorer "
                "helps manage multiple files, libraries, and assets as your ideas grow."
            ),
            "actions": [
                "Use File → New Sketch or File → Open to start a workspace.",
                "Right-click items in Project Explorer to rename, duplicate, or delete.",
            ],
        },
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Arduino IDE")
        self.setModal(True)
        self.resize(860, 520)
        self.current_step = 0
        self.step_indicators = []
        self._build_ui()
        self._apply_styles()
        self._update_step_content()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Kick-start your first Arduino project")
        header.setObjectName("header")
        layout.addWidget(header)

        subheader = QLabel(
            "Follow the guided steps below to go from plugging in your board to "
            "building a complete sketch."
        )
        subheader.setWordWrap(True)
        subheader.setObjectName("subheader")
        layout.addWidget(subheader)

        content_row = QHBoxLayout()
        content_row.setSpacing(20)

        # Progress column
        progress_panel = QFrame()
        progress_panel.setObjectName("progressPanel")
        progress_layout = QVBoxLayout(progress_panel)
        progress_layout.setContentsMargins(16, 16, 16, 16)
        progress_layout.setSpacing(10)

        progress_title = QLabel("Checklist")
        progress_title.setObjectName("sectionTitle")
        progress_layout.addWidget(progress_title)

        for index, step in enumerate(self.steps):
            indicator = StepIndicator(index, step["title"])
            progress_layout.addWidget(indicator)
            self.step_indicators.append(indicator)

        progress_layout.addStretch(1)
        content_row.addWidget(progress_panel, 1)

        # Details column
        detail_panel = QFrame()
        detail_panel.setObjectName("detailPanel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(24, 24, 24, 24)
        detail_layout.setSpacing(12)

        self.progress_label = QLabel()
        self.progress_label.setObjectName("progressLabel")
        detail_layout.addWidget(self.progress_label)

        self.step_title_label = QLabel()
        self.step_title_label.setObjectName("stepTitle")
        detail_layout.addWidget(self.step_title_label)

        self.step_description_label = QLabel()
        self.step_description_label.setWordWrap(True)
        self.step_description_label.setObjectName("stepDescription")
        detail_layout.addWidget(self.step_description_label)

        self.actions_label = QLabel()
        self.actions_label.setWordWrap(True)
        self.actions_label.setObjectName("actionsList")
        self.actions_label.setTextFormat(Qt.RichText)
        detail_layout.addWidget(self.actions_label)

        detail_layout.addStretch(1)
        content_row.addWidget(detail_panel, 2)

        layout.addLayout(content_row, 1)

        # Buttons
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)

        self.skip_button = QPushButton("Skip Tour")
        self.skip_button.setObjectName("SkipButton")
        self.skip_button.clicked.connect(self.reject)
        button_row.addWidget(self.skip_button)

        button_row.addStretch(1)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.previous_step)
        button_row.addWidget(self.back_button)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_step)
        button_row.addWidget(self.next_button)

        self.finish_button = QPushButton("Finish")
        self.finish_button.clicked.connect(self.accept)
        button_row.addWidget(self.finish_button)

        layout.addLayout(button_row)

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QDialog {
                background-color: #121212;
                color: #F3F3F3;
            }
            #header {
                font-size: 22px;
                font-weight: 600;
            }
            #subheader {
                color: #B0B0B0;
            }
            #progressPanel {
                background-color: #1E1E1E;
                border-radius: 12px;
            }
            #detailPanel {
                background-color: #1A1A1A;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
            #sectionTitle {
                font-weight: 600;
                color: #9CD1FF;
            }
            #progressLabel {
                color: #9CD1FF;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            #stepTitle {
                font-size: 20px;
                font-weight: 600;
            }
            #stepDescription {
                color: #DDDDDD;
            }
            #actionsList {
                color: #C7C7C7;
            }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #777777;
            }
            QPushButton#SkipButton {
                background-color: transparent;
                color: #B0B0B0;
            }
            QFrame#stepIndicator {
                border-radius: 20px;
                background-color: transparent;
            }
            QFrame#stepIndicator[state='done'] {
                background-color: rgba(88, 195, 145, 0.15);
            }
            QFrame#stepIndicator[state='active'] {
                background-color: rgba(15, 98, 156, 0.35);
            }
            QLabel#badge {
                border-radius: 14px;
                padding: 4px 0;
                font-weight: bold;
            }
            QLabel#badge[state='pending'] {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QLabel#badge[state='active'] {
                background-color: #0E639C;
            }
            QLabel#badge[state='done'] {
                background-color: #58C391;
            }
        """
        )

    def _format_actions(self, actions):
        if not actions:
            return ""
        items = "".join(f"<li>{action}</li>" for action in actions)
        return f"<b>Try this:</b><ul>{items}</ul>"

    def _update_step_content(self):
        total = len(self.steps)
        step = self.steps[self.current_step]
        self.progress_label.setText(f"Step {self.current_step + 1} of {total}")
        self.step_title_label.setText(step["title"])
        self.step_description_label.setText(step["description"])
        self.actions_label.setText(self._format_actions(step.get("actions")))

        for index, indicator in enumerate(self.step_indicators):
            if index < self.current_step:
                indicator.set_state("done")
            elif index == self.current_step:
                indicator.set_state("active")
            else:
                indicator.set_state("pending")

        self.back_button.setEnabled(self.current_step > 0)
        is_last = self.current_step == total - 1
        self.next_button.setVisible(not is_last)
        self.finish_button.setVisible(is_last)

    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self._update_step_content()

    def previous_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._update_step_content()

