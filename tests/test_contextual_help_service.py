"""Tests for the ContextualHelpService."""

from arduino_ide.services.contextual_help_service import ContextualHelpService


def _extract_messages(hints):
    return [hint.message for hint in hints]


def test_detects_unused_pin_mode_hint():
    service = ContextualHelpService()
    code = """
void setup() {
    pinMode(LED_PIN, OUTPUT);
}

void loop() {
    // nothing here
}
""".strip()

    hints = service.analyze_context((0, 0), code)
    messages = _extract_messages(hints)
    assert any("pinMode() called for LED_PIN" in msg for msg in messages)


def test_detects_delay_in_loop_hint():
    service = ContextualHelpService()
    code = """
void setup() {}

void loop() {
    delay(200);
}
""".strip()

    hints = service.analyze_context((4, 2), code)
    messages = _extract_messages(hints)
    assert any("Consider using millis()" in msg for msg in messages)


def test_serial_monitor_state_hint():
    service = ContextualHelpService()
    code = """
void setup() {
    Serial.begin(9600);
}

void loop() {
    Serial.println(42);
}
""".strip()

    hints = service.analyze_context(
        cursor_position={"line": 2, "column": 4},
        code=code,
        editor_state={"serial_monitor_open": False},
    )
    messages = _extract_messages(hints)
    assert any("Serial.begin() detected" in msg for msg in messages)


def test_show_inline_hints_formats_messages():
    service = ContextualHelpService()
    code = """
void setup() {
    pinMode(5, OUTPUT);
}
void loop() {
    delay(250);
}
""".strip()

    service.analyze_context(0, code)
    inline = service.show_inline_hints()
    assert inline
    assert all("line" in entry for entry in inline)
