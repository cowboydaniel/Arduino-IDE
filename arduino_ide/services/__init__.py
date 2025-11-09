"""Services for Arduino IDE Modern"""

# Lazy import to avoid PySide6 dependency when using CLI only
try:
    from .cli_runner import ArduinoCliService
    __all__ = ["ArduinoCliService"]
except ImportError:
    # PySide6 not available - CLI will work without Qt components
    __all__ = []
