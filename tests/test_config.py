"""
Test suite for configuration management functionality.

This module tests the AppConfig class and related configuration functionality
including loading, saving, defaults, thread safety, and error handling.
"""

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QSize

from grimoire_studio.core.config import AppConfig, get_config


class TestAppConfig(unittest.TestCase):
    """Test cases for AppConfig class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Use temporary settings for tests
        with patch("grimoire_studio.core.config.QSettings") as mock_settings:
            self.mock_qsettings = MagicMock()
            mock_settings.return_value = self.mock_qsettings
            self.config = AppConfig()

    def test_initialization(self) -> None:
        """Test AppConfig initialization."""
        self.assertIsNotNone(self.config)
        self.assertIsNotNone(self.config._defaults)
        self.assertIn("window/size", self.config._defaults)
        self.assertIn("recent/projects", self.config._defaults)

    def test_get_with_default(self) -> None:
        """Test getting configuration values with defaults."""

        # Mock QSettings to return the default we expect
        def mock_value(key, default=None):
            if key == "window/size":
                return default  # Return the provided default
            return None

        self.mock_qsettings.value.side_effect = mock_value

        # Should return built-in default
        size = self.config.get("window/size")
        self.assertIsInstance(size, QSize)
        self.assertEqual(size.width(), 1200)
        self.assertEqual(size.height(), 800)

    def test_get_with_custom_default(self) -> None:
        """Test getting configuration values with custom defaults."""

        # Mock QSettings to return the default we provide
        def mock_value(key, default=None):
            return default  # Return the provided default

        self.mock_qsettings.value.side_effect = mock_value

        # Should return custom default
        value = self.config.get("nonexistent/key", "custom_default")
        self.assertEqual(value, "custom_default")

    def test_set_and_get(self) -> None:
        """Test setting and getting configuration values."""
        test_value = "test_value"
        test_key = "test/key"

        # Mock QSettings to return our test value
        self.mock_qsettings.value.return_value = test_value

        # Set value
        self.config.set(test_key, test_value)

        # Verify QSettings.setValue was called
        self.mock_qsettings.setValue.assert_called_with(test_key, test_value)

        # Get value
        result = self.config.get(test_key)
        self.assertEqual(result, test_value)

    def test_qsize_handling(self) -> None:
        """Test QSize type handling in set/get operations."""
        test_size = QSize(800, 600)

        # Set QSize
        self.config.set("test/size", test_size)

        # Should store as tuple
        self.mock_qsettings.setValue.assert_called_with("test/size", (800, 600))

        # Mock getting tuple back
        self.mock_qsettings.value.return_value = (800, 600)

        # Get should convert back to QSize
        result = self.config.get("window/size")
        self.assertIsInstance(result, QSize)
        self.assertEqual(result.width(), 800)
        self.assertEqual(result.height(), 600)

    def test_recent_projects_empty(self) -> None:
        """Test getting recent projects when none exist."""
        self.mock_qsettings.value.return_value = []

        projects = self.config.get_recent_projects()
        self.assertEqual(projects, [])

    def test_add_recent_project(self) -> None:
        """Test adding projects to recent list."""

        # Mock QSettings to return appropriate values
        def mock_value(key, default=None):
            if key == "recent/projects":
                return []
            elif key == "recent/max_items":
                return 10  # Return integer, not None
            return default

        self.mock_qsettings.value.side_effect = mock_value

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            self.config.add_recent_project(str(project_path))

            # Should call setValue with list containing our project
            expected_call_args = self.mock_qsettings.setValue.call_args
            self.assertEqual(expected_call_args[0][0], "recent/projects")
            self.assertIn(str(project_path), expected_call_args[0][1])

    def test_recent_projects_validation(self) -> None:
        """Test that invalid project paths are filtered out."""
        # Mock QSettings to return list with invalid paths
        invalid_paths = ["/nonexistent/path1", "/nonexistent/path2"]
        self.mock_qsettings.value.return_value = invalid_paths

        projects = self.config.get_recent_projects()

        # Should return empty list since paths don't exist
        self.assertEqual(projects, [])

        # Should have called setValue to update the stored list
        self.mock_qsettings.setValue.assert_called_with("recent/projects", [])

    def test_recent_files_functionality(self) -> None:
        """Test recent files functionality."""

        # Mock QSettings to return appropriate values
        def mock_value(key, default=None):
            if key == "recent/files":
                return []
            elif key == "recent/max_items":
                return 10  # Return integer, not None
            return default

        self.mock_qsettings.value.side_effect = mock_value

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write("test content")
            temp_path = temp_file.name

        try:
            self.config.add_recent_file(temp_path)

            # Should call setValue with list containing our file
            expected_call_args = self.mock_qsettings.setValue.call_args
            self.assertEqual(expected_call_args[0][0], "recent/files")
            self.assertIn(temp_path, expected_call_args[0][1])
        finally:
            Path(temp_path).unlink()

    def test_save_settings(self) -> None:
        """Test explicit settings save."""
        self.config.save_settings()
        self.mock_qsettings.sync.assert_called_once()

    def test_load_settings(self) -> None:
        """Test settings loading."""
        self.config.load_settings()
        self.mock_qsettings.sync.assert_called_once()

    def test_reset_to_defaults(self) -> None:
        """Test resetting configuration to defaults."""
        # Test resetting all settings
        self.config.reset_to_defaults()
        self.mock_qsettings.clear.assert_called_once()

        # Test resetting with prefix
        self.mock_qsettings.reset_mock()
        self.mock_qsettings.allKeys.return_value = [
            "window/size",
            "window/pos",
            "editor/font",
        ]

        self.config.reset_to_defaults(prefix="window/")

        # Should remove keys with window/ prefix
        remove_calls = self.mock_qsettings.remove.call_args_list
        self.assertEqual(len(remove_calls), 2)  # window/size and window/pos

    def test_get_all_keys(self) -> None:
        """Test getting all configuration keys."""
        expected_keys = ["key1", "key2", "key3"]
        self.mock_qsettings.allKeys.return_value = expected_keys

        keys = self.config.get_all_keys()
        self.assertEqual(keys, expected_keys)

    def test_export_config(self) -> None:
        """Test configuration export."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        ) as temp_file:
            export_path = temp_file.name

        try:
            # Mock configuration data
            self.mock_qsettings.allKeys.return_value = ["test/key1", "test/key2"]
            self.mock_qsettings.value.side_effect = lambda key: f"value_for_{key}"

            self.config.export_config(export_path)

            # Verify file was created and contains expected data
            self.assertTrue(Path(export_path).exists())

            with open(export_path) as f:
                exported_data = json.load(f)

            self.assertIn("test/key1", exported_data)
            self.assertIn("test/key2", exported_data)
        finally:
            Path(export_path).unlink(missing_ok=True)

    def test_import_config(self) -> None:
        """Test configuration import."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        ) as temp_file:
            config_data = {
                "test/key1": "imported_value1",
                "test/key2": "imported_value2",
                "test/size": {"type": "size", "width": 1024, "height": 768},
            }
            json.dump(config_data, temp_file, indent=2)
            import_path = temp_file.name

        try:
            self.config.import_config(import_path)

            # Verify setValue was called for each imported key
            set_calls = self.mock_qsettings.setValue.call_args_list
            self.assertTrue(len(set_calls) >= 3)

            # Check that size was converted properly
            size_call = None
            for call in set_calls:
                if call[0][0] == "test/size":
                    size_call = call
                    break

            if size_call is not None:
                self.assertEqual(size_call[0][1], (1024, 768))
        finally:
            Path(import_path).unlink()

    def test_thread_safety(self) -> None:
        """Test thread safety of configuration operations."""
        results = []
        errors = []

        def worker_thread(thread_id: int) -> None:
            try:
                # Simulate concurrent access
                for i in range(10):
                    key = f"thread_{thread_id}/item_{i}"
                    value = f"value_{thread_id}_{i}"

                    self.config.set(key, value)
                    retrieved = self.config.get(
                        key, value
                    )  # Use value as default since mock won't return it
                    results.append((thread_id, i, retrieved))

                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, e))

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that no errors occurred
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")

        # Check that all operations completed
        self.assertEqual(len(results), 50)  # 5 threads * 10 operations each


class TestConfigurationIntegration(unittest.TestCase):
    """Integration tests for configuration functionality."""

    def test_get_config_singleton(self) -> None:
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()

        self.assertIs(config1, config2)

    def test_get_config_thread_safety(self) -> None:
        """Test thread safety of get_config function."""
        instances = []

        def get_instance() -> None:
            instances.append(get_config())

        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_instance)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All instances should be the same
        first_instance = instances[0]
        for instance in instances:
            self.assertIs(instance, first_instance)


class TestConfigurationErrorHandling(unittest.TestCase):
    """Test error handling in configuration system."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        with patch("grimoire_studio.core.config.QSettings") as mock_settings:
            self.mock_qsettings = MagicMock()
            mock_settings.return_value = self.mock_qsettings
            self.config = AppConfig()

    def test_get_error_handling(self) -> None:
        """Test error handling in get method."""
        # Mock QSettings to raise exception
        self.mock_qsettings.value.side_effect = Exception("Test error")

        # Should return default without raising exception
        result = self.config.get("test/key", "default_value")
        self.assertEqual(result, "default_value")

    def test_set_error_handling(self) -> None:
        """Test error handling in set method."""
        # Mock QSettings to raise exception
        self.mock_qsettings.setValue.side_effect = RuntimeError("Test error")

        # Should raise the exception
        with self.assertRaises(RuntimeError):
            self.config.set("test/key", "test_value")

    def test_save_settings_error_handling(self) -> None:
        """Test error handling in save_settings."""
        self.mock_qsettings.sync.side_effect = OSError("Test error")

        with self.assertRaises(OSError):
            self.config.save_settings()

    def test_import_nonexistent_file(self) -> None:
        """Test importing from nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            self.config.import_config("/nonexistent/file.json")

    def test_export_invalid_path(self) -> None:
        """Test exporting to invalid path."""
        import os

        # Use a path with invalid characters that should fail on all platforms
        if os.name == "nt":  # Windows
            # Use reserved device names that can't be files
            invalid_path = "CON/invalid/config.json"
        else:  # Unix-like systems
            # Use null bytes which are invalid in filenames
            invalid_path = "/tmp/\x00invalid\x00/config.json"

        with self.assertRaises(
            (PermissionError, OSError, FileNotFoundError, ValueError)
        ):
            self.config.export_config(invalid_path)


if __name__ == "__main__":
    unittest.main()
