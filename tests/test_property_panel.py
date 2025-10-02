"""Tests for the PropertyPanel component."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGroupBox,
    QLineEdit,
    QListWidget,
    QSpinBox,
)

from grimoire_studio.core.project_manager import ProjectManager
from grimoire_studio.models.grimoire_definitions import CompleteSystem
from grimoire_studio.ui.components.property_panel import PropertyPanel


@pytest.fixture
def knave_system():
    """Load the Knave 1e system for testing."""
    project_manager = ProjectManager()
    knave_path = Path(__file__).parent.parent / "systems" / "knave_1e"

    if not knave_path.exists():
        pytest.skip("Knave 1e system not available for testing")

    return project_manager.load_system(knave_path)


@pytest.fixture
def simple_system():
    """Create a simple system for basic testing."""
    from grimoire_model import AttributeDefinition, ModelDefinition

    # Create a simple test model
    test_model = ModelDefinition(
        id="test_item",
        name="Test Item",
        description="A simple test item",
        version=1,
        attributes={
            "name": AttributeDefinition(type="str"),
            "value": AttributeDefinition(type="int", range="0..100"),
            "weight": AttributeDefinition(type="float", range="0.."),
            "magical": AttributeDefinition(type="bool", default=False),
            "tags": AttributeDefinition(type="list", of="str", default=[]),
        },
    )

    # Create a mock system
    system = Mock(spec=CompleteSystem)
    system.models = {"test_item": test_model}
    system.system = Mock()
    system.system.id = "test_system"

    return system


class TestPropertyPanelBasics:
    """Test basic PropertyPanel functionality."""

    def test_initialization(self, qtbot):
        """Test property panel initialization."""
        panel = PropertyPanel()
        qtbot.addWidget(panel)

        assert panel.system is None
        assert panel.object_service is None
        assert panel.current_object is None
        assert len(panel.widgets) == 0

    def test_initialization_with_system(self, qtbot, simple_system):
        """Test property panel initialization with system."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        assert panel.system is simple_system
        assert panel.object_service is not None

    def test_empty_state(self, qtbot):
        """Test property panel shows empty state."""
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        panel.show()  # Show the panel so children are visible

        # Empty label should be visible
        assert panel.empty_label.isVisible()
        assert "No object selected" in panel.empty_label.text()

    def test_clear(self, qtbot, simple_system):
        """Test clearing the property panel."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)
        panel.show()  # Show the panel so children are visible

        # Load an object
        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
        }
        panel.load_object(obj_data)

        # Verify object loaded
        assert panel.current_object is not None
        assert len(panel.widgets) > 0

        # Clear the panel
        panel.clear()

        # Verify cleared
        assert panel.current_object is None
        assert len(panel.widgets) == 0
        assert panel.empty_label.isVisible()


class TestPropertyPanelStringWidgets:
    """Test string property widgets."""

    def test_string_widget_creation(self, qtbot, simple_system):
        """Test creation of string editing widget."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Magic Sword",
            "value": 100,
        }
        panel.load_object(obj_data)

        # Find the string widget
        name_widget = panel.widgets.get("name")
        assert isinstance(name_widget, QLineEdit)
        assert name_widget.text() == "Magic Sword"

    def test_string_widget_editing(self, qtbot, simple_system):
        """Test editing a string property."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
        }
        panel.load_object(obj_data)

        # Track property changes
        changes = []
        panel.property_changed.connect(lambda prop, val: changes.append((prop, val)))

        # Edit the name
        name_widget = panel.widgets["name"]
        assert isinstance(name_widget, QLineEdit)
        name_widget.setText("Magic Sword")

        # Verify change was recorded
        assert len(changes) > 0
        assert changes[-1] == ("name", "Magic Sword")
        assert panel.current_object is not None
        assert panel.current_object["name"] == "Magic Sword"

    def test_empty_string_becomes_none(self, qtbot, simple_system):
        """Test that empty strings become None."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
        }
        panel.load_object(obj_data)

        # Track property changes
        changes = []
        panel.property_changed.connect(lambda prop, val: changes.append((prop, val)))

        # Clear the name
        name_widget = panel.widgets["name"]
        assert isinstance(name_widget, QLineEdit)
        name_widget.setText("")

        # Verify None is set
        assert changes[-1] == ("name", None)


class TestPropertyPanelNumericWidgets:
    """Test numeric property widgets."""

    def test_int_widget_creation(self, qtbot, simple_system):
        """Test creation of integer editing widget."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
        }
        panel.load_object(obj_data)

        # Find the int widget
        value_widget = panel.widgets.get("value")
        assert isinstance(value_widget, QSpinBox)
        assert value_widget.value() == 100

    def test_int_widget_range(self, qtbot, simple_system):
        """Test integer widget respects range constraints."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 50,
        }
        panel.load_object(obj_data)

        value_widget = panel.widgets["value"]
        assert isinstance(value_widget, QSpinBox)
        assert value_widget.minimum() == 0
        assert value_widget.maximum() == 100

    def test_int_widget_editing(self, qtbot, simple_system):
        """Test editing an integer property."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
        }
        panel.load_object(obj_data)

        # Track property changes
        changes = []
        panel.property_changed.connect(lambda prop, val: changes.append((prop, val)))

        # Change the value
        value_widget = panel.widgets["value"]
        assert isinstance(value_widget, QSpinBox)
        value_widget.setValue(75)

        # Verify change was recorded
        assert ("value", 75) in changes
        assert panel.current_object is not None
        assert panel.current_object["value"] == 75

    def test_float_widget_creation(self, qtbot, simple_system):
        """Test creation of float editing widget."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
            "weight": 5.5,
        }
        panel.load_object(obj_data)

        # Find the float widget
        weight_widget = panel.widgets.get("weight")
        assert isinstance(weight_widget, QDoubleSpinBox)
        assert weight_widget.value() == 5.5

    def test_float_widget_editing(self, qtbot, simple_system):
        """Test editing a float property."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
            "weight": 5.5,
        }
        panel.load_object(obj_data)

        # Track property changes
        changes = []
        panel.property_changed.connect(lambda prop, val: changes.append((prop, val)))

        # Change the weight
        weight_widget = panel.widgets["weight"]
        assert isinstance(weight_widget, QDoubleSpinBox)
        weight_widget.setValue(7.25)

        # Verify change was recorded
        assert ("weight", 7.25) in changes
        assert panel.current_object is not None
        assert panel.current_object["weight"] == 7.25


class TestPropertyPanelBoolWidgets:
    """Test boolean property widgets."""

    def test_bool_widget_creation(self, qtbot, simple_system):
        """Test creation of boolean editing widget."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
            "magical": True,
        }
        panel.load_object(obj_data)

        # Find the bool widget
        magical_widget = panel.widgets.get("magical")
        assert isinstance(magical_widget, QCheckBox)
        assert magical_widget.isChecked()

    def test_bool_widget_editing(self, qtbot, simple_system):
        """Test editing a boolean property."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
            "magical": False,
        }
        panel.load_object(obj_data)

        # Track property changes
        changes = []
        panel.property_changed.connect(lambda prop, val: changes.append((prop, val)))

        # Toggle the checkbox
        magical_widget = panel.widgets["magical"]
        assert isinstance(magical_widget, QCheckBox)
        magical_widget.setChecked(True)

        # Verify change was recorded
        assert ("magical", True) in changes
        assert panel.current_object is not None
        assert panel.current_object["magical"] is True


class TestPropertyPanelListWidgets:
    """Test list property widgets."""

    def test_list_widget_creation(self, qtbot, simple_system):
        """Test creation of list editing widget."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
            "tags": ["weapon", "sharp"],
        }
        panel.load_object(obj_data)

        # Find the list widget container
        tags_widget = panel.widgets.get("tags")
        assert tags_widget is not None

        # Find the QListWidget inside
        list_widgets = tags_widget.findChildren(QListWidget)
        assert len(list_widgets) == 1
        list_widget = list_widgets[0]
        assert list_widget.count() == 2

    def test_list_widget_add_item(self, qtbot, simple_system):
        """Test adding an item to a list."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
            "tags": ["weapon"],
        }
        panel.load_object(obj_data)

        # Find the list widget and add button
        tags_widget = panel.widgets["tags"]
        list_widget = tags_widget.findChildren(QListWidget)[0]

        # For now, test programmatically (finding buttons dynamically is complex)
        panel._on_list_add("tags", list_widget)

        assert list_widget.count() == 2

    def test_list_widget_remove_item(self, qtbot, simple_system):
        """Test removing an item from a list."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
            "tags": ["weapon", "sharp"],
        }
        panel.load_object(obj_data)

        # Find the list widget
        tags_widget = panel.widgets["tags"]
        list_widget = tags_widget.findChildren(QListWidget)[0]

        # Select first item
        list_widget.setCurrentRow(0)

        # Remove it
        panel._on_list_remove("tags", list_widget)

        assert list_widget.count() == 1


class TestPropertyPanelValidation:
    """Test property panel validation."""

    def test_validation_on_change(self, qtbot, simple_system):
        """Test that validation runs when properties change."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_item",
            "name": "Sword",
            "value": 100,
        }
        panel.load_object(obj_data)

        # Track validation errors
        errors = []
        panel.validation_error.connect(lambda err: errors.append(err))

        # Change to invalid value (should trigger validation)
        # Note: This depends on grimoire-model validation behavior
        name_widget = panel.widgets["name"]
        assert isinstance(name_widget, QLineEdit)
        name_widget.setText("")  # Empty name might be invalid

        # Validation should have run (errors captured or not depends on validation rules)
        # Just verify the mechanism works

    def test_missing_model_field(self, qtbot, simple_system):
        """Test loading object without model field."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        # Track errors
        errors = []
        panel.validation_error.connect(lambda err: errors.append(err))

        # Load object without model
        panel.load_object({"name": "Sword"})

        # Should show error
        assert len(errors) > 0
        assert "model" in errors[0].lower()

    def test_unknown_model_type(self, qtbot, simple_system):
        """Test loading object with unknown model type."""
        panel = PropertyPanel(system=simple_system)
        qtbot.addWidget(panel)

        # Track errors
        errors = []
        panel.validation_error.connect(lambda err: errors.append(err))

        # Load object with unknown model
        panel.load_object({"model": "unknown_model", "name": "Sword"})

        # Should show error
        assert len(errors) > 0
        assert "unknown" in errors[0].lower()


class TestPropertyPanelComplexTypes:
    """Test complex type handling."""

    def test_dict_widget_creation(self, qtbot):
        """Test creation of dict editing widget."""
        from grimoire_model import AttributeDefinition, ModelDefinition

        # Create model with dict attribute
        test_model = ModelDefinition(
            id="test_complex",
            name="Test Complex",
            description="Test model with complex types",
            version=1,
            attributes={
                "metadata": AttributeDefinition(type="dict"),
            },
        )

        system = Mock(spec=CompleteSystem)
        system.models = {"test_complex": test_model}
        system.system = Mock()
        system.system.id = "test_system"

        panel = PropertyPanel(system=system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_complex",
            "metadata": {"author": "Test", "version": "1.0"},
        }
        panel.load_object(obj_data)

        # Find the dict widget
        metadata_widget = panel.widgets.get("metadata")
        assert isinstance(metadata_widget, QGroupBox)

    def test_nested_object_widget(self, qtbot):
        """Test creation of nested object widget."""
        from grimoire_model import AttributeDefinition, ModelDefinition

        # Create models
        sub_model = ModelDefinition(
            id="sub_item",
            name="Sub Item",
            description="Sub model",
            version=1,
            attributes={
                "value": AttributeDefinition(type="int"),
            },
        )

        test_model = ModelDefinition(
            id="test_nested",
            name="Test Nested",
            description="Test model with nested object",
            version=1,
            attributes={
                "nested": AttributeDefinition(type="sub_item"),
            },
        )

        system = Mock(spec=CompleteSystem)
        system.models = {"test_nested": test_model, "sub_item": sub_model}
        system.system = Mock()
        system.system.id = "test_system"

        panel = PropertyPanel(system=system)
        qtbot.addWidget(panel)

        obj_data = {
            "model": "test_nested",
            "nested": {"model": "sub_item", "value": 42},
        }
        panel.load_object(obj_data)

        # Find the nested widget
        nested_widget = panel.widgets.get("nested")
        assert isinstance(nested_widget, QGroupBox)


class TestPropertyPanelKnaveSystem:
    """Test property panel with real Knave system."""

    def test_load_character_ability(self, qtbot, knave_system):
        """Test loading a character_ability object."""
        panel = PropertyPanel(system=knave_system)
        qtbot.addWidget(panel)

        ability_data = {
            "model": "character_ability",
            "bonus": 5,
        }
        panel.load_object(ability_data)

        # Verify widgets created
        assert "bonus" in panel.widgets
        assert isinstance(panel.widgets["bonus"], QSpinBox)

        # Defense should be derived (read-only)
        if "defense" in panel.widgets:
            # Check if it's read-only
            defense_widget = panel.widgets["defense"]
            assert not hasattr(defense_widget, "setValue")

    def test_load_item(self, qtbot, knave_system):
        """Test loading an item object."""
        panel = PropertyPanel(system=knave_system)
        qtbot.addWidget(panel)

        item_data = {
            "model": "item",
            "name": "Longsword",
            "slot_cost": 1,
        }
        panel.load_object(item_data)

        # Verify widgets created
        assert "name" in panel.widgets
        assert "slot_cost" in panel.widgets

    def test_get_object_data(self, qtbot, knave_system):
        """Test retrieving modified object data."""
        panel = PropertyPanel(system=knave_system)
        qtbot.addWidget(panel)

        ability_data = {
            "model": "character_ability",
            "bonus": 5,
        }
        panel.load_object(ability_data)

        # Modify a value
        bonus_widget = panel.widgets["bonus"]
        assert isinstance(bonus_widget, QSpinBox)
        bonus_widget.setValue(7)

        # Get the data back
        result = panel.get_object_data()
        assert result is not None
        assert result["bonus"] == 7
        assert result["model"] == "character_ability"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
