"""Tests for the SmartErrorRecovery helper."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from arduino_ide.services.error_recovery import SmartErrorRecovery


def test_missing_semicolon_suggestion():
    recovery = SmartErrorRecovery()

    suggestions = recovery.analyze_compile_error("error: missing semicolon before '}'")

    assert suggestions, "Expected at least one suggestion for the error"
    first = suggestions[0]
    assert first.issue == "missing semicolon"
    assert "Add ; at end of line" in first.suggestions
    assert first.confidence > 0.5


def test_multiple_matches_are_preserved():
    recovery = SmartErrorRecovery()
    error_msg = "error: undeclared identifier 'foo' and not enough memory"

    suggestions = recovery.analyze_compile_error(error_msg)

    issues = {s.issue for s in suggestions}
    assert "undeclared identifier" in issues
    assert "not enough memory" in issues



def test_unknown_error_returns_generic_advice():
    recovery = SmartErrorRecovery()

    suggestions = recovery.analyze_compile_error("internal compiler panic")

    assert len(suggestions) == 1
    assert suggestions[0].issue == "unknown"
    assert suggestions[0].suggestions  # Should provide fallback guidance
