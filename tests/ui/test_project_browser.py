"""
UI Tests for ProjectBrowser component.

This module tests the UI interactions and signal handling of the ProjectBrowser
component, including clicks, double-clicks, context menus, and signal emissions.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication

from grimoire_studio.ui.components.project_browser import ProjectBrowser


@pytest.mark.ui
class TestProjectBrowserUI:
    """Test ProjectBrowser UI interactions and signal handling."""

    @pytest.fixture
    def app(self, qtbot):
        """Create QApplication for UI tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()

    @pytest.fixture
    def project_browser(self, app, qtbot):
        """Create ProjectBrowser instance for UI testing."""
        browser = ProjectBrowser()
        qtbot.addWidget(browser)
        return browser

    @pytest.fixture
    def sample_project_with_files(self):
        """Create a sample project with various file types for UI testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "ui_test_project"
            project_path.mkdir()

            # Create system.yaml
            system_yaml = project_path / "system.yaml"
            system_yaml.write_text(
                """
kind: system
id: ui-test-system
name: UI Test System
version: "1.0.0"
            """.strip(),
                encoding="utf-8",
            )

            # Create models directory with files
            models_dir = project_path / "models"
            models_dir.mkdir()

            character_yaml = models_dir / "character.yaml"
            character_yaml.write_text(
                """
kind: model
id: character
name: Character Model
            """.strip(),
                encoding="utf-8",
            )

            item_yaml = models_dir / "item.yaml"
            item_yaml.write_text(
                """
kind: model
id: item
name: Item Model
            """.strip(),
                encoding="utf-8",
            )

            # Create flows directory
            flows_dir = project_path / "flows"
            flows_dir.mkdir()

            create_char_yaml = flows_dir / "create_character.yaml"
            create_char_yaml.write_text(
                """
kind: flow
id: create-character
name: Create Character Flow
            """.strip(),
                encoding="utf-8",
            )

            # Create other file types
            readme_md = project_path / "README.md"
            readme_md.write_text("# UI Test Project", encoding="utf-8")

            notes_txt = project_path / "notes.txt"
            notes_txt.write_text("Some notes", encoding="utf-8")

            config_json = project_path / "config.json"
            config_json.write_text('{"test": true}', encoding="utf-8")

            # Create a binary file (unsupported for editing)
            binary_file = project_path / "data.bin"
            binary_file.write_bytes(b"\x00\x01\x02\x03")

            yield project_path

    def test_ui_initialization_display(self, project_browser, qtbot):
        """Test that UI components are properly initialized and displayed."""
        # Show the widget so it becomes visible
        project_browser.show()
        qtbot.waitForWindowShown(project_browser)

        # Check that tree view is visible
        assert project_browser._tree_view.isVisible()

        # Check empty state display
        model = project_browser._tree_model
        assert model.rowCount() == 2  # "No project loaded" and instruction

        # Check that items are disabled (visual indication)
        root_item = model.invisibleRootItem()
        no_project_item = root_item.child(0)
        instruction_item = root_item.child(1)

        assert not no_project_item.isEnabled()
        assert not instruction_item.isEnabled()

    def test_project_loading_ui_update(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that UI updates correctly when a project is loaded."""
        project_path = str(sample_project_with_files)

        # Load project
        project_browser.load_project(project_path)

        # Check that tree is populated
        model = project_browser._tree_model
        assert model.rowCount() > 0

        # Check header is set
        assert model.horizontalHeaderItem(0).text() == "Project Files"

        # Check project item is displayed
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)
        assert project_item.text() == "ui_test_project"
        assert project_item.toolTip() == "Project: ui_test_project"

    def test_tree_expansion_after_loading(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that tree is expanded to appropriate depth after loading."""
        project_path = str(sample_project_with_files)

        # Load project
        project_browser.load_project(project_path)

        # Check that root items are expanded (depth 1)
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)
        project_index = model.indexFromItem(project_item)

        # The tree should be expanded to show the project contents
        assert project_browser._tree_view.isExpanded(project_index)

    def test_file_selection_signal(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that file selection emits the correct signal."""
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Create signal spy
        signal_spy = Mock()
        project_browser.file_selected.connect(signal_spy)

        # Find a file item in the tree
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)

        # Look for README.md file
        readme_item = None
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            if child.text() == "README.md":
                readme_item = child
                break

        assert readme_item is not None

        # Simulate click on file
        readme_index = model.indexFromItem(readme_item)
        project_browser._on_item_clicked(readme_index)

        # Check signal was emitted
        signal_spy.assert_called_once()
        called_path = signal_spy.call_args[0][0]
        assert called_path.endswith("README.md")

    def test_file_selection_signal_directory_no_emit(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that clicking on directories does not emit file_selected signal."""
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Create signal spy
        signal_spy = Mock()
        project_browser.file_selected.connect(signal_spy)

        # Find models directory in the tree
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)

        models_item = None
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            if child.text() == "models":
                models_item = child
                break

        assert models_item is not None

        # Simulate click on directory
        models_index = model.indexFromItem(models_item)
        project_browser._on_item_clicked(models_index)

        # Check signal was not emitted
        signal_spy.assert_not_called()

    def test_file_double_click_signal_yaml(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that double-clicking on supported files emits file_opened signal."""
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Create signal spy
        signal_spy = Mock()
        project_browser.file_opened.connect(signal_spy)

        # Find character.yaml file
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)

        # Navigate to models/character.yaml
        models_item = None
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            if child.text() == "models":
                models_item = child
                break

        assert models_item is not None

        character_item = None
        for i in range(models_item.rowCount()):
            child = models_item.child(i)
            if child.text() == "character.yaml":
                character_item = child
                break

        assert character_item is not None

        # Simulate double-click
        character_index = model.indexFromItem(character_item)
        project_browser._on_item_double_clicked(character_index)

        # Check signal was emitted
        signal_spy.assert_called_once()
        called_path = signal_spy.call_args[0][0]
        assert called_path.endswith("character.yaml")

    def test_file_double_click_signal_markdown(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that double-clicking on markdown files emits file_opened signal."""
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Create signal spy
        signal_spy = Mock()
        project_browser.file_opened.connect(signal_spy)

        # Find README.md file
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)

        readme_item = None
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            if child.text() == "README.md":
                readme_item = child
                break

        assert readme_item is not None

        # Simulate double-click
        readme_index = model.indexFromItem(readme_item)
        project_browser._on_item_double_clicked(readme_index)

        # Check signal was emitted
        signal_spy.assert_called_once()
        called_path = signal_spy.call_args[0][0]
        assert called_path.endswith("README.md")

    def test_file_double_click_unsupported_no_signal(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that double-clicking on unsupported files does not emit signal."""
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Create signal spy
        signal_spy = Mock()
        project_browser.file_opened.connect(signal_spy)

        # Find data.bin file (unsupported)
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)

        bin_item = None
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            if child.text() == "data.bin":
                bin_item = child
                break

        assert bin_item is not None

        # Simulate double-click
        bin_index = model.indexFromItem(bin_item)
        project_browser._on_item_double_clicked(bin_index)

        # Check signal was not emitted
        signal_spy.assert_not_called()

    def test_directory_double_click_no_signal(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that double-clicking on directories does not emit file_opened signal."""
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Create signal spy
        signal_spy = Mock()
        project_browser.file_opened.connect(signal_spy)

        # Find models directory
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)

        models_item = None
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            if child.text() == "models":
                models_item = child
                break

        assert models_item is not None

        # Simulate double-click on directory
        models_index = model.indexFromItem(models_item)
        project_browser._on_item_double_clicked(models_index)

        # Check signal was not emitted
        signal_spy.assert_not_called()

    def test_project_changed_signal_on_load(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that project_changed signal is emitted when project is loaded."""
        # Create signal spy
        signal_spy = Mock()
        project_browser.project_changed.connect(signal_spy)

        # Load project
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Check signal was emitted
        signal_spy.assert_called_once()

    def test_project_changed_signal_on_clear(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that project_changed signal is emitted when project is cleared."""
        # Load project first
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Create signal spy after loading
        signal_spy = Mock()
        project_browser.project_changed.connect(signal_spy)

        # Clear project
        project_browser.clear_project()

        # Check signal was emitted
        signal_spy.assert_called_once()

    def test_project_changed_signal_on_refresh(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that project_changed signal is emitted when project is refreshed."""
        # Load project first
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Create signal spy after loading
        signal_spy = Mock()
        project_browser.project_changed.connect(signal_spy)

        # Refresh project
        project_browser.refresh_project()

        # Check signal was emitted
        signal_spy.assert_called_once()

    def test_context_menu_file_actions_created(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that context menu actions are created correctly for files."""
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Test the placeholder methods directly (they exist but don't do much yet)
        project_browser._delete_file("test_file.yaml")
        project_browser._create_new_file("/test/directory")

        # These should not raise exceptions and should log the requests
        # The actual functionality will be implemented in future steps

    def test_context_menu_directory_actions_created(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that context menu actions are created correctly for directories."""
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Test the placeholder methods directly
        project_browser._delete_directory("/test/directory")
        project_browser._create_new_file("/test/directory")

        # These should not raise exceptions and should log the requests
        # The actual functionality will be implemented in future steps

    def test_context_menu_invalid_position(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test context menu handling with invalid position."""
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Test with invalid position (no item at position)
        invalid_position = QPoint(-1, -1)

        # This should not crash and should handle gracefully
        project_browser._on_context_menu_requested(invalid_position)

    def test_file_tooltips_display_correctly(
        self, project_browser, sample_project_with_files, qtbot
    ):
        """Test that file tooltips show correct file type information."""
        project_path = str(sample_project_with_files)
        project_browser.load_project(project_path)

        # Find various file types and check tooltips
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        project_item = root_item.child(0)

        # Check system.yaml tooltip
        system_item = None
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            if child.text() == "system.yaml":
                system_item = child
                break

        assert system_item is not None
        assert "System Definition" in system_item.toolTip()

        # Check README.md tooltip
        readme_item = None
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            if child.text() == "README.md":
                readme_item = child
                break

        assert readme_item is not None
        assert "Markdown File" in readme_item.toolTip()

        # Check models directory tooltip
        models_item = None
        for i in range(project_item.rowCount()):
            child = project_item.child(i)
            if child.text() == "models":
                models_item = child
                break

        assert models_item is not None
        assert "Directory" in models_item.toolTip()

    def test_tree_selection_mode_single(self, project_browser, qtbot):
        """Test that tree view is configured for single selection mode."""
        tree_view = project_browser._tree_view
        from PyQt6.QtWidgets import QAbstractItemView

        assert (
            tree_view.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection
        )

    def test_tree_view_visual_properties(self, project_browser, qtbot):
        """Test tree view visual properties are set correctly."""
        tree_view = project_browser._tree_view

        # Check visual properties
        assert tree_view.isHeaderHidden()  # Header should be hidden
        assert tree_view.alternatingRowColors()  # Alternating colors enabled
        assert tree_view.rootIsDecorated()  # Show expand/collapse indicators

        # Check context menu policy
        assert tree_view.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu

    def test_error_state_display(self, project_browser, qtbot):
        """Test error state display in the UI."""
        error_message = "Test error for UI display"
        project_browser._show_error_state(error_message)

        # Check error is displayed
        model = project_browser._tree_model
        root_item = model.invisibleRootItem()
        error_item = root_item.child(0)

        assert f"Error: {error_message}" in error_item.text()
        assert not error_item.isEnabled()  # Should be visually disabled
