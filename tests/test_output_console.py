"""
Tests for OutputConsole business logic.

This module tests the core functionality of the OutputConsole class including
message display, tab management, logging integration, and content formatting.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtGui import QColor

from grimoire_studio.ui.components.output_console import LogHandler, OutputConsole


class TestOutputConsoleBusinessLogic:
    """Test OutputConsole business logic functionality."""

    @pytest.fixture
    def output_console(self, qtbot):
        """Create an OutputConsole instance for testing."""
        console = OutputConsole()
        qtbot.addWidget(console)
        return console

    def test_initialization(self, output_console):
        """Test that OutputConsole initializes correctly."""
        # Check that all tabs are created
        assert output_console._tab_widget.count() == 3
        assert output_console._tab_widget.tabText(0) == "Validation"
        assert output_console._tab_widget.tabText(1) == "Execution"
        assert output_console._tab_widget.tabText(2) == "Logs"

        # Check initial state
        assert output_console.get_current_tab() == "validation"
        assert output_console._log_level_filter == logging.INFO

        # Check that text areas exist
        assert output_console._validation_text is not None
        assert output_console._execution_text is not None
        assert output_console._logs_text is not None

    def test_color_constants(self, output_console):
        """Test that color constants are properly defined."""
        assert isinstance(output_console.ERROR_COLOR, QColor)
        assert isinstance(output_console.WARNING_COLOR, QColor)
        assert isinstance(output_console.SUCCESS_COLOR, QColor)
        assert isinstance(output_console.INFO_COLOR, QColor)
        assert isinstance(output_console.DEBUG_COLOR, QColor)

        # Verify specific colors
        assert output_console.ERROR_COLOR == QColor("#dc3545")
        assert output_console.WARNING_COLOR == QColor("#ffc107")
        assert output_console.SUCCESS_COLOR == QColor("#28a745")

    def test_validation_results_display_single_error(self, output_console):
        """Test displaying a single validation error."""
        results = [
            {
                "level": "error",
                "message": "Missing required field 'id'",
                "file": "/path/to/file.yaml",
                "line": 5,
            }
        ]

        output_console.display_validation_results(results, auto_switch=False)

        # Check that content was added
        content = output_console._validation_text.toPlainText()
        assert "Validation Results:" in content
        assert "ERROR: Missing required field 'id'" in content
        assert "file.yaml:5" in content

    def test_validation_results_display_multiple_levels(self, output_console):
        """Test displaying validation results with different levels."""
        results = [
            {"level": "error", "message": "Critical error"},
            {"level": "warning", "message": "Minor warning"},
            {"level": "success", "message": "All good"},
            {"level": "info", "message": "Information"},
        ]

        output_console.display_validation_results(results, auto_switch=False)

        content = output_console._validation_text.toPlainText()
        assert "❌ ERROR: Critical error" in content
        assert "⚠️  WARNING: Minor warning" in content
        assert "✅ SUCCESS: All good" in content
        assert "ℹ️  INFO: Information" in content

    def test_validation_results_without_file_info(self, output_console):
        """Test validation results without file/line information."""
        results = [{"level": "error", "message": "Generic error"}]

        output_console.display_validation_results(results, auto_switch=False)

        content = output_console._validation_text.toPlainText()
        assert "ERROR: Generic error" in content
        # Should not contain file references
        assert " (in " not in content

    def test_validation_results_auto_switch(self, output_console, qtbot):
        """Test that validation results auto-switch to validation tab."""
        # Start on a different tab
        output_console.switch_to_logs_tab()
        assert output_console.get_current_tab() == "logs"

        results = [{"level": "error", "message": "Test error"}]
        output_console.display_validation_results(results, auto_switch=True)

        assert output_console.get_current_tab() == "validation"

    def test_execution_output_display(self, output_console):
        """Test displaying execution output with different levels."""
        test_cases = [
            ("info", "Process started", "INFO"),
            ("warning", "Slow operation", "WARNING"),
            ("error", "Process failed", "ERROR"),
            ("success", "Process completed", "SUCCESS"),
        ]

        for level, message, expected_prefix in test_cases:
            output_console.clear_execution()
            output_console.display_execution_output(message, level, auto_switch=False)

            content = output_console._execution_text.toPlainText()
            assert f"[{expected_prefix}] {message}" in content

    def test_execution_output_auto_switch(self, output_console):
        """Test that execution output auto-switches to execution tab."""
        # Start on validation tab
        output_console.switch_to_validation_tab()
        assert output_console.get_current_tab() == "validation"

        output_console.display_execution_output("Test message", auto_switch=True)

        assert output_console.get_current_tab() == "execution"

    def test_log_message_display(self, output_console):
        """Test displaying log messages with different levels."""
        test_cases = [
            (logging.DEBUG, "Debug message", "DEBUG"),
            (logging.INFO, "Info message", "INFO"),
            (logging.WARNING, "Warning message", "WARNING"),
            (logging.ERROR, "Error message", "ERROR"),
        ]

        for level, message, expected_prefix in test_cases:
            output_console.clear_logs()
            output_console.display_log_message(message, level, "test.logger")

            content = output_console._logs_text.toPlainText()
            if level >= output_console._log_level_filter:
                assert f"{expected_prefix} test.logger: {message}" in content
            else:
                # Message should be filtered out
                assert content.strip() == ""

    def test_log_level_filtering(self, output_console):
        """Test that log level filtering works correctly."""
        # Set filter to WARNING
        output_console.set_log_level_filter(logging.WARNING)

        # Add messages at different levels
        output_console.display_log_message("Debug msg", logging.DEBUG)
        output_console.display_log_message("Info msg", logging.INFO)
        output_console.display_log_message("Warning msg", logging.WARNING)
        output_console.display_log_message("Error msg", logging.ERROR)

        content = output_console._logs_text.toPlainText()

        # Only WARNING and ERROR should appear
        assert "Debug msg" not in content
        assert "Info msg" not in content
        assert "Warning msg" in content
        assert "Error msg" in content

    def test_clear_validation(self, output_console):
        """Test clearing validation tab content."""
        results = [{"level": "error", "message": "Test error"}]
        output_console.display_validation_results(results, auto_switch=False)

        # Verify content exists
        assert output_console._validation_text.toPlainText().strip() != ""

        # Clear and verify
        output_console.clear_validation()
        assert output_console._validation_text.toPlainText().strip() == ""

    def test_clear_execution(self, output_console):
        """Test clearing execution tab content."""
        output_console.display_execution_output("Test message", auto_switch=False)

        # Verify content exists
        assert output_console._execution_text.toPlainText().strip() != ""

        # Clear and verify
        output_console.clear_execution()
        assert output_console._execution_text.toPlainText().strip() == ""

    def test_clear_logs(self, output_console):
        """Test clearing logs tab content."""
        output_console.display_log_message("Test log", logging.INFO)

        # Verify content exists
        assert output_console._logs_text.toPlainText().strip() != ""

        # Clear and verify
        output_console.clear_logs()
        assert output_console._logs_text.toPlainText().strip() == ""

    def test_clear_all(self, output_console):
        """Test clearing all tab contents."""
        # Add content to all tabs
        output_console.display_validation_results(
            [{"level": "error", "message": "Test"}], auto_switch=False
        )
        output_console.display_execution_output("Test", auto_switch=False)
        output_console.display_log_message("Test", logging.INFO)

        # Verify all have content
        assert output_console._validation_text.toPlainText().strip() != ""
        assert output_console._execution_text.toPlainText().strip() != ""
        assert output_console._logs_text.toPlainText().strip() != ""

        # Clear all
        output_console.clear_all()

        # Verify all are cleared
        assert output_console._validation_text.toPlainText().strip() == ""
        assert output_console._execution_text.toPlainText().strip() == ""
        assert output_console._logs_text.toPlainText().strip() == ""

    def test_tab_switching_methods(self, output_console):
        """Test manual tab switching methods."""
        # Test switching to each tab
        output_console.switch_to_validation_tab()
        assert output_console.get_current_tab() == "validation"

        output_console.switch_to_execution_tab()
        assert output_console.get_current_tab() == "execution"

        output_console.switch_to_logs_tab()
        assert output_console.get_current_tab() == "logs"

    def test_get_current_tab_unknown_index(self, output_console):
        """Test get_current_tab with invalid index."""
        # Manually set an invalid index - Qt will clamp to valid range
        # This test verifies the method handles edge cases gracefully
        output_console._tab_widget.setCurrentIndex(99)
        # Qt automatically clamps to valid range, so we should get a valid tab name
        result = output_console.get_current_tab()
        assert result in ["validation", "execution", "logs"]

    def test_console_font_configuration(self, output_console):
        """Test that console font is properly configured."""
        font = output_console._get_console_font()
        assert font.styleHint() == font.StyleHint.Monospace
        assert font.pointSize() == 9

    def test_timestamp_format(self, output_console):
        """Test that timestamps are included in messages."""
        with patch("grimoire_studio.ui.components.output_console.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "12:34:56"

            output_console.display_execution_output("Test", auto_switch=False)
            content = output_console._execution_text.toPlainText()
            assert "[12:34:56]" in content

    def test_signal_emission_on_content_added(self, output_console, qtbot):
        """Test that content_added signal is emitted correctly."""
        with qtbot.waitSignal(output_console.content_added) as blocker:
            output_console.display_validation_results(
                [{"level": "info", "message": "Test"}], auto_switch=False
            )

        assert blocker.args == ["validation"]

        with qtbot.waitSignal(output_console.content_added) as blocker:
            output_console.display_execution_output("Test", auto_switch=False)

        assert blocker.args == ["execution"]

        with qtbot.waitSignal(output_console.content_added) as blocker:
            output_console.display_log_message("Test", logging.INFO)

        assert blocker.args == ["logs"]


class TestLogHandler:
    """Test the LogHandler custom logging handler."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock OutputConsole for testing."""
        return MagicMock()

    @pytest.fixture
    def log_handler(self, mock_console):
        """Create a LogHandler instance for testing."""
        return LogHandler(mock_console)

    def test_log_handler_initialization(self, mock_console):
        """Test LogHandler initialization."""
        handler = LogHandler(mock_console, prefix="[TEST] ")
        assert handler._output_console is mock_console
        assert handler._prefix == "[TEST] "
        assert handler._message_queue == []

    def test_log_handler_emit(self, log_handler):
        """Test emitting log records."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        log_handler.emit(record)

        # Should have queued the message
        assert len(log_handler._message_queue) == 1
        message, level, logger_name = log_handler._message_queue[0]
        assert "Test message" in message
        assert level == logging.INFO
        assert logger_name == "test.logger"

    def test_log_handler_with_prefix(self, mock_console):
        """Test LogHandler with prefix."""
        handler = LogHandler(mock_console, prefix="[SYS] ")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Message should have prefix
        message, _, _ = handler._message_queue[0]
        assert message.startswith("[SYS] ")

    def test_log_handler_error_handling(self, mock_console):
        """Test that LogHandler doesn't crash on errors."""
        handler = LogHandler(mock_console)

        # Create a problematic record
        record = MagicMock()
        record.levelno = logging.INFO
        record.name = "test"

        # Mock format to raise an exception
        handler.format = MagicMock(side_effect=Exception("Format error"))

        # Should not raise exception
        handler.emit(record)

        # Queue should be empty due to error
        assert len(handler._message_queue) == 0

    @patch("grimoire_studio.ui.components.output_console.QTimer")
    def test_log_handler_timer_management(self, mock_timer_class, mock_console):
        """Test that the LogHandler manages its timer correctly."""
        mock_timer = MagicMock()
        mock_timer_class.return_value = mock_timer

        LogHandler(mock_console)

        # Timer should be created and configured
        mock_timer_class.assert_called_once()
        mock_timer.timeout.connect.assert_called_once()
        mock_timer.setSingleShot.assert_called_once_with(False)
        mock_timer.setInterval.assert_called_once_with(100)

    def test_message_queue_batching(self, log_handler):
        """Test that messages are properly queued for batching."""
        # Add multiple messages
        for i in range(5):
            record = logging.LogRecord(
                name=f"test{i}",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"Message {i}",
                args=(),
                exc_info=None,
            )
            log_handler.emit(record)

        # All should be queued
        assert len(log_handler._message_queue) == 5

        # Messages should be in order
        for i in range(5):
            message, level, logger_name = log_handler._message_queue[i]
            assert f"Message {i}" in message
            assert logger_name == f"test{i}"
