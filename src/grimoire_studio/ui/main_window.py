"""
Main window implementation for GRIMOIRE Design Studio.

This module provides the MainWindow class which serves as the primary application
interface with a three-panel layout for project browsing, editing, and properties.
"""

from pathlib import Path
from typing import Any, Optional

from grimoire_logging import get_logger
from PyQt6.QtCore import QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core.config import get_config
from .components.output_console import OutputConsole
from .components.project_browser import ProjectBrowser
from .dialogs.new_project import NewProjectDialog
from .views.yaml_editor_view import YamlEditorView

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window with three-panel layout.

    Provides the primary interface for GRIMOIRE Design Studio including:
    - Project browser (left panel)
    - Editor area (center panel)
    - Properties/Output console (right panel)
    - Menu bar, toolbar, and status bar
    - Window state persistence using configuration system

    Signals:
        project_opened: Emitted when a project is opened
        file_opened: Emitted when a file is opened for editing
        validation_requested: Emitted when validation is requested
    """

    # Signals for communication with other components
    project_opened = pyqtSignal(str)  # project_path
    file_opened = pyqtSignal(str)  # file_path
    validation_requested = pyqtSignal()

    # UI component type annotations
    _recent_projects_menu: QMenu

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the main window.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self._config = get_config()
        self._logger = get_logger(__name__)

        # Initialize editor tracking
        self._current_editor: Optional[YamlEditorView] = None

        # Initialize UI components
        self._setup_window()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_status_bar()

        # Load window state from configuration
        self._restore_window_state()

        # Connect signals
        self._connect_signals()

        self._logger.info("MainWindow initialized successfully")

    def _setup_window(self) -> None:
        """Set up basic window properties."""
        self.setWindowTitle("GRIMOIRE Design Studio v1.0.0")
        self.setMinimumSize(800, 600)

        # Set application icon (will be added later)
        # self.setWindowIcon(QIcon(":/icons/app-icon.png"))

        # Enable window state saving
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def _setup_menu_bar(self) -> None:
        """Create and configure the menu bar."""
        menubar = self.menuBar()
        if not isinstance(menubar, QMenuBar):
            raise RuntimeError("Failed to create menu bar")

        # File Menu
        file_menu = menubar.addMenu("&File")
        if not isinstance(file_menu, QMenu):
            raise RuntimeError("Failed to create File menu")

        # New Project action
        self._action_new_project = QAction("&New Project...", self)
        self._action_new_project.setShortcut(QKeySequence.StandardKey.New)
        self._action_new_project.setStatusTip("Create a new GRIMOIRE project")
        self._action_new_project.triggered.connect(self._on_new_project)
        file_menu.addAction(self._action_new_project)

        # Open Project action
        self._action_open_project = QAction("&Open Project...", self)
        self._action_open_project.setShortcut(QKeySequence.StandardKey.Open)
        self._action_open_project.setStatusTip("Open an existing GRIMOIRE project")
        self._action_open_project.triggered.connect(self._on_open_project)
        file_menu.addAction(self._action_open_project)

        # Recent Projects submenu (will be populated dynamically)
        recent_menu = file_menu.addMenu("Recent &Projects")
        if recent_menu is not None:
            self._recent_projects_menu = recent_menu
            self._update_recent_projects_menu()
        else:
            # Fallback - create a disabled action if menu creation failed
            no_menu_action = QAction("Recent Projects (unavailable)", self)
            no_menu_action.setEnabled(False)
            file_menu.addAction(no_menu_action)

        file_menu.addSeparator()

        # Save action
        self._action_save = QAction("&Save", self)
        self._action_save.setShortcut(QKeySequence.StandardKey.Save)
        self._action_save.setStatusTip("Save the current file")
        self._action_save.setEnabled(False)  # Enabled when file is open
        self._action_save.triggered.connect(self._on_save)
        file_menu.addAction(self._action_save)

        # Save All action
        self._action_save_all = QAction("Save &All", self)
        self._action_save_all.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._action_save_all.setStatusTip("Save all open files")
        self._action_save_all.setEnabled(False)
        self._action_save_all.triggered.connect(self._on_save_all)
        file_menu.addAction(self._action_save_all)

        file_menu.addSeparator()

        # Exit action
        self._action_exit = QAction("E&xit", self)
        self._action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self._action_exit.setStatusTip("Exit GRIMOIRE Design Studio")
        self._action_exit.triggered.connect(self.close)
        file_menu.addAction(self._action_exit)

        # Project Menu
        project_menu = menubar.addMenu("&Project")
        if not isinstance(project_menu, QMenu):
            raise RuntimeError("Failed to create Project menu")

        # Validate Project action
        self._action_validate = QAction("&Validate Project", self)
        self._action_validate.setShortcut(QKeySequence("F7"))
        self._action_validate.setStatusTip("Validate the current project")
        self._action_validate.setEnabled(False)  # Enabled when project is loaded
        self._action_validate.triggered.connect(self._on_validate_project)
        project_menu.addAction(self._action_validate)

        # Build Project action (placeholder for future)
        self._action_build = QAction("&Build Project", self)
        self._action_build.setShortcut(QKeySequence("F6"))
        self._action_build.setStatusTip("Build the current project")
        self._action_build.setEnabled(False)
        # self._action_build.triggered.connect(self._on_build_project)
        project_menu.addAction(self._action_build)

        # Flow Menu
        flow_menu = menubar.addMenu("F&low")
        if not isinstance(flow_menu, QMenu):
            raise RuntimeError("Failed to create Flow menu")

        # Run Flow action
        self._action_run_flow = QAction("&Run Flow...", self)
        self._action_run_flow.setShortcut(QKeySequence("F5"))
        self._action_run_flow.setStatusTip("Run a flow from the current project")
        self._action_run_flow.setEnabled(False)  # Enabled when project is loaded
        # self._action_run_flow.triggered.connect(self._on_run_flow)
        flow_menu.addAction(self._action_run_flow)

        # Test Flow action
        self._action_test_flow = QAction("&Test Flow...", self)
        self._action_test_flow.setShortcut(QKeySequence("Shift+F5"))
        self._action_test_flow.setStatusTip("Test a flow with sample inputs")
        self._action_test_flow.setEnabled(False)
        # self._action_test_flow.triggered.connect(self._on_test_flow)
        flow_menu.addAction(self._action_test_flow)

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        if not isinstance(help_menu, QMenu):
            raise RuntimeError("Failed to create Help menu")

        # About action
        self._action_about = QAction("&About", self)
        self._action_about.setStatusTip("About GRIMOIRE Design Studio")
        self._action_about.triggered.connect(self._on_about)
        help_menu.addAction(self._action_about)

    def _setup_toolbar(self) -> None:
        """Create and configure the toolbar."""
        toolbar = self.addToolBar("Main")
        if not isinstance(toolbar, QToolBar):
            raise RuntimeError("Failed to create toolbar")

        # Set toolbar properties
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        toolbar.setMovable(False)

        # Add actions to toolbar (using standard icons for now)
        toolbar.addAction(self._action_new_project)
        toolbar.addAction(self._action_open_project)
        toolbar.addSeparator()
        toolbar.addAction(self._action_save)
        toolbar.addAction(self._action_save_all)
        toolbar.addSeparator()
        toolbar.addAction(self._action_validate)
        toolbar.addAction(self._action_run_flow)

        # Set standard icons (these will be replaced with custom icons later)
        from PyQt6.QtWidgets import QStyle

        style = self.style()
        if style is not None:
            self._action_new_project.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
            )
            self._action_open_project.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
            )
            self._action_save.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
            )
            self._action_validate.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
            )
            self._action_run_flow.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
            )

    def _setup_central_widget(self) -> None:
        """Create and configure the central widget with three-panel layout."""
        # Create main horizontal splitter
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self._main_splitter)

        # Left panel: Project Browser
        self._project_browser = ProjectBrowser()
        self._main_splitter.addWidget(self._project_browser)

        # Center panel: Editor Area with vertical splitter for editor and output
        self._editor_splitter = QSplitter(Qt.Orientation.Vertical)

        # Editor area (placeholder)
        self._editor_widget = self._create_placeholder_panel(
            "Editor",
            "YAML editor will appear here.\n"
            "Double-click files in the project browser to open them.\n"
            "Supports syntax highlighting and real-time validation.",
        )
        self._editor_splitter.addWidget(self._editor_widget)

        # Output console
        self._output_console = OutputConsole()
        self._editor_splitter.addWidget(self._output_console)

        self._main_splitter.addWidget(self._editor_splitter)

        # Right panel: Properties Panel (placeholder)
        self._properties_widget = self._create_placeholder_panel(
            "Properties",
            "Object properties and metadata will appear here.\n"
            "When editing objects:\n"
            "• View and edit object attributes\n"
            "• Real-time validation feedback\n"
            "• Type-specific input controls",
        )
        self._main_splitter.addWidget(self._properties_widget)

        # Set initial splitter sizes from configuration
        main_ratios = self._config.get("splitter/main_horizontal", [300, 600, 300])
        self._main_splitter.setSizes(main_ratios)

        editor_ratios = self._config.get("splitter/editor_vertical", [400, 200])
        self._editor_splitter.setSizes(editor_ratios)

        # Set splitter properties
        self._main_splitter.setChildrenCollapsible(False)
        self._editor_splitter.setChildrenCollapsible(False)

    def _create_placeholder_panel(self, title: str, description: str) -> QWidget:
        """
        Create a placeholder panel widget.

        Args:
            title: Panel title
            description: Panel description text

        Returns:
            Configured placeholder widget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title label
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("QLabel { color: #2c3e50; margin-bottom: 10px; }")

        # Description label
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        description_label.setStyleSheet("QLabel { color: #7f8c8d; line-height: 1.4; }")

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch()

        # Add border and background
        widget.setStyleSheet(
            """
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            """
        )

        return widget

    def _setup_status_bar(self) -> None:
        """Create and configure the status bar."""
        status_bar = self.statusBar()
        if not isinstance(status_bar, QStatusBar):
            raise RuntimeError("Failed to create status bar")

        # Main status message
        self._status_label = QLabel("Ready")
        status_bar.addWidget(self._status_label)

        # Current file indicator
        self._file_label = QLabel("No file open")
        status_bar.addPermanentWidget(self._file_label)

        # Validation status indicator
        self._validation_label = QLabel("No validation")
        status_bar.addPermanentWidget(self._validation_label)

        # Set initial status
        self.set_status("GRIMOIRE Design Studio ready")

    def _restore_window_state(self) -> None:
        """Restore window state from configuration."""
        try:
            # Restore window size
            window_size = self._config.get("window/size")
            if isinstance(window_size, QSize):
                self.resize(window_size)
            elif isinstance(window_size, (tuple, list)) and len(window_size) >= 2:
                self.resize(QSize(int(window_size[0]), int(window_size[1])))
            else:
                self.resize(1200, 800)  # Default size

            # Restore window position
            window_position = self._config.get("window/position")
            if isinstance(window_position, QPoint):
                self.move(window_position)
            elif (
                isinstance(window_position, (tuple, list)) and len(window_position) >= 2
            ):
                self.move(QPoint(int(window_position[0]), int(window_position[1])))

            # Restore maximized state
            if self._config.get("window/maximized", False):
                self.showMaximized()

            self._logger.debug("Window state restored from configuration")

        except Exception as e:
            self._logger.warning(f"Could not restore window state: {e}")

    def _save_window_state(self) -> None:
        """Save current window state to configuration."""
        try:
            # Save window size and position
            if not self.isMaximized():
                self._config.set("window/size", self.size())
                self._config.set("window/position", self.pos())

            # Save maximized state
            self._config.set("window/maximized", self.isMaximized())

            # Save splitter positions
            self._config.set("splitter/main_horizontal", self._main_splitter.sizes())
            self._config.set("splitter/editor_vertical", self._editor_splitter.sizes())

            # Force save to disk
            self._config.save_settings()

            self._logger.debug("Window state saved to configuration")

        except Exception as e:
            self._logger.error(f"Error saving window state: {e}")

    def _connect_signals(self) -> None:
        """Connect internal signals and slots."""
        # Connect project browser signals
        self._project_browser.file_selected.connect(self._on_file_selected)
        self._project_browser.file_opened.connect(self._on_file_opened)
        self._project_browser.project_changed.connect(self._on_project_changed)

        # Connect output console signals
        self._output_console.content_added.connect(self._on_console_content_added)

        # Connect splitter moved signals to save state
        self._main_splitter.splitterMoved.connect(
            lambda: self._save_splitter_state("main_horizontal", self._main_splitter)
        )
        self._editor_splitter.splitterMoved.connect(
            lambda: self._save_splitter_state("editor_vertical", self._editor_splitter)
        )

    def _save_splitter_state(self, config_key: str, splitter: QSplitter) -> None:
        """Save splitter state to configuration."""
        try:
            full_key = f"splitter/{config_key}"
            self._config.set(full_key, splitter.sizes())
        except Exception as e:
            self._logger.warning(f"Could not save splitter state for {config_key}: {e}")

    def _update_recent_projects_menu(self) -> None:
        """Update the recent projects menu with current list."""
        self._recent_projects_menu.clear()

        recent_projects = self._config.get_recent_projects()
        if not recent_projects:
            no_recent_action = QAction("No recent projects", self)
            no_recent_action.setEnabled(False)
            self._recent_projects_menu.addAction(no_recent_action)
        else:
            for i, project_path in enumerate(recent_projects[:10]):  # Show max 10
                project_name = Path(project_path).name
                action = QAction(f"{i + 1}. {project_name}", self)
                action.setStatusTip(f"Open project: {project_path}")
                action.setData(project_path)  # Store path in action data
                action.triggered.connect(
                    lambda checked=False, path=project_path: self._open_project_path(
                        path
                    )
                )
                self._recent_projects_menu.addAction(action)

    # Action handlers
    def _on_new_project(self) -> None:
        """Handle new project action."""
        self._logger.info("New project requested")

        try:
            dialog = NewProjectDialog(self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                project_path = dialog.get_created_project_path()
                if project_path:
                    self.set_status(f"Successfully created project at: {project_path}")
                    self._logger.info(f"New project created at: {project_path}")
                    # Load the newly created project into the project browser
                    try:
                        self.load_project(project_path)
                        self.set_status(
                            f"Created and loaded project: {Path(project_path).name}"
                        )
                    except Exception as load_error:
                        self._logger.error(
                            f"Failed to load newly created project: {load_error}"
                        )
                        self.set_status(
                            f"Project created but failed to load: {load_error}"
                        )
                else:
                    self.set_status("Project creation completed")
        except Exception as e:
            error_msg = f"Failed to create new project: {e}"
            self._logger.error(error_msg)
            self.set_status(error_msg)

    def _on_open_project(self) -> None:
        """Handle open project action."""
        self._logger.info("Open project requested")

        from PyQt6.QtWidgets import QFileDialog

        # Show directory selection dialog
        project_dir = QFileDialog.getExistingDirectory(
            self,
            "Select GRIMOIRE Project Directory",
            "",  # Start from current directory
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if project_dir:
            try:
                self._open_project_path(project_dir)
                self.set_status(f"Opened project: {Path(project_dir).name}")
            except Exception as e:
                self._logger.error(f"Failed to open project: {e}")
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.critical(
                    self, "Error Opening Project", f"Failed to open project:\n{e}"
                )
        else:
            self._logger.debug("Project open cancelled by user")

    def _open_project_path(self, project_path: str) -> None:
        """
        Open a project from a specific path.

        Args:
            project_path: Path to the project directory
        """
        self._logger.info(f"Opening project: {project_path}")
        try:
            self.load_project(project_path)
        except Exception as e:
            self._logger.error(f"Failed to open project {project_path}: {e}")
            self.set_status(f"Error opening project: {e}")

    def _on_save(self) -> None:
        """Handle save action."""
        self._logger.info("Save requested")

        if self._current_editor:
            try:
                success = self._current_editor.save_file()
                if success:
                    current_file = self._current_editor.get_file_path()
                    file_name = Path(current_file).name if current_file else "file"
                    self.set_status(f"Saved: {file_name}")
                    self._logger.info(f"File saved successfully: {current_file}")
                else:
                    self.set_status("Save failed")
                    self._logger.warning("File save failed")
            except Exception as e:
                error_msg = f"Error saving file: {e}"
                self.set_status(error_msg)
                self._logger.error(error_msg)
        else:
            self.set_status("No file open to save")
            self._logger.debug("Save requested but no editor is active")

    def _on_save_all(self) -> None:
        """Handle save all action."""
        self._logger.info("Save all requested")

        # For now, we only have one editor, so save all is the same as save
        # This will be enhanced in Step 4.4 for multi-tab support
        if self._current_editor:
            self._on_save()
        else:
            self.set_status("No files open to save")
            self._logger.debug("Save all requested but no editor is active")

    def _on_validate_project(self) -> None:
        """Handle validate project action."""
        self._logger.info("Project validation requested")
        self.validation_requested.emit()
        self.set_status("Project validation will be implemented in Step 4.3")

    def _on_about(self) -> None:
        """Handle about action."""
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "About GRIMOIRE Design Studio",
            "<h3>GRIMOIRE Design Studio v1.0.0</h3>"
            "<p>A comprehensive design studio for creating and managing GRIMOIRE systems.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Visual project management</li>"
            "<li>YAML editing with syntax highlighting</li>"
            "<li>Real-time validation</li>"
            "<li>Flow execution and testing</li>"
            "<li>Object instantiation and validation</li>"
            "</ul>"
            "<p>Built with PyQt6 and Python 3.9+</p>",
        )

    # Public interface methods
    def set_status(self, message: str, timeout: int = 0) -> None:
        """
        Set the status bar message.

        Args:
            message: Status message to display
            timeout: Timeout in milliseconds (0 = permanent)
        """
        self._status_label.setText(message)
        if timeout > 0:
            status_bar = self.statusBar()
            if status_bar is not None:
                status_bar.showMessage(message, timeout)

    def set_current_file(self, file_path: Optional[str]) -> None:
        """
        Set the current file indicator in the status bar.

        Args:
            file_path: Path to the current file (None for no file)
        """
        if file_path:
            file_name = Path(file_path).name
            self._file_label.setText(f"File: {file_name}")
        else:
            self._file_label.setText("No file open")

    def set_validation_status(self, status: str) -> None:
        """
        Set the validation status indicator.

        Args:
            status: Validation status string
        """
        self._validation_label.setText(f"Validation: {status}")

    def enable_project_actions(self, enabled: bool) -> None:
        """
        Enable or disable project-related actions.

        Args:
            enabled: True to enable actions, False to disable
        """
        self._action_validate.setEnabled(enabled)
        self._action_build.setEnabled(enabled)
        self._action_run_flow.setEnabled(enabled)
        self._action_test_flow.setEnabled(enabled)

    def enable_file_actions(self, enabled: bool) -> None:
        """
        Enable or disable file-related actions.

        Args:
            enabled: True to enable actions, False to disable
        """
        self._action_save.setEnabled(enabled)
        self._action_save_all.setEnabled(enabled)

    # Project browser signal handlers
    def _on_file_selected(self, file_path: str) -> None:
        """
        Handle file selection from project browser.

        Args:
            file_path: Path of the selected file
        """
        self._logger.debug(f"File selected: {file_path}")
        self.set_current_file(file_path)

        # Enable file actions for supported file types
        path_obj = Path(file_path)
        is_editable = path_obj.suffix.lower() in [
            ".yaml",
            ".yml",
            ".md",
            ".txt",
            ".json",
        ]
        self.enable_file_actions(is_editable)

    def _on_file_opened(self, file_path: str) -> None:
        """
        Handle file opening request from project browser.

        Args:
            file_path: Path of the file to open
        """
        self._logger.info(f"File opened: {file_path}")

        try:
            # Create and set up YAML editor
            self._open_file_in_editor(file_path)

            # Emit the main window signal for file opening
            self.file_opened.emit(file_path)

            # Update status and UI
            self.set_current_file(file_path)
            self.set_status(f"Opened: {Path(file_path).name}")

            # Enable relevant actions
            self.enable_file_actions(True)

        except Exception as e:
            self._logger.error(f"Failed to open file {file_path}: {e}")
            self.set_status(f"Error opening file: {e}")

    def _open_file_in_editor(self, file_path: str) -> None:
        """
        Open a file in the appropriate editor.

        Args:
            file_path: Path to the file to open
        """
        path_obj = Path(file_path)

        # Check if this is a supported file type
        if path_obj.suffix.lower() not in [".yaml", ".yml", ".md", ".txt", ".json"]:
            raise RuntimeError(f"Unsupported file type: {path_obj.suffix}")

        # Create new YAML editor
        yaml_editor = YamlEditorView()

        # Connect editor signals
        yaml_editor.file_changed.connect(self._on_editor_file_modified)
        yaml_editor.validation_requested.connect(self._on_editor_validation_requested)

        # Load the file
        yaml_editor.load_file(path_obj)

        # Replace the current editor widget in the splitter
        if self._current_editor:
            # Remove the existing editor
            self._editor_splitter.replaceWidget(0, yaml_editor)
            self._current_editor.setParent(None)
        else:
            # Replace the placeholder editor widget
            old_widget = self._editor_splitter.widget(0)
            if old_widget:
                self._editor_splitter.replaceWidget(0, yaml_editor)
                old_widget.setParent(None)
            else:
                self._editor_splitter.insertWidget(0, yaml_editor)

        # Update current editor reference
        self._current_editor = yaml_editor

        self._logger.debug(f"File loaded in YAML editor: {file_path}")

    def _on_editor_file_modified(self, is_modified: bool) -> None:
        """
        Handle file modification status changes from editor.

        Args:
            is_modified: True if file has unsaved changes
        """
        if self._current_editor:
            current_file = self._current_editor.get_file_path()
            if current_file:
                file_name = Path(current_file).name
                if is_modified:
                    self.set_current_file(f"{file_name} *")
                else:
                    self.set_current_file(file_name)

    def _on_editor_validation_requested(self, content: str, file_path: Path) -> None:
        """
        Handle validation requests from the editor.

        Args:
            content: The content to validate
            file_path: Path to the file being validated
        """
        # For now, just emit the main validation signal
        # This will be enhanced in Step 4.3 with actual validation
        self.validation_requested.emit()
        self._logger.debug(f"Validation requested for: {file_path}")

    def _on_project_changed(self) -> None:
        """Handle project structure changes from project browser."""
        self._logger.debug("Project structure changed")

        # Check if we have a current project
        current_project = self._project_browser.get_current_project()
        if current_project:
            # Enable project actions
            self.enable_project_actions(True)
            self.set_status(f"Project: {current_project.project_name}")

            # Add to recent projects
            self._config.add_recent_project(str(current_project.project_path))
            self._update_recent_projects_menu()

            # Emit main window project opened signal
            self.project_opened.emit(str(current_project.project_path))
        else:
            # No project loaded
            self.enable_project_actions(False)
            self.enable_file_actions(False)
            self.set_status("No project loaded")
            self.set_current_file(None)

    def load_project(self, project_path: str) -> None:
        """
        Load a project into the project browser.

        Args:
            project_path: Path to the project directory

        Raises:
            RuntimeError: If project cannot be loaded
        """
        try:
            self._project_browser.load_project(project_path)
            self._logger.info(f"Project loaded in main window: {project_path}")
        except Exception as e:
            self._logger.error(f"Failed to load project in main window: {e}")
            self.set_status(f"Error loading project: {e}")
            raise

    def _on_console_content_added(self, tab_name: str) -> None:
        """
        Handle new content added to the output console.

        Args:
            tab_name: Name of the tab that received new content
        """
        # Note: Avoid logging here to prevent recursion with the logs tab
        pass

    # Output console integration methods

    def display_validation_results(
        self, results: list[dict[str, Any]], auto_switch: bool = True
    ) -> None:
        """
        Display validation results in the output console.

        Args:
            results: List of validation result dictionaries
            auto_switch: Whether to automatically switch to validation tab
        """
        self._output_console.display_validation_results(results, auto_switch)
        if results:
            # Update status based on validation results
            error_count = sum(1 for r in results if r.get("level") == "error")
            warning_count = sum(1 for r in results if r.get("level") == "warning")

            if error_count > 0:
                self.set_validation_status(
                    f"{error_count} errors, {warning_count} warnings"
                )
            elif warning_count > 0:
                self.set_validation_status(f"{warning_count} warnings")
            else:
                self.set_validation_status("Valid")

    def display_execution_output(
        self, message: str, level: str = "info", auto_switch: bool = True
    ) -> None:
        """
        Display execution output in the output console.

        Args:
            message: The execution message
            level: Message level
            auto_switch: Whether to automatically switch to execution tab
        """
        self._output_console.display_execution_output(message, level, auto_switch)

    def clear_console(self, tab: Optional[str] = None) -> None:
        """
        Clear the output console.

        Args:
            tab: Specific tab to clear ("validation", "execution", "logs") or None for all
        """
        if tab == "validation":
            self._output_console.clear_validation()
        elif tab == "execution":
            self._output_console.clear_execution()
        elif tab == "logs":
            self._output_console.clear_logs()
        else:
            self._output_console.clear_all()

    def get_output_console(self) -> OutputConsole:
        """
        Get the output console instance.

        Returns:
            The OutputConsole instance
        """
        return self._output_console

    def closeEvent(self, event) -> None:  # type: ignore
        """
        Handle window close event.

        Saves window state and provides exit confirmation if configured.
        """
        try:
            # Save window state
            self._save_window_state()

            # Check if confirmation is needed
            if self._config.get("app/confirm_exit", True):
                from PyQt6.QtWidgets import QMessageBox

                reply = QMessageBox.question(
                    self,
                    "Confirm Exit",
                    "Are you sure you want to exit GRIMOIRE Design Studio?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self._logger.info("Application closing by user request")
                    event.accept()
                    # Quit the application to ensure clean shutdown
                    QApplication.quit()
                else:
                    event.ignore()
            else:
                self._logger.info("Application closing")
                event.accept()
                QApplication.quit()

        except Exception as e:
            # Don't prevent exit due to errors
            self._logger.error(f"Error during close event: {e}")
            event.accept()
            QApplication.quit()
