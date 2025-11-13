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

    # Reasonable defaults when board metadata does not expose pin counts.
    # These mirror the classic Arduino Uno which is the most common board
    # selection in the IDE.
    DEFAULT_DIGITAL_PIN_COUNT = 14
    DEFAULT_ANALOG_PIN_COUNT = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pins = {}  # Dictionary to store pin information
        self.current_board = None  # Current board (Board object)
        self.current_pin_info = {}  # Store parsed pin info for conflict detection
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

        # Store pin_info for conflict detection
        self.current_pin_info = pin_info

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

        # First pass: Build symbol table - map ALL variable names to their values
        # This is what the compiler does: build a symbol table during compilation
        var_to_value = {}  # Map variable name to its literal value (number or constant)
        var_to_comment = {}  # Map variable name to its comment

        lines = code.split('\n')
        for i, line in enumerate(lines):
            # Match variable definitions: const int VAR = VALUE;
            var_def_match = re.search(r'^\s*(?:const\s+)?int\s+(\w+)\s*=\s*([0-9A-Z_]+)\s*;', line)
            if var_def_match:
                var_name = var_def_match.group(1)
                value = var_def_match.group(2)

                # Skip single-letter variables (loop counters)
                if len(var_name) == 1:
                    continue

                var_to_value[var_name] = value

                # Extract comment if present
                comment_match = re.search(r'//\s*(.+)', line)
                if comment_match:
                    var_to_comment[var_name] = comment_match.group(1).strip()

                print(f"[SYMBOL TABLE DEBUG] {var_name} = {value}")

        print(f"[SYMBOL TABLE DEBUG] Built symbol table with {len(var_to_value)} entries")

        # Second pass: Find all pin function calls (pinMode, digitalWrite, etc.)
        # This is what the compiler does: analyze function calls
        pinMode_pins = {}  # Track pins with explicit pinMode declarations

        # Helper function to resolve a symbol to its actual pin value
        def resolve_symbol_to_pin(symbol):
            """Resolve a symbol through the symbol table to get actual pin number"""
            # If it's a direct pin number or analog pin, use it
            if symbol.isdigit():
                pin_num = int(symbol)
                if 0 <= pin_num <= 13:
                    return f'D{pin_num}', symbol, None
                return None, None, None
            elif symbol in ['LED_BUILTIN']:
                return 'D13', symbol, None
            elif symbol.startswith('A') and len(symbol) == 2 and symbol[1].isdigit():
                return symbol, symbol, None

            # Look up in symbol table
            if symbol in var_to_value:
                value = var_to_value[symbol]
                comment = var_to_comment.get(symbol, None)

                # Recursively resolve if value is also a symbol
                if value in var_to_value:
                    resolved, _, _ = resolve_symbol_to_pin(value)
                    return resolved, symbol, comment

                # Check if value is a valid pin
                if value.isdigit():
                    pin_num = int(value)
                    if 0 <= pin_num <= 13:
                        return f'D{pin_num}', symbol, comment
                elif value.startswith('A') and len(value) == 2 and value[1].isdigit():
                    return value, symbol, comment
                elif value == 'LED_BUILTIN':
                    return 'D13', symbol, comment

            return None, None, None

        # Process pinMode() first to establish definitive modes
        pinMode_pattern = r'pinMode\s*\(\s*([A-Z0-9_]+)\s*,\s*(\w+)\s*\)'
        for match in re.finditer(pinMode_pattern, code, re.IGNORECASE):
            symbol = match.group(1)
            mode = match.group(2).upper()

            resolved_pin, var_name, comment = resolve_symbol_to_pin(symbol)
            if resolved_pin is None:
                print(f"[PIN FUNCTION DEBUG] pinMode: Cannot resolve '{symbol}' to a valid pin")
                continue

            # Store pinMode declaration
            pinMode_pins[resolved_pin] = mode

            if resolved_pin not in pin_info:
                pin_info[resolved_pin] = {
                    'modes': [],
                    'descriptions': [],
                    'var_name': var_name or symbol,
                    'pinMode_declarations': []  # Track all pinMode calls separately
                }

            # Store this pinMode declaration
            pin_info[resolved_pin]['pinMode_declarations'].append(mode)
            pin_info[resolved_pin]['modes'].append(mode)

            if comment and comment not in pin_info[resolved_pin]['descriptions']:
                pin_info[resolved_pin]['descriptions'].append(comment)

            print(f"[PIN FUNCTION DEBUG] pinMode({symbol}) -> {resolved_pin} ({mode})")

        # Process other pin function calls (digitalWrite, digitalRead, analogRead, analogWrite)
        for pattern, mode_type in patterns:
            if mode_type == 'mode':
                # Skip pinMode since we already processed it
                continue

            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                symbol = match.group(1)

                resolved_pin, var_name, comment = resolve_symbol_to_pin(symbol)
                if resolved_pin is None:
                    print(f"[PIN FUNCTION DEBUG] {mode_type}: Cannot resolve '{symbol}' to a valid pin")
                    continue

                # Skip if this pin has a pinMode declaration - that's the source of truth
                if resolved_pin in pinMode_pins:
                    print(f"[PIN FUNCTION DEBUG] {mode_type}({symbol}): Skipping - pinMode already declared as {pinMode_pins[resolved_pin]}")
                    continue

                # This pin is used without pinMode - infer mode from usage
                if resolved_pin not in pin_info:
                    pin_info[resolved_pin] = {
                        'modes': [],
                        'descriptions': [],
                        'var_name': var_name or symbol,
                        'pinMode_declarations': []  # No pinMode declarations for this pin
                    }

                pin_info[resolved_pin]['modes'].append(mode_type)

                if comment and comment not in pin_info[resolved_pin]['descriptions']:
                    pin_info[resolved_pin]['descriptions'].append(comment)

                print(f"[PIN FUNCTION DEBUG] {mode_type}({symbol}) -> {resolved_pin} (inferred {mode_type})")

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

        Real conflicts:
        1. Contradictory pinMode() declarations (e.g., pinMode(13, OUTPUT) AND pinMode(13, INPUT))
        2. Board-specific restrictions (e.g., ESP32 GPIO34-39 are input-only)

        NOT conflicts:
        - OUTPUT + INPUT without pinMode declarations (reading OUTPUT pins is valid)
        - ANALOG + digital on AVR/STM32 (analog pins can do both)
        - Multiple modes inferred from usage (digitalWrite + digitalRead)

        Returns:
            Set of pin names with conflicts
        """
        conflicts = set()

        for pin, info in pin_info.items():
            modes = info['modes']

            # Check for contradictory pinMode declarations
            # Look for explicit pinMode() calls with different modes
            pinMode_modes = self._get_pinMode_declarations(pin)
            if len(pinMode_modes) > 1:
                # Multiple different pinMode declarations for same pin
                unique_pinMode = set(pinMode_modes)
                # INPUT and INPUT_PULLUP are compatible
                if unique_pinMode not in [{'INPUT', 'INPUT_PULLUP'}, {'INPUT'}, {'INPUT_PULLUP'}]:
                    conflicts.add(pin)
                    print(f"[CONFLICT] {pin}: Contradictory pinMode declarations: {pinMode_modes}")

            # Check board-specific restrictions
            board_conflict = self._check_board_restrictions(pin, modes)
            if board_conflict:
                conflicts.add(pin)
                print(f"[CONFLICT] {pin}: {board_conflict}")

        return conflicts

    def _get_pinMode_declarations(self, pin):
        """Get all pinMode mode declarations for a specific pin from stored parse data"""
        if not hasattr(self, 'current_pin_info') or not self.current_pin_info:
            return []

        pin_data = self.current_pin_info.get(pin, {})
        return pin_data.get('pinMode_declarations', [])

    def _check_board_restrictions(self, pin, modes):
        """Check board-specific pin restrictions

        Returns:
            String describing the conflict, or None if no conflict
        """
        if not self.current_board:
            return None

        architecture = self.current_board.architecture.lower()
        pin_num = self._extract_pin_number(pin)

        if pin_num is None:
            return None

        # ESP32-specific restrictions
        if architecture == "esp32":
            # GPIO 34-39 are input-only
            if pin_num in [34, 35, 36, 37, 38, 39]:
                output_modes = {'OUTPUT', 'PWM'}
                if any(mode in output_modes for mode in modes):
                    return f"GPIO{pin_num} is input-only on ESP32"

            # GPIO 6-11 are connected to SPI flash (usually can't be used)
            if pin_num in [6, 7, 8, 9, 10, 11]:
                return f"GPIO{pin_num} is connected to SPI flash on ESP32"

        # ESP8266-specific restrictions
        elif architecture == "esp8266":
            # GPIO 6-11 are connected to SPI flash
            if pin_num in [6, 7, 8, 9, 10, 11]:
                return f"GPIO{pin_num} is connected to SPI flash on ESP8266"

        return None

    def _extract_pin_number(self, pin_name):
        """Extract numeric pin number from pin name (D13 -> 13, A0 -> 0)"""
        import re
        match = re.search(r'(\d+)', pin_name)
        if match:
            return int(match.group(1))
        return None

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
        """Get list of available pins from the current board.

        Args:
            used_pins: Set of pin names already in use

        Returns:
            List of available pin names.
        """
        # If no board is set, default to Arduino Uno pins
        if not self.current_board:
            print("[PIN WIDGET DEBUG] No board set, using Arduino Uno defaults")
            digital_count = self.DEFAULT_DIGITAL_PIN_COUNT
            analog_count = self.DEFAULT_ANALOG_PIN_COUNT
        else:
            digital_count, analog_count = self._resolve_pin_counts(used_pins)
            print(f"[PIN WIDGET DEBUG] Board: {self.current_board.name}")
            print(f"[PIN WIDGET DEBUG] Digital pins: {digital_count}, Analog pins: {analog_count}")

        all_pins = (
            [f'D{i}' for i in range(digital_count)] +
            [f'A{i}' for i in range(analog_count)]
        )

        print(f"[PIN WIDGET DEBUG] Total pins generated: {len(all_pins)}")
        print(f"[PIN WIDGET DEBUG] Used pins: {used_pins}")
        available = [p for p in all_pins if p not in used_pins]
        print(f"[PIN WIDGET DEBUG] Available pins: {len(available)} pins")
        print(f"[PIN WIDGET DEBUG] First 10 available: {available[:10]}")
        return available

    def _resolve_pin_counts(self, used_pins):
        """Determine digital and analog pin counts with sensible fallbacks."""
        specs = getattr(self.current_board, 'specs', None)
        digital_pins = getattr(specs, 'digital_pins', 0) or 0
        analog_pins = getattr(specs, 'analog_pins', 0) or 0

        min_digital, min_analog = self._infer_min_pin_counts(used_pins)

        if digital_pins <= 0:
            digital_pins = max(self.DEFAULT_DIGITAL_PIN_COUNT, min_digital)
        else:
            digital_pins = max(digital_pins, min_digital)

        if analog_pins <= 0:
            analog_pins = max(self.DEFAULT_ANALOG_PIN_COUNT, min_analog)
        else:
            analog_pins = max(analog_pins, min_analog)

        return digital_pins, analog_pins

    def _infer_min_pin_counts(self, used_pins):
        """Infer minimum required pin counts from currently used pins."""
        max_digital = -1
        max_analog = -1

        for pin in used_pins:
            if pin.startswith('D'):
                pin_number = self._extract_pin_number(pin)
                if pin_number is not None:
                    max_digital = max(max_digital, pin_number + 1)
            elif pin.startswith('A'):
                pin_number = self._extract_pin_number(pin)
                if pin_number is not None:
                    max_analog = max(max_analog, pin_number + 1)

        min_digital = max_digital if max_digital >= 0 else 0
        min_analog = max_analog if max_analog >= 0 else 0

        return min_digital, min_analog
