"""
New Project Dialog implementation for GRIMOIRE Design Studio.

This module provides the NewProjectDialog class which implements a project creation
wizard with form fields for project setup, validation, and integration with the
ProjectManager for creating valid GRIMOIRE project structures.
"""

import re
from pathlib import Path
from typing import Optional

from grimoire_logging import get_logger
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.project_manager import ProjectManager

logger = get_logger(__name__)


class NewProjectDialog(QDialog):
    """
    Dialog for creating new GRIMOIRE projects.

    Provides a user-friendly interface for:
    - Entering project name and auto-generating system ID
    - Selecting project directory location
    - Validating input fields
    - Creating project structure via ProjectManager
    - Handling errors and providing user feedback

    Signals:
        project_created: Emitted when a project is successfully created (str: project_path)
    """

    # Signals
    project_created = pyqtSignal(str)  # project_path

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the New Project Dialog.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self._logger = get_logger(__name__)

        # Initialize ProjectManager
        self._project_manager = ProjectManager()

        # Form data
        self._project_name = ""
        self._system_id = ""
        self._project_path = ""
        self._created_project_path: Optional[str] = None

        # Setup UI
        self._setup_dialog()
        self._setup_form()
        self._setup_buttons()
        self._setup_layout()
        self._connect_signals()

        # Set initial state
        self._update_form_validation()

        self._logger.debug("NewProjectDialog initialized")

    def _setup_dialog(self) -> None:
        """Set up basic dialog properties."""
        self.setWindowTitle("New GRIMOIRE Project")
        self.setModal(True)
        self.setMinimumSize(550, 450)
        self.resize(650, 550)

        # Set window flags for better behavior
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )

    def _setup_form(self) -> None:
        """Set up the form fields."""
        # Project Name
        self._project_name_label = QLabel("Project &Name:")
        self._project_name_edit = QLineEdit()
        self._project_name_edit.setPlaceholderText(
            "Enter a descriptive name for your project"
        )
        self._project_name_label.setBuddy(self._project_name_edit)

        # System ID
        self._system_id_label = QLabel("System &ID:")
        self._system_id_edit = QLineEdit()
        self._system_id_edit.setPlaceholderText("Auto-generated from project name")
        self._system_id_label.setBuddy(self._system_id_edit)

        # Project Location
        self._location_label = QLabel("Project &Location:")
        location_layout = QHBoxLayout()
        location_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins

        self._location_edit = QLineEdit()
        self._location_edit.setPlaceholderText(
            "Select folder where project will be created"
        )
        self._location_edit.setReadOnly(True)
        self._location_edit.setMinimumHeight(24)  # Ensure minimum height

        self._browse_button = QPushButton("&Browse...")
        self._browse_button.setFixedWidth(80)
        self._browse_button.setMinimumHeight(24)  # Match edit height

        location_layout.addWidget(self._location_edit)
        location_layout.addWidget(self._browse_button)

        self._location_widget = QWidget()
        self._location_widget.setLayout(location_layout)
        self._location_widget.setMinimumHeight(24)  # Ensure widget height
        self._location_label.setBuddy(self._location_edit)

        # Project Description (optional)
        self._description_label = QLabel("&Description (Optional):")
        self._description_edit = QTextEdit()
        self._description_edit.setPlaceholderText(
            "Enter a brief description of your GRIMOIRE system (optional)"
        )
        self._description_edit.setMaximumHeight(80)
        self._description_label.setBuddy(self._description_edit)

        # Validation feedback area
        self._feedback_label = QLabel()
        self._feedback_label.setWordWrap(True)
        self._feedback_label.setStyleSheet(
            """
            QLabel {
                padding: 8px;
                border-radius: 4px;
                margin: 4px 0;
            }
            """
        )
        self._feedback_label.hide()  # Hidden initially

        # Preview area
        self._preview_label = QLabel("Project Preview:")
        preview_font = QFont()
        preview_font.setBold(True)
        self._preview_label.setFont(preview_font)

        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)  # Make it read-only
        self._preview_text.setMinimumHeight(120)  # Ensure adequate height
        self._preview_text.setMaximumHeight(
            200
        )  # Set a reasonable max height for scrolling
        self._preview_text.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._preview_text.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._preview_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', 'Monaco', monospace;
                color: #212529;
            }
            """
        )
        self._preview_text.setPlainText("Please fill in the project details above.")

    def _setup_buttons(self) -> None:
        """Set up dialog buttons."""
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        # Customize button labels
        ok_button = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText("&Create Project")

        cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button:
            cancel_button.setText("&Cancel")

        # Initially disable the create button
        if ok_button:
            ok_button.setEnabled(False)

    def _setup_layout(self) -> None:
        """Set up the dialog layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Header
        header_label = QLabel("Create a New GRIMOIRE Project")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("QLabel { margin: 10px 0; color: #2c3e50; }")

        # Form layout
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        form_layout.addRow(self._project_name_label, self._project_name_edit)
        form_layout.addRow(self._system_id_label, self._system_id_edit)
        form_layout.addRow(self._location_label, self._location_widget)
        form_layout.addRow(self._description_label, self._description_edit)

        # Add components to main layout
        main_layout.addWidget(header_label)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self._feedback_label)
        main_layout.addWidget(self._preview_label)
        main_layout.addWidget(self._preview_text)
        main_layout.addStretch()  # Push buttons to bottom
        main_layout.addWidget(self._button_box)

    def _connect_signals(self) -> None:
        """Connect signals and slots."""
        # Form field changes
        self._project_name_edit.textChanged.connect(self._on_project_name_changed)
        self._system_id_edit.textChanged.connect(self._on_system_id_changed)
        self._location_edit.textChanged.connect(self._on_location_changed)

        # Button clicks
        self._browse_button.clicked.connect(self._on_browse_clicked)
        self._button_box.accepted.connect(self._on_create_project)
        self._button_box.rejected.connect(self.reject)

    def _on_project_name_changed(self, text: str) -> None:
        """
        Handle project name changes and auto-generate system ID.

        Args:
            text: New project name text
        """
        self._project_name = text.strip()

        # Auto-generate system ID if it hasn't been manually edited
        if (
            not hasattr(self, "_system_id_manually_edited")
            or not self._system_id_manually_edited
        ):
            auto_system_id = self._generate_system_id(self._project_name)
            if auto_system_id != self._system_id_edit.text():
                # Temporarily disconnect signal to avoid recursion
                self._system_id_edit.textChanged.disconnect()
                self._system_id_edit.setText(auto_system_id)
                self._system_id_edit.textChanged.connect(self._on_system_id_changed)
                self._system_id = auto_system_id

        self._update_form_validation()
        self._update_preview()

    def _on_system_id_changed(self, text: str) -> None:
        """
        Handle system ID changes.

        Args:
            text: New system ID text
        """
        self._system_id = text.strip()

        # Mark as manually edited if different from auto-generated
        auto_generated = self._generate_system_id(self._project_name)
        self._system_id_manually_edited = self._system_id != auto_generated

        self._update_form_validation()
        self._update_preview()

    def _on_location_changed(self, text: str) -> None:
        """
        Handle location changes.

        Args:
            text: New location text
        """
        self._project_path = text.strip()
        self._update_form_validation()
        self._update_preview()

    def _on_browse_clicked(self) -> None:
        """Handle browse button click to select project location."""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setWindowTitle("Select Project Location")

        # Set initial directory to user's home or current location
        if self._project_path and Path(self._project_path).exists():
            dialog.setDirectory(str(Path(self._project_path).parent))
        else:
            dialog.setDirectory(str(Path.home()))

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                selected_path = Path(selected_dirs[0])
                self._location_edit.setText(str(selected_path))
                self._logger.debug(f"Selected project location: {selected_path}")

    def _generate_system_id(self, project_name: str) -> str:
        """
        Generate a system ID from the project name.

        Args:
            project_name: The project name to convert

        Returns:
            A valid system ID (lowercase, underscores, alphanumeric)
        """
        if not project_name:
            return ""

        # Convert to lowercase and replace spaces/special chars with underscores
        system_id = re.sub(r"[^a-zA-Z0-9_]", "_", project_name.lower())

        # Remove multiple consecutive underscores
        system_id = re.sub(r"_+", "_", system_id)

        # Remove leading/trailing underscores
        system_id = system_id.strip("_")

        # Ensure it starts with a letter
        if system_id and system_id[0].isdigit():
            system_id = f"project_{system_id}"

        # Fallback if empty
        if not system_id:
            system_id = "new_project"

        return system_id

    def _validate_form(self) -> tuple[bool, str]:
        """
        Validate the current form state.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check project name
        if not self._project_name:
            return False, "Project name is required."

        if len(self._project_name) < 2:
            return False, "Project name must be at least 2 characters long."

        # Check system ID
        if not self._system_id:
            return False, "System ID is required."

        if not re.match(r"^[a-z][a-z0-9_]*$", self._system_id):
            return (
                False,
                "System ID must start with a letter and contain only lowercase letters, numbers, and underscores.",
            )

        if len(self._system_id) < 2:
            return False, "System ID must be at least 2 characters long."

        # Check project location
        if not self._project_path:
            return False, "Project location is required."

        try:
            location_path = Path(self._project_path)
            if not location_path.exists():
                return False, f"Selected location does not exist: {self._project_path}"

            if not location_path.is_dir():
                return (
                    False,
                    f"Selected location is not a directory: {self._project_path}",
                )

            # Check if we can write to the location
            test_file = location_path / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except (OSError, PermissionError):
                return False, f"Cannot write to selected location: {self._project_path}"

            # Check if project directory already exists
            project_dir = location_path / self._system_id
            if project_dir.exists():
                return (
                    False,
                    f"A directory with name '{self._system_id}' already exists in the selected location.",
                )

        except Exception as e:
            return False, f"Invalid project location: {e}"

        return True, "All fields are valid."

    def _update_form_validation(self) -> None:
        """Update form validation state and UI feedback."""
        is_valid, message = self._validate_form()

        # Update create button state
        ok_button = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setEnabled(is_valid)

        # Update feedback display
        if not is_valid and (
            self._project_name or self._system_id or self._project_path
        ):
            # Show error feedback
            self._feedback_label.setText(f"⚠️ {message}")
            self._feedback_label.setStyleSheet(
                """
                QLabel {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    color: #856404;
                    padding: 8px;
                    border-radius: 4px;
                    margin: 4px 0;
                }
                """
            )
            self._feedback_label.show()
        elif is_valid and self._project_name and self._system_id and self._project_path:
            # Show success feedback
            self._feedback_label.setText(f"✅ {message}")
            self._feedback_label.setStyleSheet(
                """
                QLabel {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                    padding: 8px;
                    border-radius: 4px;
                    margin: 4px 0;
                }
                """
            )
            self._feedback_label.show()
        else:
            # Hide feedback for empty form
            self._feedback_label.hide()

    def _update_preview(self) -> None:
        """Update the project preview display."""
        if not self._project_name:
            self._preview_text.setText("Please fill in the project details above.")
            return

        # Build preview text
        preview_lines = []

        if self._project_path and self._system_id:
            full_project_path = Path(self._project_path) / self._system_id
            preview_lines.append(f"Project Directory: {full_project_path}")

        if self._system_id:
            preview_lines.append(f"System ID: {self._system_id}")

        # Show expected structure
        preview_lines.append("")
        preview_lines.append("Project Structure:")
        if self._system_id:
            preview_lines.append(f"  {self._system_id}/")
            preview_lines.append("  ├── system.yaml")
            preview_lines.append("  ├── models/")
            preview_lines.append("  ├── flows/")
            preview_lines.append("  ├── compendiums/")
            preview_lines.append("  ├── tables/")
            preview_lines.append("  ├── sources/")
            preview_lines.append("  ├── prompts/")
            preview_lines.append("  └── README.md")

        self._preview_text.setPlainText("\n".join(preview_lines))

    def _on_create_project(self) -> None:
        """Handle project creation when OK button is clicked."""
        # Final validation
        is_valid, message = self._validate_form()
        if not is_valid:
            QMessageBox.warning(self, "Invalid Input", message)
            return

        try:
            # Create the project using system ID as folder name
            full_project_path = Path(self._project_path) / self._system_id
            description = self._description_edit.toPlainText().strip()

            self._logger.info(f"Creating new GRIMOIRE project: {full_project_path}")

            # Use ProjectManager to create the project
            project = self._project_manager.create_project(
                project_path=str(full_project_path),
                project_name=self._project_name,
                system_id=self._system_id,
            )

            # Add description to system.yaml if provided
            if description:
                system_yaml_path = full_project_path / "system.yaml"
                if system_yaml_path.exists():
                    try:
                        # Read existing content
                        content = system_yaml_path.read_text(encoding="utf-8")

                        # Add description after the first line
                        lines = content.split("\n")
                        if len(lines) > 0:
                            lines.insert(1, f"description: {description}")
                            system_yaml_path.write_text(
                                "\n".join(lines), encoding="utf-8"
                            )
                    except Exception as e:
                        self._logger.warning(
                            f"Could not add description to system.yaml: {e}"
                        )

            self._logger.info(f"Successfully created project: {project}")

            # Show success message
            QMessageBox.information(
                self,
                "Project Created",
                f"Successfully created GRIMOIRE project '{self._project_name}' at:\n{full_project_path}",
            )

            # Store created project path and emit signal
            self._created_project_path = str(full_project_path)
            self.project_created.emit(str(full_project_path))
            self.accept()

        except Exception as e:
            self._logger.error(f"Failed to create project: {e}")
            QMessageBox.critical(
                self,
                "Project Creation Failed",
                f"Failed to create the project:\n\n{str(e)}\n\nPlease check the location and try again.",
            )

    # Public API methods

    def get_project_info(self) -> tuple[str, str, str]:
        """
        Get the current project information.

        Returns:
            Tuple of (project_name, system_id, project_path)
        """
        return self._project_name, self._system_id, self._project_path

    def get_created_project_path(self) -> Optional[str]:
        """
        Get the path of the successfully created project.

        Returns:
            Path to the created project directory, or None if no project was created
        """
        return self._created_project_path

    def set_default_location(self, path: str) -> None:
        """
        Set the default project location.

        Args:
            path: Default location path
        """
        if path and Path(path).exists():
            self._location_edit.setText(path)
            self._logger.debug(f"Set default project location: {path}")

    @classmethod
    def create_project_dialog(
        cls, parent: Optional[QWidget] = None, default_location: Optional[str] = None
    ) -> Optional[str]:
        """
        Static method to create and show the new project dialog.

        Args:
            parent: Parent widget
            default_location: Default project location

        Returns:
            Project path if created successfully, None if cancelled
        """
        dialog = cls(parent)

        if default_location:
            dialog.set_default_location(default_location)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            _, _, project_path = dialog.get_project_info()
            return project_path

        return None
