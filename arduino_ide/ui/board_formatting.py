"""Utilities for presenting board specifications consistently across views."""

from __future__ import annotations

from typing import Dict, Optional

from arduino_ide.models.board import Board

_UNKNOWN = "Unknown"
_YES = "✅ Yes"
_NO = "❌ No"


def _text_or_unknown(value: Optional[str]) -> str:
    """Return the string value or a fallback when missing."""
    if value is None:
        return _UNKNOWN
    if isinstance(value, str):
        return value if value.strip() else _UNKNOWN
    return str(value)


def _format_yes_no(value: Optional[bool]) -> str:
    if value is None:
        return _UNKNOWN
    return _YES if value else _NO


def _format_digital_pins(digital: Optional[int], pwm: Optional[int]) -> str:
    digital_text = _UNKNOWN if digital is None else str(digital)
    pwm_text = _UNKNOWN if pwm is None else str(pwm)
    return f"{digital_text} (PWM: {pwm_text})"


def _format_touch_pins(value: Optional[int]) -> str:
    if value is None:
        return _UNKNOWN
    if value > 0:
        return str(value)
    return _NO


def format_board_specifications(board: Optional[Board]) -> Dict[str, str]:
    """Format core board specifications for display."""
    specs = getattr(board, "specs", None)
    return {
        "cpu": _text_or_unknown(getattr(specs, "cpu", None)),
        "clock": _text_or_unknown(getattr(specs, "clock", None)),
        "flash": _text_or_unknown(getattr(specs, "flash", None)),
        "ram": _text_or_unknown(getattr(specs, "ram", None)),
        "voltage": _text_or_unknown(getattr(specs, "voltage", None)),
        "digital_pins": _format_digital_pins(
            getattr(specs, "digital_pins", None), getattr(specs, "pwm_pins", None)
        ),
    }


def format_board_features(board: Optional[Board]) -> Dict[str, str]:
    """Format capability flags for display."""
    specs = getattr(board, "specs", None)
    return {
        "wifi": _format_yes_no(getattr(specs, "wifi", None)),
        "bluetooth": _format_yes_no(getattr(specs, "bluetooth", None)),
        "usb": _format_yes_no(getattr(specs, "usb", None)),
        "adc": _text_or_unknown(getattr(specs, "adc_resolution", None)),
        "dac": _format_yes_no(getattr(specs, "dac", None)),
        "touch": _format_touch_pins(getattr(specs, "touch_pins", None)),
        "rtc": _format_yes_no(getattr(specs, "rtc", None)),
        "sleep": _format_yes_no(getattr(specs, "sleep_mode", None)),
    }


def format_board_power(board: Optional[Board]) -> Dict[str, str]:
    """Format power consumption metrics for display."""
    specs = getattr(board, "specs", None)
    return {
        "typical": _text_or_unknown(getattr(specs, "power_typical", None)),
        "maximum": _text_or_unknown(getattr(specs, "power_max", None)),
    }
