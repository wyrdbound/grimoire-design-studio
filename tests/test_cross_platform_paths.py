"""Test cross-platform path handling compatibility."""

import sys
import tempfile
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_studio.ui.components.output_console import OutputConsole
from grimoire_studio.ui.main_window import MainWindow


class TestCrossPlatformPaths:
    """Test cases for cross-platform path handling."""

    @pytest.fixture
    def output_console(self, qtbot):
        """Create an OutputConsole instance for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        console = OutputConsole()
        qtbot.addWidget(console)
        return console

    @pytest.fixture
    def main_window(self, qtbot):
        """Create a MainWindow instance for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        window = MainWindow()
        qtbot.addWidget(window)
        return window

    def test_output_console_always_uses_forward_slashes(self, output_console):
        """Test that OutputConsole always returns forward slashes regardless of OS."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            subdir = project_root / "flows"
            subdir.mkdir()
            test_file = subdir / "test_flow.yaml"
            test_file.write_text("test content", encoding="utf-8")

            # Set project root
            output_console.set_project_root(project_root)

            # Test relative path conversion
            relative_path = output_console._get_relative_path(str(test_file))

            # Should always use forward slashes regardless of platform
            assert "/" in relative_path or "\\" not in relative_path
            assert (
                relative_path == "flows/test_flow.yaml"
            )  # Explicit forward slash check

    def test_main_window_always_uses_forward_slashes(self, main_window):
        """Test that MainWindow always returns forward slashes regardless of OS."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            subdir = project_root / "flows"
            subdir.mkdir()
            test_file = subdir / "test_flow.yaml"
            test_file.write_text("test content", encoding="utf-8")

            # Create a mock project for the main window
            class MockProject:
                def __init__(self, path):
                    self.project_path = Path(path)

            # Mock the project browser to return our test project
            mock_project = MockProject(project_root)
            main_window._project_browser.get_current_project = lambda: mock_project

            # Test relative path conversion
            relative_path = main_window._get_relative_file_path(test_file)

            # Should always use forward slashes regardless of platform
            assert "/" in relative_path or "\\" not in relative_path
            assert (
                relative_path == "flows/test_flow.yaml"
            )  # Explicit forward slash check

    def test_nested_paths_use_forward_slashes(self, output_console):
        """Test that deeply nested paths always use forward slashes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create nested directory structure
            nested_dir = project_root / "compendiums" / "items" / "weapons"
            nested_dir.mkdir(parents=True)
            test_file = nested_dir / "swords.yaml"
            test_file.write_text("test content", encoding="utf-8")

            output_console.set_project_root(project_root)
            relative_path = output_console._get_relative_path(str(test_file))

            # Should use forward slashes throughout the path
            expected = "compendiums/items/weapons/swords.yaml"
            assert relative_path == expected
            assert "\\" not in relative_path  # No backslashes should appear

    def test_path_with_spaces_uses_forward_slashes(self, output_console):
        """Test that paths with spaces still use forward slashes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create directory with spaces
            spaced_dir = project_root / "my flows" / "character creation"
            spaced_dir.mkdir(parents=True)
            test_file = spaced_dir / "test flow.yaml"
            test_file.write_text("test content", encoding="utf-8")

            output_console.set_project_root(project_root)
            relative_path = output_console._get_relative_path(str(test_file))

            # Should use forward slashes even with spaces
            expected = "my flows/character creation/test flow.yaml"
            assert relative_path == expected
            assert "\\" not in relative_path  # No backslashes should appear

    def test_windows_style_paths_converted_to_posix(self, output_console):
        """Test that Windows-style input paths are converted to POSIX style."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            subdir = project_root / "models"
            subdir.mkdir()
            test_file = subdir / "character.yaml"
            test_file.write_text("test content", encoding="utf-8")

            output_console.set_project_root(project_root)

            # Test with both forward and backward slashes in input
            # (pathlib normalizes these internally)
            relative_path = output_console._get_relative_path(str(test_file))

            # Output should always use forward slashes
            assert relative_path == "models/character.yaml"
            assert "\\" not in relative_path
