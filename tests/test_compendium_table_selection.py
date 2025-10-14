"""Test to verify the compendium lookup fix for table selections."""

import pytest
from grimoire_context import GrimoireContext

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompendiumDefinition,
    CompleteSystem,
    ModelDefinition,
    SystemDefinition,
    TableDefinition,
)
from grimoire_studio.services.object_service import ObjectInstantiationService
from grimoire_studio.services.step_executors.player_choice import (
    PlayerChoiceStepExecutor,
)


@pytest.fixture
def system_with_weapon_compendium():
    """Create a system with weapon model, compendium, and table."""

    # Base item model
    item_model = ModelDefinition(
        id="item",
        kind="model",
        name="Item",
        description="Base model for items",
        attributes={
            "name": AttributeDefinition(type="str"),
            "description": AttributeDefinition(type="str", default=""),
            "cost": AttributeDefinition(type="int", default=0),
        },
    )

    # Weapon model extending item
    weapon_model = ModelDefinition(
        id="weapon",
        kind="model",
        name="Weapon",
        description="Weapon model extending item",
        extends=["item"],
        attributes={
            "damage": AttributeDefinition(type="str"),
            "type": AttributeDefinition(type="str", default="melee"),
        },
    )

    # Weapon compendium with full weapon data
    weapon_compendium = CompendiumDefinition(
        id="weapons",
        kind="compendium",
        name="Weapons",
        description="Collection of weapons",
        model="weapon",  # This compendium contains weapon objects
        entries={
            "dagger": {
                "name": "Dagger",
                "description": "A short blade",
                "cost": 5,
                "damage": "1d6",
                "type": "melee",
            },
            "sword": {
                "name": "Sword",
                "description": "A long blade",
                "cost": 15,
                "damage": "1d8",
                "type": "melee",
            },
        },
    )

    # Weapons table that references entries by ID
    weapons_table = TableDefinition(
        id="weapons",
        kind="table",
        name="Weapons",
        description="Random weapon selection",
        entry_type="weapon",
        entries=[
            {
                "range": "1",
                "value": "dagger",
            },  # String ID that should lookup in compendium
            {"range": "2", "value": "sword"},
        ],
    )

    system_def = SystemDefinition(id="test_system", kind="system", name="Test System")

    return CompleteSystem(
        system=system_def,
        models={
            "item": item_model,
            "weapon": weapon_model,
        },
        compendiums={
            "weapons": weapon_compendium,
        },
        tables={
            "weapons": weapons_table,
        },
    )


def test_table_selection_with_compendium_lookup(system_with_weapon_compendium):
    """Test that table selection looks up full object data from compendium."""
    system = system_with_weapon_compendium
    object_service = ObjectInstantiationService(system)

    # Create player choice executor
    executor = PlayerChoiceStepExecutor(
        system=system,
        template_resolver=None,
        action_executor=lambda *args: GrimoireContext(),
        object_service=object_service,
    )

    # Test selection of "dagger" from weapons table
    choice_source = {"table": "weapons"}
    result = executor._process_table_selection(choice_source, "dagger")

    print(f"Result: {result}")
    print(f"Result keys: {list(result.keys())}")

    # Should have full weapon data from compendium
    assert result["name"] == "Dagger", (
        f"Expected name 'Dagger', got {result.get('name')}"
    )
    assert result["description"] == "A short blade", (
        f"Expected description 'A short blade', got {result.get('description')}"
    )
    assert result["cost"] == 5, f"Expected cost 5, got {result.get('cost')}"
    assert result["damage"] == "1d6", (
        f"Expected damage '1d6', got {result.get('damage')}"
    )
    assert result["type"] == "melee", f"Expected type 'melee', got {result.get('type')}"
    assert result["model"] == "weapon", (
        f"Expected model 'weapon', got {result.get('model')}"
    )

    print("✅ SUCCESS: Weapon selection correctly looked up full data from compendium!")


def test_jinja2_template_with_compendium_weapon(system_with_weapon_compendium):
    """Test that Jinja2 templates work with weapon objects from compendium."""
    from grimoire_model.resolvers.template import Jinja2TemplateResolver

    system = system_with_weapon_compendium
    object_service = ObjectInstantiationService(system)

    executor = PlayerChoiceStepExecutor(
        system=system,
        template_resolver=None,
        action_executor=lambda *args: GrimoireContext(),
        object_service=object_service,
    )

    # Get weapon from table selection
    choice_source = {"table": "weapons"}
    weapon = executor._process_table_selection(choice_source, "dagger")

    # Test Jinja2 template resolution
    resolver = Jinja2TemplateResolver()
    context = {
        "inputs": {"item": weapon},
        "outputs": {"character": {"name": "Test Character"}},
    }

    # This should now work without errors
    template = "Item '{{ inputs.item.name }}' added to inventory of '{{ outputs.character.name }}'"
    result = resolver.resolve_template(template, context)

    expected = "Item 'Dagger' added to inventory of 'Test Character'"
    assert result == expected, f"Expected '{expected}', got '{result}'"

    print(f"✅ SUCCESS: Template resolved correctly: {result}")


def test_compendium_not_found_fallback(system_with_weapon_compendium):
    """Test fallback behavior when object not found in compendium."""
    system = system_with_weapon_compendium
    object_service = ObjectInstantiationService(system)

    executor = PlayerChoiceStepExecutor(
        system=system,
        template_resolver=None,
        action_executor=lambda *args: GrimoireContext(),
        object_service=object_service,
    )

    # Test selection of non-existent weapon
    choice_source = {"table": "weapons"}

    # First add a non-existent entry to the table for testing
    system.tables["weapons"].entries.append(
        {"range": "3", "value": "nonexistent_weapon"}
    )

    result = executor._process_table_selection(choice_source, "nonexistent_weapon")

    print(f"Fallback result: {result}")
    print(f"Fallback result keys: {list(result.keys())}")

    # Should create minimal object with warning
    assert result["model"] == "weapon"
    assert result["id"] == "nonexistent_weapon"
    # Should still have inherited defaults from item model
    assert "description" in result  # Should have default empty description
    assert "cost" in result  # Should have default cost 0

    print("✅ SUCCESS: Fallback behavior works when object not found in compendium")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
