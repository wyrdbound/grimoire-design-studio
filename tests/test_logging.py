"""
Tests for logging integration in GRIMOIRE Design Studio.
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

from grimoire_studio import get_package_logger
from grimoire_studio.main import _get_app_data_directory, setup_logging


def test_package_logger_initialization():
    """Test that package logger is properly initialized."""
    logger = get_package_logger()
    assert logger is not None
    # LoggerProtocol doesn't guarantee name attribute, so just test it's callable
    assert hasattr(logger, "info")
    assert callable(logger.info)


def test_get_app_data_directory_windows():
    """Test app data directory detection on Windows."""
    with patch("platform.system", return_value="Windows"):
        with patch.dict("os.environ", {"APPDATA": "/test/appdata"}):
            result = _get_app_data_directory()
            assert result == Path("/test/appdata/GRIMOIRE Design Studio")


def test_get_app_data_directory_macos():
    """Test app data directory detection on macOS."""
    with patch("platform.system", return_value="Darwin"):
        with patch("pathlib.Path.home", return_value=Path("/Users/test")):
            result = _get_app_data_directory()
            expected = Path(
                "/Users/test/Library/Application Support/GRIMOIRE Design Studio"
            )
            assert result == expected


@patch("platform.system", return_value="Linux")
@patch("pathlib.Path.home")
def test_get_app_data_directory_linux(mock_home, mock_system):
    """Test app data directory detection on Linux."""
    mock_home.return_value = Path("/home/test")
    # Clear XDG_CONFIG_HOME to ensure we use the home directory path
    with patch.dict("os.environ", {}, clear=True):
        result = _get_app_data_directory()
        expected = Path("/home/test/.config/grimoire-design-studio")
        assert result == expected


def test_get_app_data_directory_linux_xdg():
    """Test app data directory detection on Linux with XDG_CONFIG_HOME."""
    with patch("platform.system", return_value="Linux"):
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": "/test/config"}):
            result = _get_app_data_directory()
            expected = Path("/test/config/grimoire-design-studio")
            assert result == expected


def test_setup_logging_creates_log_directory():
    """Test that setup_logging creates the log directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_app_dir = Path(temp_dir) / "test_app"

        with patch(
            "grimoire_studio.main._get_app_data_directory", return_value=test_app_dir
        ):
            # Clear any existing handlers before test
            root_logger = logging.getLogger()
            original_handlers = root_logger.handlers[:]
            root_logger.handlers.clear()

            try:
                setup_logging(debug=False)

                # Check that log directory was created
                log_dir = test_app_dir / "logs"
                assert log_dir.exists()
                assert log_dir.is_dir()
            finally:
                # Clean up handlers to avoid file locks on Windows
                for handler in root_logger.handlers[:]:
                    if hasattr(handler, "close"):
                        handler.close()
                    root_logger.removeHandler(handler)
                # Restore original handlers
                root_logger.handlers[:] = original_handlers


def test_setup_logging_configures_handlers():
    """Test that setup_logging configures both console and file handlers."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_app_dir = Path(temp_dir) / "test_app"

        with patch(
            "grimoire_studio.main._get_app_data_directory", return_value=test_app_dir
        ):
            # Clear any existing handlers
            root_logger = logging.getLogger()
            original_handlers = root_logger.handlers[:]
            root_logger.handlers.clear()

            try:
                setup_logging(debug=True)

                # Check that handlers were added
                assert len(root_logger.handlers) >= 2

                # Check handler types
                handler_types = [type(h).__name__ for h in root_logger.handlers]
                assert "StreamHandler" in handler_types  # Console handler
                assert "RotatingFileHandler" in handler_types  # File handler
            finally:
                # Clean up handlers to avoid file locks on Windows
                for handler in root_logger.handlers[:]:
                    if hasattr(handler, "close"):
                        handler.close()
                    root_logger.removeHandler(handler)
                # Restore original handlers
                root_logger.handlers[:] = original_handlers


def test_setup_logging_debug_mode():
    """Test that debug mode sets appropriate log levels."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_app_dir = Path(temp_dir) / "test_app"

        with patch(
            "grimoire_studio.main._get_app_data_directory", return_value=test_app_dir
        ):
            root_logger = logging.getLogger()
            original_handlers = root_logger.handlers[:]
            root_logger.handlers.clear()

            try:
                setup_logging(debug=True)

                # Check that root logger level is DEBUG
                assert root_logger.level == logging.DEBUG

                # Check console handler level is DEBUG
                console_handlers = [
                    h
                    for h in root_logger.handlers
                    if isinstance(h, logging.StreamHandler)
                    and not hasattr(h, "maxBytes")
                ]
                assert len(console_handlers) > 0
                assert console_handlers[0].level == logging.DEBUG
            finally:
                # Clean up handlers to avoid file locks on Windows
                for handler in root_logger.handlers[:]:
                    if hasattr(handler, "close"):
                        handler.close()
                    root_logger.removeHandler(handler)
                # Restore original handlers
                root_logger.handlers[:] = original_handlers


def test_setup_logging_production_mode():
    """Test that production mode sets appropriate log levels."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_app_dir = Path(temp_dir) / "test_app"

        with patch(
            "grimoire_studio.main._get_app_data_directory", return_value=test_app_dir
        ):
            root_logger = logging.getLogger()
            original_handlers = root_logger.handlers[:]
            root_logger.handlers.clear()

            try:
                setup_logging(debug=False)

                # Check that root logger level is INFO
                assert root_logger.level == logging.INFO

                # Check console handler level is INFO
                console_handlers = [
                    h
                    for h in root_logger.handlers
                    if isinstance(h, logging.StreamHandler)
                    and not hasattr(h, "maxBytes")
                ]
                assert len(console_handlers) > 0
                assert console_handlers[0].level == logging.INFO
            finally:
                # Clean up handlers to avoid file locks on Windows
                for handler in root_logger.handlers[:]:
                    if hasattr(handler, "close"):
                        handler.close()
                    root_logger.removeHandler(handler)
                # Restore original handlers
                root_logger.handlers[:] = original_handlers
