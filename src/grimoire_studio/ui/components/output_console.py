"""
Output console implementation for GRIMOIRE Design Studio.

This module provides the OutputConsole class which implements a tabbed interface
for displaying validation results, execution logs, and application logs with
proper formatting, color coding, and automatic tab switching.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from grimoire_logging import get_logger
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = get_logger(__name__)


class OutputConsole(QWidget):
    """
    Tabbed output console for displaying validation results, execution logs, and application logs.

    The console provides three main tabs:
    - Validation: Display validation results with color-coded errors, warnings, and success messages
    - Execution: Show flow execution output, progress, and results
    - Logs: Application debug information from the logging system

    Features:
    - Color-coded output (errors in red, warnings in yellow, success in green)
    - Auto-switching to relevant tab when new content arrives
    - Clear buttons for each tab
    - Automatic scrolling to new content
    - Timestamp display for logs
    - Log level filtering
    """

    # Color constants for different message types
    ERROR_COLOR = QColor("#dc3545")  # Bootstrap danger red
    WARNING_COLOR = QColor("#ffc107")  # Bootstrap warning yellow
    SUCCESS_COLOR = QColor("#28a745")  # Bootstrap success green
    INFO_COLOR = QColor("#17a2b8")  # Bootstrap info blue
    DEBUG_COLOR = QColor("#6c757d")  # Bootstrap secondary gray

    # Signals
    content_added = pyqtSignal(str)  # Emitted when content is added to any tab

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the output console.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        # Use a separate logger for OutputConsole's internal logging to avoid circular references
        self._logger = get_logger("grimoire_studio.ui.internal")

        # Tab indices
        self._validation_tab_index = 0
        self._execution_tab_index = 1
        self._logs_tab_index = 2

        # Log filtering - use INFO level by default to capture important messages
        # Users can change this later if needed via set_log_level_filter()
        self._log_level_filter = logging.INFO

        # Setup UI
        self._setup_ui()
        self._setup_logging_handler()

        self._logger.debug("OutputConsole initialized")

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create tab widget
        self._tab_widget = QTabWidget()
        layout.addWidget(self._tab_widget)

        # Create tabs
        self._create_validation_tab()
        self._create_execution_tab()
        self._create_logs_tab()

        # Connect tab change signal
        self._tab_widget.currentChanged.connect(self._on_tab_changed)

    def _create_validation_tab(self) -> None:
        """Create the validation results tab."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)

        # Header with clear button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 0)

        self._validation_clear_btn = QPushButton("Clear")
        self._validation_clear_btn.clicked.connect(self.clear_validation)
        header_layout.addStretch()
        header_layout.addWidget(self._validation_clear_btn)

        layout.addLayout(header_layout)

        # Text area
        self._validation_text = QTextEdit()
        self._validation_text.setReadOnly(True)
        self._validation_text.setFont(self._get_console_font())
        self._validation_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 8px;
            }
            """
        )

        layout.addWidget(self._validation_text)

        self._tab_widget.addTab(tab_widget, "Validation")

    def _create_execution_tab(self) -> None:
        """Create the execution results tab."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)

        # Header with clear button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 0)

        self._execution_clear_btn = QPushButton("Clear")
        self._execution_clear_btn.clicked.connect(self.clear_execution)
        header_layout.addStretch()
        header_layout.addWidget(self._execution_clear_btn)

        layout.addLayout(header_layout)

        # Text area
        self._execution_text = QTextEdit()
        self._execution_text.setReadOnly(True)
        self._execution_text.setFont(self._get_console_font())
        self._execution_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 8px;
            }
            """
        )

        layout.addWidget(self._execution_text)

        self._tab_widget.addTab(tab_widget, "Execution")

    def _create_logs_tab(self) -> None:
        """Create the application logs tab."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)

        # Header with clear button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 0)

        self._logs_clear_btn = QPushButton("Clear")
        self._logs_clear_btn.clicked.connect(self.clear_logs)
        header_layout.addStretch()
        header_layout.addWidget(self._logs_clear_btn)

        layout.addLayout(header_layout)

        # Text area
        self._logs_text = QTextEdit()
        self._logs_text.setReadOnly(True)
        self._logs_text.setFont(self._get_console_font())
        self._logs_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 8px;
            }
            """
        )

        layout.addWidget(self._logs_text)

        self._tab_widget.addTab(tab_widget, "Logs")

    def _get_console_font(self) -> QFont:
        """Get a monospace font for console display."""
        font = QFont("Consolas")
        if not font.exactMatch():
            font = QFont("Monaco")
            if not font.exactMatch():
                font = QFont("Courier New")

        font.setPointSize(11)  # Increased from 9 to 11 for better readability
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    def _setup_logging_handler(self) -> None:
        """Set up logging handler to capture ALL application logs from the same logger that feeds the terminal."""
        # Create simple log handler - no batching, immediate display
        self._log_handler = LogHandler(self, use_batching=False)
        self._log_handler.setLevel(self._log_level_filter)

        # The main app sends all logs through the root logger, so we attach there
        # to capture the same messages that appear in the terminal
        root_logger = logging.getLogger()
        root_logger.addHandler(self._log_handler)

        self._logger.debug("OutputConsole handler attached to root logger")

    def _append_colored_text(
        self, text_edit: QTextEdit, text: str, color: QColor
    ) -> None:
        """
        Append colored text to a text edit widget.

        Args:
            text_edit: The QTextEdit to append to
            text: Text to append
            color: Color for the text
        """
        # Move cursor to end
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Create format with color
        format = QTextCharFormat()
        format.setForeground(color)

        # Insert text with format
        cursor.insertText(text, format)

        # Ensure cursor moves to end and text is visible
        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()

    def _switch_to_tab(self, tab_index: int) -> None:
        """
        Switch to a specific tab.

        Args:
            tab_index: Index of the tab to switch to
        """
        if 0 <= tab_index < self._tab_widget.count():
            self._tab_widget.setCurrentIndex(tab_index)

    def _on_tab_changed(self, index: int) -> None:
        """
        Handle tab change events.

        Args:
            index: New tab index
        """
        tab_names = ["Validation", "Execution", "Logs"]
        if 0 <= index < len(tab_names):
            self._logger.debug(f"Switched to {tab_names[index]} tab")

    # Public API methods for displaying content

    def display_validation_results(
        self, results: list[dict[str, Any]], auto_switch: bool = True
    ) -> None:
        """
        Display validation results in the validation tab.

        Args:
            results: List of validation result dictionaries with keys:
                    - level: "error", "warning", "info", or "success"
                    - message: The validation message
                    - file: Optional file path where issue occurred
                    - line: Optional line number
            auto_switch: Whether to automatically switch to validation tab
        """
        if auto_switch:
            self._switch_to_tab(self._validation_tab_index)

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._append_colored_text(
            self._validation_text,
            f"[{timestamp}] Validation Results:\n",
            self.INFO_COLOR,
        )

        for result in results:
            level = result.get("level", "info").lower()
            message = result.get("message", "Unknown validation result")
            file_path = result.get("file")
            line_num = result.get("line")

            # Determine color based on level
            if level == "error":
                color = self.ERROR_COLOR
                prefix = "❌ ERROR: "
            elif level == "warning":
                color = self.WARNING_COLOR
                prefix = "⚠️  WARNING: "
            elif level == "success":
                color = self.SUCCESS_COLOR
                prefix = "✅ SUCCESS: "
            else:
                color = self.INFO_COLOR
                prefix = "ℹ️  INFO: "

            # Format message with file/line if available
            full_message = f"{prefix}{message}"
            if file_path:
                file_name = Path(file_path).name
                if line_num:
                    full_message += f" (in {file_name}:{line_num})"
                else:
                    full_message += f" (in {file_name})"

            self._append_colored_text(self._validation_text, full_message + "\n", color)

        # Add separator
        self._append_colored_text(
            self._validation_text, "-" * 50 + "\n\n", self.DEBUG_COLOR
        )

        # Emit signal
        self.content_added.emit("validation")

    def display_execution_output(
        self, message: str, level: str = "info", auto_switch: bool = True
    ) -> None:
        """
        Display execution output in the execution tab.

        Args:
            message: The execution message to display
            level: Message level ("info", "warning", "error", "success")
            auto_switch: Whether to automatically switch to execution tab
        """
        if auto_switch:
            self._switch_to_tab(self._execution_tab_index)

        timestamp = datetime.now().strftime("%H:%M:%S")
        level = level.lower()

        # Determine color and prefix
        if level == "error":
            color = self.ERROR_COLOR
            prefix = "[ERROR] "
        elif level == "warning":
            color = self.WARNING_COLOR
            prefix = "[WARNING] "
        elif level == "success":
            color = self.SUCCESS_COLOR
            prefix = "[SUCCESS] "
        else:
            color = self.INFO_COLOR
            prefix = "[INFO] "

        full_message = f"[{timestamp}] {prefix}{message}\n"
        self._append_colored_text(self._execution_text, full_message, color)

        # Emit signal
        self.content_added.emit("execution")

    def display_log_message(
        self, message: str, level: int, logger_name: str = ""
    ) -> None:
        """
        Display a log message in the logs tab.

        Args:
            message: The log message
            level: Logging level (from logging module constants)
            logger_name: Name of the logger that generated the message
        """
        # Filter based on current log level
        if level < self._log_level_filter:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")

        # Determine color and level name
        if level >= logging.ERROR:
            color = self.ERROR_COLOR
            level_name = "ERROR"
        elif level >= logging.WARNING:
            color = self.WARNING_COLOR
            level_name = "WARNING"
        elif level >= logging.INFO:
            color = self.INFO_COLOR
            level_name = "INFO"
        else:
            color = self.DEBUG_COLOR
            level_name = "DEBUG"

        # Format message with timestamp and logger
        if logger_name:
            full_message = f"[{timestamp}] {level_name} {logger_name}: {message}\n"
        else:
            full_message = f"[{timestamp}] {level_name}: {message}\n"

        self._append_colored_text(self._logs_text, full_message, color)

        # Emit signal
        self.content_added.emit("logs")

    # Tab clearing methods

    def clear_validation(self) -> None:
        """Clear the validation tab content."""
        self._validation_text.clear()
        self._logger.debug("Validation tab cleared")

    def clear_execution(self) -> None:
        """Clear the execution tab content."""
        self._execution_text.clear()
        self._logger.debug("Execution tab cleared")

    def clear_logs(self) -> None:
        """Clear the logs tab content."""
        self._logs_text.clear()
        self._logger.debug("Logs tab cleared")

    def clear_all(self) -> None:
        """Clear all tab contents."""
        self.clear_validation()
        self.clear_execution()
        self.clear_logs()
        self._logger.debug("All console tabs cleared")

    # Utility methods

    def set_log_level_filter(self, level: int) -> None:
        """
        Set the minimum log level to display in the logs tab.

        Args:
            level: Logging level constant (DEBUG, INFO, WARNING, ERROR)
        """
        self._log_level_filter = level
        self._log_handler.setLevel(level)
        self._logger.debug(f"Log level filter set to {logging.getLevelName(level)}")

    def get_current_tab(self) -> str:
        """
        Get the name of the currently active tab.

        Returns:
            Tab name: "validation", "execution", or "logs"
        """
        current_index = self._tab_widget.currentIndex()
        tab_names = ["validation", "execution", "logs"]
        if 0 <= current_index < len(tab_names):
            return tab_names[current_index]
        return "unknown"

    def switch_to_validation_tab(self) -> None:
        """Switch to the validation tab."""
        self._switch_to_tab(self._validation_tab_index)

    def switch_to_execution_tab(self) -> None:
        """Switch to the execution tab."""
        self._switch_to_tab(self._execution_tab_index)

    def switch_to_logs_tab(self) -> None:
        """Switch to the logs tab."""
        self._switch_to_tab(self._logs_tab_index)

    def closeEvent(self, event) -> None:  # type: ignore
        """Handle close event to clean up logging handlers."""
        try:
            # Remove our handler from root logger
            if hasattr(self, "_log_handler"):
                root_logger = logging.getLogger()
                root_logger.removeHandler(self._log_handler)

            self._logger.debug("OutputConsole logging handlers cleaned up")
        except Exception as e:
            # Don't prevent closing due to cleanup errors
            self._logger.warning(f"Error cleaning up logging handlers: {e}")

        super().closeEvent(event)


class LogHandler(logging.Handler):
    """
    Custom logging handler that sends log messages to the OutputConsole.

    This handler captures log messages from the application and forwards them
    to the OutputConsole's logs tab for real-time monitoring.
    """

    def __init__(
        self, output_console: OutputConsole, prefix: str = "", use_batching: bool = True
    ) -> None:
        """
        Initialize the log handler.

        Args:
            output_console: The OutputConsole instance to send logs to
            prefix: Optional prefix to add to all log messages
            use_batching: Whether to use timer-based batching (True) or immediate display (False)
        """
        super().__init__()
        self._output_console = output_console
        self._prefix = prefix
        self._use_batching = use_batching

        # Initialize attributes based on batching mode
        self._message_queue: Optional[list[tuple]] = []
        self._timer: Optional[QTimer] = None

        if use_batching:
            # Use a timer to batch log messages and avoid UI freezing
            self._timer = QTimer()
            self._timer.timeout.connect(self._flush_messages)
            self._timer.setSingleShot(False)
            self._timer.setInterval(100)  # Flush every 100ms
        else:
            self._message_queue = None

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to the output console.

        Args:
            record: The log record to emit
        """
        try:
            message = self.format(record)
            if self._prefix:
                message = f"{self._prefix}{message}"

            if self._use_batching and self._message_queue is not None:
                # Add to queue for batched processing
                self._message_queue.append((message, record.levelno, record.name))

                # Start timer if not already running
                if self._timer is not None and not self._timer.isActive():
                    self._timer.start()
            else:
                # Display immediately
                self._output_console.display_log_message(
                    message, record.levelno, record.name
                )

        except Exception as e:
            # Don't let logging errors crash the application
            # We explicitly ignore logging errors to prevent recursion
            import sys

            print(f"LogHandler error: {e}", file=sys.stderr)

    def _flush_messages(self) -> None:
        """Flush queued messages to the output console."""
        if not self._use_batching or self._message_queue is None:
            return

        if not self._message_queue:
            if self._timer is not None:
                self._timer.stop()
            return

        # Process all queued messages
        messages_to_process = self._message_queue[:]
        self._message_queue.clear()

        for message, level, logger_name in messages_to_process:
            self._output_console.display_log_message(message, level, logger_name)

        # Stop timer if queue is empty
        if not self._message_queue and self._timer is not None:
            self._timer.stop()

    def flush_now(self) -> None:
        """Manually flush any queued messages immediately."""
        if self._use_batching:
            self._flush_messages()
