"""
YAML Editor View for GRIMOIRE Design Studio.

This module provides the YamlEditorView class which implements a comprehensive
YAML editor with syntax highlighting, validation integration, change tracking,
and find/replace functionality.
"""

from pathlib import Path
from typing import Optional

from grimoire_logging import get_logger
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.validator import YamlValidator
from ..components.output_console import OutputConsole
from ..components.yaml_highlighter import YamlSyntaxHighlighter

logger = get_logger(__name__)


class YamlEditorView(QWidget):
    """
    A comprehensive YAML editor with validation integration.

    This editor provides:
    - Basic text editing with QPlainTextEdit
    - File loading and saving with proper encoding
    - Change tracking and unsaved changes indicator
    - Basic find/replace functionality
    - Real-time validation with error display
    - Keyboard shortcuts for common operations

    Signals:
        file_changed: Emitted when the file content is modified
        validation_requested: Emitted when validation should be performed
        file_saved: Emitted when the file is successfully saved
    """

    # Signals
    file_changed = pyqtSignal(bool)  # True if file has unsaved changes
    validation_requested = pyqtSignal(str, Path)  # content, file_path
    file_saved = pyqtSignal(Path)  # file_path

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the YAML editor view.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)

        # Internal state
        self._file_path: Optional[Path] = None
        self._has_unsaved_changes = False
        self._original_content = ""
        self._validator = YamlValidator()
        self._output_console: Optional[OutputConsole] = None

        # Validation timer for real-time validation
        self._validation_timer = QTimer()
        self._validation_timer.setSingleShot(True)
        self._validation_timer.timeout.connect(self._perform_validation)
        self._validation_timer.setInterval(1000)  # 1 second delay

        # Setup UI
        self._setup_ui()
        self._setup_shortcuts()

        logger.debug("YamlEditorView initialized")

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Text editor (create first)
        self._text_edit = QPlainTextEdit()
        self._text_edit.setFont(self._get_editor_font())
        self._text_edit.setTabStopDistance(20)  # 4-space tabs
        self._text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Set up syntax highlighting
        self._highlighter = YamlSyntaxHighlighter(self._text_edit.document())
        self._highlighter.set_font(self._get_editor_font())

        # Connect text change signal
        self._text_edit.textChanged.connect(self._on_text_changed)

        # Status bar for file info and unsaved changes indicator
        self._status_bar = self._create_status_bar()
        layout.addWidget(self._status_bar)

        layout.addWidget(self._text_edit)

        # Update status initially
        self._update_status()

    def _create_status_bar(self) -> QWidget:
        """Create the status bar widget."""
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(5, 2, 5, 2)

        # File path label
        self._file_label = QLabel("No file loaded")
        self._file_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self._file_label)

        status_layout.addStretch()

        # Unsaved changes indicator
        self._changes_label = QLabel("")
        self._changes_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        status_layout.addWidget(self._changes_label)

        # Line/column indicator
        self._position_label = QLabel("Line 1, Col 1")
        self._position_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self._position_label)

        # Connect cursor position change
        self._text_edit.cursorPositionChanged.connect(self._update_cursor_position)

        return status_widget

    def _get_editor_font(self) -> QFont:
        """Get a monospace font for the editor."""
        font = QFont("Consolas")
        if not font.exactMatch():
            font = QFont("Monaco")
            if not font.exactMatch():
                font = QFont("Courier New")

        font.setPointSize(12)  # Increased from 10 to 12 for better readability
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Save shortcut
        save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        save_shortcut.activated.connect(self.save_file)

        # Find shortcut
        find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        find_shortcut.activated.connect(self.show_find_dialog)

        # Replace shortcut
        replace_shortcut = QShortcut(QKeySequence.StandardKey.Replace, self)
        replace_shortcut.activated.connect(self.show_replace_dialog)

        logger.debug("Keyboard shortcuts configured")

    def _on_text_changed(self) -> None:
        """Handle text change events."""
        current_content = self._text_edit.toPlainText()
        has_changes = current_content != self._original_content

        if has_changes != self._has_unsaved_changes:
            self._has_unsaved_changes = has_changes
            self._update_status()
            self.file_changed.emit(has_changes)

        # Start validation timer
        if self._file_path:
            self._validation_timer.start()

    def _update_status(self) -> None:
        """Update the status bar information."""
        # Update file path
        if self._file_path:
            self._file_label.setText(str(self._file_path))
        else:
            self._file_label.setText("No file loaded")

        # Update unsaved changes indicator
        if self._has_unsaved_changes:
            self._changes_label.setText("● Unsaved changes")
        else:
            self._changes_label.setText("")

        # Update cursor position
        self._update_cursor_position()

    def _update_cursor_position(self) -> None:
        """Update the cursor position display."""
        cursor = self._text_edit.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self._position_label.setText(f"Line {line}, Col {col}")

    def _perform_validation(self) -> None:
        """Perform validation on the current content."""
        if not self._file_path:
            return

        content = self._text_edit.toPlainText()
        results = self._validator.validate_yaml_syntax(content, self._file_path)

        # Clear previous error highlighting
        self._highlighter.clear_error_highlights()

        # If we have an output console, display results
        if self._output_console:
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "level": result.severity.value,
                        "message": result.message,
                        "file": str(result.file_path) if result.file_path else None,
                        "line": result.line_number,
                    }
                )

            if formatted_results:
                self._output_console.display_validation_results(
                    formatted_results, auto_switch=False
                )

        # Highlight validation errors in the editor
        for result in results:
            if result.line_number is not None and result.line_number > 0:
                # Convert to 0-based line number for highlighter
                self._highlighter.highlight_error(result.line_number - 1)

        # Emit validation signal
        self.validation_requested.emit(content, self._file_path)

        logger.debug(f"Validation performed: {len(results)} issues found")

    # Public API methods

    def set_output_console(self, output_console: OutputConsole) -> None:
        """
        Set the output console for displaying validation results.

        Args:
            output_console: The OutputConsole instance to use
        """
        self._output_console = output_console
        logger.debug("Output console connected to YAML editor")

    def load_file(self, file_path: Path) -> bool:
        """
        Load a file into the editor.

        Args:
            file_path: Path to the file to load

        Returns:
            True if file was loaded successfully, False otherwise
        """
        try:
            if not file_path.exists():
                QMessageBox.warning(
                    self, "File Not Found", f"File does not exist: {file_path}"
                )
                return False

            # Read file content
            content = file_path.read_text(encoding="utf-8")

            # Set content in editor
            self._text_edit.setPlainText(content)

            # Update state
            self._file_path = file_path
            self._original_content = content
            self._has_unsaved_changes = False

            # Update UI
            self._update_status()

            # Perform initial validation
            self._perform_validation()

            logger.info(f"Loaded file: {file_path}")
            return True

        except UnicodeDecodeError as e:
            QMessageBox.critical(
                self,
                "File Encoding Error",
                f"Cannot read file due to encoding error: {e}",
            )
            return False

        except Exception as e:
            QMessageBox.critical(self, "File Load Error", f"Failed to load file: {e}")
            logger.error(f"Failed to load file {file_path}: {e}")
            return False

    def save_file(self, file_path: Optional[Path] = None) -> bool:
        """
        Save the current content to a file.

        Args:
            file_path: Optional path to save to (uses current file path if None)

        Returns:
            True if file was saved successfully, False otherwise
        """
        target_path = file_path or self._file_path

        if not target_path:
            QMessageBox.warning(
                self, "No File Path", "No file path specified for saving"
            )
            return False

        try:
            content = self._text_edit.toPlainText()

            # Write file with UTF-8 encoding
            target_path.write_text(content, encoding="utf-8")

            # Update state
            if not self._file_path:
                self._file_path = target_path

            self._original_content = content
            self._has_unsaved_changes = False

            # Update UI
            self._update_status()

            # Perform validation on saved content
            self._perform_validation()

            # Emit signal
            self.file_saved.emit(target_path)

            logger.info(f"Saved file: {target_path}")
            return True

        except Exception as e:
            QMessageBox.critical(self, "File Save Error", f"Failed to save file: {e}")
            logger.error(f"Failed to save file {target_path}: {e}")
            return False

    def get_content(self) -> str:
        """
        Get the current editor content.

        Returns:
            The current text content
        """
        return self._text_edit.toPlainText()

    def set_content(self, content: str) -> None:
        """
        Set the editor content.

        Args:
            content: The content to set
        """
        self._text_edit.setPlainText(content)
        self._original_content = content
        self._has_unsaved_changes = False
        self._update_status()

    def has_unsaved_changes(self) -> bool:
        """
        Check if the editor has unsaved changes.

        Returns:
            True if there are unsaved changes
        """
        return self._has_unsaved_changes

    def get_file_path(self) -> Optional[Path]:
        """
        Get the current file path.

        Returns:
            The current file path or None if no file is loaded
        """
        return self._file_path

    def set_color_scheme(self, scheme_name: str) -> None:
        """
        Set the syntax highlighting color scheme.

        Args:
            scheme_name: Name of the Pygments color scheme to use
        """
        self._highlighter.set_color_scheme(scheme_name)
        logger.debug(f"Color scheme set to: {scheme_name}")

    def set_font_size(self, size: int) -> None:
        """
        Set the editor font size.

        Args:
            size: Font size in points
        """
        current_font = self._text_edit.font()
        current_font.setPointSize(size)
        self._text_edit.setFont(current_font)
        self._highlighter.set_font(current_font)
        logger.debug(f"Editor font size set to: {size}pt")

    def show_find_dialog(self) -> None:
        """Show the find dialog."""
        dialog = FindDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            search_text = dialog.get_search_text()
            if search_text:
                self._find_text(search_text)

    def show_replace_dialog(self) -> None:
        """Show the find/replace dialog."""
        dialog = ReplaceDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            search_text = dialog.get_search_text()
            replace_text = dialog.get_replace_text()
            if search_text is not None:
                self._replace_text(search_text, replace_text)

    def _find_text(self, search_text: str) -> bool:
        """
        Find text in the editor.

        Args:
            search_text: Text to search for

        Returns:
            True if text was found
        """
        document = self._text_edit.document()
        if document is None:
            return False

        cursor = self._text_edit.textCursor()
        found_cursor = document.find(search_text, cursor)

        if not found_cursor.isNull():
            self._text_edit.setTextCursor(found_cursor)
            return True
        else:
            # Search from beginning
            found_cursor = document.find(search_text)
            if not found_cursor.isNull():
                self._text_edit.setTextCursor(found_cursor)
                return True

        QMessageBox.information(self, "Find", f"'{search_text}' not found")
        return False

    def _replace_text(self, search_text: str, replace_text: str) -> None:
        """
        Replace text in the editor.

        Args:
            search_text: Text to search for
            replace_text: Text to replace with
        """
        content = self._text_edit.toPlainText()
        new_content = content.replace(search_text, replace_text)

        if new_content != content:
            self._text_edit.setPlainText(new_content)
            count = content.count(search_text)
            QMessageBox.information(
                self, "Replace", f"Replaced {count} occurrence(s) of '{search_text}'"
            )
        else:
            QMessageBox.information(self, "Replace", f"'{search_text}' not found")


class FindDialog(QDialog):
    """Simple find dialog."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Find")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Search input
        layout.addWidget(QLabel("Find:"))
        self._search_edit = QLineEdit()
        layout.addWidget(self._search_edit)

        # Buttons
        button_layout = QHBoxLayout()

        find_btn = QPushButton("Find")
        find_btn.clicked.connect(self.accept)
        find_btn.setDefault(True)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(find_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        # Focus on search edit
        self._search_edit.setFocus()

    def get_search_text(self) -> str:
        """Get the search text."""
        return self._search_edit.text()


class ReplaceDialog(QDialog):
    """Simple find/replace dialog."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Replace")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Search input
        layout.addWidget(QLabel("Find:"))
        self._search_edit = QLineEdit()
        layout.addWidget(self._search_edit)

        # Replace input
        layout.addWidget(QLabel("Replace with:"))
        self._replace_edit = QLineEdit()
        layout.addWidget(self._replace_edit)

        # Buttons
        button_layout = QHBoxLayout()

        replace_btn = QPushButton("Replace All")
        replace_btn.clicked.connect(self.accept)
        replace_btn.setDefault(True)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(replace_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        # Focus on search edit
        self._search_edit.setFocus()

    def get_search_text(self) -> str:
        """Get the search text."""
        return self._search_edit.text()

    def get_replace_text(self) -> str:
        """Get the replace text."""
        return self._replace_edit.text()
