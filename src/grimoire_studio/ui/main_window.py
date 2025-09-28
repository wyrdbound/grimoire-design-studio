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
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
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

        # Initialize tabbed editor system
        self._editor_tabs: QTabWidget = QTabWidget()
        self._open_editors: dict[str, YamlEditorView] = {}  # file_path -> editor

        # Test mode flag to prevent blocking dialogs during testing
        self._test_mode = False

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

    def set_test_mode(self, enabled: bool = True) -> None:
        """
        Enable or disable test mode to prevent blocking dialogs during testing.

        Args:
            enabled: Whether to enable test mode
        """
        self._test_mode = enabled

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

        file_menu.addSeparator()

        # New Welcome Tab action
        self._action_new_welcome = QAction("New &Welcome Tab", self)
        self._action_new_welcome.setStatusTip("Create a new Welcome tab")
        self._action_new_welcome.triggered.connect(self._on_new_welcome_tab)
        file_menu.addAction(self._action_new_welcome)

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

        # Validate File action
        self._action_validate_file = QAction("&Validate Current File", self)
        self._action_validate_file.setShortcut(QKeySequence("Ctrl+F7"))
        self._action_validate_file.setStatusTip("Validate the current file")
        self._action_validate_file.setEnabled(False)  # Enabled when file is open
        self._action_validate_file.triggered.connect(self._on_validate_current_file)
        project_menu.addAction(self._action_validate_file)

        # Validate Project action
        self._action_validate = QAction("Validate &Project", self)
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

        # Window Menu
        window_menu = menubar.addMenu("&Window")
        if not isinstance(window_menu, QMenu):
            raise RuntimeError("Failed to create Window menu")

        # Close Tab action
        self._action_close_tab = QAction("&Close Tab", self)
        self._action_close_tab.setShortcut(QKeySequence.StandardKey.Close)
        self._action_close_tab.setStatusTip("Close the current tab")
        self._action_close_tab.setEnabled(False)
        self._action_close_tab.triggered.connect(self._close_current_tab)
        window_menu.addAction(self._action_close_tab)

        # Close All Tabs action
        self._action_close_all = QAction("Close &All", self)
        self._action_close_all.setShortcut(QKeySequence("Ctrl+Shift+W"))
        self._action_close_all.setStatusTip("Close all tabs")
        self._action_close_all.setEnabled(False)
        self._action_close_all.triggered.connect(self._close_all_tabs)
        window_menu.addAction(self._action_close_all)

        window_menu.addSeparator()

        # Next Tab action
        self._action_next_tab = QAction("&Next Tab", self)
        self._action_next_tab.setShortcut(QKeySequence("Ctrl+Tab"))
        self._action_next_tab.setStatusTip("Switch to next tab")
        self._action_next_tab.setEnabled(False)
        self._action_next_tab.triggered.connect(self._next_tab)
        window_menu.addAction(self._action_next_tab)

        # Previous Tab action
        self._action_prev_tab = QAction("&Previous Tab", self)
        self._action_prev_tab.setShortcut(QKeySequence("Ctrl+Shift+Tab"))
        self._action_prev_tab.setStatusTip("Switch to previous tab")
        self._action_prev_tab.setEnabled(False)
        self._action_prev_tab.triggered.connect(self._prev_tab)
        window_menu.addAction(self._action_prev_tab)

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
        toolbar.addAction(self._action_validate_file)
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
            self._action_validate_file.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_DialogYesButton)
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

        # Set up tabbed editor area
        self._setup_editor_tabs()
        self._editor_splitter.addWidget(self._editor_tabs)

        # Output console
        self._output_console = OutputConsole()
        # Set minimum size to ensure it's always visible
        self._output_console.setMinimumSize(300, 150)
        # Set size policy to ensure it maintains its size
        from PyQt6.QtWidgets import QSizePolicy

        size_policy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        size_policy.setVerticalStretch(0)
        self._output_console.setSizePolicy(size_policy)
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

        # Set splitter properties (must be done before setting sizes)
        self._main_splitter.setChildrenCollapsible(False)
        self._editor_splitter.setChildrenCollapsible(False)

        # Make splitter handle more visible
        self._editor_splitter.setHandleWidth(6)
        self._main_splitter.setHandleWidth(6)

        # Set stretch factors for editor splitter (editor area gets more space)
        self._editor_splitter.setStretchFactor(0, 1)  # Editor tabs
        self._editor_splitter.setStretchFactor(1, 0)  # Output console (fixed size)

        # Set initial splitter sizes from configuration
        main_ratios = self._config.get("splitter/main_horizontal", [300, 600, 300])
        # Ensure all ratios are integers (PyQt6 compatibility fix)
        main_ratios = [int(size) for size in main_ratios]
        self._main_splitter.setSizes(main_ratios)

        editor_ratios = self._config.get("splitter/editor_vertical", [400, 200])
        # Ensure all ratios are integers (PyQt6 compatibility fix)
        editor_ratios = [int(size) for size in editor_ratios]
        # Ensure output console always has at least 150px height
        if len(editor_ratios) >= 2:
            if editor_ratios[1] < 150:
                editor_ratios[1] = 150
        self._editor_splitter.setSizes(editor_ratios)

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
        title_font.setPointSize(16)
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

    def _setup_editor_tabs(self) -> None:
        """Set up the tabbed editor area."""
        # Configure tab widget
        self._editor_tabs.setTabsClosable(True)
        self._editor_tabs.setMovable(True)
        self._editor_tabs.setDocumentMode(True)

        # Connect tab signals
        self._editor_tabs.tabCloseRequested.connect(self._close_tab)
        self._editor_tabs.currentChanged.connect(self._on_tab_changed)

        # Start with dark background when no tabs are open
        self._create_dark_background()

        # Enable tab context menu
        self._editor_tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._editor_tabs.customContextMenuRequested.connect(
            self._show_tab_context_menu
        )

    def _create_editor_placeholder(self) -> None:
        """Create a placeholder widget when no tabs are open."""
        if self._editor_tabs.count() == 0:
            placeholder = self._create_placeholder_panel(
                "Editor",
                "YAML editor will appear here.\n"
                "Double-click files in the project browser to open them.\n"
                "Supports syntax highlighting and real-time validation.",
            )
            self._editor_tabs.addTab(placeholder, "Welcome")
            # Welcome tab can be closed like any other tab

    def _create_dark_background(self) -> None:
        """Create a dark background when no tabs are open."""
        # Clear all tabs and add a single dark background tab
        self._editor_tabs.clear()

        # Create dark background widget
        dark_widget = QWidget()
        dark_widget.setStyleSheet(
            """
            QWidget {
                background-color: #2b2b2b;
                border: none;
            }
            """
        )

        # Add as a single tab with no close button
        self._editor_tabs.addTab(dark_widget, "")

        # Hide the tab bar when showing dark background
        tab_bar = self._editor_tabs.tabBar()
        if tab_bar:
            tab_bar.setVisible(False)

        # Ensure tab widget is visible
        self._editor_tabs.setVisible(True)

    def _show_tab_bar(self) -> None:
        """Show the tab bar (used when switching from dark background mode)."""
        tab_bar = self._editor_tabs.tabBar()
        if tab_bar:
            tab_bar.setVisible(True)

    def _is_dark_background_mode(self) -> bool:
        """Check if we're currently in dark background mode."""
        if self._editor_tabs.count() == 1:
            # Check if the single tab has no text (dark background indicator)
            return self._editor_tabs.tabText(0) == ""
        return False

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

            # Restore splitter states with validation
            main_ratios = self._config.get("splitter/main_horizontal", [300, 600, 300])
            if isinstance(main_ratios, (list, tuple)) and len(main_ratios) >= 3:
                # Ensure all ratios are integers (PyQt6 compatibility fix)
                main_ratios = [int(size) for size in main_ratios]
                self._main_splitter.setSizes(main_ratios)

            editor_ratios = self._config.get("splitter/editor_vertical", [400, 200])
            if isinstance(editor_ratios, (list, tuple)) and len(editor_ratios) >= 2:
                # Ensure all ratios are integers (PyQt6 compatibility fix)
                editor_ratios = [int(size) for size in editor_ratios]
                # Ensure output console always has at least 150px height
                if editor_ratios[1] < 150:
                    editor_ratios[1] = 150
                self._editor_splitter.setSizes(editor_ratios)

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

    # Tab management methods

    def _close_tab(self, index: int) -> None:
        """Close a tab at the specified index."""
        # Ensure index is an integer (PyQt6 compatibility fix)
        try:
            index = int(index)
        except (ValueError, TypeError):
            return

        if index < 0 or index >= self._editor_tabs.count():
            return

        widget = self._editor_tabs.widget(index)
        if widget is None:
            return

        # Check if it's a YAML editor with unsaved changes
        if isinstance(widget, YamlEditorView):
            if widget.has_unsaved_changes():
                if not self._confirm_close_unsaved_file(widget):
                    return  # User cancelled

            # Remove from open editors dict
            file_path = widget.get_file_path()
            if file_path and str(file_path) in self._open_editors:
                del self._open_editors[str(file_path)]

        # Remove the tab
        self._editor_tabs.removeTab(index)
        widget.setParent(None)

        # If no more tabs at all, show dark background
        if self._editor_tabs.count() == 0:
            self._create_dark_background()

        # Update UI state
        self._update_editor_ui_state()

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change events."""
        # Ensure index is an integer (PyQt6 compatibility fix)
        try:
            index = int(index)
        except (ValueError, TypeError):
            return

        if index < 0:
            return

        # Skip if status bar is not initialized yet (during construction)
        if not hasattr(self, "_file_label"):
            return

        widget = self._editor_tabs.widget(index)
        if isinstance(widget, YamlEditorView):
            # Update current file in status bar
            file_path = widget.get_file_path()
            if file_path:
                self.set_current_file(str(file_path))
                self.enable_file_actions(True)
            else:
                self.set_current_file(None)
                self.enable_file_actions(False)
        else:
            # Placeholder tab
            self.set_current_file(None)
            self.enable_file_actions(False)

    def _show_tab_context_menu(self, position: QPoint) -> None:
        """Show context menu for tabs."""
        tab_bar = self._editor_tabs.tabBar()
        if not tab_bar:
            return

        tab_index = tab_bar.tabAt(position)
        # Ensure tab_index is an integer (PyQt6 compatibility fix)
        try:
            tab_index = int(tab_index)
        except (ValueError, TypeError):
            return
        if tab_index < 0:
            return

        widget = self._editor_tabs.widget(tab_index)
        if not isinstance(widget, YamlEditorView):
            return  # Don't show context menu for placeholder

        menu = QMenu(self)

        # Close tab action
        close_action = menu.addAction("Close")
        if close_action:
            close_action.triggered.connect(lambda: self._close_tab(tab_index))

        # Close other tabs action
        if self._editor_tabs.count() > 1:
            close_others_action = menu.addAction("Close Others")
            if close_others_action:
                close_others_action.triggered.connect(
                    lambda: self._close_other_tabs(tab_index)
                )

        # Close all tabs action
        if self._has_editor_tabs():
            close_all_action = menu.addAction("Close All")
            if close_all_action:
                close_all_action.triggered.connect(self._close_all_tabs)

        menu.addSeparator()

        # Save action
        save_action = menu.addAction("Save")
        if save_action:
            save_action.triggered.connect(lambda: widget.save_file())
            save_action.setEnabled(widget.has_unsaved_changes())

        menu.exec(self._editor_tabs.mapToGlobal(position))

    def _has_editor_tabs(self) -> bool:
        """Check if there are any real editor tabs (not just placeholder)."""
        for i in range(self._editor_tabs.count()):
            widget = self._editor_tabs.widget(i)
            if isinstance(widget, YamlEditorView):
                return True
        return False

    def _has_no_editor_tabs(self) -> bool:
        """Check if there are no real editor tabs."""
        return not self._has_editor_tabs()

    def _close_other_tabs(self, keep_index: int) -> None:
        """Close all tabs except the one at keep_index."""
        # Ensure keep_index is an integer (PyQt6 compatibility fix)
        try:
            keep_index = int(keep_index)
        except (ValueError, TypeError):
            return
        # Close tabs from right to left to maintain indices
        for i in range(self._editor_tabs.count() - 1, -1, -1):
            if i != keep_index:
                self._close_tab(i)

    def _close_all_tabs(self) -> None:
        """Close all editor tabs."""
        # Close tabs from right to left to maintain indices
        for i in range(self._editor_tabs.count() - 1, -1, -1):
            widget = self._editor_tabs.widget(i)
            if isinstance(widget, YamlEditorView):
                self._close_tab(i)

    def _confirm_close_unsaved_file(self, editor: YamlEditorView) -> bool:
        """
        Confirm closing a file with unsaved changes.

        Args:
            editor: The editor with unsaved changes

        Returns:
            True if user wants to proceed, False if cancelled
        """
        if self._test_mode:
            return True  # Don't show dialogs during testing

        file_path = editor.get_file_path()
        file_name = file_path.name if file_path else "Untitled"

        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            f"'{file_name}' has unsaved changes.\n\nDo you want to save before closing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if reply == QMessageBox.StandardButton.Save:
            return editor.save_file()
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        else:  # Cancel
            return False

    def _update_editor_ui_state(self) -> None:
        """Update UI state based on current editor tabs."""
        current_widget = self._editor_tabs.currentWidget()
        if isinstance(current_widget, YamlEditorView):
            file_path = current_widget.get_file_path()
            if file_path:
                self.set_current_file(str(file_path))
                self.enable_file_actions(True)
                self._update_multi_tab_actions()
                return

        # No valid editor tab
        self.set_current_file(None)
        self.enable_file_actions(False)

    def _get_current_editor(self) -> Optional[YamlEditorView]:
        """Get the current active editor, if any."""
        current_widget = self._editor_tabs.currentWidget()
        if isinstance(current_widget, YamlEditorView):
            return current_widget
        return None

    def _update_tab_title(self, editor: YamlEditorView) -> None:
        """Update the tab title for the given editor."""
        # Find the tab index for this editor
        for i in range(self._editor_tabs.count()):
            if self._editor_tabs.widget(i) is editor:
                file_path = editor.get_file_path()
                if file_path:
                    title = file_path.name
                    if editor.has_unsaved_changes():
                        title += " *"
                    self._editor_tabs.setTabText(i, title)
                break

    def _get_all_editors(self) -> list[YamlEditorView]:
        """Get all open editors."""
        editors = []
        for i in range(self._editor_tabs.count()):
            widget = self._editor_tabs.widget(i)
            if isinstance(widget, YamlEditorView):
                editors.append(widget)
        return editors

    def _close_current_tab(self) -> None:
        """Close the current tab."""
        current_index = self._editor_tabs.currentIndex()
        if current_index >= 0:
            self._close_tab(current_index)

    def _next_tab(self) -> None:
        """Switch to the next tab."""
        current = self._editor_tabs.currentIndex()
        count = self._editor_tabs.count()
        if count > 1:
            next_index = (current + 1) % count
            self._editor_tabs.setCurrentIndex(next_index)

    def _prev_tab(self) -> None:
        """Switch to the previous tab."""
        current = self._editor_tabs.currentIndex()
        count = self._editor_tabs.count()
        if count > 1:
            prev_index = (current - 1) % count
            self._editor_tabs.setCurrentIndex(prev_index)

    def _on_new_welcome_tab(self) -> None:
        """Create a new Welcome tab."""
        # Show the tab bar (in case we were in dark background mode)
        self._show_tab_bar()

        # Create welcome placeholder
        placeholder = self._create_placeholder_panel(
            "Welcome to GRIMOIRE Design Studio",
            "YAML editor will appear here.\n"
            "Double-click files in the project browser to open them.\n"
            "Supports syntax highlighting and real-time validation.\n\n"
            "Get started:\n"
            "• Create a new project (Ctrl+N)\n"
            "• Open an existing project (Ctrl+O)\n"
            "• Browse the project files in the left panel",
        )

        # Add the tab and make it current
        tab_index = self._editor_tabs.addTab(placeholder, "Welcome")
        # Ensure tab_index is an integer (PyQt6 compatibility fix)
        self._editor_tabs.setCurrentIndex(int(tab_index))

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

        current_editor = self._get_current_editor()
        if current_editor:
            try:
                success = current_editor.save_file()
                if success:
                    current_file = current_editor.get_file_path()
                    file_name = Path(current_file).name if current_file else "file"
                    self.set_status(f"Saved: {file_name}")
                    self._logger.info(f"File saved successfully: {current_file}")
                    # Update tab title to remove unsaved indicator
                    self._update_tab_title(current_editor)
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

        editors = self._get_all_editors()
        if not editors:
            self.set_status("No files open to save")
            self._logger.debug("Save all requested but no editors are open")
            return

        saved_count = 0
        failed_count = 0

        for editor in editors:
            if editor.has_unsaved_changes():
                try:
                    if editor.save_file():
                        saved_count += 1
                        self._update_tab_title(editor)
                    else:
                        failed_count += 1
                except Exception as e:
                    self._logger.error(f"Failed to save file: {e}")
                    failed_count += 1

        # Update status based on results
        if failed_count == 0:
            if saved_count > 0:
                self.set_status(f"Saved {saved_count} file(s)")
            else:
                self.set_status("No files needed saving")
        else:
            self.set_status(f"Saved {saved_count} file(s), {failed_count} failed")

        self._logger.info(
            f"Save all completed: {saved_count} saved, {failed_count} failed"
        )

    def _get_relative_file_path(self, file_path: Optional[Path]) -> Optional[str]:
        """
        Get a file path relative to the current project root if possible.

        Args:
            file_path: Absolute file path

        Returns:
            Relative path from project root if possible, otherwise absolute path as string
        """
        if not file_path:
            return None

        # Get current project to determine root
        current_project = self._project_browser.get_current_project()
        if not current_project:
            return str(file_path)

        try:
            # Try to make it relative to project root
            relative_path = file_path.relative_to(current_project.project_path)
            # Use forward slashes for cross-platform compatibility
            return relative_path.as_posix()
        except (ValueError, OSError):
            # If path is not within project root, return absolute path
            return str(file_path)

    def _perform_project_validation(
        self, auto_switch_console: bool = True, update_status_message: bool = True
    ) -> bool:
        """
        Perform project validation and display results.

        Args:
            auto_switch_console: Whether to automatically switch to validation tab
            update_status_message: Whether to update status bar with completion message

        Returns:
            True if validation was performed successfully, False otherwise
        """
        # Get current project
        current_project = self._project_browser.get_current_project()
        if not current_project:
            if update_status_message:
                self.set_status("No project loaded for validation")
            return False

        try:
            from ..core.validator import YamlValidator

            validator = YamlValidator()
            all_results = []

            # Find YAML files only in official GRIMOIRE directories
            project_path = Path(current_project.project_path)
            yaml_files = []

            # Add system.yaml if it exists
            system_file = project_path / "system.yaml"
            if system_file.exists():
                yaml_files.append(system_file)

            # Scan only official directories for YAML files
            for directory in validator.GRIMOIRE_DIRECTORIES:
                dir_path = project_path / directory
                if dir_path.exists() and dir_path.is_dir():
                    yaml_files.extend(dir_path.rglob("*.yaml"))
                    yaml_files.extend(dir_path.rglob("*.yml"))

            if not yaml_files:
                if update_status_message:
                    self.set_status("No YAML files found in project")
                # Still update validation status to show no issues found
                self.set_validation_status("No files")
                return True

            # Validate each file
            for yaml_file in yaml_files:
                file_results = validator.validate_file(yaml_file)
                all_results.extend(file_results)

            # Also try system-level validation if possible
            try:
                system_results = validator.validate_system(project_path)
                all_results.extend(system_results)
            except Exception as e:
                self._logger.warning(f"System-level validation failed: {e}")

            # Format and display results
            formatted_results = []
            for result in all_results:
                formatted_results.append(
                    {
                        "level": result.severity.value,
                        "message": result.message,
                        "file": self._get_relative_file_path(result.file_path),
                        "line": result.line_number,
                    }
                )

            # Display in output console
            self._output_console.display_validation_results(
                formatted_results, auto_switch=auto_switch_console
            )

            # Update status
            error_count = sum(1 for r in all_results if r.is_error)
            warning_count = sum(1 for r in all_results if r.is_warning)

            if error_count > 0:
                self.set_validation_status(
                    f"{error_count} errors, {warning_count} warnings"
                )
                if update_status_message:
                    self.set_status(
                        f"Project validation completed: {error_count} errors, {warning_count} warnings"
                    )
            elif warning_count > 0:
                self.set_validation_status(f"{warning_count} warnings")
                if update_status_message:
                    self.set_status(
                        f"Project validation completed: {warning_count} warnings"
                    )
            else:
                self.set_validation_status("Valid")
                if update_status_message:
                    self.set_status("Project validation completed: No issues found")

            self.validation_requested.emit()
            self._logger.debug(
                f"Project validation completed: {len(all_results)} total issues"
            )
            return True

        except Exception as e:
            error_msg = f"Project validation failed: {e}"
            self._logger.error(error_msg)
            if update_status_message:
                self.set_status(error_msg)
            return False

    def _on_validate_project(self) -> None:
        """Handle validate project action."""
        self._logger.info("Manual project validation requested")
        self._perform_project_validation(
            auto_switch_console=True, update_status_message=True
        )

    def _on_validate_current_file(self) -> None:
        """Handle validate current file action."""
        self._logger.info("Current file validation requested")

        current_editor = self._get_current_editor()
        if not current_editor:
            self.set_status("No file open for validation")
            return

        current_file = current_editor.get_file_path()
        if not current_file:
            self.set_status("Current editor has no file path")
            return

        # Trigger validation in the editor (which handles the validation and display)
        current_editor._perform_validation(force_validation=True)
        self.set_status(f"Validation completed for: {current_file.name}")

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
        self._action_validate_file.setEnabled(enabled)
        # Note: save_all is managed separately by _update_editor_ui_state

        # Enable/disable tab actions
        self._action_close_tab.setEnabled(enabled)

        # Save all and tab navigation actions depend on having multiple tabs
        self._update_multi_tab_actions()

    def _update_multi_tab_actions(self) -> None:
        """Update actions that depend on having multiple tabs or unsaved changes."""
        editors = self._get_all_editors()
        has_editors = len(editors) > 0
        has_multiple_tabs = len(editors) > 1
        has_unsaved_changes = any(editor.has_unsaved_changes() for editor in editors)

        # Save All is enabled if any editor has unsaved changes
        self._action_save_all.setEnabled(has_unsaved_changes)

        # Tab navigation is enabled if there are multiple tabs
        self._action_next_tab.setEnabled(has_multiple_tabs)
        self._action_prev_tab.setEnabled(has_multiple_tabs)

        # Close All is enabled if there are any editors
        self._action_close_all.setEnabled(has_editors)

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

    def _detect_file_type(self, file_path: Path) -> str:
        """
        Detect the file type and return the appropriate editor type.

        Args:
            file_path: Path to the file

        Returns:
            Editor type: 'yaml', 'text', or 'unsupported'
        """
        suffix = file_path.suffix.lower()

        # YAML files
        if suffix in [".yaml", ".yml"]:
            return "yaml"

        # Text files
        if suffix in [".md", ".txt", ".json", ".py", ".js", ".css", ".html", ".xml"]:
            return "text"

        # Check for YAML content in files without extension
        if not suffix:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                # Simple heuristic: if it looks like YAML structure
                if any(line.strip().endswith(":") for line in content.split("\n")[:10]):
                    return "yaml"
            except (OSError, PermissionError, UnicodeDecodeError) as e:
                # Log specific file reading errors but continue with fallback
                self._logger.debug(
                    f"Could not read file {file_path} for type detection: {e}"
                )
            except Exception as e:
                # Log unexpected errors but continue with fallback
                self._logger.warning(
                    f"Unexpected error reading file {file_path} for type detection: {e}"
                )

            return "text"

        return "unsupported"

    def _create_editor_for_file(self, file_path: Path) -> Optional[YamlEditorView]:
        """
        Create the appropriate editor for a file.

        Args:
            file_path: Path to the file

        Returns:
            Editor instance or None if file type not supported
        """
        file_type = self._detect_file_type(file_path)

        if file_type in ["yaml", "text"]:
            # For now, we use YamlEditorView for both YAML and text files
            # In the future, we could create different editor types
            editor = YamlEditorView()

            # Configure syntax highlighting based on file type
            if file_type == "yaml":
                # YamlEditorView defaults to YAML highlighting
                pass
            else:
                # For text files, we could disable syntax highlighting or use a basic scheme
                # For now, keep YAML highlighting as it's not intrusive for text files
                pass

            return editor

        return None

    def _open_file_in_editor(self, file_path: str) -> None:
        """
        Open a file in the appropriate editor.

        Args:
            file_path: Path to the file to open
        """
        path_obj = Path(file_path)

        # Detect file type and check if supported
        file_type = self._detect_file_type(path_obj)
        if file_type == "unsupported":
            raise RuntimeError(
                f"Unsupported file type: {path_obj.suffix}\n"
                f"Supported formats: YAML (.yaml, .yml), Text (.txt, .md, .json, .py, .js, .css, .html, .xml)"
            )

        # Check if file is already open in a tab
        file_key = str(path_obj)
        if file_key in self._open_editors:
            # Switch to existing tab
            existing_editor = self._open_editors[file_key]
            for i in range(self._editor_tabs.count()):
                if self._editor_tabs.widget(i) is existing_editor:
                    self._editor_tabs.setCurrentIndex(i)
                    return

        # Remove dark background if we were in that mode
        if self._is_dark_background_mode():
            self._show_tab_bar()
            # Remove the dark background tab
            self._editor_tabs.removeTab(0)

        # Create appropriate editor for the file type
        editor = self._create_editor_for_file(path_obj)
        if not editor:
            raise RuntimeError(f"Could not create editor for file: {path_obj}")

        # Connect editor signals
        editor.file_changed.connect(self._on_editor_file_modified)
        editor.validation_requested.connect(self._on_editor_validation_requested)

        # Connect editor to output console for validation results
        editor.set_output_console(self._output_console)

        # Load the file
        editor.load_file(path_obj)

        # Add to tab widget with appropriate icon/indicator
        tab_title = path_obj.name
        tab_index = self._editor_tabs.addTab(editor, tab_title)

        # Store in open editors dict
        self._open_editors[file_key] = editor

        # Switch to the new tab
        # Ensure tab_index is an integer (PyQt6 compatibility fix)
        self._editor_tabs.setCurrentIndex(int(tab_index))

        # Enable file actions since we now have a file open
        self.enable_file_actions(True)
        self.set_current_file(file_path)

        self._logger.debug(f"File loaded in new tab (type: {file_type}): {file_path}")

    def _on_editor_file_modified(self, is_modified: bool) -> None:
        """
        Handle file modification status changes from editor.

        Args:
            is_modified: True if file has unsaved changes
        """
        # Find which editor sent this signal and update its tab title
        sender = self.sender()
        if isinstance(sender, YamlEditorView):
            self._update_tab_title(sender)

            # Update multi-tab actions (Save All state may have changed)
            self._update_multi_tab_actions()

            # If this is the current editor, also update the status bar
            current_editor = self._get_current_editor()
            if sender is current_editor:
                current_file = sender.get_file_path()
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
        from ..core.validator import YamlValidator

        # Perform validation
        validator = YamlValidator()

        # Validate YAML syntax first
        syntax_results = validator.validate_yaml_syntax(content, file_path)

        # If syntax is valid, validate structure
        if not any(r.is_error for r in syntax_results):
            try:
                import yaml

                data = yaml.safe_load(content)
                field_results = validator.validate_required_fields(data, file_path)
                structure_results = validator.validate_component_structure(
                    data, file_path
                )
                all_results = syntax_results + field_results + structure_results
            except Exception:
                # If YAML parsing fails unexpectedly, just use syntax results
                all_results = syntax_results
        else:
            all_results = syntax_results

        # Format results for display
        formatted_results = []
        for result in all_results:
            formatted_results.append(
                {
                    "level": result.severity.value,
                    "message": result.message,
                    "file": self._get_relative_file_path(result.file_path),
                    "line": result.line_number,
                }
            )

        # Display results in output console
        if formatted_results:
            self._output_console.display_validation_results(
                formatted_results, auto_switch=False
            )

        # Update validation status in status bar
        error_count = sum(1 for r in all_results if r.is_error)
        warning_count = sum(1 for r in all_results if r.is_warning)

        if error_count > 0:
            self.set_validation_status(
                f"{error_count} errors, {warning_count} warnings"
            )
        elif warning_count > 0:
            self.set_validation_status(f"{warning_count} warnings")
        else:
            self.set_validation_status("Valid")

        # Emit the main validation signal
        self.validation_requested.emit()
        self._logger.debug(
            f"Validation completed for: {file_path} - {len(all_results)} issues found"
        )

    def _on_project_changed(self) -> None:
        """Handle project structure changes from project browser."""
        self._logger.debug("Project structure changed")

        # Check if we have a current project
        current_project = self._project_browser.get_current_project()
        if current_project:
            # Enable project actions
            self.enable_project_actions(True)
            self.set_status(f"Project loaded: {current_project.project_name}")

            # Add to recent projects
            self._config.add_recent_project(str(current_project.project_path))
            self._update_recent_projects_menu()

            # Emit main window project opened signal
            self.project_opened.emit(str(current_project.project_path))

            # Automatically validate the project when loaded/created
            self._logger.info(
                f"Auto-validating project: {current_project.project_name}"
            )
            validation_success = self._perform_project_validation(
                auto_switch_console=False,  # Don't auto-switch to avoid disrupting workflow
                update_status_message=False,  # Don't override the "Project loaded" message yet
            )

            if validation_success:
                # Update status with both project name and validation result
                validation_text = self._validation_label.text()
                if "Valid" in validation_text:
                    self.set_status(
                        f"Project: {current_project.project_name} - No validation issues"
                    )
                elif "error" in validation_text or "warning" in validation_text:
                    self.set_status(
                        f"Project: {current_project.project_name} - {validation_text.replace('Validation: ', '')}"
                    )
                else:
                    self.set_status(f"Project: {current_project.project_name}")
        else:
            # No project loaded
            self.enable_project_actions(False)
            self.enable_file_actions(False)
            self.set_status("No project loaded")
            self.set_current_file(None)
            self.set_validation_status("No validation")
            # Clear project root for output console
            self._output_console.set_project_root(None)

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
            # Set project root for relative path display in output console
            self._output_console.set_project_root(project_path)
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

            # Check if we're in a test environment (QApplication.applicationName contains 'test')
            app = QApplication.instance()
            is_test_environment = (
                app and "test" in app.applicationName().lower()
            ) or hasattr(self, "_test_mode")

            # Check if confirmation is needed (skip in test environment)
            if self._config.get("app/confirm_exit", True) and not is_test_environment:
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
                    if not is_test_environment:
                        QApplication.quit()
                else:
                    event.ignore()
            else:
                self._logger.info("Application closing")
                event.accept()
                if not is_test_environment:
                    QApplication.quit()

        except Exception as e:
            # Don't prevent exit due to errors
            self._logger.error(f"Error during close event: {e}")
            event.accept()
            if not hasattr(self, "_test_mode"):
                QApplication.quit()
