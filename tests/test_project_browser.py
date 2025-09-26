"""
Tests for ProjectBrowser component business logic.

This module tests the core functionality of the ProjectBrowser component,
including project loading, file type detection, and tree structure building.
"""

import tempfile
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from grimoire_studio.ui.components.project_browser import ProjectBrowser


class TestProjectBrowserBusinessLogic:
    """Test ProjectBrowser business logic without UI interaction."""

    @pytest.fixture
    def app(self, qtbot):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()

    @pytest.fixture
    def project_browser(self, app, qtbot):
        """Create ProjectBrowser instance for testing."""
        browser = ProjectBrowser()
        qtbot.addWidget(browser)
        return browser

    @pytest.fixture
    def sample_project_structure(self):
        """Create a temporary GRIMOIRE project structure for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Create system.yaml
            system_yaml = project_path / "system.yaml"
            system_yaml.write_text(
                """
kind: system
id: test-system
name: Test System
version: "1.0.0"
            """.strip(),
                encoding="utf-8",
            )

            # Create directory structure
            (project_path / "models").mkdir()
            (project_path / "flows").mkdir()
            (project_path / "compendiums").mkdir()
            (project_path / "tables").mkdir()
            (project_path / "sources").mkdir()
            (project_path / "prompts").mkdir()

            # Create sample files
            model_file = project_path / "models" / "character.yaml"
            model_file.write_text(
                """
kind: model
id: character
name: Character
            """.strip(),
                encoding="utf-8",
            )

            flow_file = project_path / "flows" / "create_character.yaml"
            flow_file.write_text(
                """
kind: flow
id: create-character
name: Create Character
            """.strip(),
                encoding="utf-8",
            )

            readme_file = project_path / "README.md"
            readme_file.write_text(
                "# Test Project\n\nA test GRIMOIRE project.", encoding="utf-8"
            )

            # Create subdirectories with files
            subdir = project_path / "models" / "subdir"
            subdir.mkdir()
            sub_model = subdir / "item.yaml"
            sub_model.write_text(
                """
kind: model
id: item
name: Item
            """.strip(),
                encoding="utf-8",
            )

            yield project_path

    def test_initialization(self, project_browser):
        """Test ProjectBrowser initialization."""
        assert project_browser._current_project is None
        assert project_browser._tree_view is not None
        assert project_browser._tree_model is not None

        # Check empty state is displayed
        model = project_browser._tree_model
        assert model.rowCount() == 2  # "No project loaded" and instruction

        root_item = model.invisibleRootItem()
        assert root_item.child(0).text() == "No project loaded"
        assert "Use File >" in root_item.child(1).text()

    def test_get_file_type_system_yaml(self, project_browser):
        """Test file type detection for system.yaml."""
        test_path = Path("/test/system.yaml")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "System Definition"

    def test_get_file_type_model_yaml(self, project_browser):
        """Test file type detection for model YAML files."""
        test_path = Path("/test/models/character.yaml")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "Model Definition"

    def test_get_file_type_flow_yaml(self, project_browser):
        """Test file type detection for flow YAML files."""
        test_path = Path("/test/flows/create_character.yaml")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "Flow Definition"

    def test_get_file_type_compendium_yaml(self, project_browser):
        """Test file type detection for compendium YAML files."""
        test_path = Path("/test/compendiums/spells.yaml")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "Compendium"

    def test_get_file_type_table_yaml(self, project_browser):
        """Test file type detection for table YAML files."""
        test_path = Path("/test/tables/random_encounters.yaml")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "Table Definition"

    def test_get_file_type_source_yaml(self, project_browser):
        """Test file type detection for source YAML files."""
        test_path = Path("/test/sources/equipment.yaml")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "Source Definition"

    def test_get_file_type_prompt_yaml(self, project_browser):
        """Test file type detection for prompt YAML files."""
        test_path = Path("/test/prompts/character_creation.yaml")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "Prompt Definition"

    def test_get_file_type_markdown(self, project_browser):
        """Test file type detection for Markdown files."""
        test_path = Path("/test/README.md")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "Markdown File"

    def test_get_file_type_text(self, project_browser):
        """Test file type detection for text files."""
        test_path = Path("/test/notes.txt")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "Text File"

    def test_get_file_type_json(self, project_browser):
        """Test file type detection for JSON files."""
        test_path = Path("/test/config.json")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "JSON File"

    def test_get_file_type_generic_yaml(self, project_browser):
        """Test file type detection for generic YAML files."""
        test_path = Path("/test/config.yaml")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "YAML File"

    def test_get_file_type_unknown(self, project_browser):
        """Test file type detection for unknown file types."""
        test_path = Path("/test/binary.exe")
        file_type = project_browser._get_file_type(test_path)
        assert file_type == "File"

    def test_load_project_success(self, project_browser, sample_project_structure):
        """Test successful project loading."""
        project_path = str(sample_project_structure)

        # Load project
        project_browser.load_project(project_path)

        # Verify project is loaded
        assert project_browser._current_project is not None
        assert project_browser._current_project.project_name == "Test System"

        # Verify tree is populated
        model = project_browser._tree_model
        assert model.rowCount() > 0

        # Check project root item
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)
        assert project_item.text() == "Test System"
        assert project_item.data(Qt.ItemDataRole.UserRole) == project_path

    def test_load_project_nonexistent_path(self, project_browser):
        """Test loading project with nonexistent path."""
        nonexistent_path = "/path/that/does/not/exist"

        with pytest.raises(RuntimeError, match="Project path does not exist"):
            project_browser.load_project(nonexistent_path)

        # Verify project browser shows error state
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        error_item = root_item.child(0)
        assert "Error:" in error_item.text()

    def test_load_project_missing_system_yaml(self, project_browser):
        """Test loading project without system.yaml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "invalid_project"
            project_path.mkdir()

            # Don't create system.yaml
            readme = project_path / "README.md"
            readme.write_text("# Invalid Project", encoding="utf-8")

            with pytest.raises(RuntimeError, match="Invalid GRIMOIRE project"):
                project_browser.load_project(str(project_path))

    def test_clear_project(self, project_browser, sample_project_structure):
        """Test clearing the current project."""
        # First load a project
        project_browser.load_project(str(sample_project_structure))
        assert project_browser._current_project is not None

        # Clear the project
        project_browser.clear_project()

        # Verify project is cleared
        assert project_browser._current_project is None

        # Verify empty state is shown
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        assert root_item.child(0).text() == "No project loaded"

    def test_refresh_project(self, project_browser, sample_project_structure):
        """Test refreshing the project display."""
        # Load project
        project_browser.load_project(str(sample_project_structure))

        # Get initial tree state
        initial_count = project_browser._tree_model.rowCount()

        # Refresh project
        project_browser.refresh_project()

        # Verify tree is refreshed (should have same structure)
        assert project_browser._tree_model.rowCount() == initial_count
        assert project_browser._current_project is not None

    def test_get_current_project(self, project_browser, sample_project_structure):
        """Test getting the current project."""
        # Initially no project
        assert project_browser.get_current_project() is None

        # Load project
        project_browser.load_project(str(sample_project_structure))

        # Get current project
        current = project_browser.get_current_project()
        assert current is not None
        assert current.project_name == "Test System"

    def test_show_error_state(self, project_browser):
        """Test displaying error state."""
        error_message = "Test error message"
        project_browser._show_error_state(error_message)

        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        error_item = root_item.child(0)

        assert f"Error: {error_message}" in error_item.text()
        assert not error_item.isEnabled()

    def test_add_directory_to_tree_with_files(
        self, project_browser, sample_project_structure
    ):
        """Test adding directory contents to tree including files and subdirectories."""
        # Load project first
        project_browser.load_project(str(sample_project_structure))

        # Find the models directory in the tree
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)

        # Look for models directory
        models_item = None
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            if child.text() == "models":
                models_item = child
                break

        assert models_item is not None

        # Check that files and subdirectories are added
        assert models_item.rowCount() >= 2  # character.yaml and subdir

        # Verify file types are detected
        character_item = None
        subdir_item = None

        for i in range(models_item.rowCount()):
            child = models_item.child(i)
            if child.text() == "character.yaml":
                character_item = child
            elif child.text() == "subdir":
                subdir_item = child

        assert character_item is not None
        assert "Model Definition" in character_item.toolTip()

        assert subdir_item is not None
        assert "Directory" in subdir_item.toolTip()

    def test_tree_item_sorting(self, project_browser, sample_project_structure):
        """Test that tree items are sorted correctly (directories first, then alphabetical)."""
        # Load project
        project_browser.load_project(str(sample_project_structure))

        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)

        # Collect directory and file names
        directories = []
        files = []

        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            file_path = child.data(Qt.ItemDataRole.UserRole)
            if file_path and Path(file_path).is_dir():
                directories.append(child.text())
            elif file_path and Path(file_path).is_file():
                files.append(child.text())

        # Directories should come before files
        # (We check this by ensuring we see directories in the first part)
        assert len(directories) > 0
        assert len(files) > 0

        # Find first file index
        first_file_index = -1
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            file_path = child.data(Qt.ItemDataRole.UserRole)
            if file_path and Path(file_path).is_file():
                first_file_index = i
                break

        # All directories should come before the first file
        if first_file_index != -1:
            for i in range(first_file_index):
                child = project_item.child(i)
                file_path = child.data(Qt.ItemDataRole.UserRole)
                if file_path:
                    assert Path(file_path).is_dir()

    def test_hidden_files_skipped(self, project_browser):
        """Test that hidden files and __pycache__ directories are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Create system.yaml
            system_yaml = project_path / "system.yaml"
            system_yaml.write_text(
                "kind: system\nid: test\nname: Test", encoding="utf-8"
            )

            # Create hidden files and __pycache__
            hidden_file = project_path / ".hidden_file"
            hidden_file.write_text("hidden", encoding="utf-8")

            pycache_dir = project_path / "__pycache__"
            pycache_dir.mkdir()

            normal_file = project_path / "normal.txt"
            normal_file.write_text("normal", encoding="utf-8")

            # Load project
            project_browser.load_project(str(project_path))

            # Check that hidden files are not in tree
            model = project_browser._tree_model
            root_item = model.invisibleRootItem()
            project_item = root_item.child(0)

            item_names = []
            for i in range(project_item.rowCount()):
                child = project_item.child(i)
                item_names.append(child.text())

            assert ".hidden_file" not in item_names
            assert "__pycache__" not in item_names
            assert "normal.txt" in item_names
            assert "system.yaml" in item_names
