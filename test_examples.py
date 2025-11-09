#!/usr/bin/env python3
"""Regression tests for example loading fallbacks."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


def _load_template_builder():
    """Load the template builder without importing PySide dependencies."""

    module_path = Path(__file__).parent / "arduino_ide" / "ui" / "example_templates.py"
    spec = spec_from_file_location("arduino_ide.ui.example_templates", module_path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_missing_example_template


build_missing_example_template = _load_template_builder()


class MissingExampleTemplateTest(unittest.TestCase):
    """Verify the generated fallback sketch content."""

    def test_template_includes_board_information_and_docs(self):
        """The fallback template should mention the board and documentation."""
        template = build_missing_example_template("Foo", "Arduino Uno")

        self.assertIn("Missing Example: Foo", template)
        self.assertIn("Selected board: Arduino Uno", template)
        self.assertIn("https://docs.arduino.cc/built-in-examples/", template)
        self.assertIn("Serial.begin(9600);", template)
        self.assertIn("Open the Serial Monitor", template)
        self.assertNotIn("while (!Serial)", template)

    def test_template_waits_for_usb_serial_on_native_boards(self):
        """Boards with native USB should include the wait-for-serial loop."""
        template = build_missing_example_template("Bar", "Arduino Leonardo")

        self.assertIn("while (!Serial)", template)
        self.assertIn("USB serial connection on Arduino Leonardo", template)


if __name__ == "__main__":
    unittest.main()
