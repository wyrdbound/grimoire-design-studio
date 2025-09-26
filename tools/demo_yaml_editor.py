#!/usr/bin/env python3
"""
Demo script for testing the YamlEditorView functionality.

This script creates a simple demo showing the YAML editor with sample content.
"""

import sys
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from grimoire_studio.ui.views.yaml_editor_view import YamlEditorView
from grimoire_studio.ui.components.output_console import OutputConsole


def create_sample_yaml_file() -> Path:
    """Create a temporary YAML file with sample content."""
    sample_content = """id: test_model
kind: model
name: Test Character Model
description: A sample character model for demonstration
attributes:
  name:
    type: string
    required: true
    description: Character's name
  level:
    type: integer
    minimum: 1
    maximum: 20
    default: 1
    description: Character level
  health:
    type: integer
    minimum: 1
    description: Current health points
  stats:
    type: object
    properties:
      strength:
        type: integer
        minimum: 1
        maximum: 20
      dexterity:
        type: integer  
        minimum: 1
        maximum: 20
      intelligence:
        type: integer
        minimum: 1
        maximum: 20
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as temp_file:
        temp_file.write(sample_content)
        temp_file.flush()
        return Path(temp_file.name)


class DemoMainWindow(QMainWindow):
    """Simple demo main window for testing the YAML editor."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YAML Editor Demo")
        self.setGeometry(100, 100, 1000, 700)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Create YAML editor
        self.yaml_editor = YamlEditorView()
        layout.addWidget(self.yaml_editor)

        # Create output console
        self.output_console = OutputConsole()
        layout.addWidget(self.output_console)

        # Connect editor to console
        self.yaml_editor.set_output_console(self.output_console)

        # Create and load sample file
        self.sample_file = create_sample_yaml_file()
        self.yaml_editor.load_file(self.sample_file)

        # Connect signals
        self.yaml_editor.file_changed.connect(self.on_file_changed)
        self.yaml_editor.file_saved.connect(self.on_file_saved)

        print(f"Demo started with sample file: {self.sample_file}")
        print("Features to test:")
        print("- Edit the YAML content and see change tracking")
        print("- Press Ctrl+S to save")
        print("- Press Ctrl+F to find text")
        print("- Press Ctrl+H to replace text")
        print("- Validation errors will appear in the output console")

    def on_file_changed(self, has_changes: bool):
        """Handle file change notifications."""
        status = "has unsaved changes" if has_changes else "saved"
        print(f"File status: {status}")

    def on_file_saved(self, file_path: Path):
        """Handle file save notifications."""
        print(f"File saved: {file_path}")

    def closeEvent(self, a0):  # type: ignore
        """Clean up when closing."""
        event = a0
        try:
            self.sample_file.unlink()
            print(f"Cleaned up sample file: {self.sample_file}")
        except (OSError, PermissionError):
            print(f"Could not clean up sample file: {self.sample_file}")
        super().closeEvent(event)


def main():
    """Run the YAML editor demo."""
    app = QApplication(sys.argv)

    # Create and show demo window
    demo_window = DemoMainWindow()
    demo_window.show()

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()