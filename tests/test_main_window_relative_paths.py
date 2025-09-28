"""Test the end-to-end relative path functionality in validation flow."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from PyQt6.QtWidgets import QApplication

from src.grimoire_studio.core.validator import ValidationResult, ValidationSeverity
from src.grimoire_studio.ui.main_window import MainWindow


class TestMainWindowRelativePaths:
    """Test relative path functionality in MainWindow validation flow."""

    @pytest.fixture
    def main_window(self, qtbot):
        """Create a MainWindow instance for testing."""
        # Ensure QApplication exists
        app = QApplication.instance()
        if app:
            app.setApplicationName("test-grimoire-studio")

        window = MainWindow()
        window.set_test_mode(True)  # Disable blocking dialogs
        qtbot.addWidget(window)
        return window

    @pytest.fixture
    def mock_project(self):
        """Create a mock project structure."""
        mock_project = Mock()
        mock_project.project_name = "test-project"

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            mock_project.project_path = project_path

            # Create test structure
            flows_dir = project_path / "flows"
            models_dir = project_path / "models"
            flows_dir.mkdir()
            models_dir.mkdir()

            # Create test files
            test_flow = flows_dir / "test_flow.yaml"
            test_model = models_dir / "character.yaml"
            test_flow.touch()
            test_model.touch()

            yield mock_project

    def test_get_relative_file_path_with_project(self, main_window, mock_project):
        """Test _get_relative_file_path method with a loaded project."""
        # Mock the project browser to return our mock project
        main_window._project_browser.get_current_project = Mock(
            return_value=mock_project
        )

        # Test file within project
        test_file = mock_project.project_path / "flows" / "test_flow.yaml"
        result = main_window._get_relative_file_path(test_file)
        assert result == "flows/test_flow.yaml"

        # Test nested file
        nested_file = mock_project.project_path / "models" / "character.yaml"
        result = main_window._get_relative_file_path(nested_file)
        assert result == "models/character.yaml"

    def test_get_relative_file_path_without_project(self, main_window):
        """Test _get_relative_file_path method without a loaded project."""
        # Mock no project loaded
        main_window._project_browser.get_current_project = Mock(return_value=None)

        test_file = Path("/some/absolute/path/file.yaml")
        result = main_window._get_relative_file_path(test_file)
        assert result == str(test_file)  # Should return absolute path

    def test_get_relative_file_path_outside_project(self, main_window, mock_project):
        """Test _get_relative_file_path method with file outside project."""
        # Mock the project browser to return our mock project
        main_window._project_browser.get_current_project = Mock(
            return_value=mock_project
        )

        # Test file outside project
        outside_file = Path("/completely/different/path/file.yaml")
        result = main_window._get_relative_file_path(outside_file)
        assert result == str(outside_file)  # Should return absolute path

    def test_validation_result_formatting_with_project(self, main_window, mock_project):
        """Test that validation result formatting produces relative paths."""
        # Mock the project browser to return our mock project
        main_window._project_browser.get_current_project = Mock(
            return_value=mock_project
        )

        # Create a validation result with file in project
        test_file = mock_project.project_path / "flows" / "test_flow.yaml"
        validation_result = ValidationResult(
            severity=ValidationSeverity.ERROR,
            message="Missing required field: 'kind'",
            file_path=test_file,
            line_number=5,
        )

        # Test the formatting logic that would be used in validation methods
        formatted_result = {
            "level": validation_result.severity.value,
            "message": validation_result.message,
            "file": main_window._get_relative_file_path(validation_result.file_path),
            "line": validation_result.line_number,
        }

        # Should have relative path
        assert formatted_result["file"] == "flows/test_flow.yaml"
        assert formatted_result["level"] == "error"
        assert formatted_result["message"] == "Missing required field: 'kind'"
        assert formatted_result["line"] == 5

    def test_validation_result_formatting_without_project(self, main_window):
        """Test that validation result formatting falls back to absolute paths."""
        # Mock no project loaded
        main_window._project_browser.get_current_project = Mock(return_value=None)

        # Create a validation result
        test_file = Path("/some/absolute/path/file.yaml")
        validation_result = ValidationResult(
            severity=ValidationSeverity.WARNING,
            message="Deprecated field detected",
            file_path=test_file,
            line_number=10,
        )

        # Test the formatting logic
        formatted_result = {
            "level": validation_result.severity.value,
            "message": validation_result.message,
            "file": main_window._get_relative_file_path(validation_result.file_path),
            "line": validation_result.line_number,
        }

        # Should have absolute path since no project is loaded
        assert formatted_result["file"] == str(test_file)
        assert formatted_result["level"] == "warning"
