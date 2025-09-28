"""
Application configuration management for GRIMOIRE Design Studio.

This module provides a thread-safe configuration system using QSettings
for persistent storage of user preferences and application state.
"""

import threading
from pathlib import Path
from typing import Any, Optional, Union

from grimoire_logging import get_logger
from PyQt6.QtCore import QSettings, QSize

logger = get_logger(__name__)


class AppConfig:
    """
    Thread-safe application configuration manager.

    Uses QSettings for cross-platform persistent storage of user preferences.
    Provides default values for all settings and validates input where appropriate.

    Thread Safety:
    All public methods are thread-safe using a read-write lock pattern.
    """

    def __init__(self) -> None:
        """Initialize configuration with default values."""
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._settings = QSettings()
        self._logger = get_logger(__name__)

        # Default configuration values
        self._defaults: dict[str, Any] = {
            # Window and UI settings
            "window/size": QSize(1200, 800),
            "window/maximized": False,
            "window/position": None,  # Will be set by Qt automatically
            "splitter/main_horizontal": [
                300,
                600,
                300,
            ],  # Left, center, right panel ratios
            "splitter/editor_vertical": [400, 200],  # Editor, output console ratios
            # Recent files and projects
            "recent/projects": [],  # List of recent project paths
            "recent/files": [],  # List of recent file paths
            "recent/max_items": 10,  # Maximum items to keep in recent lists
            # Editor preferences
            "editor/font_family": "Consolas",  # Windows default
            "editor/font_size": 14,
            "editor/tab_width": 2,
            "editor/word_wrap": True,
            "editor/line_numbers": True,
            "editor/syntax_highlighting": True,
            "editor/auto_save": True,
            "editor/auto_save_interval": 30,  # seconds
            # Validation settings
            "validation/auto_validate": True,
            "validation/delay_ms": 1000,  # Delay after typing stops
            "validation/show_warnings": True,
            "validation/show_info": True,
            # Logging preferences
            "logging/level": "INFO",
            "logging/console_output": True,
            "logging/file_output": True,
            "logging/max_file_size_mb": 10,
            "logging/backup_count": 5,
            # Application behavior
            "app/check_updates": True,
            "app/restore_session": True,
            "app/confirm_exit": True,
            "app/theme": "system",  # "light", "dark", "system"
        }

        self._logger.debug("AppConfig initialized with defaults")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key (e.g., 'window/size')
            default: Default value if key not found (overrides built-in default)

        Returns:
            Configuration value or default

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            try:
                # Use provided default or built-in default
                fallback = default if default is not None else self._defaults.get(key)
                value = self._settings.value(key, fallback)

                # Handle special Qt types that need conversion
                if key == "window/size" and isinstance(value, (list, tuple)):
                    # Convert list/tuple back to QSize if needed
                    if len(value) >= 2:
                        value = QSize(int(value[0]), int(value[1]))
                    else:
                        value = self._defaults["window/size"]

                self._logger.debug(f"Config get: {key} = {value}")
                return value

            except Exception as e:
                self._logger.warning(f"Error getting config key '{key}': {e}")
                return default if default is not None else self._defaults.get(key)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Value to set

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            try:
                # Handle special Qt types
                if isinstance(value, QSize):
                    # Store QSize as tuple for better serialization
                    value = (value.width(), value.height())

                self._settings.setValue(key, value)
                self._logger.debug(f"Config set: {key} = {value}")

            except Exception as e:
                self._logger.error(f"Error setting config key '{key}': {e}")
                raise

    def get_recent_projects(self) -> list[str]:
        """
        Get list of recent project paths.

        Returns:
            List of recent project paths (most recent first)

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            projects = self.get("recent/projects", [])
            if not isinstance(projects, list):
                projects = []

            # Validate that paths exist and are accessible
            valid_projects = []
            for project_path in projects:
                if isinstance(project_path, str):
                    path = Path(project_path)
                    if path.exists() and path.is_dir():
                        valid_projects.append(project_path)

            # Update stored list if we removed invalid entries
            if len(valid_projects) != len(projects):
                self.set("recent/projects", valid_projects)

            return valid_projects

    def add_recent_project(self, project_path: Union[str, Path]) -> None:
        """
        Add a project to the recent projects list.

        Args:
            project_path: Path to the project directory

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            path_str = str(project_path)
            recent = self.get_recent_projects()
            max_items = self.get("recent/max_items", 10)

            # Remove existing entry if present (to move it to front)
            if path_str in recent:
                recent.remove(path_str)

            # Add to front of list
            recent.insert(0, path_str)

            # Trim to maximum length
            recent = recent[:max_items]

            self.set("recent/projects", recent)
            self._logger.info(f"Added recent project: {path_str}")

    def get_recent_files(self) -> list[str]:
        """
        Get list of recent file paths.

        Returns:
            List of recent file paths (most recent first)

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            files = self.get("recent/files", [])
            if not isinstance(files, list):
                files = []

            # Validate that files exist
            valid_files = []
            for file_path in files:
                if isinstance(file_path, str):
                    path = Path(file_path)
                    if path.exists() and path.is_file():
                        valid_files.append(file_path)

            # Update stored list if we removed invalid entries
            if len(valid_files) != len(files):
                self.set("recent/files", valid_files)

            return valid_files

    def add_recent_file(self, file_path: Union[str, Path]) -> None:
        """
        Add a file to the recent files list.

        Args:
            file_path: Path to the file

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            path_str = str(file_path)
            recent = self.get_recent_files()
            max_items = self.get("recent/max_items", 10)

            # Remove existing entry if present (to move it to front)
            if path_str in recent:
                recent.remove(path_str)

            # Add to front of list
            recent.insert(0, path_str)

            # Trim to maximum length
            recent = recent[:max_items]

            self.set("recent/files", recent)
            self._logger.debug(f"Added recent file: {path_str}")

    def save_settings(self) -> None:
        """
        Explicitly save settings to persistent storage.

        QSettings usually saves automatically, but this can be used
        to force immediate saving of critical settings.

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            try:
                self._settings.sync()
                self._logger.debug("Settings saved to persistent storage")
            except Exception as e:
                self._logger.error(f"Error saving settings: {e}")
                raise

    def load_settings(self) -> None:
        """
        Load settings from persistent storage.

        This is primarily for initialization - QSettings loads automatically.
        Can be used to reload settings if they were changed externally.

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            try:
                self._settings.sync()
                self._logger.debug("Settings loaded from persistent storage")
            except Exception as e:
                self._logger.error(f"Error loading settings: {e}")
                raise

    def reset_to_defaults(self, prefix: Optional[str] = None) -> None:
        """
        Reset configuration to default values.

        Args:
            prefix: If specified, only reset keys starting with this prefix
                   If None, reset all settings

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            try:
                if prefix is None:
                    # Reset all settings
                    self._settings.clear()
                    self._logger.info("All settings reset to defaults")
                else:
                    # Reset only keys with specified prefix
                    all_keys = self._settings.allKeys()
                    for key in all_keys:
                        if key.startswith(prefix):
                            self._settings.remove(key)
                    self._logger.info(
                        f"Settings with prefix '{prefix}' reset to defaults"
                    )

                # Force save
                self.save_settings()

            except Exception as e:
                self._logger.error(f"Error resetting settings: {e}")
                raise

    def get_all_keys(self) -> list[str]:
        """
        Get all configuration keys that have been set.

        Returns:
            List of all configuration keys

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            try:
                return self._settings.allKeys()
            except Exception as e:
                self._logger.error(f"Error getting all keys: {e}")
                return []

    def display_config(self) -> str:
        """
        Generate a formatted display of current configuration.

        Returns a human-readable string representation of the current
        configuration, organized by category with current values and
        whether they are defaults or user-set values.

        Returns:
            Formatted configuration string

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            try:
                lines = []
                lines.append("GRIMOIRE Design Studio Configuration")
                lines.append("=" * 40)
                lines.append("")

                # Group settings by category
                categories = {
                    "Window & UI": ["window/", "splitter/"],
                    "Recent Files": ["recent/"],
                    "Editor": ["editor/"],
                    "Validation": ["validation/"],
                    "Logging": ["logging/"],
                    "Application": ["app/"],
                }

                # Display categorized settings
                for category, prefixes in categories.items():
                    category_settings = []

                    # Get defaults for this category
                    for key, default_value in self._defaults.items():
                        if any(key.startswith(prefix) for prefix in prefixes):
                            current_value = self.get(key)
                            is_default = current_value == default_value

                            # Format the value for display
                            if isinstance(current_value, QSize):
                                display_value = (
                                    f"{current_value.width()}x{current_value.height()}"
                                )
                            elif isinstance(current_value, (list, tuple)):
                                if len(current_value) <= 3:
                                    display_value = str(current_value)
                                else:
                                    display_value = f"[{len(current_value)} items]"
                            else:
                                display_value = str(current_value)

                            # Truncate very long values
                            if len(display_value) > 50:
                                display_value = display_value[:47] + "..."

                            status = "[DEFAULT]" if is_default else "[CUSTOM]"
                            category_settings.append(
                                f"  {key:<25} = {display_value:<20} {status}"
                            )

                    if category_settings:
                        lines.append(f"{category}:")
                        lines.extend(category_settings)
                        lines.append("")

                # Display recent projects and files info
                recent_projects = self.get_recent_projects()
                recent_files = self.get_recent_files()

                if recent_projects or recent_files:
                    lines.append("Recent Items:")
                    if recent_projects:
                        lines.append(f"  Recent projects: {len(recent_projects)} items")
                        for i, project in enumerate(
                            recent_projects[:3]
                        ):  # Show first 3
                            lines.append(f"    {i + 1}. {project}")
                        if len(recent_projects) > 3:
                            lines.append(f"    ... and {len(recent_projects) - 3} more")

                    if recent_files:
                        lines.append(f"  Recent files: {len(recent_files)} items")
                        for i, file_path in enumerate(recent_files[:3]):  # Show first 3
                            # Show just filename for brevity
                            from pathlib import Path

                            filename = Path(file_path).name
                            lines.append(f"    {i + 1}. {filename}")
                        if len(recent_files) > 3:
                            lines.append(f"    ... and {len(recent_files) - 3} more")

                    lines.append("")

                # Display configuration storage info
                lines.append("Configuration Storage:")
                lines.append(f"  Total settings keys: {len(self.get_all_keys())}")
                lines.append("  Settings format: QSettings (cross-platform)")

                # Add storage location info based on platform
                import platform

                system = platform.system()
                if system == "Darwin":  # macOS
                    lines.append("  Storage location: ~/Library/Preferences/")
                elif system == "Windows":
                    lines.append("  Storage location: Windows Registry")
                else:  # Linux
                    lines.append("  Storage location: ~/.config/")

                lines.append("")
                lines.append("Use --config-export <file> to backup configuration")
                lines.append("Use --config-import <file> to restore configuration")
                lines.append("Use --config-reset to restore all defaults")

                return "\n".join(lines)

            except Exception as e:
                self._logger.error(f"Error displaying configuration: {e}")
                return f"Error displaying configuration: {e}"

    def export_config(self, file_path: Union[str, Path]) -> None:
        """
        Export current configuration to a file.

        Args:
            file_path: Path where to save the configuration

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            try:
                import json

                # Collect all current settings
                config_dict = {}
                for key in self._settings.allKeys():
                    value = self._settings.value(key)
                    # Convert special types for JSON serialization
                    if isinstance(value, tuple) and len(value) == 2:
                        # Likely a QSize stored as tuple
                        config_dict[key] = {
                            "type": "size",
                            "width": value[0],
                            "height": value[1],
                        }
                    else:
                        config_dict[key] = value

                # Write to file
                path = Path(file_path)
                path.parent.mkdir(parents=True, exist_ok=True)

                with open(path, "w", encoding="utf-8") as f:
                    json.dump(config_dict, f, indent=2, default=str)

                self._logger.info(f"Configuration exported to {file_path}")

            except Exception as e:
                self._logger.error(f"Error exporting configuration: {e}")
                raise

    def import_config(self, file_path: Union[str, Path]) -> None:
        """
        Import configuration from a file.

        Args:
            file_path: Path to the configuration file

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            try:
                import json

                path = Path(file_path)
                if not path.exists():
                    raise FileNotFoundError(
                        f"Configuration file not found: {file_path}"
                    )

                with open(path, encoding="utf-8") as f:
                    config_dict = json.load(f)

                # Import settings
                for key, value in config_dict.items():
                    # Handle special types
                    if isinstance(value, dict) and value.get("type") == "size":
                        value = (value["width"], value["height"])

                    self._settings.setValue(key, value)

                self.save_settings()
                self._logger.info(f"Configuration imported from {file_path}")

            except Exception as e:
                self._logger.error(f"Error importing configuration: {e}")
                raise


# Global configuration instance
# This provides a singleton pattern for application-wide configuration access
_config_instance: Optional[AppConfig] = None
_config_lock = threading.Lock()


def get_config() -> AppConfig:
    """
    Get the global application configuration instance.

    This function provides thread-safe singleton access to the configuration.
    The configuration is initialized on first access.

    Returns:
        Global AppConfig instance

    Thread Safety:
        This function is thread-safe and uses double-checked locking pattern.
    """
    global _config_instance

    if _config_instance is None:
        with _config_lock:
            # Double-checked locking pattern
            if _config_instance is None:
                _config_instance = AppConfig()
                logger.debug("Global AppConfig instance created")

    return _config_instance
