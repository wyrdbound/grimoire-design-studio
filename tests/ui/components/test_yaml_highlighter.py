"""
Tests for YAML Syntax Highlighter.

This module provides comprehensive testing for the YamlSyntaxHighlighter class,
including syntax highlighting functionality, error highlighting, and integration.
"""

import pytest
from PyQt6.QtGui import QTextDocument
from PyQt6.QtWidgets import QApplication

from grimoire_studio.ui.components.yaml_highlighter import YamlSyntaxHighlighter


@pytest.mark.ui
class TestYamlSyntaxHighlighter:
    """Test suite for YamlSyntaxHighlighter class."""

    @pytest.fixture
    def app(self):
        """Create QApplication for UI tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()

    @pytest.fixture
    def document(self, app):
        """Create a QTextDocument for testing."""
        return QTextDocument()

    @pytest.fixture
    def highlighter(self, app, document):
        """Create YamlSyntaxHighlighter instance for testing."""
        return YamlSyntaxHighlighter(document)

    def test_initialization(self, highlighter):
        """Test YamlSyntaxHighlighter initialization."""
        assert highlighter is not None
        assert len(highlighter._token_formats) > 0

    def test_highlight_basic_yaml(self, highlighter, document):
        """Test highlighting of basic YAML constructs."""
        yaml_content = """# Comment
key: value
number: 42
string: "quoted string"
list:
  - item1
  - item2
"""
        document.setPlainText(yaml_content)
        # The highlighting should complete without errors
        # Specific format testing would require more complex setup

    def test_highlight_empty_content(self, highlighter, document):
        """Test highlighting with empty content."""
        document.setPlainText("")
        # Should not raise any exceptions

    def test_highlight_none_content(self, highlighter):
        """Test highlighting with None content."""
        # Should handle None gracefully without exceptions
        highlighter.highlightBlock(None)

    def test_set_color_scheme(self, highlighter):
        """Test setting color scheme."""
        # Test default scheme
        highlighter.set_color_scheme("default")

        # Test invalid scheme (should not crash)
        highlighter.set_color_scheme("nonexistent_scheme")

    def test_error_highlighting(self, highlighter, document):
        """Test error highlighting functionality."""
        yaml_content = """key: value
invalid line without colon
another: value"""

        document.setPlainText(yaml_content)

        # Test highlighting an error on line 1 (0-indexed)
        highlighter.highlight_error(1)

        # Test clearing error highlights
        highlighter.clear_error_highlights()

    def test_fallback_highlighting(self, highlighter):
        """Test fallback highlighting when Pygments fails."""
        # Test the fallback highlighting method directly
        test_text = "key: value  # comment"
        highlighter._fallback_highlighting(test_text)
        # Should not raise exceptions

    def test_font_setting(self, highlighter, app):
        """Test setting font for the highlighter."""
        from PyQt6.QtGui import QFont

        test_font = QFont("Arial", 14)
        highlighter.set_font(test_font)
        # Should not raise exceptions


@pytest.mark.ui
class TestYamlHighlighterIntegration:
    """Test YamlSyntaxHighlighter integration scenarios."""

    @pytest.fixture
    def app(self):
        """Create QApplication for UI tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()

    def test_complex_yaml_highlighting(self, app):
        """Test highlighting of complex YAML document."""
        document = QTextDocument()
        highlighter = YamlSyntaxHighlighter(document)

        complex_yaml = """---
# GRIMOIRE System Definition
kind: system
id: test_system
metadata:
  version: "1.0.0"
  author: Test Author
  description: |
    Multi-line description
    with various content

models:
  character:
    id: character
    attributes:
      name:
        type: string
        required: true
      level:
        type: integer
        minimum: 1
        maximum: 20
flows:
  - id: test_flow
    name: "Test Flow"
    steps:
      - type: input
        prompt: "Enter value:"
        output: user_input
      - type: dice_roll
        expression: "1d20+5"

# Nested structures
nested:
  level1:
    level2:
      - array_item: value
      - another_item: 42
      - boolean_value: true
      - null_value: null

special_characters: "@#$%^&*()"
numbers:
  integer: 123
  float: 3.14
  negative: -42
  scientific: 1.23e-4
"""

        document.setPlainText(complex_yaml)
        # Should highlight without errors

        # Test multiple error highlights
        highlighter.highlight_error(5, 0, 10)  # Highlight part of line 5
        highlighter.highlight_error(10)  # Highlight entire line 10

        # Clear all errors
        highlighter.clear_error_highlights()

    def test_malformed_yaml_highlighting(self, app):
        """Test highlighting of malformed YAML that might cause Pygments to fail."""
        document = QTextDocument()
        YamlSyntaxHighlighter(
            document
        )  # Create highlighter but don't store unused reference

        malformed_yaml = """
key: value
  bad indentation
[unclosed bracket
"unclosed quote
key without value:
  - list item
    bad indentation again
invalid: {unclosed: dict
"""

        document.setPlainText(malformed_yaml)
        # Should handle gracefully and fall back if needed

    def test_color_scheme_changes(self, app):
        """Test changing color schemes during operation."""
        document = QTextDocument()
        highlighter = YamlSyntaxHighlighter(document)

        yaml_content = "key: value  # comment"
        document.setPlainText(yaml_content)

        # Test various color schemes
        schemes = ["default", "emacs", "vim", "nonexistent"]
        for scheme in schemes:
            highlighter.set_color_scheme(scheme)
            # Should not crash with any scheme name
