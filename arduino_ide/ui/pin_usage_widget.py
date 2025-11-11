"""
Pin Usage Overview Widget
Shows real-time pin usage from Arduino code
"""

import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class PinUsageWidget(QWidget):
    """Widget showing pin usage overview with icons and descriptions"""

    pin_clicked = Signal(str)  # Emitted when a pin is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pins = {}  # Dictionary to store pin information
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("Pin Usage Overview")
        header.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                font-weight: bold;
                border-bottom: 1px solid #3d3d3d;
            }
        """)
        layout.addWidget(header)

        # Scrollable area for pins
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Container for pin items
        self.pin_container = QWidget()
        self.pin_layout = QVBoxLayout(self.pin_container)
        self.pin_layout.setContentsMargins(4, 4, 4, 4)
        self.pin_layout.setSpacing(2)
        self.pin_layout.addStretch()

        scroll.setWidget(self.pin_container)
        layout.addWidget(scroll)

        # Set default message
        self.show_empty_state()

    def show_empty_state(self):
        """Show message when no pins are detected"""
        self.clear_pins()
        empty_label = QLabel("No pin usage detected\n\nAnalyze your code to see pin assignments")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("""
            QLabel {
                color: #888888;
                padding: 20px;
                font-style: italic;
            }
        """)
        self.pin_layout.insertWidget(0, empty_label)

    def clear_pins(self):
        """Clear all pin items"""
        while self.pin_layout.count() > 1:  # Keep the stretch
            item = self.pin_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_pin(self, pin_name, mode, description="", conflict=False):
        """Add a pin to the display

        Args:
            pin_name: Pin identifier (e.g., "D2", "A0", "13")
            mode: Pin mode (e.g., "INPUT", "OUTPUT", "PWM", "ANALOG")
            description: Optional description (e.g., "sensor", "LED")
            conflict: Whether this pin has a conflict
        """
        # Remove empty state if present
        if self.pin_layout.count() == 2:  # Header + empty state + stretch
            item = self.pin_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Determine icon based on status
        if conflict:
            icon = "⚠"
            status_color = "#ff6b6b"
        elif mode.upper() == "AVAILABLE":
            icon = "○"
            status_color = "#888888"
        else:
            icon = "●"
            status_color = "#51cf66"

        # Create pin item
        pin_item = QFrame()
        pin_item.setFrameShape(QFrame.StyledPanel)
        pin_item.setCursor(Qt.PointingHandCursor)

        # Format the display text
        if description:
            display_text = f"{icon} {pin_name:6s} - {mode:8s} ({description})"
        else:
            display_text = f"{icon} {pin_name:6s} - {mode}"

        pin_label = QLabel(display_text)
        pin_label.setFont(QFont("Monospace", 9))

        # Style based on state
        if conflict:
            style = f"""
                QFrame {{
                    background-color: #4a2020;
                    border-left: 3px solid {status_color};
                    padding: 6px;
                    margin: 1px;
                }}
                QFrame:hover {{
                    background-color: #5a3030;
                }}
                QLabel {{
                    color: {status_color};
                }}
            """
        elif mode.upper() == "AVAILABLE":
            style = f"""
                QFrame {{
                    background-color: #1a1a1a;
                    border-left: 3px solid {status_color};
                    padding: 6px;
                    margin: 1px;
                }}
                QFrame:hover {{
                    background-color: #2a2a2a;
                }}
                QLabel {{
                    color: {status_color};
                }}
            """
        else:
            style = f"""
                QFrame {{
                    background-color: #1e2a1e;
                    border-left: 3px solid {status_color};
                    padding: 6px;
                    margin: 1px;
                }}
                QFrame:hover {{
                    background-color: #2e3a2e;
                }}
                QLabel {{
                    color: #ffffff;
                }}
            """

        pin_item.setStyleSheet(style)

        item_layout = QVBoxLayout(pin_item)
        item_layout.setContentsMargins(4, 2, 4, 2)
        item_layout.addWidget(pin_label)

        # Store pin data
        pin_item.pin_name = pin_name
        pin_item.mousePressEvent = lambda e: self.pin_clicked.emit(pin_name)

        # Insert before stretch
        self.pin_layout.insertWidget(self.pin_layout.count() - 1, pin_item)

        # Store in dictionary
        self.pins[pin_name] = {
            'mode': mode,
            'description': description,
            'conflict': conflict,
            'widget': pin_item
        }

    def update_from_code(self, code_text):
        """Parse Arduino code and update pin display

        Args:
            code_text: Arduino sketch code as string
        """
        self.clear_pins()
        self.pins = {}

        # Parse the code
        pin_info = self.parse_arduino_code(code_text)

        if not pin_info:
            self.show_empty_state()
            return

        # Check for conflicts (same pin used in different modes)
        conflicts = self.detect_conflicts(pin_info)

        # Sort pins for display (digital first, then analog)
        sorted_pins = sorted(pin_info.keys(), key=self.pin_sort_key)

        # Add pins to display
        for pin_name in sorted_pins:
            info = pin_info[pin_name]
            is_conflict = pin_name in conflicts

            # If multiple uses, show the most recent one
            mode = info['modes'][-1] if info['modes'] else 'UNKNOWN'
            description = info['descriptions'][-1] if info['descriptions'] else ''

            self.add_pin(pin_name, mode, description, is_conflict)

        # Add some common available pins if space permits
        used_pins = set(pin_info.keys())
        available_pins = self.get_available_pins(used_pins)
        for pin in available_pins[:5]:  # Show up to 5 available pins
            self.add_pin(pin, "AVAILABLE", "")

    def parse_arduino_code(self, code):
        """Parse Arduino code to extract pin usage

        Returns:
            Dictionary mapping pin names to their usage information
        """
        print(f"\n[PIN PARSER DEBUG] Parsing code, length: {len(code)} chars")
        print(f"[PIN PARSER DEBUG] First 500 chars:\n{code[:500]}\n")

        pin_info = {}
        var_to_pin = {}  # Map variable names to pin numbers

        # Common Arduino pin functions
        patterns = [
            # pinMode(pin, MODE)
            (r'pinMode\s*\(\s*([A-Z0-9_]+)\s*,\s*(\w+)\s*\)', 'mode'),
            # digitalWrite(pin, value)
            (r'digitalWrite\s*\(\s*([A-Z0-9_]+)\s*,', 'OUTPUT'),
            # digitalRead(pin)
            (r'digitalRead\s*\(\s*([A-Z0-9_]+)\s*\)', 'INPUT'),
            # analogWrite(pin, value) - PWM
            (r'analogWrite\s*\(\s*([A-Z0-9_]+)\s*,', 'PWM'),
            # analogRead(pin)
            (r'analogRead\s*\(\s*([A-Z0-9_]+)\s*\)', 'ANALOG'),
        ]

        # First pass: Find pin variable definitions with comments for descriptions
        lines = code.split('\n')
        for i, line in enumerate(lines):
            # Look for const/int pin definitions with comments
            pin_def_match = re.search(r'(?:const\s+)?int\s+(\w+)\s*=\s*([0-9A-Z_]+)\s*;?\s*(?://\s*(.+))?', line)
            if pin_def_match:
                var_name = pin_def_match.group(1)
                pin_num = pin_def_match.group(2)
                comment = pin_def_match.group(3) if pin_def_match.group(3) else ''

                # Resolve the pin number to standard format (e.g., A0 -> A0, 9 -> D9)
                resolved_pin = self.resolve_pin_name(pin_num, {})

                # Build variable to pin mapping
                var_to_pin[var_name] = resolved_pin
                print(f"[PIN PARSER DEBUG] Found definition: {var_name} = {pin_num} -> {resolved_pin}")

                # Initialize pin info
                if resolved_pin not in pin_info:
                    pin_info[resolved_pin] = {'modes': [], 'descriptions': [], 'var_name': var_name}
                if comment:
                    pin_info[resolved_pin]['descriptions'].append(comment.strip())

        print(f"[PIN PARSER DEBUG] Variable mapping: {var_to_pin}")

        # Second pass: Search for pin functions and resolve variable names
        for pattern, mode_type in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                pin = match.group(1)

                # Resolve pin name (handle LED_BUILTIN, variable names, etc.)
                resolved_pin = self.resolve_pin_name(pin, var_to_pin)

                if mode_type == 'mode':
                    # Extract the actual mode from pinMode
                    mode_match = re.search(r'pinMode\s*\([^,]+,\s*(\w+)\s*\)', match.group(0))
                    if mode_match:
                        actual_mode = mode_match.group(1).upper()
                    else:
                        actual_mode = 'UNKNOWN'
                else:
                    actual_mode = mode_type

                if resolved_pin not in pin_info:
                    pin_info[resolved_pin] = {'modes': [], 'descriptions': [], 'var_name': pin}

                pin_info[resolved_pin]['modes'].append(actual_mode)

                # Try to infer description from variable name if not already set
                if pin != resolved_pin and not pin_info[resolved_pin]['descriptions']:
                    # Convert snake_case and remove common pin suffixes
                    desc = pin.replace('_PIN', '').replace('_pin', '').replace('_', ' ')
                    # Handle camelCase: add space before uppercase letter that follows lowercase
                    desc = re.sub(r'([a-z])([A-Z])', r'\1 \2', desc)
                    # Clean up and normalize
                    desc = desc.replace('  ', ' ').strip().lower()
                    if desc and desc not in ['led', 'builtin']:
                        pin_info[resolved_pin]['descriptions'].append(desc)

        print(f"[PIN PARSER DEBUG] Final result: {len(pin_info)} pins found")
        for pin, info in pin_info.items():
            print(f"  {pin}: modes={info['modes']}, desc={info['descriptions']}")

        return pin_info

    def resolve_pin_name(self, pin_name, var_to_pin=None):
        """Resolve special pin names to actual pin numbers

        Args:
            pin_name: The pin name to resolve (could be a variable name, number, or special name)
            var_to_pin: Optional dictionary mapping variable names to pin numbers

        Returns:
            Resolved pin name in standard format (e.g., 'D9', 'A0')
        """
        if var_to_pin is None:
            var_to_pin = {}

        # First check if it's a variable name we've seen
        if pin_name in var_to_pin:
            return var_to_pin[pin_name]

        # Check for special pin names
        special_pins = {
            'LED_BUILTIN': 'D13',
            'A0': 'A0', 'A1': 'A1', 'A2': 'A2', 'A3': 'A3',
            'A4': 'A4', 'A5': 'A5', 'A6': 'A6', 'A7': 'A7',
        }

        if pin_name in special_pins:
            return special_pins[pin_name]

        # If it's just a number, prepend 'D'
        if pin_name.isdigit():
            return f'D{pin_name}'

        return pin_name

    def detect_conflicts(self, pin_info):
        """Detect pins with conflicting modes

        Returns:
            Set of pin names with conflicts
        """
        conflicts = set()

        for pin, info in pin_info.items():
            modes = info['modes']
            # Check if pin has multiple different modes
            if len(set(modes)) > 1:
                # INPUT_PULLUP and INPUT are not conflicts
                unique_modes = set(modes)
                if unique_modes - {'INPUT', 'INPUT_PULLUP'}:
                    conflicts.add(pin)

        return conflicts

    def pin_sort_key(self, pin_name):
        """Generate sort key for pin names

        Digital pins (D0-D13) come first, then analog (A0-A7)
        """
        if pin_name.startswith('D'):
            try:
                return (0, int(pin_name[1:]))
            except ValueError:
                return (0, 999)
        elif pin_name.startswith('A'):
            try:
                return (1, int(pin_name[1:]))
            except ValueError:
                return (1, 999)
        else:
            return (2, 0)

    def get_available_pins(self, used_pins):
        """Get list of commonly available pins not in use

        Args:
            used_pins: Set of pin names already in use

        Returns:
            List of available pin names
        """
        # Common Arduino Uno pins
        all_pins = (
            [f'D{i}' for i in range(14)] +  # D0-D13
            [f'A{i}' for i in range(6)]      # A0-A5
        )

        available = [p for p in all_pins if p not in used_pins]
        return available
