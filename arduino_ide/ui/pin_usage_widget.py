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
        self.current_board = None  # Current board (Board object)
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
        print(f"[CLEAR_PINS DEBUG] Layout count before clear: {self.pin_layout.count()}")
        cleared_count = 0
        while self.pin_layout.count() > 1:  # Keep the stretch
            item = self.pin_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                cleared_count += 1
        print(f"[CLEAR_PINS DEBUG] Cleared {cleared_count} pin widgets")

    def add_pin(self, pin_name, mode, description="", conflict=False):
        """Add a pin to the display

        Args:
            pin_name: Pin identifier (e.g., "D2", "A0", "13")
            mode: Pin mode (e.g., "INPUT", "OUTPUT", "PWM", "ANALOG")
            description: Optional description (e.g., "sensor", "LED")
            conflict: Whether this pin has a conflict
        """
        # Remove empty state if present (check if first widget is a QLabel, not a QFrame)
        if self.pin_layout.count() > 1:
            first_item = self.pin_layout.itemAt(0)
            if first_item and first_item.widget():
                # Empty state is a QLabel, pin items are QFrame
                widget = first_item.widget()
                if isinstance(widget, QLabel):
                    self.pin_layout.takeAt(0)
                    widget.deleteLater()
                    print(f"[ADD_PIN DEBUG] Removed empty state label for first pin {pin_name}")

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
        insert_position = self.pin_layout.count() - 1
        self.pin_layout.insertWidget(insert_position, pin_item)
        print(f"[ADD_PIN DEBUG] Added {pin_name} ({mode}) at position {insert_position}, layout now has {self.pin_layout.count()} items")

        # Store in dictionary
        self.pins[pin_name] = {
            'mode': mode,
            'description': description,
            'conflict': conflict,
            'widget': pin_item
        }

    def set_board(self, board):
        """Set the current board

        Args:
            board: Board object from arduino_ide.models.board
        """
        self.current_board = board
        # Trigger a refresh of the pin display if we have code
        # This will update available pins based on the new board

    def update_from_code(self, code_text):
        """Parse Arduino code and update pin display

        Args:
            code_text: Arduino sketch code as string
        """
        print(f"\n[UPDATE_FROM_CODE DEBUG] Called with {len(code_text)} chars of code")
        print(f"[UPDATE_FROM_CODE DEBUG] Current board: {self.current_board.name if self.current_board else 'None'}")
        self.clear_pins()
        self.pins = {}

        # Parse the code
        pin_info = self.parse_arduino_code(code_text)

        # Check for conflicts (same pin used in different modes)
        conflicts = self.detect_conflicts(pin_info) if pin_info else set()

        # Sort pins for display (digital first, then analog)
        sorted_pins = sorted(pin_info.keys(), key=self.pin_sort_key) if pin_info else []

        # Add used pins to display
        for pin_name in sorted_pins:
            info = pin_info[pin_name]
            is_conflict = pin_name in conflicts

            # If multiple uses, show the most recent one
            mode = info['modes'][-1] if info['modes'] else 'UNKNOWN'
            description = info['descriptions'][-1] if info['descriptions'] else ''

            self.add_pin(pin_name, mode, description, is_conflict)

        # Add ALL available pins from the board
        used_pins = set(pin_info.keys())
        available_pins = self.get_available_pins(used_pins)
        print(f"[PIN WIDGET DEBUG] Adding {len(available_pins)} available pins to display")
        for pin in available_pins:  # Show ALL available pins
            self.add_pin(pin, "AVAILABLE", "")

        print(f"[UPDATE_FROM_CODE DEBUG] Finished. Layout has {self.pin_layout.count()} items total")
        print(f"[UPDATE_FROM_CODE DEBUG] Pins dictionary has {len(self.pins)} entries\n")

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

        # First pass: Find POTENTIAL pin variable definitions with comments for descriptions
        # We'll only add them to pin_info if they're actually used in pin functions
        potential_pin_vars = {}  # Map var_name to (pin_num, comment)
        lines = code.split('\n')
        for i, line in enumerate(lines):
            # Look for const/int pin definitions with comments
            # Only match at the start of lines (after whitespace), not in function signatures or loops
            pin_def_match = re.search(r'^\s*(?:const\s+)?int\s+(\w+)\s*=\s*([0-9A-Z_]+)\s*;', line)
            if pin_def_match:
                var_name = pin_def_match.group(1)
                pin_num = pin_def_match.group(2)

                # Skip if this looks like a loop variable (single letter like 'i', 'j', 'x', etc.)
                if len(var_name) == 1:
                    continue

                # Only process if it looks like a valid pin number
                # Valid: A0-A7, 0-13, LED_BUILTIN
                is_valid_pin = False
                if pin_num in ['LED_BUILTIN']:
                    is_valid_pin = True
                elif pin_num.startswith('A') and len(pin_num) == 2 and pin_num[1].isdigit():
                    # A0-A9
                    is_valid_pin = True
                elif pin_num.isdigit() and 0 <= int(pin_num) <= 13:
                    # Digital pins 0-13
                    is_valid_pin = True

                if not is_valid_pin:
                    continue

                # Extract comment if present
                comment_match = re.search(r'//\s*(.+)', line)
                comment = comment_match.group(1) if comment_match else ''

                # Store as potential pin variable - we'll confirm it later
                potential_pin_vars[var_name] = (pin_num, comment)
                print(f"[PIN PARSER DEBUG] Found potential pin variable: {var_name} = {pin_num}")

        # Determine which potential variables are likely pins based on naming patterns
        likely_pin_vars = self.filter_likely_pin_names(potential_pin_vars)
        print(f"[PIN PARSER DEBUG] Likely pin variables after name filtering: {list(likely_pin_vars.keys())}")

        # Second pass: Search for pin functions and resolve variable names
        # Process pinMode() first to establish definitive modes
        pinMode_pins = {}  # Track pins with explicit pinMode declarations
        used_vars = set()  # Track which variables are actually used in pin functions

        # First, find all pinMode declarations
        pinMode_pattern = r'pinMode\s*\(\s*([A-Z0-9_]+)\s*,\s*(\w+)\s*\)'
        for match in re.finditer(pinMode_pattern, code, re.IGNORECASE):
            pin = match.group(1)
            mode = match.group(2).upper()

            # If this is a potential pin variable, confirm it and add to var_to_pin
            if pin in potential_pin_vars and pin not in var_to_pin:
                pin_num, comment = potential_pin_vars[pin]
                resolved_pin = self.resolve_pin_name(pin_num, {})
                var_to_pin[pin] = resolved_pin
                used_vars.add(pin)
                print(f"[PIN PARSER DEBUG] Confirmed pin variable: {pin} -> {resolved_pin}")

                # Initialize pin info with description
                if resolved_pin not in pin_info:
                    pin_info[resolved_pin] = {'modes': [], 'descriptions': [], 'var_name': pin}
                if comment:
                    pin_info[resolved_pin]['descriptions'].append(comment.strip())

            # Resolve pin name
            resolved_pin = self.resolve_pin_name(pin, var_to_pin)

            # Validate that resolved pin looks like a real pin
            if pin not in var_to_pin:
                if not (resolved_pin.startswith('D') or resolved_pin.startswith('A') or resolved_pin == 'LED_BUILTIN'):
                    continue
                if resolved_pin.startswith('D'):
                    try:
                        pin_num = int(resolved_pin[1:])
                        if pin_num > 13:
                            continue
                    except ValueError:
                        continue

            # Store pinMode declaration
            pinMode_pins[resolved_pin] = mode

            if resolved_pin not in pin_info:
                pin_info[resolved_pin] = {'modes': [], 'descriptions': [], 'var_name': pin}

            pin_info[resolved_pin]['modes'].append(mode)
            print(f"[PIN PARSER DEBUG] pinMode found: {resolved_pin} -> {mode}")

        # Now process other function calls, but don't override pinMode declarations
        for pattern, mode_type in patterns:
            if mode_type == 'mode':
                # Skip pinMode since we already processed it
                continue

            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                pin = match.group(1)

                # If this is a potential pin variable, confirm it and add to var_to_pin
                if pin in potential_pin_vars and pin not in var_to_pin:
                    pin_num, comment = potential_pin_vars[pin]
                    resolved_pin_temp = self.resolve_pin_name(pin_num, {})
                    var_to_pin[pin] = resolved_pin_temp
                    used_vars.add(pin)
                    print(f"[PIN PARSER DEBUG] Confirmed pin variable: {pin} -> {resolved_pin_temp}")

                    # Initialize pin info with description
                    if resolved_pin_temp not in pin_info:
                        pin_info[resolved_pin_temp] = {'modes': [], 'descriptions': [], 'var_name': pin}
                    if comment:
                        pin_info[resolved_pin_temp]['descriptions'].append(comment.strip())

                # Resolve pin name (handle LED_BUILTIN, variable names, etc.)
                resolved_pin = self.resolve_pin_name(pin, var_to_pin)

                # Validate that resolved pin looks like a real pin
                # Skip if it's not a known variable and doesn't look like a valid pin
                if pin not in var_to_pin:
                    # Check if it's a valid direct pin reference
                    if not (resolved_pin.startswith('D') or resolved_pin.startswith('A') or resolved_pin == 'LED_BUILTIN'):
                        continue
                    # Check pin number range
                    if resolved_pin.startswith('D'):
                        try:
                            pin_num = int(resolved_pin[1:])
                            if pin_num > 13:
                                continue
                        except ValueError:
                            continue

                # Skip if this pin has a pinMode declaration - that's the source of truth
                if resolved_pin in pinMode_pins:
                    print(f"[PIN PARSER DEBUG] Skipping {mode_type} for {resolved_pin} - pinMode already declared as {pinMode_pins[resolved_pin]}")
                    continue

                actual_mode = mode_type

                if resolved_pin not in pin_info:
                    pin_info[resolved_pin] = {'modes': [], 'descriptions': [], 'var_name': pin}

                pin_info[resolved_pin]['modes'].append(actual_mode)
                print(f"[PIN PARSER DEBUG] Inferred {mode_type} for {resolved_pin}")

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

        # Third pass: Add likely pin variables that weren't confirmed by function usage
        # This handles files with pin definitions but no actual pin function calls
        for var_name, (pin_num, comment) in likely_pin_vars.items():
            if var_name not in var_to_pin:  # Not yet confirmed by function usage
                resolved_pin = self.resolve_pin_name(pin_num, {})
                var_to_pin[var_name] = resolved_pin
                print(f"[PIN PARSER DEBUG] Auto-confirmed likely pin: {var_name} -> {resolved_pin}")

                # Initialize pin info
                if resolved_pin not in pin_info:
                    pin_info[resolved_pin] = {'modes': [], 'descriptions': [], 'var_name': var_name}

                # Add UNKNOWN mode since we don't have pinMode info
                if not pin_info[resolved_pin]['modes']:
                    pin_info[resolved_pin]['modes'].append('UNKNOWN')

                # Add description from comment if available
                if comment and comment not in pin_info[resolved_pin]['descriptions']:
                    pin_info[resolved_pin]['descriptions'].append(comment.strip())

        print(f"[PIN PARSER DEBUG] Confirmed variable mapping: {var_to_pin}")
        print(f"[PIN PARSER DEBUG] Final result: {len(pin_info)} pins found")
        for pin, info in pin_info.items():
            print(f"  {pin}: modes={info['modes']}, desc={info['descriptions']}")

        return pin_info

    def filter_likely_pin_names(self, potential_vars):
        """Filter potential pin variables to identify likely pins based on naming patterns

        Args:
            potential_vars: Dict mapping var_name to (pin_num, comment)

        Returns:
            Dict with same structure, containing only likely pin variables
        """
        # Common keywords that indicate a pin variable
        pin_keywords = [
            'PIN', 'RELAY', 'LED', 'BUTTON', 'SWITCH', 'SENSOR', 'MOTOR',
            'SERVO', 'LIGHT', 'LAMP', 'BUZZER', 'SPEAKER', 'INPUT', 'OUTPUT',
            'PWM', 'ANALOG', 'DIGITAL', 'TX', 'RX', 'SDA', 'SCL', 'MOSI', 'MISO',
            'SCK', 'CS', 'SS', 'ENABLE', 'TRIGGER', 'ECHO', 'TURNOUT',
            'SIGNAL', 'CROSSING', 'VALVE', 'SOLENOID', 'HEATER', 'FAN', 'PUMP'
        ]

        # Keywords that indicate NOT a pin (configuration values, thresholds, etc.)
        non_pin_keywords = [
            'THRESHOLD', 'DELAY', 'TIMEOUT', 'INTERVAL', 'DURATION', 'COUNT',
            'SIZE', 'LENGTH', 'WIDTH', 'HEIGHT', 'SAMPLES', 'RATE', 'SPEED',
            'BAUD', 'FREQUENCY', 'PERIOD', 'HYSTERESIS', 'OFFSET', 'MULTIPLIER',
            'DIVISOR', 'MINIMUM', 'MAXIMUM', 'MIN', 'MAX', 'LIMIT', 'RANGE',
            'DEBOUNCE_TIME', 'CALIBRATION', 'FILTER', 'ROUTE', 'STATE', 'MODE',
            'STATUS', 'FLAG', 'ACTIVE', 'INACTIVE', 'CONFIG', 'SETTING'
        ]

        likely_pins = {}

        for var_name, (pin_num, comment) in potential_vars.items():
            var_upper = var_name.upper()

            # Check for non-pin keywords first (these take priority)
            is_non_pin = any(keyword in var_upper for keyword in non_pin_keywords)
            if is_non_pin:
                print(f"[PIN FILTER DEBUG] Excluding {var_name} - contains non-pin keyword")
                continue

            # Check for pin keywords
            is_likely_pin = any(keyword in var_upper for keyword in pin_keywords)
            if is_likely_pin:
                likely_pins[var_name] = (pin_num, comment)
                print(f"[PIN FILTER DEBUG] Including {var_name} - contains pin keyword")
            else:
                print(f"[PIN FILTER DEBUG] Excluding {var_name} - no pin keywords found")

        return likely_pins

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
        """Get list of available pins from the current board

        Args:
            used_pins: Set of pin names already in use

        Returns:
            List of available pin names
        """
        # If no board is set, default to Arduino Uno pins
        if not self.current_board:
            print("[PIN WIDGET DEBUG] No board set, using Arduino Uno defaults")
            all_pins = (
                [f'D{i}' for i in range(14)] +  # D0-D13
                [f'A{i}' for i in range(6)]      # A0-A5
            )
        else:
            # Use the board's pin configuration
            digital_pins = self.current_board.specs.digital_pins
            analog_pins = self.current_board.specs.analog_pins
            print(f"[PIN WIDGET DEBUG] Board: {self.current_board.name}")
            print(f"[PIN WIDGET DEBUG] Digital pins: {digital_pins}, Analog pins: {analog_pins}")

            all_pins = (
                [f'D{i}' for i in range(digital_pins)] +
                [f'A{i}' for i in range(analog_pins)]
            )

        print(f"[PIN WIDGET DEBUG] Total pins generated: {len(all_pins)}")
        print(f"[PIN WIDGET DEBUG] Used pins: {used_pins}")
        available = [p for p in all_pins if p not in used_pins]
        print(f"[PIN WIDGET DEBUG] Available pins: {len(available)} pins")
        print(f"[PIN WIDGET DEBUG] First 10 available: {available[:10]}")
        return available
