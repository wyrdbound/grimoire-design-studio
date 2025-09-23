"""
GRIMOIRE Design Studio

A comprehensive design studio for creating, editing, and testing GRIMOIRE system YAML definitions.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grimoire_logging import LoggerProtocol

__version__ = "1.0.0"
__author__ = "The Wyrd One"
__email__ = "wyrdbound@proton.me"

from grimoire_logging import get_logger

# Package-level logger
_logger = get_logger(__name__)


def get_package_logger() -> "LoggerProtocol":
    """Get the package-level logger for grimoire_studio."""
    return _logger


def initialize_package() -> None:
    """Initialize the GRIMOIRE Design Studio package."""
    _logger.info(f"GRIMOIRE Design Studio v{__version__} package initialized")
    _logger.debug(f"Author: {__author__} <{__email__}>")


# Auto-initialize when package is imported
initialize_package()
