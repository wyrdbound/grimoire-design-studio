"""
Test the main window implementation.

These tests require PyQt6 and are marked as UI tests.
On Windows, these tests may not run properly in headless CI environments.
"""

import os
import platform

import pytest
from PyQt6.QtWidgets import QApplication

from grimoire_studio.ui.main_window import MainWindow

# Skip UI tests on Windows in CI environments to avoid headless PyQt6 issues
SKIP_UI_ON_WINDOWS_CI = platform.system() == "Windows" and (
    bool(os.environ.get("CI")) or bool(os.environ.get("GITHUB_ACTIONS"))
)

pytestmark = pytest.mark.ui  # Mark all tests in this module as UI tests


@pytest.mark.skipif(SKIP_UI_ON_WINDOWS_CI, reason="UI tests don't work in Windows CI")
def test_main_window_creation(qapp: QApplication) -> None:
    """Test that MainWindow can be created without errors."""
    window = MainWindow()
    assert window is not None
    assert window.windowTitle() == "GRIMOIRE Design Studio v1.0.0"


@pytest.mark.skipif(SKIP_UI_ON_WINDOWS_CI, reason="UI tests don't work in Windows CI")
def test_main_window_actions_exist(qapp: QApplication) -> None:
    """Test that all required actions are created."""
    window = MainWindow()

    # Check file actions
    assert hasattr(window, "_action_new_project")
    assert hasattr(window, "_action_open_project")
    assert hasattr(window, "_action_save")
    assert hasattr(window, "_action_save_all")
    assert hasattr(window, "_action_exit")

    # Check project actions
    assert hasattr(window, "_action_validate")
    assert hasattr(window, "_action_build")

    # Check flow actions
    assert hasattr(window, "_action_run_flow")
    assert hasattr(window, "_action_test_flow")

    # Check help actions
    assert hasattr(window, "_action_about")


@pytest.mark.skipif(SKIP_UI_ON_WINDOWS_CI, reason="UI tests don't work in Windows CI")
def test_main_window_status_methods(qapp: QApplication) -> None:
    """Test that status bar methods work correctly."""
    window = MainWindow()

    # Test status setting
    window.set_status("Test status")
    assert window._status_label.text() == "Test status"

    # Test file setting
    window.set_current_file("/path/to/test.yaml")
    assert "test.yaml" in window._file_label.text()

    window.set_current_file(None)
    assert window._file_label.text() == "No file open"

    # Test validation status
    window.set_validation_status("Valid")
    assert "Valid" in window._validation_label.text()


@pytest.mark.skipif(SKIP_UI_ON_WINDOWS_CI, reason="UI tests don't work in Windows CI")
def test_main_window_action_enabling(qapp: QApplication) -> None:
    """Test that action enabling/disabling works correctly."""
    window = MainWindow()

    # Test project actions
    window.enable_project_actions(True)
    assert window._action_validate.isEnabled()
    assert window._action_build.isEnabled()
    assert window._action_run_flow.isEnabled()
    assert window._action_test_flow.isEnabled()

    window.enable_project_actions(False)
    assert not window._action_validate.isEnabled()
    assert not window._action_build.isEnabled()
    assert not window._action_run_flow.isEnabled()
    assert not window._action_test_flow.isEnabled()

    # Test file actions
    window.enable_file_actions(True)
    assert window._action_save.isEnabled()
    assert window._action_save_all.isEnabled()

    window.enable_file_actions(False)
    assert not window._action_save.isEnabled()
    assert not window._action_save_all.isEnabled()


@pytest.mark.skipif(SKIP_UI_ON_WINDOWS_CI, reason="UI tests don't work in Windows CI")
def test_main_window_signals(qapp: QApplication) -> None:
    """Test that window signals are properly defined."""
    window = MainWindow()

    # Check signals exist
    assert hasattr(window, "project_opened")
    assert hasattr(window, "file_opened")
    assert hasattr(window, "validation_requested")


@pytest.mark.skipif(SKIP_UI_ON_WINDOWS_CI, reason="UI tests don't work in Windows CI")
def test_main_window_layout(qapp: QApplication) -> None:
    """Test that the main window layout is set up correctly."""
    window = MainWindow()

    # Check that central widget is a splitter
    central_widget = window.centralWidget()
    assert central_widget is not None

    # Check that main splitter has three widgets
    main_splitter = window._main_splitter
    assert main_splitter.count() == 3

    # Check that editor splitter has two widgets (editor + output)
    editor_splitter = window._editor_splitter
    assert editor_splitter.count() == 2
