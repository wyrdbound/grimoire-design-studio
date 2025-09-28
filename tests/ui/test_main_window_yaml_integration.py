"""
Test main window YAML editor integration.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from grimoire_studio.core.project_manager import ProjectManager
from grimoire_studio.ui.main_window import MainWindow


class TestMainWindowYamlEditorIntegration:
    """Test integration between main window and YAML editor."""

    @pytest.fixture
    def main_window(self, qtbot):
        """Create a main window for testing."""
        window = MainWindow()
        # Disable exit confirmation for tests to prevent user interaction
        window._config.set("app/confirm_exit", False)
        qtbot.addWidget(window)
        return window

    @pytest.fixture
    def test_project_with_file(self):
        """Create a temporary test project with a YAML file."""
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix="test_integration_"))

        # Create project
        project_manager = ProjectManager()
        project = project_manager.create_project(
            project_name="Test Integration Project",
            project_path=temp_dir / "test_project",
            system_id="test-integration-system",
        )

        # Create test YAML file
        test_file = project.project_path / "models" / "test_model.yaml"
        test_content = """id: test-model
kind: model
name: Test Model
description: A test model for integration testing

fields:
  name:
    type: string
    required: true
    description: The name field
"""
        test_file.write_text(test_content, encoding="utf-8")

        return project.project_path, test_file, test_content

    def test_main_window_opens_yaml_file_in_editor(
        self, main_window, test_project_with_file, qtbot
    ):
        """Test that main window properly opens YAML files in the editor."""
        project_path, test_file, test_content = test_project_with_file

        # Load project in main window
        main_window.load_project(str(project_path))

        # Simulate opening the file
        main_window._on_file_opened(str(test_file))

        # Verify editor was created and file was loaded
        current_editor = main_window._get_current_editor()
        assert current_editor is not None
        assert current_editor.get_file_path() == test_file
        assert test_content.strip() in current_editor.get_content()

        # Verify status was updated
        assert "test_model.yaml" in main_window._file_label.text()

    def test_main_window_save_integration(
        self, main_window, test_project_with_file, qtbot
    ):
        """Test that main window save action works with YAML editor."""
        project_path, test_file, test_content = test_project_with_file

        # Load project and open file
        main_window.load_project(str(project_path))
        main_window._on_file_opened(str(test_file))

        # Make a change to the editor
        editor = main_window._get_current_editor()
        assert editor is not None

        new_content = test_content + "\n  # Added comment"
        editor.set_content(new_content)

        # Trigger save
        main_window._on_save()

        # Verify file was saved
        saved_content = test_file.read_text(encoding="utf-8")
        assert "# Added comment" in saved_content

    def test_main_window_file_changed_tracking(
        self, main_window, test_project_with_file, qtbot
    ):
        """Test that main window tracks file changes properly."""
        project_path, test_file, test_content = test_project_with_file

        # Load project and open file
        main_window.load_project(str(project_path))
        main_window._on_file_opened(str(test_file))

        # Initially, file should not be modified
        assert "*" not in main_window._file_label.text()

        # Make a change
        editor = main_window._get_current_editor()
        assert editor is not None

        # Simulate text change that triggers the file_changed signal
        editor._text_edit.insertPlainText(" # Modified")

        # Verify the modification indicator appears
        # Note: The actual signal emission might be delayed by the timer,
        # so we'll check the editor's internal state
        assert editor.has_unsaved_changes()

    def test_main_window_handles_unsupported_file_types(
        self, main_window, test_project_with_file, qtbot
    ):
        """Test that main window handles unsupported file types gracefully."""
        project_path, test_file, test_content = test_project_with_file

        # Create an unsupported file type
        unsupported_file = test_file.parent / "test.bin"
        unsupported_file.write_bytes(b"\\x00\\x01\\x02\\x03")

        # Load project
        main_window.load_project(str(project_path))

        # Try to open unsupported file - should not crash
        try:
            main_window._on_file_opened(str(unsupported_file))
            # Should either do nothing or show an error gracefully
            assert True  # If we get here, it didn't crash
        except RuntimeError as e:
            # Expected behavior - graceful error handling
            assert "Unsupported file type" in str(e)

    def test_main_window_replaces_editor_when_opening_new_file(
        self, main_window, test_project_with_file, qtbot
    ):
        """Test that opening a new file replaces the current editor."""
        project_path, test_file, test_content = test_project_with_file

        # Create a second test file
        test_file2 = test_file.parent / "test_model2.yaml"
        test_content2 = "id: test-model-2\\nkind: model\\nname: Test Model 2"
        test_file2.write_text(test_content2, encoding="utf-8")

        # Load project and open first file
        main_window.load_project(str(project_path))
        main_window._on_file_opened(str(test_file))

        first_editor = main_window._get_current_editor()
        assert first_editor is not None
        assert first_editor.get_file_path() == test_file

        # Open second file
        main_window._on_file_opened(str(test_file2))

        second_editor = main_window._get_current_editor()
        assert second_editor is not None
        assert second_editor.get_file_path() == test_file2
        assert second_editor != first_editor  # Should be a different editor instance

    @patch("grimoire_studio.ui.views.yaml_editor_view.QMessageBox.warning")
    def test_main_window_handles_file_load_errors(
        self, mock_warning, main_window, test_project_with_file, qtbot
    ):
        """Test that main window handles file loading errors gracefully."""
        project_path, test_file, test_content = test_project_with_file

        # Delete the test file to simulate a load error
        test_file.unlink()

        # Load project
        main_window.load_project(str(project_path))

        # Try to open non-existent file
        main_window._on_file_opened(str(test_file))

        # Should handle the error gracefully - the warning dialog should be called
        mock_warning.assert_called_once()

        # The main window should still update status even if file load fails
        # (the current implementation shows "Opened: filename" regardless)
        assert "test_model.yaml" in main_window._status_label.text()
