"""
UI tests for OutputConsole component.

This module tests the user interface behavior of the OutputConsole class
including user interactions, tab switching, visual properties, and signal handling.
"""

import logging
from unittest.mock import patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTabWidget

from grimoire_studio.ui.components.output_console import OutputConsole


@pytest.mark.ui
class TestOutputConsoleUI:
    """Test OutputConsole user interface behavior."""

    @pytest.fixture
    def output_console(self, qtbot):
        """Create an OutputConsole instance for UI testing."""
        console = OutputConsole()
        qtbot.addWidget(console)
        console.show()
        return console

    def test_ui_initialization_display(self, output_console):
        """Test that UI components are properly displayed."""
        # Check tab widget exists and is visible
        assert output_console._tab_widget.isVisible()
        assert isinstance(output_console._tab_widget, QTabWidget)

        # Check all tabs are present
        assert output_console._tab_widget.count() == 3

        # Check tab names
        tab_names = []
        for i in range(output_console._tab_widget.count()):
            tab_names.append(output_console._tab_widget.tabText(i))

        assert "Validation" in tab_names
        assert "Execution" in tab_names
        assert "Logs" in tab_names

        # Check that text areas exist and are configured (visibility depends on active tab)
        assert output_console._validation_text is not None
        assert output_console._execution_text is not None
        assert output_console._logs_text is not None

        # Validation tab should be visible by default (active tab)
        assert output_console._validation_text.isVisible()

    def test_tab_switching_ui(self, output_console, qtbot):
        """Test tab switching through UI interaction."""
        # Start on validation tab (default)
        assert output_console._tab_widget.currentIndex() == 0

        # Click on execution tab
        execution_tab_index = 1
        output_console._tab_widget.setCurrentIndex(execution_tab_index)
        qtbot.wait(10)

        assert output_console._tab_widget.currentIndex() == execution_tab_index
        assert output_console.get_current_tab() == "execution"

        # Click on logs tab
        logs_tab_index = 2
        output_console._tab_widget.setCurrentIndex(logs_tab_index)
        qtbot.wait(10)

        assert output_console._tab_widget.currentIndex() == logs_tab_index
        assert output_console.get_current_tab() == "logs"

    def test_clear_buttons_functionality(self, output_console, qtbot):
        """Test that clear buttons work correctly."""
        # Add content to validation tab
        results = [{"level": "error", "message": "Test error"}]
        output_console.display_validation_results(results, auto_switch=False)

        # Verify content exists
        assert output_console._validation_text.toPlainText().strip() != ""

        # Click clear button
        qtbot.mouseClick(
            output_console._validation_clear_btn, Qt.MouseButton.LeftButton
        )
        qtbot.wait(10)

        # Verify content is cleared
        assert output_console._validation_text.toPlainText().strip() == ""

    def test_clear_buttons_for_all_tabs(self, output_console, qtbot):
        """Test clear buttons for all tabs."""
        # Add content to all tabs
        output_console.display_validation_results(
            [{"level": "info", "message": "Test"}], auto_switch=False
        )
        output_console.display_execution_output("Test execution", auto_switch=False)
        output_console.display_log_message("Test log", logging.INFO)

        # Test validation clear
        qtbot.mouseClick(
            output_console._validation_clear_btn, Qt.MouseButton.LeftButton
        )
        qtbot.wait(10)
        assert output_console._validation_text.toPlainText().strip() == ""

        # Test execution clear
        output_console.switch_to_execution_tab()
        qtbot.mouseClick(output_console._execution_clear_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(10)
        assert output_console._execution_text.toPlainText().strip() == ""

        # Test logs clear
        output_console.switch_to_logs_tab()
        qtbot.mouseClick(output_console._logs_clear_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(10)
        assert output_console._logs_text.toPlainText().strip() == ""

    def test_text_areas_read_only(self, output_console):
        """Test that text areas are read-only."""
        assert output_console._validation_text.isReadOnly()
        assert output_console._execution_text.isReadOnly()
        assert output_console._logs_text.isReadOnly()

    def test_text_areas_font(self, output_console):
        """Test that text areas use monospace font."""
        validation_font = output_console._validation_text.font()
        execution_font = output_console._execution_text.font()
        logs_font = output_console._logs_text.font()

        # All should use same console font
        assert validation_font.styleHint() == validation_font.StyleHint.Monospace
        assert execution_font.styleHint() == execution_font.StyleHint.Monospace
        assert logs_font.styleHint() == logs_font.StyleHint.Monospace

        # Check font size
        assert validation_font.pointSize() == 13
        assert execution_font.pointSize() == 13
        assert logs_font.pointSize() == 13

    def test_content_added_signal_emission(self, output_console, qtbot):
        """Test that content_added signal is emitted on UI operations."""
        # Test validation content signal
        with qtbot.waitSignal(output_console.content_added, timeout=1000) as blocker:
            output_console.display_validation_results(
                [{"level": "info", "message": "Test"}], auto_switch=False
            )

        assert blocker.args == ["validation"]

        # Test execution content signal
        with qtbot.waitSignal(output_console.content_added, timeout=1000) as blocker:
            output_console.display_execution_output("Test", auto_switch=False)

        assert blocker.args == ["execution"]

        # Test logs content signal
        with qtbot.waitSignal(output_console.content_added, timeout=1000) as blocker:
            output_console.display_log_message("Test", logging.INFO)

        assert blocker.args == ["logs"]

    def test_auto_switch_behavior(self, output_console, qtbot):
        """Test auto-switching behavior when content is added."""
        # Start on logs tab
        output_console.switch_to_logs_tab()
        assert output_console.get_current_tab() == "logs"

        # Add validation content with auto-switch
        output_console.display_validation_results(
            [{"level": "error", "message": "Test"}], auto_switch=True
        )
        qtbot.wait(10)

        assert output_console.get_current_tab() == "validation"

        # Add execution content with auto-switch
        output_console.display_execution_output("Test", auto_switch=True)
        qtbot.wait(10)

        assert output_console.get_current_tab() == "execution"

    def test_no_auto_switch_behavior(self, output_console, qtbot):
        """Test that auto-switch can be disabled."""
        # Start on logs tab
        output_console.switch_to_logs_tab()
        assert output_console.get_current_tab() == "logs"

        # Add content without auto-switch
        output_console.display_validation_results(
            [{"level": "error", "message": "Test"}], auto_switch=False
        )
        qtbot.wait(10)

        # Should still be on logs tab
        assert output_console.get_current_tab() == "logs"

        output_console.display_execution_output("Test", auto_switch=False)
        qtbot.wait(10)

        # Should still be on logs tab
        assert output_console.get_current_tab() == "logs"

    def test_validation_results_visual_formatting(self, output_console):
        """Test that validation results are visually formatted correctly."""
        results = [
            {"level": "error", "message": "Critical error"},
            {"level": "warning", "message": "Minor warning"},
            {"level": "success", "message": "Success message"},
            {"level": "info", "message": "Information"},
        ]

        output_console.display_validation_results(results, auto_switch=False)

        # Get the text content
        content = output_console._validation_text.toPlainText()

        # Check that all message types are present with their prefixes
        assert "❌ ERROR: Critical error" in content
        assert "⚠️  WARNING: Minor warning" in content
        assert "✅ SUCCESS: Success message" in content
        assert "ℹ️  INFO: Information" in content

        # Check for separator
        assert "-" * 50 in content

    def test_execution_output_timestamping(self, output_console):
        """Test that execution output includes timestamps."""
        with patch("grimoire_studio.ui.components.output_console.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "15:30:45"

            output_console.display_execution_output("Test message", auto_switch=False)
            content = output_console._execution_text.toPlainText()

            assert "[15:30:45]" in content
            assert "[INFO] Test message" in content

    def test_log_message_formatting(self, output_console):
        """Test that log messages are formatted correctly."""
        with patch("grimoire_studio.ui.components.output_console.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "10:15:20"

            output_console.display_log_message(
                "Test log", logging.WARNING, "test.module"
            )
            content = output_console._logs_text.toPlainText()

            assert "[10:15:20]" in content
            assert "WARNING test.module: Test log" in content

    def test_text_scrolling_to_bottom(self, output_console, qtbot):
        """Test that text areas scroll to bottom when new content is added."""
        # Add multiple lines of content to exceed visible area
        for i in range(50):
            output_console.display_validation_results(
                [{"level": "info", "message": f"Line {i}"}], auto_switch=False
            )

        qtbot.wait(100)  # Allow UI to update

        # Check that we're scrolled to the bottom (allow small tolerance for UI differences)
        validation_scrollbar = output_console._validation_text.verticalScrollBar()
        scroll_value = validation_scrollbar.value()
        scroll_max = validation_scrollbar.maximum()
        assert abs(scroll_value - scroll_max) <= 5  # Allow small tolerance

    def test_tab_change_signal_handling(self, output_console, qtbot):
        """Test that tab change signals are properly handled."""
        # Track tab changes using the existing signal
        tab_changes = []

        def track_tab_change(index):
            tab_changes.append(index)

        # Connect to the actual signal
        output_console._tab_widget.currentChanged.connect(track_tab_change)

        # Change tabs and check signal is emitted
        output_console._tab_widget.setCurrentIndex(1)
        qtbot.wait(10)

        output_console._tab_widget.setCurrentIndex(2)
        qtbot.wait(10)

        # Should have received tab change signals
        assert len(tab_changes) >= 1  # At least one signal should have fired

    def test_widget_styling(self, output_console):
        """Test that widgets have proper styling applied."""
        # Check that text areas have styling
        validation_style = output_console._validation_text.styleSheet()
        execution_style = output_console._execution_text.styleSheet()
        logs_style = output_console._logs_text.styleSheet()

        # All should have some styling
        assert validation_style.strip() != ""
        assert execution_style.strip() != ""
        assert logs_style.strip() != ""

        # Check for expected style properties
        assert "background-color" in validation_style
        assert "border" in validation_style
        assert "padding" in validation_style

    def test_clear_button_positions(self, output_console):
        """Test that clear buttons are positioned correctly."""
        # All clear buttons should exist (visibility depends on active tab)
        assert output_console._validation_clear_btn is not None
        assert output_console._execution_clear_btn is not None
        assert output_console._logs_clear_btn is not None

        # Validation clear button should be visible (active tab)
        assert output_console._validation_clear_btn.isVisible()

        # Buttons should have correct text
        assert output_console._validation_clear_btn.text() == "Clear"
        assert output_console._execution_clear_btn.text() == "Clear"
        assert output_console._logs_clear_btn.text() == "Clear"

        # Test visibility when switching tabs
        output_console.switch_to_execution_tab()
        assert output_console._execution_clear_btn.isVisible()

        output_console.switch_to_logs_tab()
        assert output_console._logs_clear_btn.isVisible()

    def test_console_resize_behavior(self, output_console, qtbot):
        """Test that console handles resizing correctly."""
        # Set initial size
        output_console.resize(400, 300)
        qtbot.wait(10)

        # Verify initial size
        assert output_console.size().width() == 400
        assert output_console.size().height() == 300

        # Resize larger
        output_console.resize(800, 600)
        qtbot.wait(10)

        # Components should still be visible and functional
        assert output_console._tab_widget.isVisible()
        assert output_console._validation_text.isVisible()

        # Test functionality still works after resize
        output_console.display_validation_results(
            [{"level": "info", "message": "Test after resize"}], auto_switch=False
        )
        content = output_console._validation_text.toPlainText()
        assert "Test after resize" in content

    def test_multiple_rapid_content_additions(self, output_console, qtbot):
        """Test handling of multiple rapid content additions."""
        # Add content rapidly to test UI responsiveness
        for i in range(20):
            output_console.display_validation_results(
                [{"level": "info", "message": f"Rapid message {i}"}], auto_switch=False
            )
            if i % 5 == 0:
                qtbot.wait(1)  # Brief pause every 5 messages

        # All messages should be present
        content = output_console._validation_text.toPlainText()
        assert "Rapid message 0" in content
        assert "Rapid message 19" in content

        # UI should still be responsive
        assert output_console._tab_widget.isVisible()
        assert output_console.get_current_tab() == "validation"

    def test_content_persistence_across_tab_switches(self, output_console, qtbot):
        """Test that content persists when switching between tabs."""
        # Add content to validation tab
        validation_content = [{"level": "error", "message": "Validation error"}]
        output_console.display_validation_results(validation_content, auto_switch=False)

        # Switch to execution and add content
        output_console.switch_to_execution_tab()
        output_console.display_execution_output("Execution message", auto_switch=False)

        # Switch to logs and add content
        output_console.switch_to_logs_tab()
        output_console.display_log_message("Log message", logging.INFO)

        # Switch back to validation - content should still be there
        output_console.switch_to_validation_tab()
        validation_text = output_console._validation_text.toPlainText()
        assert "Validation error" in validation_text

        # Switch to execution - content should still be there
        output_console.switch_to_execution_tab()
        execution_text = output_console._execution_text.toPlainText()
        assert "Execution message" in execution_text

        # Switch to logs - content should still be there
        output_console.switch_to_logs_tab()
        logs_text = output_console._logs_text.toPlainText()
        assert "Log message" in logs_text
