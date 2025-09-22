"""
GRIMOIRE Design Studio

A comprehensive design studio for creating, editing, and testing GRIMOIRE system YAML definitions.
"""

__version__ = "1.0.0"
__author__ = "The Wyrd One"
__email__ = "wyrdbound@proton.me"

from grimoire_logging import get_logger

# Initialize logging for the package
logger = get_logger(__name__)
logger.info(f"GRIMOIRE Design Studio v{__version__} initialized")
