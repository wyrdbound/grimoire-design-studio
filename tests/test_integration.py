"""
Integration tests for GRIMOIRE Design Studio application startup and signal handling.
"""

import subprocess
import sys
import time
from pathlib import Path


def test_application_starts_and_responds_to_sigterm():
    """Test that the application starts and responds to SIGTERM signal."""
    # Get the path to the virtual environment and grimoire-studio command
    venv_path = Path(__file__).parent.parent / ".venv"
    if sys.platform == "win32":
        grimoire_studio = venv_path / "Scripts" / "grimoire-studio.exe"
    else:
        grimoire_studio = venv_path / "bin" / "grimoire-studio"

    # Start the application process using the actual grimoire-studio command
    process = subprocess.Popen(
        [str(grimoire_studio), "--debug"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Give it a moment to start
    time.sleep(1.0)

    # Send SIGTERM to gracefully shut it down
    process.terminate()

    # Wait for it to finish (with timeout)
    stdout, stderr = process.communicate(timeout=10)

    # Check that it exited cleanly (0 or SIGTERM exit code)
    # SIGTERM typically results in exit code -15 or 143, but our handler should make it 0
    assert process.returncode in [0, -15, 143], (
        f"Process exited with code {process.returncode}"
    )
    assert "GRIMOIRE Design Studio starting" in stderr


def test_application_help_works():
    """Test that the --help flag works correctly."""
    venv_path = Path(__file__).parent.parent / ".venv"
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"

    # Test help flag
    process = subprocess.run(
        [str(python_path), "-m", "grimoire_studio.main", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert process.returncode == 0
    assert "GRIMOIRE Design Studio" in process.stdout
    assert "--debug" in process.stdout
    assert "--version" in process.stdout


def test_application_version_works():
    """Test that the --version flag works correctly."""
    venv_path = Path(__file__).parent.parent / ".venv"
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"

    # Test version flag
    process = subprocess.run(
        [str(python_path), "-m", "grimoire_studio.main", "--version"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert process.returncode == 0
    assert "1.0.0" in process.stdout
