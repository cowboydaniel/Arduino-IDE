"""
Memory Panel
Displays memory profiling information with visual usage indicators
Shows RAM, Flash, and Stack/Heap breakdown
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QProgressBar, QPushButton, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QPalette, QColor
import logging
from typing import Optional, Dict

from arduino_ide.services.debug_service import DebugService, MemoryRegion


logger = logging.getLogger(__name__)


class MemoryRegionWidget(QWidget):
    """Widget for displaying a single memory region"""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)

        self.name = name
        self._region: Optional[MemoryRegion] = None

        self._setup_ui()


    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Name label
        self.name_label = QLabel(self.name)
        font = self.name_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        self.name_label.setFont(font)
        layout.addWidget(self.name_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setMinimumHeight(25)
        layout.addWidget(self.progress_bar)

        # Info grid
        info_layout = QGridLayout()
        info_layout.setSpacing(5)

        # Labels
        info_layout.addWidget(QLabel("Used:"), 0, 0)
        self.used_label = QLabel("0 bytes")
        info_layout.addWidget(self.used_label, 0, 1)

        info_layout.addWidget(QLabel("Free:"), 1, 0)
        self.free_label = QLabel("0 bytes")
        info_layout.addWidget(self.free_label, 1, 1)

        info_layout.addWidget(QLabel("Total:"), 2, 0)
        self.total_label = QLabel("0 bytes")
        info_layout.addWidget(self.total_label, 2, 1)

        layout.addLayout(info_layout)


    def update_region(self, region: MemoryRegion):
        """Update the display with new region data"""
        self._region = region

        # Update progress bar
        usage_percent = region.usage_percent
        self.progress_bar.setValue(int(usage_percent))

        # Update progress bar color based on usage
        if usage_percent < 50:
            color = "#4CAF50"  # Green
        elif usage_percent < 75:
            color = "#FFC107"  # Yellow
        elif usage_percent < 90:
            color = "#FF9800"  # Orange
        else:
            color = "#F44336"  # Red

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)

        # Update labels
        self.used_label.setText(self._format_bytes(region.used))
        self.free_label.setText(self._format_bytes(region.free))
        self.total_label.setText(self._format_bytes(region.size))


    def _format_bytes(self, bytes_count: int) -> str:
        """Format byte count with appropriate unit"""
        if bytes_count < 1024:
            return f"{bytes_count} B"
        elif bytes_count < 1024 * 1024:
            return f"{bytes_count / 1024:.2f} KB"
        else:
            return f"{bytes_count / (1024 * 1024):.2f} MB"


    def clear(self):
        """Clear the display"""
        self.progress_bar.setValue(0)
        self.used_label.setText("0 bytes")
        self.free_label.setText("0 bytes")
        self.total_label.setText("0 bytes")


class MemoryPanel(QWidget):
    """
    Panel for displaying memory profiling information
    Shows RAM, Flash, Stack, and Heap usage with visual indicators
    """

    # Signals
    refresh_requested = Signal()

    def __init__(self, debug_service: Optional[DebugService] = None, parent=None):
        super().__init__(parent)

        self.debug_service = debug_service

        # Memory region widgets
        self.region_widgets: Dict[str, MemoryRegionWidget] = {}

        # Auto-refresh timer
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self._auto_refresh)
        self.auto_refresh_interval = 1000  # 1 second

        # UI setup
        self._setup_ui()
        self._setup_connections()

        # Connect to debug service if provided
        if self.debug_service:
            self.set_debug_service(self.debug_service)

        logger.info("Memory panel initialized")


    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Toolbar
        toolbar_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Refresh memory information")

        self.auto_refresh_checkbox = QWidget()
        auto_refresh_layout = QHBoxLayout(self.auto_refresh_checkbox)
        auto_refresh_layout.setContentsMargins(0, 0, 0, 0)

        from PySide6.QtWidgets import QCheckBox
        self.auto_refresh_cb = QCheckBox("Auto-refresh")
        self.auto_refresh_cb.setToolTip("Automatically refresh memory info while debugging")
        auto_refresh_layout.addWidget(self.auto_refresh_cb)

        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.auto_refresh_checkbox)
        toolbar_layout.addStretch()

        layout.addLayout(toolbar_layout)

        # Memory regions container
        self.regions_layout = QVBoxLayout()
        self.regions_layout.setSpacing(10)

        # Create default region widgets
        self._create_region_widget("SRAM")
        self._create_region_widget("FLASH")
        self._create_region_widget("STACK")
        self._create_region_widget("HEAP")

        layout.addLayout(self.regions_layout)

        # Status label
        self.status_label = QLabel("Connect debugger to view memory usage")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Spacer
        layout.addStretch()


    def _setup_connections(self):
        """Setup signal connections"""
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        self.auto_refresh_cb.stateChanged.connect(self._on_auto_refresh_toggled)


    def _create_region_widget(self, name: str):
        """Create a memory region widget"""
        group_box = QGroupBox(name)
        group_layout = QVBoxLayout(group_box)
        group_layout.setContentsMargins(5, 10, 5, 5)

        widget = MemoryRegionWidget(name)
        group_layout.addWidget(widget)

        self.region_widgets[name] = widget
        self.regions_layout.addWidget(group_box)


    def set_debug_service(self, debug_service: DebugService):
        """Connect to debug service"""
        self.debug_service = debug_service

        # Connect signals
        self.debug_service.memory_updated.connect(self._on_memory_updated)
        self.debug_service.state_changed.connect(self._on_debug_state_changed)

        # Initial refresh
        self.refresh_memory()


    def refresh_memory(self):
        """Request memory information refresh from debug service"""
        if not self.debug_service:
            logger.warning("No debug service connected")
            return

        self.debug_service.refresh_memory_info()
        self.refresh_requested.emit()


    @Slot(dict)
    def _on_memory_updated(self, memory_regions: Dict[str, MemoryRegion]):
        """Handle memory update from debug service"""
        if not memory_regions:
            self._show_empty_state()
            return

        # Hide status label
        self.status_label.setVisible(False)

        # Update existing regions
        for name, region in memory_regions.items():
            if name in self.region_widgets:
                self.region_widgets[name].update_region(region)
            else:
                # Create new region widget if needed
                self._create_region_widget(name)
                self.region_widgets[name].update_region(region)


    @Slot(object)
    def _on_debug_state_changed(self, state):
        """Handle debug state change"""
        from arduino_ide.services.debug_service import DebugState

        if state in (DebugState.IDLE, DebugState.DISCONNECTED):
            self._show_empty_state()
            self.auto_refresh_timer.stop()
        elif state == DebugState.CONNECTED:
            self.status_label.setText("Connected - waiting for memory data...")
        elif state in (DebugState.PAUSED, DebugState.RUNNING):
            self.refresh_memory()


    def _show_empty_state(self):
        """Show empty state"""
        for widget in self.region_widgets.values():
            widget.clear()

        self.status_label.setText("Connect debugger to view memory usage")
        self.status_label.setVisible(True)


    @Slot()
    def _on_refresh_clicked(self):
        """Handle refresh button click"""
        self.refresh_memory()


    @Slot(int)
    def _on_auto_refresh_toggled(self, state: int):
        """Handle auto-refresh toggle"""
        if state == Qt.Checked:
            self.auto_refresh_timer.start(self.auto_refresh_interval)
            logger.info("Memory auto-refresh enabled")
        else:
            self.auto_refresh_timer.stop()
            logger.info("Memory auto-refresh disabled")


    def _auto_refresh(self):
        """Auto-refresh timer callback"""
        if self.debug_service:
            from arduino_ide.services.debug_service import DebugState
            state = self.debug_service.state

            if state in (DebugState.PAUSED, DebugState.RUNNING):
                self.refresh_memory()


    def set_auto_refresh_interval(self, interval_ms: int):
        """Set auto-refresh interval in milliseconds"""
        self.auto_refresh_interval = interval_ms
        if self.auto_refresh_timer.isActive():
            self.auto_refresh_timer.setInterval(interval_ms)


    def clear(self):
        """Clear all memory displays"""
        self._show_empty_state()
        self.auto_refresh_timer.stop()
        self.auto_refresh_cb.setChecked(False)
