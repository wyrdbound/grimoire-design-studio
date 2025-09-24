#!/usr/bin/env python3
"""
Demo script for OutputConsole functionality.

This script demonstrates the OutputConsole component capabilities including
validation results, execution output, and logging integration.
"""

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from grimoire_studio.ui.components.output_console import OutputConsole


class DemoWindow(QMainWindow):
    """Demo window to showcase OutputConsole functionality."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OutputConsole Demo - GRIMOIRE Design Studio")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout
        layout = QVBoxLayout(central_widget)

        # Add OutputConsole
        self.output_console = OutputConsole()
        layout.addWidget(self.output_console)

        # Set up demo timer
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self.run_demo)
        self.demo_step = 0

        # Start demo after window is shown
        QTimer.singleShot(1000, self.start_demo)

    def start_demo(self):
        """Start the demo sequence."""
        print("Starting OutputConsole Demo...")
        self.demo_timer.start(2000)  # Demo step every 2 seconds

    def run_demo(self):
        """Run demo steps."""
        if self.demo_step == 0:
            # Demo 1: Validation results
            print("Demo Step 1: Validation Results")
            validation_results = [
                {
                    "level": "error",
                    "message": "Missing required field 'id'",
                    "file": "system.yaml",
                    "line": 15,
                },
                {
                    "level": "warning",
                    "message": "Deprecated field 'old_attribute' used",
                    "file": "model.yaml",
                    "line": 42,
                },
                {
                    "level": "success",
                    "message": "All flow definitions valid",
                },
                {
                    "level": "info",
                    "message": "Found 25 models, 12 flows, 3 tables",
                },
            ]
            self.output_console.display_validation_results(validation_results)

        elif self.demo_step == 1:
            # Demo 2: Execution output
            print("Demo Step 2: Execution Output")
            self.output_console.display_execution_output(
                "Starting flow execution: character_creation", "info"
            )
            QTimer.singleShot(500, lambda: self.output_console.display_execution_output(
                "Rolling dice: 3d6 => [4, 2, 6] = 12", "success"
            ))
            QTimer.singleShot(1000, lambda: self.output_console.display_execution_output(
                "Generated character: Elara the Wise", "success"
            ))

        elif self.demo_step == 2:
            # Demo 3: Logging messages
            print("Demo Step 3: Application Logs")
            logger = logging.getLogger("demo.test")
            logger.setLevel(logging.DEBUG)
            
            logger.info("Demo logger initialized")
            logger.warning("This is a warning message")
            logger.error("This is an error message")

        elif self.demo_step == 3:
            # Demo 4: Show different tabs
            print("Demo Step 4: Tab Switching")
            self.output_console.switch_to_execution_tab()
            QTimer.singleShot(1000, lambda: self.output_console.switch_to_logs_tab())
            QTimer.singleShot(2000, lambda: self.output_console.switch_to_validation_tab())

        elif self.demo_step == 4:
            # Demo 5: More complex validation
            print("Demo Step 5: Complex Validation Results")
            complex_results = [
                {"level": "error", "message": "Circular dependency detected in flow chain"},
                {"level": "error", "message": "Invalid model reference: 'NonExistentModel'"},
                {"level": "warning", "message": "Unused table definition 'old_loot_table'"},
                {"level": "info", "message": "Validation completed in 0.125 seconds"},
            ]
            self.output_console.display_validation_results(complex_results)

        elif self.demo_step >= 5:
            # End demo
            print("Demo completed! Press Ctrl+C to exit.")
            self.demo_timer.stop()

        self.demo_step += 1


def main():
    """Run the OutputConsole demo."""
    app = QApplication(sys.argv)

    # Create and show demo window
    demo = DemoWindow()
    demo.show()

    print("OutputConsole Demo starting...")
    print("This demo will show:")
    print("1. Validation results with different levels and colors")
    print("2. Execution output with timestamps")
    print("3. Application logging integration")
    print("4. Tab switching functionality")
    print("5. Complex validation scenarios")
    print()
    print("Watch the console output for demo steps...")

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()