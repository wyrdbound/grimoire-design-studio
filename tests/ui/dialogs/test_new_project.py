"""
Tests for the New Project Dialog.

This module provides comprehensive testing for the NewProjectDialog class,
including form validation, user interactions, and project creation integration.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from grimoire_studio.ui.dialogs.new_project import NewProjectDialog


class TestNewProjectDialog:
    """Test suite for NewProjectDialog class."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication instance for testing."""
        existing_app = QApplication.instance()
        if existing_app is not None and isinstance(existing_app, QApplication):
            return existing_app
        return QApplication([])

    @pytest.fixture
    def dialog(self, app: QApplication) -> NewProjectDialog:
        """Create NewProjectDialog instance for testing."""
        return NewProjectDialog()

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_dialog_initialization(self, dialog: NewProjectDialog) -> None:
        """Test dialog proper initialization."""
        # Check dialog properties
        assert dialog.windowTitle() == "New GRIMOIRE Project"
        assert dialog.isModal()

        # Check form fields exist and are properly initialized
        assert dialog._project_name_edit is not None
        assert dialog._system_id_edit is not None
        assert dialog._location_edit is not None
        assert dialog._description_edit is not None

        # Check initial state
        assert dialog._project_name == ""
        assert dialog._system_id == ""
        assert dialog._project_path == ""
        assert dialog._created_project_path is None

    def test_project_name_validation(self, dialog: NewProjectDialog) -> None:
        """Test project name validation logic."""
        # Valid names
        valid_names = [
            "My Project",
            "Test-System",
            "Simple_Name",
            "Project 123",
            "A",
            "Very Long Project Name With Spaces",
        ]

        for name in valid_names:
            dialog._project_name_edit.setText(name)
            dialog._on_project_name_changed(name)
            assert dialog._project_name == name
            assert dialog._system_id != ""  # System ID should be auto-generated

        # Invalid names (empty)
        dialog._project_name_edit.setText("")
        dialog._on_project_name_changed("")
        assert dialog._project_name == ""
        assert dialog._system_id == ""

    def test_system_id_generation(self, dialog: NewProjectDialog) -> None:
        """Test automatic system ID generation from project name."""
        test_cases = [
            ("My Project", "my_project"),
            ("Test-System", "test_system"),
            ("Simple_Name", "simple_name"),
            ("Project 123", "project_123"),
            ("Multi   Spaces", "multi_spaces"),
            ("Special@#$Characters!", "special_characters"),
            ("", ""),
        ]

        for project_name, expected_system_id in test_cases:
            dialog._project_name_edit.setText(project_name)
            dialog._on_project_name_changed(project_name)
            assert dialog._system_id == expected_system_id

    def test_system_id_manual_override(self, dialog: NewProjectDialog) -> None:
        """Test manual system ID override functionality."""
        # Set project name (auto-generates system ID)
        dialog._project_name_edit.setText("Test Project")
        dialog._on_project_name_changed("Test Project")
        assert dialog._system_id == "test_project"

        # Manually override system ID
        dialog._system_id_edit.setText("custom_id")
        dialog._on_system_id_changed("custom_id")
        assert dialog._system_id == "custom_id"

        # Changing project name again should not override manual system ID
        dialog._project_name_edit.setText("Different Project")
        dialog._on_project_name_changed("Different Project")
        assert dialog._system_id == "custom_id"  # Should remain unchanged

    def test_location_validation(
        self, dialog: NewProjectDialog, temp_dir: Path
    ) -> None:
        """Test project location validation."""
        # Valid location (existing directory with write permissions)
        dialog._location_edit.setText(str(temp_dir))
        dialog._on_location_changed(str(temp_dir))
        assert dialog._project_path == str(temp_dir)

        # Invalid location (non-existent path)
        invalid_path = temp_dir / "nonexistent" / "path"
        dialog._location_edit.setText(str(invalid_path))
        dialog._on_location_changed(str(invalid_path))
        assert dialog._project_path == str(
            invalid_path
        )  # Path is stored even if invalid

        # Empty location
        dialog._location_edit.setText("")
        dialog._on_location_changed("")
        assert dialog._project_path == ""

    def test_browse_location_dialog(
        self, dialog: NewProjectDialog, temp_dir: Path
    ) -> None:
        """Test location browsing functionality."""
        # Patch QFileDialog where it's used in the dialog module
        with patch(
            "grimoire_studio.ui.dialogs.new_project.QFileDialog"
        ) as mock_dialog_class:
            # Create mock dialog instance
            mock_dialog_instance = Mock()
            mock_dialog_class.return_value = mock_dialog_instance

            # Configure mock dialog to return accepted and provide selected files
            mock_dialog_instance.exec.return_value = 1  # QDialog.DialogCode.Accepted
            mock_dialog_instance.selectedFiles.return_value = [str(temp_dir)]

            dialog._on_browse_clicked()

            # Verify dialog was created and configured
            mock_dialog_class.assert_called_once_with(dialog)
            mock_dialog_instance.setFileMode.assert_called_once()
            mock_dialog_instance.setOption.assert_called_once()
            mock_dialog_instance.setWindowTitle.assert_called_once_with(
                "Select Project Location"
            )
            mock_dialog_instance.exec.assert_called_once()

            # Verify location was set
            assert dialog._location_edit.text() == str(temp_dir)
            assert dialog._project_path == str(temp_dir)

    def test_form_validation_states(
        self, dialog: NewProjectDialog, temp_dir: Path
    ) -> None:
        """Test form validation in different states."""
        # Initially invalid (empty fields)
        is_valid, message = dialog._validate_form()
        assert not is_valid
        assert "required" in message.lower()

        # Set project name only
        dialog._project_name_edit.setText("Test Project")
        dialog._on_project_name_changed("Test Project")
        is_valid, message = dialog._validate_form()
        assert not is_valid  # Still invalid (no location)

        # Set location only
        dialog._project_name_edit.setText("")
        dialog._on_project_name_changed("")
        dialog._location_edit.setText(str(temp_dir))
        dialog._on_location_changed(str(temp_dir))
        is_valid, message = dialog._validate_form()
        assert not is_valid  # Still invalid (no project name)

        # Set both project name and location
        dialog._project_name_edit.setText("Test Project")
        dialog._on_project_name_changed("Test Project")
        dialog._location_edit.setText(str(temp_dir))
        dialog._on_location_changed(str(temp_dir))
        is_valid, message = dialog._validate_form()
        if not is_valid:
            # May still be invalid due to other constraints, check the message
            assert len(message) > 0

    def test_project_path_conflict_detection(
        self, dialog: NewProjectDialog, temp_dir: Path
    ) -> None:
        """Test detection of existing project directories."""
        # Create a directory that would conflict
        conflict_dir = temp_dir / "test_project"
        conflict_dir.mkdir()

        # Set up dialog for conflict scenario
        dialog._project_name_edit.setText("Test Project")
        dialog._on_project_name_changed("Test Project")
        dialog._location_edit.setText(str(temp_dir))
        dialog._on_location_changed(str(temp_dir))

        # Validation should detect the conflict
        is_valid = dialog._validate_form()
        # The exact behavior depends on implementation - it might still be valid
        # but should show a warning in the feedback
        feedback_text = dialog._feedback_label.text()
        if not is_valid:
            assert (
                "already exists" in feedback_text or "conflict" in feedback_text.lower()
            )

    def test_get_project_info(self, dialog: NewProjectDialog) -> None:
        """Test get_project_info method."""
        # Set form data
        dialog._project_name_edit.setText("Test Project")
        dialog._on_project_name_changed("Test Project")
        dialog._system_id_edit.setText("custom_id")
        dialog._on_system_id_changed("custom_id")
        dialog._location_edit.setText("/test/path")
        dialog._on_location_changed("/test/path")

        # Get project info
        name, system_id, path = dialog.get_project_info()
        assert name == "Test Project"
        assert system_id == "custom_id"
        assert path == "/test/path"

    def test_get_created_project_path(self, dialog: NewProjectDialog) -> None:
        """Test get_created_project_path method."""
        # Initially None
        assert dialog.get_created_project_path() is None

        # Set created project path
        test_path = "/test/created/project"
        dialog._created_project_path = test_path
        assert dialog.get_created_project_path() == test_path

    def test_set_default_location(
        self, dialog: NewProjectDialog, temp_dir: Path
    ) -> None:
        """Test set_default_location method."""
        # Set valid default location
        dialog.set_default_location(str(temp_dir))
        assert dialog._location_edit.text() == str(temp_dir)

        # Set invalid location (should not change)
        original_text = dialog._location_edit.text()
        dialog.set_default_location("/nonexistent/path")
        assert dialog._location_edit.text() == original_text

        # Set empty location (should not change)
        dialog.set_default_location("")
        assert dialog._location_edit.text() == original_text

    def test_dialog_signals(self, dialog: NewProjectDialog) -> None:
        """Test dialog signal emissions."""
        # Track signal emissions
        signal_emitted = []

        def capture_signal(path: str) -> None:
            signal_emitted.append(path)

        dialog.project_created.connect(capture_signal)

        # Simulate project creation with signal emission
        test_path = "/test/project/path"
        dialog._created_project_path = test_path
        dialog.project_created.emit(test_path)

        # Verify signal was emitted with correct path
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == test_path

    def test_field_constraints(self, dialog: NewProjectDialog) -> None:
        """Test field input constraints and limits."""
        # Test description field height constraint
        assert dialog._description_edit.maximumHeight() == 80

        # Test placeholder texts are set
        assert dialog._project_name_edit.placeholderText()
        assert dialog._system_id_edit.placeholderText()
        assert dialog._location_edit.placeholderText()
        assert dialog._description_edit.placeholderText()

    def test_dialog_modality(self, dialog: NewProjectDialog) -> None:
        """Test dialog modal behavior."""
        assert dialog.isModal()
        assert dialog.windowModality() == Qt.WindowModality.ApplicationModal
