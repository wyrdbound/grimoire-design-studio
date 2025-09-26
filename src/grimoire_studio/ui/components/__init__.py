"""
UI Components for GRIMOIRE Design Studio.

This package contains reusable UI components used throughout the application.
"""

from .output_console import OutputConsole
from .project_browser import ProjectBrowser
from .yaml_highlighter import YamlSyntaxHighlighter

__all__ = ["OutputConsole", "ProjectBrowser", "YamlSyntaxHighlighter"]
