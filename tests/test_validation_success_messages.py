"""Test validation success messages in output console."""

import sys
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_studio.ui.components.output_console import OutputConsole


class TestValidationSuccessMessages:
    """Test cases for validation success messages in output console."""

    @pytest.fixture
    def output_console(self, qtbot):
        """Create an OutputConsole instance for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        console = OutputConsole()
        qtbot.addWidget(console)
        return console

    def test_empty_validation_results_shows_success_message(self, output_console):
        """Test that empty validation results show a success message."""
        # Display empty validation results
        output_console.display_validation_results([])

        # Get the content of the validation tab
        content = output_console._validation_text.toPlainText()

        # Should contain the success message
        assert "✅ No validation issues found. All files are valid!" in content
        assert "Validation Results:" in content

    def test_info_only_results_shows_success_message(self, output_console):
        """Test that results with only info messages show success."""
        results = [
            {"level": "info", "message": "File processed successfully"},
            {"level": "success", "message": "Component validated"},
        ]

        output_console.display_validation_results(results)
        content = output_console._validation_text.toPlainText()

        # Should contain the success message for no failures
        assert (
            "✅ Validation completed successfully. No errors or warnings found!"
            in content
        )
        # Should also contain the individual info/success messages
        assert "ℹ️  INFO: File processed successfully" in content
        assert "✅ SUCCESS: Component validated" in content

    def test_results_with_warnings_does_not_show_success_message(self, output_console):
        """Test that results with warnings don't show the success message."""
        results = [
            {"level": "warning", "message": "Deprecated feature used"},
            {"level": "info", "message": "File processed"},
        ]

        output_console.display_validation_results(results)
        content = output_console._validation_text.toPlainText()

        # Should NOT contain success message
        assert "✅ No validation issues found" not in content
        assert "✅ Validation completed successfully" not in content
        # Should contain the warning
        assert "⚠️  WARNING: Deprecated feature used" in content

    def test_results_with_errors_does_not_show_success_message(self, output_console):
        """Test that results with errors don't show the success message."""
        results = [{"level": "error", "message": "Syntax error in file"}]

        output_console.display_validation_results(results)
        content = output_console._validation_text.toPlainText()

        # Should NOT contain success message
        assert "✅ No validation issues found" not in content
        assert "✅ Validation completed successfully" not in content
        # Should contain the error
        assert "❌ ERROR: Syntax error in file" in content

    def test_mixed_results_with_failures_does_not_show_success_message(
        self, output_console
    ):
        """Test that mixed results with any failures don't show success message."""
        results = [
            {"level": "info", "message": "File loaded"},
            {"level": "warning", "message": "Minor issue found"},
            {"level": "success", "message": "Component valid"},
        ]

        output_console.display_validation_results(results)
        content = output_console._validation_text.toPlainText()

        # Should NOT contain success message due to warning
        assert "✅ No validation issues found" not in content
        assert "✅ Validation completed successfully" not in content
        # Should contain all individual messages
        assert "ℹ️  INFO: File loaded" in content
        assert "⚠️  WARNING: Minor issue found" in content
        assert "✅ SUCCESS: Component valid" in content

    def test_validation_results_header_always_present(self, output_console):
        """Test that validation results header is always shown."""
        # Test with empty results
        output_console.display_validation_results([])
        content = output_console._validation_text.toPlainText()
        assert "Validation Results:" in content

        # Clear and test with results
        output_console._validation_text.clear()
        results = [{"level": "info", "message": "Test"}]
        output_console.display_validation_results(results)
        content = output_console._validation_text.toPlainText()
        assert "Validation Results:" in content

    def test_separator_line_always_added(self, output_console):
        """Test that separator line is always added after results."""
        # Test with empty results
        output_console.display_validation_results([])
        content = output_console._validation_text.toPlainText()
        assert "-" * 50 in content

        # Clear and test with results
        output_console._validation_text.clear()
        results = [{"level": "error", "message": "Test error"}]
        output_console.display_validation_results(results)
        content = output_console._validation_text.toPlainText()
        assert "-" * 50 in content
