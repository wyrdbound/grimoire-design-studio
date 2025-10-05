"""Flow test input dialog for collecting flow execution parameters.

This module provides a dialog for users to provide input values when testing
GRIMOIRE flows in the design studio.
"""

from __future__ import annotations

from typing import Any

from grimoire_logging import get_logger
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from grimoire_studio.models.grimoire_definitions import FlowDefinition

logger = get_logger(__name__)


class FlowTestDialog(QDialog):
    """Dialog for collecting flow input values before execution.

    This dialog dynamically creates input widgets based on the flow's
    input definitions, allowing users to provide values for testing.
    """

    def __init__(
        self, flow_definition: FlowDefinition, parent: QWidget | None = None
    ) -> None:
        """Initialize the flow test dialog.

        Args:
            flow_definition: The flow definition to collect inputs for
            parent: Parent widget
        """
        super().__init__(parent)
        self.flow_definition = flow_definition
        self.input_widgets: dict[str, QSpinBox | QCheckBox | QTextEdit | QLineEdit] = {}

        self.setWindowTitle(f"{flow_definition.name}: Input Values")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"<h2>{self.flow_definition.name}</h2>")
        layout.addWidget(header)

        if self.flow_definition.description:
            desc = QLabel(self.flow_definition.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: gray; font-style: italic;")
            layout.addWidget(desc)

        # Scroll area for inputs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        # Container for input widgets
        container = QWidget()
        form_layout = QFormLayout(container)
        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        # Create input widgets based on flow inputs
        if self.flow_definition.inputs:
            for flow_input in self.flow_definition.inputs:
                widget = self._create_input_widget(flow_input.type, flow_input.id)
                self.input_widgets[flow_input.id] = widget

                # Create label
                label_text = f"{flow_input.id} ({flow_input.type})"
                if flow_input.required:
                    label_text += " *"

                label = QLabel(label_text)
                label.setWordWrap(True)

                form_layout.addRow(label, widget)
        else:
            # No inputs required
            no_inputs = QLabel("This flow does not require any inputs.")
            no_inputs.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_inputs.setStyleSheet("color: gray; font-style: italic; padding: 20px;")
            form_layout.addRow(no_inputs)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)  # Give it stretch factor

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_input_widget(
        self, input_type: str, input_id: str
    ) -> QSpinBox | QCheckBox | QTextEdit | QLineEdit:
        """Create appropriate widget for input type.

        Args:
            input_type: Type of input (e.g., 'string', 'integer', 'boolean')
            input_id: ID of the input parameter

        Returns:
            Widget for collecting the input value
        """
        input_type_lower = input_type.lower()

        if input_type_lower in ("int", "integer", "number"):
            spin_box = QSpinBox()
            spin_box.setMinimum(-999999)
            spin_box.setMaximum(999999)
            spin_box.setValue(0)
            return spin_box

        elif input_type_lower in ("bool", "boolean"):
            return QCheckBox("Enabled")

        elif input_type_lower in ("text", "multiline", "description"):
            text_edit = QTextEdit()
            text_edit.setMaximumHeight(100)
            text_edit.setPlaceholderText(f"Enter {input_id}...")
            return text_edit

        else:
            # Default to single-line text input (string, object reference, etc.)
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(f"Enter {input_id}...")
            return line_edit

    def get_input_values(self) -> dict[str, Any]:
        """Get the collected input values.

        Returns:
            Dictionary mapping input IDs to their values
        """
        values: dict[str, Any] = {}

        for input_id, widget in self.input_widgets.items():
            if isinstance(widget, QLineEdit):
                values[input_id] = widget.text()
            elif isinstance(widget, QSpinBox):
                values[input_id] = widget.value()
            elif isinstance(widget, QCheckBox):
                values[input_id] = widget.isChecked()
            elif isinstance(widget, QTextEdit):
                values[input_id] = widget.toPlainText()

        return values

    @staticmethod
    def get_flow_inputs(
        flow_definition: FlowDefinition, parent: QWidget | None = None
    ) -> dict[str, Any] | None:
        """Static method to show dialog and get input values.

        Args:
            flow_definition: Flow definition to collect inputs for
            parent: Parent widget

        Returns:
            Dictionary of input values, or None if cancelled
        """
        logger.info(f"Showing flow input dialog for: {flow_definition.name}")
        logger.debug(f"Flow has {len(flow_definition.inputs)} inputs")

        dialog = FlowTestDialog(flow_definition, parent)
        result = dialog.exec()

        logger.debug(
            f"Dialog result: {result} (Accepted={QDialog.DialogCode.Accepted})"
        )

        if result == QDialog.DialogCode.Accepted:
            input_values = dialog.get_input_values()
            logger.info(f"User accepted dialog with values: {input_values}")
            return input_values

        logger.info("User cancelled dialog")
        return None
