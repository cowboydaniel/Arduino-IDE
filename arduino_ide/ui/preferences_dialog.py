"""Application preferences dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QVBoxLayout
from PySide6.QtCore import QSettings


def _coerce_bool(value) -> bool:
    """Convert QSettings values to a real boolean."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    if isinstance(value, int):
        return value != 0
    return False


class PreferencesDialog(QDialog):
    """Simple dialog used to configure application preferences."""

    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self._settings = settings

        layout = QVBoxLayout(self)

        self._verbose_checkbox = QCheckBox("Show verbose output during compilation")
        current_value = _coerce_bool(self._settings.value("cli/verboseCompile", False))
        self._verbose_checkbox.setChecked(current_value)
        layout.addWidget(self._verbose_checkbox)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    @property
    def verbose_compile_enabled(self) -> bool:
        """Return True when verbose compilation output is enabled."""

        return self._verbose_checkbox.isChecked()

    def accept(self) -> None:
        """Persist updated preferences before closing the dialog."""

        self._settings.setValue("cli/verboseCompile", self.verbose_compile_enabled)
        super().accept()
