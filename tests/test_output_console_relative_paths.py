"""Test the relative path functionality in output console."""

import tempfile
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from src.grimoire_studio.ui.components.output_console import OutputConsole


class TestOutputConsoleRelativePaths:
    """Test relative path functionality in OutputConsole."""

    @pytest.fixture
    def output_console(self, qtbot):
        """Create an OutputConsole instance for testing."""
        # Ensure QApplication exists
        app = QApplication.instance()
        if app:
            app.setApplicationName("test-grimoire-studio")

        console = OutputConsole()
        qtbot.addWidget(console)
        return console

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create some subdirectories
            (project_root / "flows").mkdir()
            (project_root / "models").mkdir()
            (project_root / "models" / "characters").mkdir()

            # Create some test files
            (project_root / "flows" / "test_flow.yaml").touch()
            (project_root / "models" / "character.yaml").touch()
            (project_root / "models" / "characters" / "wizard.yaml").touch()

            yield project_root

    def test_relative_path_without_project_root(self, output_console):
        """Test relative path calculation when no project root is set."""
        test_path = "/some/absolute/path/to/file.yaml"
        result = output_console._get_relative_path(test_path)
        assert result == test_path  # Should return original path

    def test_relative_path_with_project_root(self, output_console, temp_project_dir):
        """Test relative path calculation with project root set."""
        # Set project root
        output_console.set_project_root(str(temp_project_dir))

        # Test file within project
        test_file = temp_project_dir / "flows" / "test_flow.yaml"
        result = output_console._get_relative_path(str(test_file))
        assert result == "flows/test_flow.yaml"

        # Test nested file
        nested_file = temp_project_dir / "models" / "characters" / "wizard.yaml"
        result = output_console._get_relative_path(str(nested_file))
        assert result == "models/characters/wizard.yaml"

    def test_relative_path_outside_project(self, output_console, temp_project_dir):
        """Test relative path calculation for files outside project root."""
        # Set project root
        output_console.set_project_root(str(temp_project_dir))

        # Test file outside project
        outside_file = "/completely/different/path/file.yaml"
        result = output_console._get_relative_path(outside_file)
        assert result == outside_file  # Should return original path

    def test_set_project_root_none(self, output_console, temp_project_dir):
        """Test clearing project root."""
        # First set a project root
        output_console.set_project_root(str(temp_project_dir))
        # Use resolve() to handle symlinks consistently
        assert output_console._project_root == temp_project_dir.resolve()

        # Then clear it
        output_console.set_project_root(None)
        assert output_console._project_root is None

    def test_validation_results_with_relative_paths(
        self, output_console, temp_project_dir
    ):
        """Test that validation results display relative paths correctly."""
        # Set project root
        output_console.set_project_root(str(temp_project_dir))

        # Create validation results with files in project
        test_file = temp_project_dir / "flows" / "test_flow.yaml"
        results = [
            {
                "level": "error",
                "message": "Missing required field: 'kind'",
                "file": str(test_file),
                "line": 5,
            }
        ]

        # Display results (this should not raise any errors)
        output_console.display_validation_results(results, auto_switch=False)

        # Get the validation text to check content
        validation_text = output_console._validation_text.toPlainText()

        # Should contain relative path, not absolute
        assert "flows/test_flow.yaml:5" in validation_text
        assert (
            str(temp_project_dir) not in validation_text
        )  # Absolute path should not appear
