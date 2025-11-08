"""
Inline suggestions analyzer for Arduino code
"""

import re
from typing import List, Dict, Tuple


class Suggestion:
    """Represents a code suggestion"""

    def __init__(self, line_number: int, message: str, severity: str = 'tip',
                 column: int = 0, length: int = 0):
        """
        Initialize a suggestion

        Args:
            line_number: Line number (1-indexed)
            message: Suggestion message to display
            severity: 'tip', 'info', or 'warning'
            column: Column position in the line (0-indexed)
            length: Length of the text to underline (0 means whole line)
        """
        self.line_number = line_number
        self.message = message
        self.severity = severity
        self.column = column
        self.length = length


class SuggestionAnalyzer:
    """Analyzes Arduino code for helpful suggestions"""

    def __init__(self):
        """Initialize the analyzer"""
        pass

    def analyze(self, text: str) -> List[Suggestion]:
        """
        Analyze code and return list of suggestions

        Args:
            text: Full code text

        Returns:
            List of Suggestion objects
        """
        suggestions = []
        lines = text.split('\n')

        # Check for various patterns
        suggestions.extend(self._detect_hardcoded_led_pin(lines))
        suggestions.extend(self._detect_hardcoded_pins(lines))
        suggestions.extend(self._detect_serial_without_monitor(text, lines))
        suggestions.extend(self._detect_delay_in_loop(lines))
        suggestions.extend(self._detect_missing_pinMode(text, lines))
        suggestions.extend(self._detect_magic_numbers(lines))
        suggestions.extend(self._detect_analog_pin_mode(lines))

        return suggestions

    def _detect_hardcoded_led_pin(self, lines: List[str]) -> List[Suggestion]:
        """Detect pinMode(13, OUTPUT) and suggest LED_BUILTIN"""
        suggestions = []

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            clean_line = re.sub(r'//.*', '', line)
            clean_line = re.sub(r'/\*.*?\*/', '', clean_line)

            # Check for pinMode(13, OUTPUT)
            match = re.search(r'pinMode\s*\(\s*13\s*,\s*(OUTPUT|INPUT)\s*\)', clean_line)
            if match:
                suggestions.append(Suggestion(
                    line_number=line_num,
                    message="💡 Tip: Use LED_BUILTIN instead of 13 for the built-in LED",
                    severity='tip',
                    column=match.start(),
                    length=match.end() - match.start()
                ))

            # Check for digitalWrite(13, ...)
            match = re.search(r'digitalWrite\s*\(\s*13\s*,', clean_line)
            if match:
                suggestions.append(Suggestion(
                    line_number=line_num,
                    message="💡 Tip: Use LED_BUILTIN instead of hardcoding 13",
                    severity='tip',
                    column=match.start(),
                    length=match.end() - match.start()
                ))

        return suggestions

    def _detect_hardcoded_pins(self, lines: List[str]) -> List[Suggestion]:
        """Detect hardcoded pin numbers and suggest using constants"""
        suggestions = []

        for line_num, line in enumerate(lines, 1):
            # Skip comments and strings
            clean_line = re.sub(r'//.*', '', line)
            clean_line = re.sub(r'/\*.*?\*/', '', clean_line)
            clean_line = re.sub(r'"[^"]*"', '', clean_line)

            # Skip if line already has constants (likely a definition)
            if re.search(r'\b(const|#define)\b', clean_line):
                continue

            # Check for pinMode/digitalWrite/digitalRead with numeric literals (except 13 which is handled separately)
            match = re.search(r'(pinMode|digitalWrite|digitalRead)\s*\(\s*([0-9]|1[0-2])\s*,', clean_line)
            if match and match.group(2) != '13':
                pin_num = match.group(2)
                suggestions.append(Suggestion(
                    line_number=line_num,
                    message=f"💡 Tip: Consider using a named constant instead of pin {pin_num}",
                    severity='tip',
                    column=match.start(),
                    length=match.end() - match.start()
                ))

        return suggestions

    def _detect_serial_without_monitor(self, text: str, lines: List[str]) -> List[Suggestion]:
        """Detect Serial usage without checking Serial Monitor"""
        suggestions = []

        # Check if Serial is used anywhere
        has_serial = bool(re.search(r'Serial\.(begin|print|println|write)', text))

        if has_serial:
            # Check if there's a comment about Serial Monitor
            has_monitor_reminder = bool(re.search(r'(Serial Monitor|serial monitor|monitor)', text, re.IGNORECASE))

            if not has_monitor_reminder:
                # Find the first Serial usage
                for line_num, line in enumerate(lines, 1):
                    if re.search(r'Serial\.(begin|print|println|write)', line):
                        suggestions.append(Suggestion(
                            line_number=line_num,
                            message="💡 Remember to open the Serial Monitor to see output (Tools > Serial Monitor)",
                            severity='info'
                        ))
                        break  # Only show once

        return suggestions

    def _detect_delay_in_loop(self, lines: List[str]) -> List[Suggestion]:
        """Detect delay() in loop() and suggest millis()"""
        suggestions = []

        in_loop = False
        loop_start = 0

        for line_num, line in enumerate(lines, 1):
            # Detect loop function
            if re.search(r'void\s+loop\s*\(', line):
                in_loop = True
                loop_start = line_num
                continue

            # Exit loop function when we see another function definition
            if in_loop and re.search(r'void\s+\w+\s*\(', line) and line_num > loop_start + 1:
                in_loop = False

            # Check for delay in loop
            if in_loop:
                match = re.search(r'delay\s*\(\s*(\d+)\s*\)', line)
                if match:
                    delay_ms = match.group(1)
                    # Only suggest for delays > 50ms (shorter delays are usually fine)
                    if int(delay_ms) > 50:
                        suggestions.append(Suggestion(
                            line_number=line_num,
                            message=f"💡 Tip: Consider using millis() instead of delay() for non-blocking code",
                            severity='tip',
                            column=match.start(),
                            length=match.end() - match.start()
                        ))

        return suggestions

    def _detect_missing_pinMode(self, text: str, lines: List[str]) -> List[Suggestion]:
        """Detect digitalWrite/digitalRead without corresponding pinMode"""
        suggestions = []

        # Find all pinMode declarations
        pinmode_pins = set()
        for line in lines:
            matches = re.finditer(r'pinMode\s*\(\s*(\w+)\s*,', line)
            for match in matches:
                pinmode_pins.add(match.group(1))

        # Check digitalWrite/digitalRead
        checked_pins = set()
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            clean_line = re.sub(r'//.*', '', line)

            # Find digitalWrite/digitalRead
            for func in ['digitalWrite', 'digitalRead']:
                matches = re.finditer(rf'{func}\s*\(\s*(\w+)\s*,?', clean_line)
                for match in matches:
                    pin = match.group(1)
                    # Skip if already checked or if pinMode exists
                    if pin in checked_pins or pin in pinmode_pins:
                        continue

                    # Skip if it's a number (might be intentional)
                    if pin.isdigit():
                        continue

                    checked_pins.add(pin)
                    suggestions.append(Suggestion(
                        line_number=line_num,
                        message=f"💡 Tip: Don't forget to set pinMode for pin '{pin}' in setup()",
                        severity='info',
                        column=match.start(),
                        length=match.end() - match.start()
                    ))

        return suggestions

    def _detect_magic_numbers(self, lines: List[str]) -> List[Suggestion]:
        """Detect magic numbers in comparisons"""
        suggestions = []

        for line_num, line in enumerate(lines, 1):
            # Skip comments and const definitions
            clean_line = re.sub(r'//.*', '', line)
            if re.search(r'\b(const|#define)\b', clean_line):
                continue

            # Check for sensor thresholds (common magic numbers)
            matches = re.finditer(r'(analogRead|digitalRead)\s*\([^)]+\)\s*([<>=!]+)\s*(\d{2,})', clean_line)
            for match in matches:
                threshold = match.group(3)
                suggestions.append(Suggestion(
                    line_number=line_num,
                    message=f"💡 Tip: Consider using a named constant for threshold value {threshold}",
                    severity='tip',
                    column=match.start(),
                    length=match.end() - match.start()
                ))

        return suggestions

    def _detect_analog_pin_mode(self, lines: List[str]) -> List[Suggestion]:
        """Detect pinMode on analog pins (usually not needed)"""
        suggestions = []

        for line_num, line in enumerate(lines, 1):
            # Check for pinMode on analog pins
            match = re.search(r'pinMode\s*\(\s*A[0-7]\s*,\s*INPUT\s*\)', line)
            if match:
                suggestions.append(Suggestion(
                    line_number=line_num,
                    message="💡 Note: pinMode is not required for analogRead() on analog pins",
                    severity='info',
                    column=match.start(),
                    length=match.end() - match.start()
                ))

        return suggestions
