"""
Integration tests for GRIMOIRE Design Studio application startup and signal handling.
"""

import os
import shutil
import subprocess
import sys
import time


def test_application_starts_and_can_be_terminated():
    """Test that the application starts and can be terminated."""
    # Find grimoire-studio command in PATH (works in both local .venv and CI)
    grimoire_studio = shutil.which("grimoire-studio")
    assert grimoire_studio is not None, "grimoire-studio command not found in PATH"

    # Set appropriate environment for headless operation
    env = dict(os.environ)
    # Use existing QT_QPA_PLATFORM if set (for CI), otherwise default to minimal
    if "QT_QPA_PLATFORM" not in env:
        env["QT_QPA_PLATFORM"] = "minimal"

    # Start the application process using the grimoire-studio command
    process = subprocess.Popen(
        [grimoire_studio, "--debug"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    # Give it a moment to start up properly
    time.sleep(1.5)

    # Check if process started successfully
    if process.poll() is not None:
        # Process already exited, get output
        stdout, stderr = process.communicate()
        # If it exited with code 0, that's actually fine for our test
        if process.returncode == 0:
            assert "GRIMOIRE Design Studio starting" in stderr
            return
        # Otherwise it's an error
        raise AssertionError(
            f"Process exited early with code {process.returncode}. "
            f"Stdout: {stdout}, Stderr: {stderr}"
        )

    # Process is still running, try to terminate it gracefully
    process.terminate()

    # Wait for it to finish with reasonable timeout
    try:
        stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        # If graceful termination doesn't work, force kill
        process.kill()
        stdout, stderr = process.communicate()

    # Check that the application at least started properly
    assert "GRIMOIRE Design Studio starting" in stderr, (
        f"Expected startup message not found. Stderr: {stderr}"
    )

    # Accept various exit codes as valid
    # 0 = clean exit, -15/143 = SIGTERM, -9/137 = SIGKILL
    valid_codes = [0, -15, 143, -9, 137]
    assert process.returncode in valid_codes, (
        f"Process exited with unexpected code {process.returncode}. "
        f"Stdout: {stdout}, Stderr: {stderr}"
    )


def test_application_help_works():
    """Test that the --help flag works correctly."""
    # Use the current Python executable (works in both local .venv and CI)
    python_path = sys.executable

    # Test help flag
    process = subprocess.run(
        [python_path, "-m", "grimoire_studio.main", "--help"],
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
    # Use the current Python executable (works in both local .venv and CI)
    python_path = sys.executable

    # Test version flag
    process = subprocess.run(
        [python_path, "-m", "grimoire_studio.main", "--version"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert process.returncode == 0
    assert "1.0.0" in process.stdout
