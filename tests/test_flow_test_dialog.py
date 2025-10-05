"""
Tests for the FlowTestDialog component.

This module tests the FlowTestDialog's ability to dynamically create input
widgets based on flow definitions and collect user input values.
"""

from typing import cast
from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QCheckBox, QLineEdit, QSpinBox, QTextEdit

from grimoire_studio.models.grimoire_definitions import FlowDefinition, FlowInputOutput
from grimoire_studio.ui.dialogs.flow_test_dialog import FlowTestDialog


@pytest.fixture
def basic_flow_def() -> FlowDefinition:
    """Create a basic flow definition for testing."""
    return FlowDefinition(
        id="test_flow",
        kind="flow",
        name="Test Flow",
        description="A test flow",
        inputs=[
            FlowInputOutput(
                id="player_name",
                type="string",
                required=True,
                validate=None,
            ),
            FlowInputOutput(
                id="level",
                type="int",
                required=True,
                validate=None,
            ),
            FlowInputOutput(
                id="is_active",
                type="bool",
                required=False,
                validate=None,
            ),
            FlowInputOutput(
                id="notes",
                type="text",
                required=False,
                validate=None,
            ),
        ],
        outputs=[],
        variables=[],
        steps=[],
    )


def test_dialog_creation(qtbot, basic_flow_def) -> None:
    """Test that dialog is created with correct title and inputs."""
    dialog = FlowTestDialog(basic_flow_def)
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "Test Flow: Input Values"
    assert len(dialog.input_widgets) == 4
    assert "player_name" in dialog.input_widgets
    assert "level" in dialog.input_widgets
    assert "is_active" in dialog.input_widgets
    assert "notes" in dialog.input_widgets


def test_string_input_widget(qtbot, basic_flow_def) -> None:
    """Test that string input creates QLineEdit widget."""
    dialog = FlowTestDialog(basic_flow_def)
    qtbot.addWidget(dialog)

    widget = dialog.input_widgets["player_name"]
    assert isinstance(widget, QLineEdit)
    assert widget.placeholderText() == "Enter player_name..."


def test_int_input_widget(qtbot, basic_flow_def) -> None:
    """Test that int input creates QSpinBox widget."""
    dialog = FlowTestDialog(basic_flow_def)
    qtbot.addWidget(dialog)

    widget = dialog.input_widgets["level"]
    assert isinstance(widget, QSpinBox)
    assert widget.minimum() == -999999
    assert widget.maximum() == 999999
    assert widget.value() == 0


def test_bool_input_widget(qtbot, basic_flow_def) -> None:
    """Test that bool input creates QCheckBox widget."""
    dialog = FlowTestDialog(basic_flow_def)
    qtbot.addWidget(dialog)

    widget = dialog.input_widgets["is_active"]
    assert isinstance(widget, QCheckBox)
    assert widget.text() == "Enabled"


def test_text_input_widget(qtbot, basic_flow_def) -> None:
    """Test that text input creates QTextEdit widget."""
    dialog = FlowTestDialog(basic_flow_def)
    qtbot.addWidget(dialog)

    widget = dialog.input_widgets["notes"]
    assert isinstance(widget, QTextEdit)
    assert widget.placeholderText() == "Enter notes..."
    assert widget.maximumHeight() == 100


def test_get_input_values(qtbot, basic_flow_def) -> None:
    """Test retrieving input values from the dialog."""
    dialog = FlowTestDialog(basic_flow_def)
    qtbot.addWidget(dialog)

    # Set values with proper type casts
    cast(QLineEdit, dialog.input_widgets["player_name"]).setText("TestPlayer")
    cast(QSpinBox, dialog.input_widgets["level"]).setValue(10)
    cast(QCheckBox, dialog.input_widgets["is_active"]).setChecked(True)
    cast(QTextEdit, dialog.input_widgets["notes"]).setPlainText("Test notes")

    values = dialog.get_input_values()

    assert values["player_name"] == "TestPlayer"
    assert values["level"] == 10
    assert values["is_active"] is True
    assert values["notes"] == "Test notes"


def test_get_input_values_empty(qtbot, basic_flow_def) -> None:
    """Test retrieving input values when no values are set."""
    dialog = FlowTestDialog(basic_flow_def)
    qtbot.addWidget(dialog)

    values = dialog.get_input_values()

    assert values["player_name"] == ""
    assert values["level"] == 0
    assert values["is_active"] is False
    assert values["notes"] == ""


def test_static_get_flow_inputs_accepted(qtbot, basic_flow_def) -> None:
    """Test static helper method when user accepts dialog."""
    # Just test that the static method creates a dialog and calls exec
    # We can't easily test the full flow without showing a real dialog
    with patch.object(FlowTestDialog, "exec", return_value=1):  # QDialog.Accepted
        with patch.object(
            FlowTestDialog,
            "get_input_values",
            return_value={"player_name": "Test", "level": 5},
        ):
            result = FlowTestDialog.get_flow_inputs(basic_flow_def, None)

            # Should return the values from get_input_values
            assert result == {"player_name": "Test", "level": 5}


def test_static_get_flow_inputs_rejected(qtbot, basic_flow_def) -> None:
    """Test static helper method when user cancels dialog."""
    # Mock to return rejected
    with patch.object(FlowTestDialog, "exec", return_value=0):  # QDialog.Rejected
        result = FlowTestDialog.get_flow_inputs(basic_flow_def, None)

        assert result is None


def test_flow_with_no_inputs(qtbot) -> None:
    """Test dialog with flow that has no inputs."""
    flow_def = FlowDefinition(
        id="no_input_flow",
        kind="flow",
        name="No Input Flow",
        description="A flow with no inputs",
        inputs=[],
        outputs=[],
        variables=[],
        steps=[],
    )

    dialog = FlowTestDialog(flow_def)
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "No Input Flow: Input Values"
    assert len(dialog.input_widgets) == 0
    assert dialog.get_input_values() == {}


def test_widget_type_variations(qtbot) -> None:
    """Test that various type names map to correct widgets."""
    flow_def = FlowDefinition(
        id="type_test_flow",
        kind="flow",
        name="Type Test",
        description="Testing various input types",
        inputs=[
            FlowInputOutput(
                id="int_field", type="integer", required=True, validate=None
            ),
            FlowInputOutput(
                id="num_field", type="number", required=True, validate=None
            ),
            FlowInputOutput(
                id="bool_field", type="boolean", required=True, validate=None
            ),
            FlowInputOutput(
                id="text_field", type="multiline", required=True, validate=None
            ),
            FlowInputOutput(
                id="desc_field", type="description", required=True, validate=None
            ),
            FlowInputOutput(
                id="obj_field", type="object_ref", required=True, validate=None
            ),
        ],
        outputs=[],
        variables=[],
        steps=[],
    )

    dialog = FlowTestDialog(flow_def)
    qtbot.addWidget(dialog)

    # Integer types -> QSpinBox
    assert isinstance(dialog.input_widgets["int_field"], QSpinBox)
    assert isinstance(dialog.input_widgets["num_field"], QSpinBox)

    # Boolean types -> QCheckBox
    assert isinstance(dialog.input_widgets["bool_field"], QCheckBox)

    # Multiline text types -> QTextEdit
    assert isinstance(dialog.input_widgets["text_field"], QTextEdit)
    assert isinstance(dialog.input_widgets["desc_field"], QTextEdit)

    # Other types -> QLineEdit
    assert isinstance(dialog.input_widgets["obj_field"], QLineEdit)
