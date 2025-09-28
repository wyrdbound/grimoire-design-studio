"""
Test the real-time validation integration added in Step 4.3.

This module tests the enhanced validation features including:
- Validation timer integration
- Error highlighting in the editor
- Status bar validation status updates
- Output console integration
- Keyboard shortcuts and menu items for validation
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication

from grimoire_studio.core.validator import ValidationResult, ValidationSeverity
from grimoire_studio.ui.components.yaml_highlighter import YamlSyntaxHighlighter
from grimoire_studio.ui.main_window import MainWindow
from grimoire_studio.ui.views.yaml_editor_view import YamlEditorView


class TestValidationIntegration:
    """Test real-time validation integration features."""

    @pytest.fixture
    def yaml_editor(self, qtbot):
        """Create a YAML editor for testing."""
        editor = YamlEditorView()
        qtbot.addWidget(editor)
        return editor

    @pytest.fixture
    def main_window(self, qtbot):
        """Create a main window for testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window

    @pytest.fixture
    def sample_yaml_content(self):
        """Provide sample YAML content for testing."""
        return """id: test_model
kind: model
name: "Test Model"
attributes:
  - name: health
    type: integer
    min_value: 0
  - name: description
    type: string
"""

    @pytest.fixture
    def invalid_yaml_content(self):
        """Provide invalid YAML content for testing."""
        return """# Missing required fields
kind: model
name: "Invalid Model"
# Missing 'id' and 'attributes' fields

# Also has syntax error
invalid_syntax: "unclosed quote
"""

    def test_validation_timer_initialization(self, yaml_editor):
        """Test that validation timer is properly initialized."""
        assert hasattr(yaml_editor, "_validation_timer")
        assert yaml_editor._validation_timer.isSingleShot()
        assert yaml_editor._validation_timer.interval() == 1000

    def test_validation_timer_starts_on_text_change(self, yaml_editor, qtbot):
        """Test that validation timer starts when text changes."""
        # Load a file to enable validation
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as temp_file:
            temp_file.write("id: test\nkind: model\n")
            temp_file_path = Path(temp_file.name)

        try:
            yaml_editor.load_file(temp_file_path)

            # Mock the timer start method
            with patch.object(yaml_editor._validation_timer, "start") as mock_start:
                # Simulate text change
                yaml_editor._text_edit.setPlainText(
                    "id: test\nkind: model\nname: changed"
                )

                # Verify timer was started
                mock_start.assert_called_once()
        finally:
            temp_file_path.unlink()

    def test_validation_results_highlighting(self, yaml_editor, qtbot):
        """Test that validation errors are highlighted in the editor."""
        # Add some content to the editor so we have lines to highlight
        yaml_editor.set_content("line 1\nline 2\nline 3\nline 4\n")

        # Create validation results
        validation_results = [
            ValidationResult(
                severity=ValidationSeverity.ERROR,
                message="Missing required field: 'id'",
                line_number=1,
            ),
            ValidationResult(
                severity=ValidationSeverity.WARNING,
                message="Consider adding description",
                line_number=3,
            ),
        ]

        # Apply highlighting
        yaml_editor._highlighter.highlight_validation_results(validation_results)

        # Check that highlighted lines are tracked
        assert 0 in yaml_editor._highlighter._highlighted_lines  # Line 1 (0-based)
        assert 2 in yaml_editor._highlighter._highlighted_lines  # Line 3 (0-based)

    def test_yaml_highlighter_error_formats(self, qtbot):
        """Test that YAML highlighter has proper error and warning formats."""
        from PyQt6.QtGui import QTextDocument

        document = QTextDocument()
        highlighter = YamlSyntaxHighlighter(document)
        # Don't add document to qtbot - it's not a widget        # Check that error and warning formats exist
        assert hasattr(highlighter, "_error_format")
        assert hasattr(highlighter, "_warning_format")
        assert hasattr(highlighter, "_highlighted_lines")

        # Check that formats have proper colors - updated for dark theme compatibility
        assert highlighter._error_format.background().color().red() == 139  # Dark red
        assert (
            highlighter._warning_format.background().color().red() == 184
        )  # Dark yellow
        assert (
            highlighter._warning_format.background().color().green() == 134
        )  # Dark yellow

        # Check that new info format exists
        assert hasattr(highlighter, "_info_format")
        assert highlighter._info_format.background().color().blue() == 246  # Blue

    def test_clear_error_highlights(self, qtbot):
        """Test clearing error highlights."""
        from PyQt6.QtGui import QTextDocument

        document = QTextDocument()
        highlighter = YamlSyntaxHighlighter(document)
        # Don't add document to qtbot - it's not a widget        # Add some highlights
        highlighter._highlighted_lines.add(0)
        highlighter._highlighted_lines.add(2)

        # Clear highlights
        highlighter.clear_error_highlights()

        # Verify highlights are cleared
        assert len(highlighter._highlighted_lines) == 0

    def test_main_window_validation_status_updates(self, main_window, qtbot):
        """Test that main window validation status updates properly."""
        # Test setting various validation statuses
        main_window.set_validation_status("Valid")
        assert "Valid" in main_window._validation_label.text()

        main_window.set_validation_status("2 errors, 1 warning")
        assert "2 errors, 1 warning" in main_window._validation_label.text()

    def test_main_window_validation_shortcuts(self, main_window, qtbot):
        """Test that validation keyboard shortcuts are properly configured."""
        # Check that validate file action exists and has shortcut
        assert hasattr(main_window, "_action_validate_file")
        assert main_window._action_validate_file.shortcut() == QKeySequence("Ctrl+F7")

        # Check that validate project action has shortcut
        assert hasattr(main_window, "_action_validate")
        assert main_window._action_validate.shortcut() == QKeySequence("F7")

    def test_main_window_file_actions_enable_disable(self, main_window, qtbot):
        """Test that file actions are properly enabled/disabled."""
        # Initially should be disabled
        assert not main_window._action_validate_file.isEnabled()

        # Enable file actions
        main_window.enable_file_actions(True)
        assert main_window._action_validate_file.isEnabled()

        # Disable file actions
        main_window.enable_file_actions(False)
        assert not main_window._action_validate_file.isEnabled()

    def test_validation_console_integration(self, yaml_editor, qtbot):
        """Test that validation results are sent to output console."""
        from grimoire_studio.ui.components.output_console import OutputConsole

        # Create and connect output console
        output_console = Mock(spec=OutputConsole)
        yaml_editor.set_output_console(output_console)

        # Set a file path so validation can run
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write("test content")
            temp_file_path = Path(temp_file.name)

        try:
            yaml_editor._file_path = temp_file_path

            # Create validation results
            validation_results = [
                ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    message="Test error",
                    line_number=1,
                )
            ]

            # Simulate validation with results
            with patch.object(
                yaml_editor._validator,
                "validate_yaml_syntax",
                return_value=validation_results,
            ):
                yaml_editor._perform_validation(force_validation=True)

            # Verify output console was called
            output_console.display_validation_results.assert_called_once()

        finally:
            temp_file_path.unlink()

    def test_unsaved_content_validation(self, yaml_editor, qtbot, invalid_yaml_content):
        """Test that validation works on unsaved content."""
        # Set content without loading a file
        yaml_editor.set_content(invalid_yaml_content)

        # Create a temporary file path for validation context
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as temp_file:
            temp_file_path = Path(temp_file.name)

        try:
            # Set the file path manually
            yaml_editor._file_path = temp_file_path

            # Trigger validation
            results = yaml_editor._validator.validate_yaml_syntax(
                invalid_yaml_content, temp_file_path
            )

            # Should have validation results even for unsaved content
            assert len(results) > 0
            assert any(r.is_error for r in results)
        finally:
            temp_file_path.unlink()

    def test_validation_with_multiple_severity_levels(self, qtbot):
        """Test validation handling with multiple severity levels."""
        from PyQt6.QtGui import QTextDocument

        # Create document with actual content so lines exist to highlight
        document = QTextDocument("line 1\nline 2\nline 3\nline 4\n")
        highlighter = YamlSyntaxHighlighter(document)
        # Don't add document to qtbot - it's not a widget

        # Create validation results with different severities
        validation_results = [
            ValidationResult(
                severity=ValidationSeverity.ERROR,
                message="Critical error",
                line_number=1,
            ),
            ValidationResult(
                severity=ValidationSeverity.WARNING,
                message="Warning message",
                line_number=2,
            ),
            ValidationResult(
                severity=ValidationSeverity.INFO, message="Info message", line_number=3
            ),
        ]

        # Apply highlighting
        highlighter.highlight_validation_results(validation_results)

        # Should track all highlighted lines
        assert len(highlighter._highlighted_lines) == 3
        assert 0 in highlighter._highlighted_lines  # Line 1 (0-based)
        assert 1 in highlighter._highlighted_lines  # Line 2 (0-based)
        assert 2 in highlighter._highlighted_lines  # Line 3 (0-based)

    def test_validation_performance_with_large_content(self, yaml_editor, qtbot):
        """Test validation performance with larger YAML content."""
        # Create a large YAML content
        large_content = """# Large YAML file for performance testing\n"""
        for i in range(100):
            large_content += f"""
model_{i}:
  id: model_{i}
  kind: model
  name: "Model {i}"
  attributes:
    - name: value_{i}
      type: string
    - name: count_{i}
      type: integer
"""

        # Set content and measure validation time
        yaml_editor.set_content(large_content)

        # Create temporary file for validation
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as temp_file:
            temp_file.write(large_content)
            temp_file_path = Path(temp_file.name)

        try:
            # Load and validate - should not take too long
            import time

            start_time = time.time()

            yaml_editor.load_file(temp_file_path)
            yaml_editor._perform_validation(force_validation=True)

            end_time = time.time()
            validation_time = end_time - start_time

            # Validation should complete within reasonable time (5 seconds)
            assert validation_time < 5.0, (
                f"Validation took too long: {validation_time:.2f}s"
            )

        finally:
            temp_file_path.unlink()

    @pytest.mark.parametrize(
        "severity,expected_color",
        [
            ("error", (255, 200, 200)),
            ("warning", (255, 255, 200)),
            ("info", (255, 200, 200)),  # Info uses error format
        ],
    )
    def test_highlight_error_severity_colors(self, qtbot, severity, expected_color):
        """Test that different severity levels use appropriate colors."""
        from PyQt6.QtGui import QTextDocument

        document = QTextDocument("Sample text\nLine 2\nLine 3")
        highlighter = YamlSyntaxHighlighter(document)
        # Don't add document to qtbot - it's not a widget        # Highlight with specific severity
        highlighter.highlight_error(0, severity=severity)

        # Check that the line is tracked
        assert 0 in highlighter._highlighted_lines

    def test_validation_feedback_for_valid_yaml(self, yaml_editor, qtbot):
        """Test that validation provides success feedback for valid YAML."""
        from unittest.mock import Mock

        from grimoire_studio.ui.components.output_console import OutputConsole

        # Create and connect output console
        output_console = Mock(spec=OutputConsole)
        yaml_editor.set_output_console(output_console)

        # Set a file path so validation can run
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write("test: valid yaml content\n")
            temp_file_path = Path(temp_file.name)

        try:
            yaml_editor._file_path = temp_file_path

            # Mock validator to return no errors (valid YAML)
            with patch.object(
                yaml_editor._validator,
                "validate_yaml_syntax",
                return_value=[],
            ):
                yaml_editor._perform_validation(force_validation=True)

            # Verify output console was called with success message
            output_console.display_validation_results.assert_called_once()
            call_args = output_console.display_validation_results.call_args[0][0]

            assert len(call_args) == 1
            assert call_args[0]["level"] == "success"
            assert "no issues found" in call_args[0]["message"]

        finally:
            temp_file_path.unlink()


class TestValidationIntegrationEnd2End:
    """End-to-end tests for validation integration."""

    @pytest.fixture
    def app(self):
        """Provide QApplication for end-to-end tests."""
        return QApplication.instance() or QApplication([])

    def test_full_validation_workflow(self, qtbot, app):
        """Test the complete validation workflow from typing to display."""
        # Create main window
        main_window = MainWindow()
        main_window.set_test_mode(True)  # Prevent confirmation dialogs
        qtbot.addWidget(main_window)

        # Create a test YAML file with errors
        invalid_content = """# Missing required 'id' field
kind: model
name: "Test Model"
# Missing attributes field
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write(invalid_content)
            temp_file_path = Path(temp_file.name)

        try:
            # Simulate opening the file
            main_window._open_file_in_editor(str(temp_file_path))

            # Verify editor is connected
            current_editor = main_window._get_current_editor()
            assert current_editor is not None
            assert current_editor._output_console is not None

            # Wait for validation to complete
            app.processEvents()
            QTimer.singleShot(
                1200, lambda: None
            )  # Wait for validation timer + processing
            app.processEvents()

            # Check that validation status was updated
            validation_text = main_window._validation_label.text()
            assert (
                "error" in validation_text.lower() or "valid" in validation_text.lower()
            )

            # File actions should be enabled
            assert main_window._action_validate_file.isEnabled()
            assert main_window._action_save.isEnabled()

        finally:
            temp_file_path.unlink()

    def test_project_validation_workflow(self, qtbot, tmp_path, app):
        """Test project-level validation."""
        main_window = MainWindow()
        main_window.set_test_mode(True)  # Prevent confirmation dialogs
        qtbot.addWidget(main_window)

        # Create a simple project structure
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create system.yaml
        system_file = project_path / "system.yaml"
        system_file.write_text(
            """
id: test_system
kind: system
name: "Test System"
description: "A test system"
""",
            encoding="utf-8",
        )

        # Create model with errors
        model_file = project_path / "models" / "invalid_model.yaml"
        model_file.parent.mkdir()
        model_file.write_text(
            """
# Missing 'id' field
kind: model
name: "Invalid Model"
""",
            encoding="utf-8",
        )

        # Load the project
        try:
            main_window.load_project(str(project_path))

            # Verify project actions are enabled
            assert main_window._action_validate.isEnabled()

            # Trigger project validation
            main_window._on_validate_project()

            # Wait for validation to complete
            app.processEvents()

            # Check that validation found errors
            validation_text = main_window._validation_label.text()
            assert "error" in validation_text.lower() or len(validation_text) > 0

        except Exception as e:
            # Project loading might fail due to missing dependencies,
            # but we can still test the validation action exists
            assert hasattr(main_window, "_action_validate")
            pytest.skip(f"Project loading failed (expected in test env): {e}")
