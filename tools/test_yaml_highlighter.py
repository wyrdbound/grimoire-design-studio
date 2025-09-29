#!/usr/bin/env python3
"""
Test script for YAML syntax highlighting.

This script creates a simple window to test the YAML editor with syntax highlighting.
Run this to verify the highlighter is working correctly.
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from grimoire_studio.ui.views.yaml_editor_view import YamlEditorView  # noqa: E402


class TestWindow(QMainWindow):
    """Test window for YAML syntax highlighting."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YAML Syntax Highlighter Test")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout
        layout = QVBoxLayout(central_widget)

        # Create YAML editor
        self.yaml_editor = YamlEditorView()
        layout.addWidget(self.yaml_editor)

        # Set some sample YAML content
        sample_yaml = """# Sample GRIMOIRE System
kind: system
id: sample_system
name: "Sample System"
description: |
  This is a sample YAML file to test syntax highlighting.
  It includes various YAML constructs.

metadata:
  version: "1.0.0"
  author: "Test Author"
  tags:
    - test
    - sample
    - demo

models:
  - id: character
    name: "Character Model"
    attributes:
      name:
        type: string
        required: true
      level:
        type: integer
        minimum: 1
        maximum: 20
        default: 1
      stats:
        strength: 10
        dexterity: 10
        intelligence: 10

flows:
  - id: character_creation
    name: "Character Creation Flow"
    steps:
      - type: input
        id: get_name
        prompt: "Enter character name:"
        output: character_name

      - type: dice_roll
        id: roll_stats
        expression: "3d6"
        count: 6
        output: rolled_stats

# This is a comment with special characters: @#$%^&*()
invalid_yaml_for_error_test:
  - this should be fine
  but this line has bad indentation
"""
        self.yaml_editor.set_content(sample_yaml)


def main():
    """Main function to run the test."""
    app = QApplication(sys.argv)

    window = TestWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
