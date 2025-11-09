"""Arduino IDE Modern - A modern Arduino development environment"""

from .config import APP_AUTHORS, APP_VERSION

__version__ = APP_VERSION
__author__ = ", ".join(APP_AUTHORS)

__all__ = ["__version__", "__author__"]
