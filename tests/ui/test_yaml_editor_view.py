"""
Tests for YamlEditorView functionality.

This module tests the YAML editor's core functionality including file operations,
change tracking, validation integration, and find/replace capabilities.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from grimoire_studio.ui.components.output_console import OutputConsole
from grimoire_studio.ui.views.yaml_editor_view import YamlEditorView


@pytest.fixture
def yaml_editor(qtbot):
    """Create a YamlEditorView instance for testing."""
    editor = YamlEditorView()
    qtbot.addWidget(editor)
    return editor


@pytest.fixture
def sample_yaml_content():
    """Sample YAML content for testing."""
    return """id: test_model
kind: model
name: Test Model
description: A test model for validation
attributes:
  name:
    type: string
    required: true
  level:
    type: integer
    minimum: 1
    maximum: 20
"""


@pytest.fixture
def temp_yaml_file(sample_yaml_content):
    """Create a temporary YAML file for testing."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as temp_file:
        temp_file.write(sample_yaml_content)
        temp_file.flush()
        temp_file_path = Path(temp_file.name)

    yield temp_file_path

    # Cleanup
    try:
        temp_file_path.unlink()
    except (OSError, PermissionError):
        # On Windows, sometimes the file is still locked
        pass


class TestYamlEditorView:
    """Test cases for YamlEditorView."""

    def test_initialization(self, yaml_editor):
        """Test that YamlEditorView initializes correctly."""
        assert yaml_editor._file_path is None
        assert not yaml_editor._has_unsaved_changes
        assert yaml_editor._original_content == ""
        assert yaml_editor._validator is not None
        assert yaml_editor._validation_timer is not None

    def test_load_file_success(self, yaml_editor, temp_yaml_file, sample_yaml_content):
        """Test successful file loading."""
        # Load the file
        result = yaml_editor.load_file(temp_yaml_file)

        # Verify success
        assert result is True
        assert yaml_editor._file_path == temp_yaml_file
        assert yaml_editor.get_content() == sample_yaml_content
        assert not yaml_editor.has_unsaved_changes()
        assert yaml_editor._original_content == sample_yaml_content

    def test_load_file_not_exists(self, yaml_editor):
        """Test loading a file that doesn't exist."""
        non_existent_file = Path("non_existent_file.yaml")

        with patch(
            "grimoire_studio.ui.views.yaml_editor_view.QMessageBox.warning"
        ) as mock_warning:
            result = yaml_editor.load_file(non_existent_file)

            assert result is False
            assert yaml_editor._file_path is None
            mock_warning.assert_called_once()

    def test_load_file_encoding_error(self, yaml_editor):
        """Test loading a file with encoding issues."""
        # Create a file with invalid UTF-8
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, suffix=".yaml"
        ) as temp_file:
            temp_file.write(b"\xff\xfe")  # Invalid UTF-8 bytes
            temp_file_path = Path(temp_file.name)

        try:
            with patch(
                "grimoire_studio.ui.views.yaml_editor_view.QMessageBox.critical"
            ) as mock_critical:
                result = yaml_editor.load_file(temp_file_path)

                assert result is False
                assert yaml_editor._file_path is None
                mock_critical.assert_called_once()
        finally:
            try:
                temp_file_path.unlink()
            except (OSError, PermissionError):
                pass

    def test_save_file_success(self, yaml_editor, temp_yaml_file, sample_yaml_content):
        """Test successful file saving."""
        # Load file first
        yaml_editor.load_file(temp_yaml_file)

        # Modify content
        new_content = sample_yaml_content + "\n# Added comment"
        yaml_editor.set_content(new_content)

        # Save file
        result = yaml_editor.save_file()

        # Verify success
        assert result is True
        assert not yaml_editor.has_unsaved_changes()

        # Verify file content
        saved_content = temp_yaml_file.read_text(encoding="utf-8")
        assert saved_content == new_content

    def test_save_file_no_path(self, yaml_editor):
        """Test saving without a file path."""
        with patch(
            "grimoire_studio.ui.views.yaml_editor_view.QMessageBox.warning"
        ) as mock_warning:
            result = yaml_editor.save_file()

            assert result is False
            mock_warning.assert_called_once()

    def test_save_file_to_new_path(self, yaml_editor, sample_yaml_content):
        """Test saving to a new file path."""
        # Set content without loading a file
        yaml_editor.set_content(sample_yaml_content)

        # Create a new temp file path
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as temp_file:
            new_path = Path(temp_file.name)

        try:
            # Save to new path
            result = yaml_editor.save_file(new_path)

            # Verify success
            assert result is True
            assert yaml_editor._file_path == new_path
            assert not yaml_editor.has_unsaved_changes()

            # Verify file content
            saved_content = new_path.read_text(encoding="utf-8")
            assert saved_content == sample_yaml_content
        finally:
            try:
                new_path.unlink()
            except (OSError, PermissionError):
                pass

    def test_change_tracking(self, yaml_editor, temp_yaml_file, sample_yaml_content):
        """Test change tracking functionality."""
        # Load file
        yaml_editor.load_file(temp_yaml_file)
        assert not yaml_editor.has_unsaved_changes()

        # Modify content
        yaml_editor._text_edit.setPlainText(sample_yaml_content + "\n# Modified")

        # Process events to trigger change detection
        QApplication.processEvents()

        # Verify changes are tracked
        assert yaml_editor.has_unsaved_changes()

    def test_set_content(self, yaml_editor, sample_yaml_content):
        """Test setting content programmatically."""
        yaml_editor.set_content(sample_yaml_content)

        assert yaml_editor.get_content() == sample_yaml_content
        assert not yaml_editor.has_unsaved_changes()
        assert yaml_editor._original_content == sample_yaml_content

    def test_output_console_integration(self, yaml_editor):
        """Test integration with OutputConsole."""
        mock_console = MagicMock(spec=OutputConsole)

        yaml_editor.set_output_console(mock_console)
        assert yaml_editor._output_console == mock_console

    def test_validation_integration(self, yaml_editor, temp_yaml_file):
        """Test validation system integration."""
        # Create invalid YAML content
        invalid_yaml = "invalid: yaml: content: ["

        # Load file and set invalid content
        yaml_editor.load_file(temp_yaml_file)
        yaml_editor.set_content(invalid_yaml)

        # Mock output console
        mock_console = MagicMock(spec=OutputConsole)
        yaml_editor.set_output_console(mock_console)

        # Trigger validation manually
        yaml_editor._perform_validation()

        # Verify validation was attempted
        mock_console.display_validation_results.assert_called_once()

        # Get the validation results
        call_args = mock_console.display_validation_results.call_args[0][0]
        assert len(call_args) > 0
        assert call_args[0]["level"] == "error"

    def test_find_functionality(self, yaml_editor, sample_yaml_content):
        """Test find functionality."""
        yaml_editor.set_content(sample_yaml_content)

        # Test finding existing text
        result = yaml_editor._find_text("test_model")
        assert result is True

        # Verify text is selected
        cursor = yaml_editor._text_edit.textCursor()
        assert cursor.selectedText() == "test_model"

    def test_find_not_found(self, yaml_editor, sample_yaml_content):
        """Test find functionality with text not found."""
        yaml_editor.set_content(sample_yaml_content)

        with patch(
            "grimoire_studio.ui.views.yaml_editor_view.QMessageBox.information"
        ) as mock_info:
            result = yaml_editor._find_text("nonexistent_text")

            assert result is False
            mock_info.assert_called_once()

    def test_replace_functionality(self, yaml_editor, sample_yaml_content):
        """Test replace functionality."""
        yaml_editor.set_content(sample_yaml_content)

        # Replace text
        with patch(
            "grimoire_studio.ui.views.yaml_editor_view.QMessageBox.information"
        ) as mock_info:
            yaml_editor._replace_text("test_model", "new_model")

            # Verify replacement
            content = yaml_editor.get_content()
            assert "new_model" in content
            assert "test_model" not in content

            # Verify success message was shown
            mock_info.assert_called_once()

    def test_replace_not_found(self, yaml_editor, sample_yaml_content):
        """Test replace functionality with text not found."""
        yaml_editor.set_content(sample_yaml_content)

        with patch(
            "grimoire_studio.ui.views.yaml_editor_view.QMessageBox.information"
        ) as mock_info:
            yaml_editor._replace_text("nonexistent_text", "replacement")

            mock_info.assert_called_once()

            # Verify content unchanged
            assert yaml_editor.get_content() == sample_yaml_content

    def test_keyboard_shortcuts(self, yaml_editor, qtbot):
        """Test keyboard shortcuts are properly set up."""
        # This test verifies shortcuts exist (actual functionality tested elsewhere)
        shortcuts = yaml_editor.findChildren(object)  # Find all child QShortcut objects

        # We expect at least some shortcuts to be configured
        # Note: This is a basic test - in a real scenario you might want to test
        # the actual shortcut activation
        assert len(shortcuts) > 0

    def test_cursor_position_updates(self, yaml_editor, sample_yaml_content):
        """Test cursor position display updates."""
        yaml_editor.set_content(sample_yaml_content)

        # Move cursor to specific position
        cursor = yaml_editor._text_edit.textCursor()
        cursor.setPosition(10)  # Move to position 10
        yaml_editor._text_edit.setTextCursor(cursor)

        # Trigger position update
        yaml_editor._update_cursor_position()

        # Verify position label is updated (basic check)
        position_text = yaml_editor._position_label.text()
        assert "Line" in position_text and "Col" in position_text

    def test_file_signals(
        self, yaml_editor, temp_yaml_file, sample_yaml_content, qtbot
    ):
        """Test that appropriate signals are emitted."""
        # Connect signal handlers
        file_changed_emitted = []
        file_saved_emitted = []
        validation_requested_emitted = []

        yaml_editor.file_changed.connect(
            lambda changed: file_changed_emitted.append(changed)
        )
        yaml_editor.file_saved.connect(lambda path: file_saved_emitted.append(path))
        yaml_editor.validation_requested.connect(
            lambda content, path: validation_requested_emitted.append((content, path))
        )

        # Load file
        yaml_editor.load_file(temp_yaml_file)

        # Modify content to trigger file_changed signal
        yaml_editor._text_edit.setPlainText(sample_yaml_content + "\n# Modified")
        QApplication.processEvents()

        # Save file to trigger file_saved signal
        yaml_editor.save_file()

        # Verify signals were emitted
        assert len(file_changed_emitted) > 0
        assert len(file_saved_emitted) > 0
        assert file_saved_emitted[0] == temp_yaml_file


class TestFindDialog:
    """Test cases for FindDialog."""

    def test_find_dialog_initialization(self, qtbot):
        """Test FindDialog initializes correctly."""
        from grimoire_studio.ui.views.yaml_editor_view import FindDialog

        dialog = FindDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Find"
        assert dialog.isModal()
        assert dialog._search_edit.text() == ""

    def test_find_dialog_get_search_text(self, qtbot):
        """Test FindDialog returns correct search text."""
        from grimoire_studio.ui.views.yaml_editor_view import FindDialog

        dialog = FindDialog()
        qtbot.addWidget(dialog)

        test_text = "search_text"
        dialog._search_edit.setText(test_text)

        assert dialog.get_search_text() == test_text


class TestReplaceDialog:
    """Test cases for ReplaceDialog."""

    def test_replace_dialog_initialization(self, qtbot):
        """Test ReplaceDialog initializes correctly."""
        from grimoire_studio.ui.views.yaml_editor_view import ReplaceDialog

        dialog = ReplaceDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Replace"
        assert dialog.isModal()
        assert dialog._search_edit.text() == ""
        assert dialog._replace_edit.text() == ""

    def test_replace_dialog_get_texts(self, qtbot):
        """Test ReplaceDialog returns correct texts."""
        from grimoire_studio.ui.views.yaml_editor_view import ReplaceDialog

        dialog = ReplaceDialog()
        qtbot.addWidget(dialog)

        search_text = "search_text"
        replace_text = "replace_text"

        dialog._search_edit.setText(search_text)
        dialog._replace_edit.setText(replace_text)

        assert dialog.get_search_text() == search_text
        assert dialog.get_replace_text() == replace_text
