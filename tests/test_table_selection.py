"""Test for table selection functionality in player choice steps."""

import pytest
from grimoire_context import GrimoireContext

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompleteSystem,
    ModelDefinition,
    SystemDefinition,
    TableDefinition,
)
from grimoire_studio.services.exceptions import FlowExecutionError
from grimoire_studio.services.object_service import ObjectInstantiationService
from grimoire_studio.services.step_executors.player_choice import (
    PlayerChoiceStepExecutor,
)


@pytest.fixture
def sample_system_with_weapon_table():
    """Create a system with a weapon table for testing."""
    # Create a weapon model
    weapon_model = ModelDefinition(
        id="weapon",
        kind="model",
        name="Weapon",
        description="A weapon in the game",
        attributes={
            "name": AttributeDefinition(type="str"),
            "damage": AttributeDefinition(type="str"),
        },
    )

    # Create a weapon table with entry_type="weapon" (matching real Knave structure)
    weapon_table = TableDefinition(
        id="weapons",
        kind="table",
        name="Weapons",
        description="List of available weapons",
        entry_type="weapon",  # This should create weapon objects
        entries=[
            {"range": "1", "value": "dagger"},  # String IDs like in real Knave tables
            {"range": "2", "value": "sword"},
        ],
    )

    system_def = SystemDefinition(id="test_system", kind="system", name="Test System")

    return CompleteSystem(
        system=system_def,
        models={"weapon": weapon_model},
        tables={"weapons": weapon_table},
    )


def test_table_selection_creates_grimoire_model_object(sample_system_with_weapon_table):
    """Test that selecting from a table with entry_type creates proper GrimoireModel object."""
    system = sample_system_with_weapon_table
    object_service = ObjectInstantiationService(system)

    # Create player choice executor with object service
    executor = PlayerChoiceStepExecutor(
        system=system,
        template_resolver=None,  # Not needed for this test
        action_executor=lambda *args: GrimoireContext(),  # Mock action executor
        object_service=object_service,
    )

    # Test table selection processing
    choice_source = {"table": "weapons"}
    result = executor._process_table_selection(choice_source, "dagger")

    # Should return a GrimoireModel weapon object, not a string
    assert not isinstance(result, str), (
        f"Expected GrimoireModel object, got string: {result}"
    )
    # Check that it's a GrimoireModel with the expected properties
    assert result["id"] == "dagger", "Weapon ID should be preserved"
    assert result["model"] == "weapon", "Model type should be set in data"
    # Verify it's a proper GrimoireModel object
    assert hasattr(result, "model_definition"), "Result should be a GrimoireModel"


def test_table_selection_with_str_entry_type_returns_string(
    sample_system_with_weapon_table,
):
    """Test that tables with entry_type='str' return strings, not objects."""
    # Create a string table
    system = sample_system_with_weapon_table
    string_table = TableDefinition(
        id="locations",
        kind="table",
        name="Locations",
        description="List of locations",
        entry_type="str",  # Should return strings
        entries=[
            {"range": "1", "value": "Forest"},
            {"range": "2", "value": "Cave"},
        ],
    )
    system.tables["locations"] = string_table

    object_service = ObjectInstantiationService(system)
    executor = PlayerChoiceStepExecutor(
        system=system,
        template_resolver=None,
        action_executor=lambda *args: GrimoireContext(),
        object_service=object_service,
    )

    choice_source = {"table": "locations"}
    result = executor._process_table_selection(choice_source, "Forest")

    # Should return the string, not an object
    assert isinstance(result, str), (
        f"Expected string for str entry_type, got: {type(result)}"
    )
    assert result == "Forest", "Should return the selection ID as-is"


def test_table_not_found_raises_explicit_error(sample_system_with_weapon_table):
    """Test that missing tables raise explicit errors instead of falling back silently."""
    system = sample_system_with_weapon_table
    object_service = ObjectInstantiationService(system)

    executor = PlayerChoiceStepExecutor(
        system=system,
        template_resolver=None,
        action_executor=lambda *args: GrimoireContext(),
        object_service=object_service,
    )

    choice_source = {"table": "nonexistent_table"}

    # Should raise FlowExecutionError, not return string silently
    with pytest.raises(FlowExecutionError) as exc_info:
        executor._process_table_selection(choice_source, "some_selection")

    error_message = str(exc_info.value)
    assert "nonexistent_table" in error_message
    assert "not found in system" in error_message
    assert "Available tables" in error_message


def test_entry_not_found_raises_explicit_error(sample_system_with_weapon_table):
    """Test that missing entries raise explicit errors instead of falling back silently."""
    system = sample_system_with_weapon_table
    object_service = ObjectInstantiationService(system)

    executor = PlayerChoiceStepExecutor(
        system=system,
        template_resolver=None,
        action_executor=lambda *args: GrimoireContext(),
        object_service=object_service,
    )

    choice_source = {"table": "weapons"}

    # Should raise FlowExecutionError for non-existent entry
    with pytest.raises(FlowExecutionError) as exc_info:
        executor._process_table_selection(choice_source, "NonexistentWeapon")

    error_message = str(exc_info.value)
    assert "NonexistentWeapon" in error_message
    assert "not found in table" in error_message
    assert "Available entries" in error_message


def test_no_choice_source_returns_string_as_is(sample_system_with_weapon_table):
    """Test that selections without choice_source return strings as-is."""
    system = sample_system_with_weapon_table
    object_service = ObjectInstantiationService(system)

    executor = PlayerChoiceStepExecutor(
        system=system,
        template_resolver=None,
        action_executor=lambda *args: GrimoireContext(),
        object_service=object_service,
    )

    # No choice_source (static choices)
    result = executor._process_table_selection(None, "some_static_choice")

    # Should return string as-is for static choices
    assert isinstance(result, str)
    assert result == "some_static_choice"
