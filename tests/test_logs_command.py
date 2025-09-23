"""
Tests for the --logs command line option.
"""

import subprocess
import sys
from pathlib import Path


def test_logs_flag_shows_information():
    """Test that --logs flag displays log information."""
    # Run the application with --logs flag
    result = subprocess.run(
        [sys.executable, "-m", "grimoire_studio.main", "--logs"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )

    # Should exit successfully
    assert result.returncode == 0

    # Should contain expected output
    output = result.stdout
    assert "[DIR] Log directory:" in output
    assert "[FILE] Log file:" in output
    assert "[INFO] Log directory exists:" in output
    assert "[INFO] Log file exists:" in output
    assert "grimoire-studio.log" in output

    # Should skip file manager opening during tests
    assert "[TEST] Skipping file manager open (detected test environment)" in output


def test_logs_flag_shows_help_option():
    """Test that --logs option appears in help."""
    result = subprocess.run(
        [sys.executable, "-m", "grimoire_studio.main", "--help"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )

    # Should exit successfully
    assert result.returncode == 0

    # Should mention the logs option
    assert "--logs" in result.stdout
    assert "Show log directory path and exit" in result.stdout
