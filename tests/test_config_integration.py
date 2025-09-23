"""
Test suite for configuration integration in main.py.

This module tests the command-line argument handling and configuration
integration in the main application entry point.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from grimoire_studio.main import parse_arguments


class TestMainConfigIntegration(unittest.TestCase):
    """Test configuration integration in main.py."""

    def test_parse_arguments_config_options(self) -> None:
        """Test parsing of configuration-related command line arguments."""
        # Test config reset
        with patch("sys.argv", ["grimoire_studio", "--config-reset"]):
            args = parse_arguments()
            self.assertTrue(args.config_reset)

        # Test config export
        with patch("sys.argv", ["grimoire_studio", "--config-export", "config.json"]):
            args = parse_arguments()
            self.assertEqual(args.config_export, "config.json")

        # Test config import
        with patch("sys.argv", ["grimoire_studio", "--config-import", "config.json"]):
            args = parse_arguments()
            self.assertEqual(args.config_import, "config.json")

        # Test no restore session
        with patch("sys.argv", ["grimoire_studio", "--no-restore-session"]):
            args = parse_arguments()
            self.assertTrue(args.no_restore_session)

        # Test config show
        with patch("sys.argv", ["grimoire_studio", "--config-show"]):
            args = parse_arguments()
            self.assertTrue(args.config_show)

    def test_config_reset_command(self) -> None:
        """Test --config-reset command execution."""
        # Create a test script to run the config reset command
        result = subprocess.run(
            [sys.executable, "-m", "grimoire_studio.main", "--config-reset"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Configuration reset to defaults", result.stdout)

    def test_config_export_command(self) -> None:
        """Test --config-export command execution."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        ) as temp_file:
            export_path = temp_file.name

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "grimoire_studio.main",
                    "--config-export",
                    export_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn(f"Configuration exported to {export_path}", result.stdout)

            # Verify file was created
            self.assertTrue(Path(export_path).exists())

            # Verify it's valid JSON
            with open(export_path) as f:
                config_data = json.load(f)
            self.assertIsInstance(config_data, dict)
        finally:
            Path(export_path).unlink(missing_ok=True)

    def test_config_import_command(self) -> None:
        """Test --config-import command execution."""
        # Create a test configuration file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        ) as temp_file:
            test_config = {"test/key": "test_value", "app/theme": "dark"}
            json.dump(test_config, temp_file, indent=2)
            import_path = temp_file.name

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "grimoire_studio.main",
                    "--config-import",
                    import_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn(f"Configuration imported from {import_path}", result.stdout)
        finally:
            Path(import_path).unlink()

    def test_invalid_config_file_import(self) -> None:
        """Test importing from invalid configuration file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "grimoire_studio.main",
                "--config-import",
                "/nonexistent/config.json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Failed to import configuration", result.stderr)

    def test_config_show_command(self) -> None:
        """Test --config-show command execution."""
        result = subprocess.run(
            [sys.executable, "-m", "grimoire_studio.main", "--config-show"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("GRIMOIRE Design Studio Configuration", result.stdout)
        self.assertIn("Window & UI:", result.stdout)
        self.assertIn("Editor:", result.stdout)
        self.assertIn("Configuration Storage:", result.stdout)

    def test_debug_mode_config_override(self) -> None:
        """Test that --debug flag overrides configuration."""
        # This test would need to be run in a subprocess since we can't easily
        # mock the configuration in the main function. For now, we'll test
        # the argument parsing logic.
        with patch("sys.argv", ["grimoire_studio", "--debug"]):
            args = parse_arguments()
            self.assertTrue(args.debug)

    @patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "test"})
    def test_headless_mode_with_config(self) -> None:
        """Test that configuration works in headless mode."""
        # Mock the configuration to avoid actual QSettings
        with patch("grimoire_studio.main.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.get.return_value = "INFO"
            mock_config.get_all_keys.return_value = ["test/key"]
            mock_config.get_recent_projects.return_value = []
            mock_get_config.return_value = mock_config

            result = subprocess.run(
                [sys.executable, "-m", "grimoire_studio.main"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Should run successfully in headless mode
            self.assertEqual(result.returncode, 0)
            self.assertIn("Running in headless mode", result.stdout)


class TestConfigurationCommandLine(unittest.TestCase):
    """Test command line configuration handling."""

    def test_argument_combinations(self) -> None:
        """Test various argument combinations."""
        # Test debug with config import
        with patch(
            "sys.argv", ["grimoire_studio", "--debug", "--config-import", "config.json"]
        ):
            args = parse_arguments()
            self.assertTrue(args.debug)
            self.assertEqual(args.config_import, "config.json")

        # Test multiple config operations (should be mutually exclusive in practice)
        with patch(
            "sys.argv",
            [
                "grimoire_studio",
                "--config-export",
                "export.json",
                "--config-import",
                "import.json",
            ],
        ):
            args = parse_arguments()
            self.assertEqual(args.config_export, "export.json")
            self.assertEqual(args.config_import, "import.json")

    def test_help_includes_config_options(self) -> None:
        """Test that help output includes configuration options."""
        result = subprocess.run(
            [sys.executable, "-m", "grimoire_studio.main", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0)
        help_output = result.stdout

        # Check for configuration options in help
        self.assertIn("--config-reset", help_output)
        self.assertIn("--config-export", help_output)
        self.assertIn("--config-import", help_output)
        self.assertIn("--no-restore-session", help_output)
        self.assertIn("--config-show", help_output)


if __name__ == "__main__":
    unittest.main()
