"""
Tests for the tabbed editor system in MainWindow.

This module tests the multi-file editing functionality including:
- Opening multiple files in tabs
- Tab management (close, switch)
- Unsaved changes handling
- Save All functionality
- Keyboard shortcuts
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox

from grimoire_studio.ui.main_window import MainWindow
from grimoire_studio.ui.views.yaml_editor_view import YamlEditorView


class TestTabbedEditor:
    """Test tabbed editor functionality."""

    @pytest.fixture
    def main_window(self, qtbot):
        """Create a MainWindow instance for testing."""
        # Set test application name to prevent blocking dialogs
        app = QApplication.instance()
        if app:
            app.setApplicationName("test-grimoire-studio")

        window = MainWindow()
        window.set_test_mode(True)  # Disable blocking dialogs
        qtbot.addWidget(window)
        return window

    @pytest.fixture
    def temp_yaml_file(self):
        """Create a temporary YAML file for testing."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write("""
# Test YAML file
test:
  name: "Test Object"
  value: 42
  items:
    - "item1"
    - "item2"
""")
            temp_file.flush()
            temp_file_path = Path(temp_file.name)

        yield temp_file_path

        # Cleanup
        try:
            temp_file_path.unlink()
        except (OSError, PermissionError):
            pass  # File might be locked on Windows

    @pytest.fixture
    def second_temp_yaml_file(self):
        """Create a second temporary YAML file for testing."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write("""
# Second test YAML file
second:
  description: "Another test object"
  enabled: true
""")
            temp_file.flush()
            temp_file_path = Path(temp_file.name)

        yield temp_file_path

        # Cleanup
        try:
            temp_file_path.unlink()
        except (OSError, PermissionError):
            pass

    def test_tab_widget_initialization(self, main_window):
        """Test that the tab widget is properly initialized."""
        # Should have a placeholder tab initially
        assert main_window._editor_tabs.count() == 1

        # Check that tab widget is properly configured
        assert main_window._editor_tabs.tabsClosable()
        assert main_window._editor_tabs.isMovable()
        assert main_window._editor_tabs.documentMode()

    def test_open_single_file(self, main_window, temp_yaml_file):
        """Test opening a single file in a tab."""
        # Open file
        main_window._open_file_in_editor(str(temp_yaml_file))

        # Should have one editor tab (placeholder removed)
        assert main_window._editor_tabs.count() == 1

        # Check that it's a YAML editor
        widget = main_window._editor_tabs.widget(0)
        assert isinstance(widget, YamlEditorView)

        # Check tab title
        assert main_window._editor_tabs.tabText(0) == temp_yaml_file.name

        # Check file is in open editors dict
        assert str(temp_yaml_file) in main_window._open_editors

    def test_open_multiple_files(
        self, main_window, temp_yaml_file, second_temp_yaml_file
    ):
        """Test opening multiple files in separate tabs."""
        # Open first file
        main_window._open_file_in_editor(str(temp_yaml_file))

        # Open second file
        main_window._open_file_in_editor(str(second_temp_yaml_file))

        # Should have two editor tabs
        assert main_window._editor_tabs.count() == 2

        # Check both are YAML editors
        for i in range(2):
            widget = main_window._editor_tabs.widget(i)
            assert isinstance(widget, YamlEditorView)

        # Check tab titles
        assert main_window._editor_tabs.tabText(0) == temp_yaml_file.name
        assert main_window._editor_tabs.tabText(1) == second_temp_yaml_file.name

        # Check both files are in open editors dict
        assert str(temp_yaml_file) in main_window._open_editors
        assert str(second_temp_yaml_file) in main_window._open_editors

    def test_open_same_file_twice(self, main_window, temp_yaml_file):
        """Test that opening the same file twice switches to existing tab."""
        # Open file first time
        main_window._open_file_in_editor(str(temp_yaml_file))
        initial_count = main_window._editor_tabs.count()
        initial_widget = main_window._editor_tabs.widget(0)

        # Open same file again
        main_window._open_file_in_editor(str(temp_yaml_file))

        # Should still have same number of tabs
        assert main_window._editor_tabs.count() == initial_count

        # Should be same widget (switched to existing tab)
        assert main_window._editor_tabs.widget(0) is initial_widget

    def test_close_tab(self, main_window, temp_yaml_file, second_temp_yaml_file):
        """Test closing a tab."""
        # Open two files
        main_window._open_file_in_editor(str(temp_yaml_file))
        main_window._open_file_in_editor(str(second_temp_yaml_file))

        # Close first tab
        main_window._close_tab(0)

        # Should have one tab left
        assert main_window._editor_tabs.count() == 1

        # Should be the second file
        assert main_window._editor_tabs.tabText(0) == second_temp_yaml_file.name

        # First file should be removed from open editors
        assert str(temp_yaml_file) not in main_window._open_editors
        assert str(second_temp_yaml_file) in main_window._open_editors

    def test_close_all_tabs(self, main_window, temp_yaml_file, second_temp_yaml_file):
        """Test closing all tabs."""
        # Open two files
        main_window._open_file_in_editor(str(temp_yaml_file))
        main_window._open_file_in_editor(str(second_temp_yaml_file))

        # Close all tabs
        main_window._close_all_tabs()

        # Should have placeholder tab
        assert main_window._editor_tabs.count() == 1

        # Should not be a YAML editor (placeholder)
        widget = main_window._editor_tabs.widget(0)
        assert not isinstance(widget, YamlEditorView)

        # Open editors dict should be empty
        assert len(main_window._open_editors) == 0

    def test_unsaved_changes_tab_title(self, main_window, temp_yaml_file):
        """Test that unsaved changes are reflected in tab title."""
        # Open file
        main_window._open_file_in_editor(str(temp_yaml_file))

        editor = main_window._editor_tabs.widget(0)
        assert isinstance(editor, YamlEditorView)

        # Initially no unsaved changes
        assert main_window._editor_tabs.tabText(0) == temp_yaml_file.name

        # Simulate text change
        editor._text_edit.setPlainText("modified content")
        editor._on_text_changed()

        # Tab title should show unsaved indicator
        assert main_window._editor_tabs.tabText(0) == f"{temp_yaml_file.name} *"

    def test_save_all_functionality(
        self, main_window, temp_yaml_file, second_temp_yaml_file
    ):
        """Test Save All functionality."""
        # Open two files
        main_window._open_file_in_editor(str(temp_yaml_file))
        main_window._open_file_in_editor(str(second_temp_yaml_file))

        # Modify both files
        editor1 = main_window._open_editors[str(temp_yaml_file)]
        editor2 = main_window._open_editors[str(second_temp_yaml_file)]

        editor1._text_edit.setPlainText("modified content 1")
        editor1._on_text_changed()

        editor2._text_edit.setPlainText("modified content 2")
        editor2._on_text_changed()

        # Both should have unsaved changes
        assert editor1.has_unsaved_changes()
        assert editor2.has_unsaved_changes()

        # Save all
        main_window._on_save_all()

        # Neither should have unsaved changes
        assert not editor1.has_unsaved_changes()
        assert not editor2.has_unsaved_changes()

        # Tab titles should not show unsaved indicator
        assert "*" not in main_window._editor_tabs.tabText(0)
        assert "*" not in main_window._editor_tabs.tabText(1)

    def test_tab_navigation(self, main_window, temp_yaml_file, second_temp_yaml_file):
        """Test tab navigation (next/previous)."""
        # Open two files
        main_window._open_file_in_editor(str(temp_yaml_file))
        main_window._open_file_in_editor(str(second_temp_yaml_file))

        # Should be on second tab (last opened)
        assert main_window._editor_tabs.currentIndex() == 1

        # Go to previous tab
        main_window._prev_tab()
        assert main_window._editor_tabs.currentIndex() == 0

        # Go to next tab
        main_window._next_tab()
        assert main_window._editor_tabs.currentIndex() == 1

    def test_file_type_detection(self, main_window):
        """Test file type detection for different file types."""
        # YAML files
        yaml_path = Path("test.yaml")
        assert main_window._detect_file_type(yaml_path) == "yaml"

        yml_path = Path("test.yml")
        assert main_window._detect_file_type(yml_path) == "yaml"

        # Text files
        txt_path = Path("test.txt")
        assert main_window._detect_file_type(txt_path) == "text"

        md_path = Path("test.md")
        assert main_window._detect_file_type(md_path) == "text"

        json_path = Path("test.json")
        assert main_window._detect_file_type(json_path) == "text"

        # Unsupported files
        bin_path = Path("test.exe")
        assert main_window._detect_file_type(bin_path) == "unsupported"

    def test_action_states(self, main_window, temp_yaml_file, second_temp_yaml_file):
        """Test that menu actions are enabled/disabled appropriately."""
        # Initially, file actions should be disabled
        assert not main_window._action_save.isEnabled()
        assert not main_window._action_save_all.isEnabled()
        assert not main_window._action_close_tab.isEnabled()

        # Open one file
        main_window._open_file_in_editor(str(temp_yaml_file))

        # File actions should be enabled, but not multi-tab actions
        assert main_window._action_save.isEnabled()
        assert main_window._action_close_tab.isEnabled()
        assert not main_window._action_next_tab.isEnabled()
        assert not main_window._action_prev_tab.isEnabled()

        # Open second file
        main_window._open_file_in_editor(str(second_temp_yaml_file))

        # Multi-tab actions should now be enabled
        assert main_window._action_next_tab.isEnabled()
        assert main_window._action_prev_tab.isEnabled()

    @patch("grimoire_studio.ui.main_window.QMessageBox.question")
    def test_unsaved_changes_close_confirmation(
        self, mock_question, main_window, temp_yaml_file
    ):
        """Test that closing tab with unsaved changes shows confirmation dialog."""
        # Disable test mode for this test to ensure dialog is shown
        main_window.set_test_mode(False)

        # Set up mock to return "Discard"
        mock_question.return_value = QMessageBox.StandardButton.Discard

        # Open file and modify it
        main_window._open_file_in_editor(str(temp_yaml_file))
        editor = main_window._editor_tabs.widget(0)

        editor._text_edit.setPlainText("modified content")
        editor._on_text_changed()

        # Close tab - should show confirmation dialog
        main_window._close_tab(0)

        # Dialog should have been shown
        mock_question.assert_called_once()

        # Tab should be closed
        assert main_window._editor_tabs.count() == 1  # Placeholder
        assert not isinstance(main_window._editor_tabs.widget(0), YamlEditorView)

    def test_keyboard_shortcuts(self, main_window, qtbot):
        """Test keyboard shortcuts for tab operations."""
        # Test that shortcuts are properly set up
        # Note: Close tab uses StandardKey.Close which is platform-dependent
        # Linux/Windows: Ctrl+W, macOS: Cmd+W (may show as Ctrl+F4 in some contexts)
        close_shortcut = main_window._action_close_tab.shortcut().toString()
        assert close_shortcut in ["Ctrl+W", "Ctrl+F4", "Meta+W"]  # Platform variations

        assert main_window._action_close_all.shortcut().toString() == "Ctrl+Shift+W"
        assert main_window._action_next_tab.shortcut().toString() == "Ctrl+Tab"
        assert main_window._action_prev_tab.shortcut().toString() == "Ctrl+Shift+Tab"

    def test_get_current_editor(self, main_window, temp_yaml_file):
        """Test getting the current active editor."""
        # Initially no current editor
        assert main_window._get_current_editor() is None

        # Open file
        main_window._open_file_in_editor(str(temp_yaml_file))

        # Should have current editor
        current = main_window._get_current_editor()
        assert isinstance(current, YamlEditorView)
        assert current.get_file_path() == temp_yaml_file

    def test_update_tab_title(self, main_window, temp_yaml_file):
        """Test updating tab titles."""
        # Open file
        main_window._open_file_in_editor(str(temp_yaml_file))
        editor = main_window._editor_tabs.widget(0)

        # Simulate unsaved changes
        editor._has_unsaved_changes = True

        # Update tab title
        main_window._update_tab_title(editor)

        # Should show unsaved indicator
        assert main_window._editor_tabs.tabText(0) == f"{temp_yaml_file.name} *"

        # Remove unsaved changes
        editor._has_unsaved_changes = False
        main_window._update_tab_title(editor)

        # Should not show unsaved indicator
        assert main_window._editor_tabs.tabText(0) == temp_yaml_file.name
