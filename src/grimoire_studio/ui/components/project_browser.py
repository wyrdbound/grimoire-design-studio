"""
Project Browser Component for GRIMOIRE Design Studio.

This module provides the ProjectBrowser class which displays the project file
structure in a tree view with file type detection, icons, and interaction
capabilities.
"""

from pathlib import Path
from typing import Optional

from grimoire_logging import get_logger
from PyQt6.QtCore import QModelIndex, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ...core.project_manager import ProjectManager
from ...models.project import GrimoireProject

logger = get_logger(__name__)


class ProjectBrowser(QWidget):
    """
    Project browser component with hierarchical file display.

    Provides a tree view of GRIMOIRE project files with:
    - File type detection and appropriate icons
    - Double-click to open files
    - Context menus for file operations
    - Integration with project manager
    - Signal-based communication with main window

    Signals:
        file_selected: Emitted when a file is selected (file_path: str)
        file_opened: Emitted when a file should be opened (file_path: str)
        project_changed: Emitted when project structure changes
    """

    # Signals for communication with main window and other components
    file_selected = pyqtSignal(str)  # file_path
    file_opened = pyqtSignal(str)  # file_path
    project_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the project browser.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self._logger = get_logger(__name__)
        self._project_manager = ProjectManager()
        self._current_project: Optional[GrimoireProject] = None

        # Setup UI
        self._setup_ui()
        self._connect_signals()

        self._logger.info("ProjectBrowser initialized successfully")

    def _setup_ui(self) -> None:
        """Setup the user interface components."""
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create tree view
        self._tree_view = QTreeView()
        self._tree_model = QStandardItemModel()

        # Configure tree view
        self._tree_view.setModel(self._tree_model)
        self._tree_view.setHeaderHidden(True)
        self._tree_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._tree_view.setAlternatingRowColors(True)
        self._tree_view.setRootIsDecorated(True)
        self._tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Add to layout
        layout.addWidget(self._tree_view)

        # Setup initial empty state
        self._show_empty_state()

    def _connect_signals(self) -> None:
        """Connect internal signals to handlers."""
        self._tree_view.doubleClicked.connect(self._on_item_double_clicked)
        self._tree_view.clicked.connect(self._on_item_clicked)
        self._tree_view.customContextMenuRequested.connect(
            self._on_context_menu_requested
        )

    def _show_empty_state(self) -> None:
        """Display empty state when no project is loaded."""
        self._tree_model.clear()
        root_item = self._tree_model.invisibleRootItem()
        if root_item is None:
            raise RuntimeError("Tree model root item is None")

        # Add informational items
        no_project_item = QStandardItem("No project loaded")
        no_project_item.setEnabled(False)
        root_item.appendRow(no_project_item)

        instruction_item = QStandardItem("Use File > New Project or Open Project")
        instruction_item.setEnabled(False)
        root_item.appendRow(instruction_item)

    def load_project(self, project_path: str) -> None:
        """
        Load a GRIMOIRE project and display its structure.

        Args:
            project_path: Path to the project directory

        Raises:
            RuntimeError: If project cannot be loaded
        """
        try:
            project_path_obj = Path(project_path)
            if not project_path_obj.exists():
                raise RuntimeError(f"Project path does not exist: {project_path}")

            # Verify project exists (has system.yaml)
            system_file = project_path_obj / "system.yaml"
            if not system_file.exists():
                raise RuntimeError(
                    f"Invalid GRIMOIRE project: missing system.yaml in {project_path}"
                )

            # Try to load the system to get proper project name and system ID
            try:
                system = self._project_manager.load_system(project_path)
                project_name = system.system.name or project_path_obj.name
                system_id = system.system.id
            except Exception as load_error:
                # Fallback to directory name if system loading fails
                self._logger.warning(
                    f"Could not load system metadata, using fallback: {load_error}"
                )
                project_name = project_path_obj.name
                system_id = (
                    f"{project_name.lower().replace(' ', '-').replace('_', '-')}-system"
                )

            self._current_project = GrimoireProject(
                project_path_obj, project_name, system_id
            )
            self._logger.info(f"Loading project: {self._current_project.project_name}")

            # Update tree view
            self._populate_tree()

            # Expand root items
            self._tree_view.expandToDepth(1)

            self.project_changed.emit()
            self._logger.info(f"Project loaded successfully: {project_path}")

        except Exception as e:
            self._logger.error(f"Failed to load project {project_path}: {e}")
            self._show_error_state(f"Error loading project: {e}")
            raise RuntimeError(f"Failed to load project: {e}") from e

    def _populate_tree(self) -> None:
        """Populate the tree view with project structure."""
        if not self._current_project:
            self._show_empty_state()
            return

        self._tree_model.clear()
        self._tree_model.setHorizontalHeaderLabels(["Project Files"])
        root_item = self._tree_model.invisibleRootItem()
        if root_item is None:
            raise RuntimeError("Tree model root item is None")

        # Add project root
        project_item = QStandardItem(self._current_project.project_name)
        project_item.setData(
            str(self._current_project.project_path), Qt.ItemDataRole.UserRole
        )
        project_item.setToolTip(f"Project: {self._current_project.project_name}")
        root_item.appendRow(project_item)

        # Add project structure
        self._add_directory_to_tree(project_item, self._current_project.project_path)

    def _add_directory_to_tree(
        self, parent_item: QStandardItem, directory_path: Path
    ) -> None:
        """
        Recursively add directory contents to tree.

        Args:
            parent_item: Parent tree item
            directory_path: Directory path to add
        """
        try:
            if not directory_path.is_dir():
                return

            # Get sorted directory contents
            items = sorted(
                directory_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            )

            for item_path in items:
                # Skip hidden files and __pycache__
                if item_path.name.startswith(".") or item_path.name == "__pycache__":
                    continue

                item = QStandardItem(item_path.name)
                item.setData(str(item_path), Qt.ItemDataRole.UserRole)

                if item_path.is_dir():
                    # Directory
                    item.setToolTip(f"Directory: {item_path.name}")
                    self._add_directory_to_tree(item, item_path)
                else:
                    # File - determine type and set appropriate icon/tooltip
                    file_type = self._get_file_type(item_path)
                    item.setToolTip(f"{file_type}: {item_path.name}")

                parent_item.appendRow(item)

        except (OSError, PermissionError) as e:
            self._logger.warning(f"Cannot read directory {directory_path}: {e}")

    def _get_file_type(self, file_path: Path) -> str:
        """
        Determine the type of a file based on its path and extension.

        Args:
            file_path: Path to the file

        Returns:
            Human-readable file type string
        """
        suffix = file_path.suffix.lower()
        name = file_path.name.lower()

        # GRIMOIRE specific files
        if name == "system.yaml":
            return "System Definition"
        elif suffix == ".yaml" or suffix == ".yml":
            if "models" in str(file_path):
                return "Model Definition"
            elif "flows" in str(file_path):
                return "Flow Definition"
            elif "compendiums" in str(file_path):
                return "Compendium"
            elif "tables" in str(file_path):
                return "Table Definition"
            elif "sources" in str(file_path):
                return "Source Definition"
            elif "prompts" in str(file_path):
                return "Prompt Definition"
            else:
                return "YAML File"
        elif suffix == ".md":
            return "Markdown File"
        elif suffix == ".txt":
            return "Text File"
        elif suffix == ".json":
            return "JSON File"
        else:
            return "File"

    def _show_error_state(self, error_message: str) -> None:
        """
        Display error state in the tree view.

        Args:
            error_message: Error message to display
        """
        self._tree_model.clear()
        root_item = self._tree_model.invisibleRootItem()
        if root_item is None:
            raise RuntimeError("Tree model root item is None")

        error_item = QStandardItem(f"Error: {error_message}")
        error_item.setEnabled(False)
        root_item.appendRow(error_item)

    def _on_item_clicked(self, index: QModelIndex) -> None:
        """
        Handle tree item click events.

        Args:
            index: Model index of clicked item
        """
        item = self._tree_model.itemFromIndex(index)
        if not item:
            return

        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and Path(file_path).is_file():
            self.file_selected.emit(file_path)
            self._logger.debug(f"File selected: {file_path}")

    def _on_item_double_clicked(self, index: QModelIndex) -> None:
        """
        Handle tree item double-click events.

        Args:
            index: Model index of double-clicked item
        """
        item = self._tree_model.itemFromIndex(index)
        if not item:
            return

        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and Path(file_path).is_file():
            # Only open supported file types
            path_obj = Path(file_path)
            if path_obj.suffix.lower() in [".yaml", ".yml", ".md", ".txt", ".json"]:
                self.file_opened.emit(file_path)
                self._logger.info(f"Opening file: {file_path}")
            else:
                self._logger.debug(f"Unsupported file type for editing: {file_path}")

    def _on_context_menu_requested(self, position: QPoint) -> None:
        """
        Handle context menu requests.

        Args:
            position: Position where context menu was requested
        """
        index = self._tree_view.indexAt(position)
        if not index.isValid():
            return

        item = self._tree_model.itemFromIndex(index)
        if not item:
            return

        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not file_path:
            return

        # Create context menu
        menu = QMenu(self)
        path_obj = Path(file_path)

        if path_obj.is_file():
            # File context menu
            open_action = QAction("Open", self)
            open_action.triggered.connect(
                lambda: self.file_opened.emit(file_path)
                if path_obj.suffix.lower() in [".yaml", ".yml", ".md", ".txt", ".json"]
                else None
            )

            if path_obj.suffix.lower() in [".yaml", ".yml", ".md", ".txt", ".json"]:
                menu.addAction(open_action)

            menu.addSeparator()

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self._delete_file(file_path))
            menu.addAction(delete_action)

        elif path_obj.is_dir():
            # Directory context menu
            new_file_action = QAction("New YAML File...", self)
            new_file_action.triggered.connect(lambda: self._create_new_file(file_path))
            menu.addAction(new_file_action)

            menu.addSeparator()

            delete_action = QAction("Delete Directory", self)
            delete_action.triggered.connect(lambda: self._delete_directory(file_path))
            menu.addAction(delete_action)

        # Show menu
        menu.exec(self._tree_view.mapToGlobal(position))

    def _delete_file(self, file_path: str) -> None:
        """
        Delete a file (placeholder for now).

        Args:
            file_path: Path to file to delete
        """
        # TODO: Implement file deletion with confirmation dialog
        self._logger.info(f"Delete file requested: {file_path}")

    def _delete_directory(self, dir_path: str) -> None:
        """
        Delete a directory (placeholder for now).

        Args:
            dir_path: Path to directory to delete
        """
        # TODO: Implement directory deletion with confirmation dialog
        self._logger.info(f"Delete directory requested: {dir_path}")

    def _create_new_file(self, dir_path: str) -> None:
        """
        Create a new file in the specified directory (placeholder for now).

        Args:
            dir_path: Path to directory where file should be created
        """
        # TODO: Implement new file creation dialog
        self._logger.info(f"New file requested in: {dir_path}")

    def refresh_project(self) -> None:
        """Refresh the project tree display."""
        if self._current_project:
            self._populate_tree()
            self._tree_view.expandToDepth(1)
            self.project_changed.emit()
            self._logger.debug("Project tree refreshed")

    def get_current_project(self) -> Optional[GrimoireProject]:
        """
        Get the currently loaded project.

        Returns:
            Currently loaded project or None
        """
        return self._current_project

    def clear_project(self) -> None:
        """Clear the current project and return to empty state."""
        self._current_project = None
        self._show_empty_state()
        self.project_changed.emit()
        self._logger.info("Project browser cleared")
