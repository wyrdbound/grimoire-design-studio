"""
YAML Syntax Highlighter for GRIMOIRE Design Studio.

This module provides the YamlSyntaxHighlighter class which implements
comprehensive YAML syntax highlighting using Pygments for accurate
parsing and PyQt6's QSyntaxHighlighter for rendering.
"""

from typing import Any, Optional

from grimoire_logging import get_logger
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.token import Token
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)

logger = get_logger(__name__)


class YamlSyntaxHighlighter(QSyntaxHighlighter):
    """
    Advanced YAML syntax highlighter using Pygments.

    This highlighter provides comprehensive YAML syntax highlighting with:
    - Keys, values, comments, strings, numbers
    - Lists, mappings, and multi-line strings
    - Error highlighting for syntax issues
    - Configurable color schemes
    - Integration with Pygments for accurate parsing
    """

    def __init__(self, parent: Optional[QTextDocument] = None) -> None:
        """
        Initialize the YAML syntax highlighter.

        Args:
            parent: Parent QTextDocument (optional)
        """
        super().__init__(parent)

        # Initialize Pygments components
        self._lexer = get_lexer_by_name("yaml")
        self._style = get_style_by_name("default")

        # Cache for token formats to improve performance
        self._token_formats: dict[Any, QTextCharFormat] = {}

        # Error highlighting format
        self._error_format = QTextCharFormat()
        self._error_format.setBackground(QColor(255, 200, 200, 100))
        self._error_format.setUnderlineStyle(
            QTextCharFormat.UnderlineStyle.WaveUnderline
        )
        self._error_format.setUnderlineColor(QColor(255, 0, 0))

        # Initialize token formats based on Pygments style
        self._setup_token_formats()

        logger.debug("YamlSyntaxHighlighter initialized with Pygments")

    def _setup_token_formats(self) -> None:
        """Set up text formats for different token types based on Pygments style."""
        # Clear existing formats
        self._token_formats.clear()

        # Define color mappings for YAML tokens
        token_colors = {
            Token.Keyword: QColor(0, 100, 200),  # YAML directives, tags
            Token.Name.Tag: QColor(0, 100, 200),  # YAML tags
            Token.Literal.Scalar.Plain: QColor(0, 0, 0),  # Plain scalars
            Token.Literal.Scalar.Single: QColor(0, 128, 0),  # Single quoted strings
            Token.Literal.Scalar.Double: QColor(0, 128, 0),  # Double quoted strings
            Token.Comment: QColor(128, 128, 128),  # Comments
            Token.Punctuation: QColor(100, 100, 100),  # Punctuation (-, :, etc.)
            Token.Number: QColor(200, 0, 100),  # Numbers
            Token.Literal: QColor(150, 75, 0),  # Literals
            Token.Name.Variable: QColor(50, 50, 200),  # Variables
            Token.Error: QColor(255, 0, 0),  # Errors
        }

        # Create QTextCharFormat for each token type
        for token_type, color in token_colors.items():
            format_obj = QTextCharFormat()
            format_obj.setForeground(color)

            # Apply special formatting based on token type
            if token_type in (Token.Comment,):
                format_obj.setFontItalic(True)
            elif token_type in (Token.Keyword, Token.Name.Tag):
                format_obj.setFontWeight(QFont.Weight.Bold)
            elif token_type == Token.Error:
                format_obj.setFontWeight(QFont.Weight.Bold)
                format_obj.setBackground(QColor(255, 200, 200, 100))

            self._token_formats[token_type] = format_obj

        logger.debug(f"Set up {len(self._token_formats)} token formats")

    def highlightBlock(self, text: Optional[str]) -> None:
        """
        Highlight a block of text.

        Args:
            text: Text to highlight
        """
        if not text or not text.strip():
            return

        try:
            # Tokenize the text using Pygments
            tokens = list(self._lexer.get_tokens(text))

            # Apply highlighting based on tokens
            current_pos = 0

            for token_type, token_text in tokens:
                if not token_text:
                    continue

                # Find the actual position of this token in the text
                token_start = text.find(token_text, current_pos)
                if token_start == -1:
                    # If we can't find the token, skip it
                    continue

                token_length = len(token_text)

                # Apply format based on token type
                format_obj = self._get_format_for_token(token_type)
                if format_obj:
                    self.setFormat(token_start, token_length, format_obj)

                current_pos = token_start + token_length

        except Exception as e:
            # If pygments fails, fall back to basic highlighting
            logger.warning(f"Pygments highlighting failed, using fallback: {e}")
            if text:
                self._fallback_highlighting(text)

    def _get_format_for_token(self, token_type: Any) -> Optional[QTextCharFormat]:
        """
        Get the format for a specific token type.

        Args:
            token_type: Pygments token type

        Returns:
            QTextCharFormat for the token type, or None
        """
        # Try exact match first
        if token_type in self._token_formats:
            return self._token_formats[token_type]

        # Try parent token types (Pygments uses hierarchical tokens)
        for parent in token_type.split():
            if parent in self._token_formats:
                return self._token_formats[parent]

        return None

    def _fallback_highlighting(self, text: str) -> None:
        """
        Fallback highlighting using regex patterns when Pygments fails.

        Args:
            text: Text to highlight
        """
        # Define basic regex patterns for YAML elements
        patterns = [
            # YAML keys (word followed by colon)
            (
                r"^(\s*)([^:\s#]+)(\s*:)",
                [
                    (2, self._token_formats.get(Token.Name.Tag, QTextCharFormat())),
                    (3, self._token_formats.get(Token.Punctuation, QTextCharFormat())),
                ],
            ),
            # Comments (# to end of line)
            (r"#.*$", [(0, self._token_formats.get(Token.Comment, QTextCharFormat()))]),
            # Quoted strings
            (
                r'(["\'])(?:(?=(\\?))\2.)*?\1',
                [
                    (
                        0,
                        self._token_formats.get(
                            Token.Literal.Scalar.Single, QTextCharFormat()
                        ),
                    )
                ],
            ),
            # Numbers
            (
                r"\b\d+\.?\d*\b",
                [(0, self._token_formats.get(Token.Number, QTextCharFormat()))],
            ),
            # YAML list indicators
            (
                r"^(\s*)([-+*])(\s+)",
                [(2, self._token_formats.get(Token.Punctuation, QTextCharFormat()))],
            ),
        ]

        for pattern_str, format_groups in patterns:
            expression = QRegularExpression(pattern_str)
            iterator = expression.globalMatch(text)

            while iterator.hasNext():
                match = iterator.next()
                for group_num, format_obj in format_groups:
                    start = match.capturedStart(group_num)
                    length = match.capturedLength(group_num)
                    if start >= 0 and length > 0:
                        self.setFormat(start, length, format_obj)

    def set_color_scheme(self, scheme_name: str = "default") -> None:
        """
        Set the color scheme for syntax highlighting.

        Args:
            scheme_name: Name of the Pygments style to use
        """
        try:
            self._style = get_style_by_name(scheme_name)
            self._setup_token_formats()

            # Trigger re-highlighting of the document
            if self.document():
                self.rehighlight()

            logger.info(f"Color scheme changed to: {scheme_name}")

        except Exception as e:
            logger.error(f"Failed to set color scheme '{scheme_name}': {e}")

    def highlight_error(
        self, line_number: int, start_col: int = 0, end_col: int = -1
    ) -> None:
        """
        Highlight a specific line or range as an error.

        Args:
            line_number: Line number to highlight (0-based)
            start_col: Starting column (0-based), default 0
            end_col: Ending column (0-based), -1 for entire line
        """
        document = self.document()
        if not document:
            return

        # Get the text block for the specified line
        block = document.findBlockByLineNumber(line_number)
        if not block.isValid():
            return

        # Determine the range to highlight
        start_pos = start_col
        if end_col == -1:
            end_pos = len(block.text())
        else:
            end_pos = min(end_col, len(block.text()))

        # Apply error highlighting using additional format
        if start_pos < end_pos:
            # Store current block and apply error format
            current_block = self.currentBlock()
            if current_block == block:
                current_format = self.format(start_pos)
                error_format = QTextCharFormat(current_format)
                error_format.merge(self._error_format)
                self.setFormat(start_pos, end_pos - start_pos, error_format)

    def clear_error_highlights(self) -> None:
        """Clear all error highlighting and re-highlight the document."""
        if self.document():
            self.rehighlight()
            logger.debug("Error highlights cleared")

    def set_font(self, font: QFont) -> None:
        """
        Set the base font for the highlighter.

        Args:
            font: Font to use for highlighting
        """
        # Update all token formats with the new font
        for format_obj in self._token_formats.values():
            format_obj.setFont(font)

        # Update error format font
        self._error_format.setFont(font)

        # Trigger re-highlighting
        if self.document():
            self.rehighlight()

        logger.debug(f"Font updated: {font.family()} {font.pointSize()}pt")
