"""Tests for GRIMOIRE data models and YAML parsing.

This module tests all the GRIMOIRE dataclass definitions to ensure they can
correctly parse YAML data and handle various edge cases.
"""

import pytest

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompendiumDefinition,
    FlowDefinition,
    ModelDefinition,
    PromptDefinition,
    SourceDefinition,
    SystemDefinition,
    TableDefinition,
)


class TestSystemDefinition:
    """Test SystemDefinition parsing."""

    def test_basic_system_definition(self):
        """Test basic system definition parsing."""
        data = {
            "id": "test_system",
            "kind": "system",
            "name": "Test System",
            "description": "A test RPG system",
            "version": 1,
        }

        system = SystemDefinition.from_dict(data)

        assert system.id == "test_system"
        assert system.kind == "system"
        assert system.name == "Test System"
        assert system.description == "A test RPG system"
        assert system.version == 1
        assert system.currency is None
        assert system.credits is None

    def test_system_with_currency(self):
        """Test system definition with currency."""
        data = {
            "id": "test_system",
            "kind": "system",
            "name": "Test System",
            "version": 1,
            "currency": {
                "base_unit": "copper",
                "denominations": {
                    "silver": {"name": "Silver", "symbol": "s", "value": 10},
                    "gold": {"name": "Gold", "symbol": "g", "value": 100},
                },
            },
        }

        system = SystemDefinition.from_dict(data)

        assert system.currency is not None
        assert system.currency.base_unit == "copper"
        assert len(system.currency.denominations) == 2
        assert "silver" in system.currency.denominations
        assert "gold" in system.currency.denominations

    def test_system_with_credits(self):
        """Test system definition with credits."""
        data = {
            "id": "test_system",
            "kind": "system",
            "name": "Test System",
            "version": 1,
            "credits": {
                "author": "Test Author",
                "license": "MIT",
                "publisher": "Test Publisher",
                "source_url": "https://example.com",
            },
        }

        system = SystemDefinition.from_dict(data)

        assert system.credits is not None
        assert system.credits.author == "Test Author"
        assert system.credits.license == "MIT"
        assert system.credits.publisher == "Test Publisher"
        assert system.credits.source_url == "https://example.com"


class TestModelDefinition:
    """Test ModelDefinition parsing."""

    def test_basic_model_definition(self):
        """Test basic model definition parsing."""
        data = {
            "id": "character",
            "kind": "model",
            "name": "Character",
            "description": "A player character",
            "version": 1,
            "attributes": {
                "name": {"type": "str", "required": True},
                "level": {"type": "int", "default": 1},
            },
            "validations": [],
        }

        model = ModelDefinition.from_dict(data)

        assert model.id == "character"
        assert model.kind == "model"
        assert model.name == "Character"
        assert model.description == "A player character"
        assert model.version == 1
        assert len(model.attributes) == 2
        assert "name" in model.attributes
        assert "level" in model.attributes
        assert len(model.validations) == 0
        assert model.extends == []

    def test_model_with_inheritance(self):
        """Test model definition with inheritance."""
        data = {
            "id": "weapon",
            "kind": "model",
            "name": "Weapon",
            "extends": ["item", "breakable"],
            "attributes": {
                "damage": {"type": "str", "required": True},
            },
            "validations": [],
        }

        model = ModelDefinition.from_dict(data)

        assert model.extends == ["item", "breakable"]
        assert len(model.attributes) == 1
        assert "damage" in model.attributes

    def test_model_with_nested_attributes(self):
        """Test model with nested attribute structure."""
        data = {
            "id": "character",
            "kind": "model",
            "name": "Character",
            "attributes": {
                "abilities": {
                    "strength": {"type": "int", "min": 1, "max": 20},
                    "dexterity": {"type": "int", "min": 1, "max": 20},
                }
            },
            "validations": [],
        }

        model = ModelDefinition.from_dict(data)

        assert "abilities" in model.attributes
        # The nested structure should be preserved as a dict
        abilities = model.attributes["abilities"]
        assert isinstance(abilities, dict)
        assert "strength" in abilities
        assert "dexterity" in abilities


class TestFlowDefinition:
    """Test FlowDefinition parsing."""

    def test_basic_flow_definition(self):
        """Test basic flow definition parsing."""
        data = {
            "id": "character_creation",
            "kind": "flow",
            "name": "Character Creation",
            "description": "Create a new character",
            "version": 1,
            "inputs": [{"type": "str", "id": "player_name", "required": True}],
            "outputs": [{"type": "character", "id": "new_character", "validate": True}],
            "variables": [
                {"type": "int", "id": "rolled_hp", "description": "Hit points rolled"}
            ],
            "steps": [
                {
                    "id": "roll_stats",
                    "name": "Roll Statistics",
                    "type": "dice_roll",
                    "roll": "4d6kh3",
                    "actions": [],
                }
            ],
        }

        flow = FlowDefinition.from_dict(data)

        assert flow.id == "character_creation"
        assert flow.kind == "flow"
        assert flow.name == "Character Creation"
        assert flow.description == "Create a new character"
        assert flow.version == 1
        assert len(flow.inputs) == 1
        assert len(flow.outputs) == 1
        assert len(flow.variables) == 1
        assert len(flow.steps) == 1

        # Check input
        input_def = flow.inputs[0]
        assert input_def.type == "str"
        assert input_def.id == "player_name"
        assert input_def.required is True

        # Check output
        output_def = flow.outputs[0]
        assert output_def.type == "character"
        assert output_def.id == "new_character"
        assert output_def.validate is True

        # Check variable
        variable_def = flow.variables[0]
        assert variable_def.type == "int"
        assert variable_def.id == "rolled_hp"
        assert variable_def.description == "Hit points rolled"

        # Check step
        step_def = flow.steps[0]
        assert step_def.id == "roll_stats"
        assert step_def.name == "Roll Statistics"
        assert step_def.type == "dice_roll"

    def test_flow_with_resume_points(self):
        """Test flow definition with resume points."""
        data = {
            "id": "long_process",
            "kind": "flow",
            "name": "Long Process",
            "version": 1,
            "inputs": [],
            "outputs": [],
            "variables": [],
            "steps": [],
            "resume_points": ["step_1", "step_5", "final_step"],
        }

        flow = FlowDefinition.from_dict(data)

        assert len(flow.resume_points) == 3
        assert "step_1" in flow.resume_points
        assert "step_5" in flow.resume_points
        assert "final_step" in flow.resume_points

    def test_flow_step_with_minimal_fields(self):
        """Test flow step with minimal required fields."""
        data = {
            "id": "test_flow",
            "kind": "flow",
            "name": "Test Flow",
            "version": 1,
            "inputs": [],
            "outputs": [],
            "variables": [],
            "steps": [
                {
                    "id": "completion_step",
                    "name": "Complete Process",
                    "type": "completion",
                    "actions": [],
                }
            ],
        }

        flow = FlowDefinition.from_dict(data)

        assert len(flow.steps) == 1
        step = flow.steps[0]
        assert step.id == "completion_step"
        assert step.name == "Complete Process"
        assert step.type == "completion"


class TestCompendiumDefinition:
    """Test CompendiumDefinition parsing."""

    def test_basic_compendium_definition(self):
        """Test basic compendium definition parsing."""
        data = {
            "id": "weapons",
            "kind": "compendium",
            "name": "Basic Weapons",
            "model": "weapon",
            "version": 1,
            "entries": {
                "sword": {"name": "Sword", "damage": "1d8", "cost": 10},
                "dagger": {"name": "Dagger", "damage": "1d4", "cost": 2},
            },
        }

        compendium = CompendiumDefinition.from_dict(data)

        assert compendium.id == "weapons"
        assert compendium.kind == "compendium"
        assert compendium.name == "Basic Weapons"
        assert compendium.model == "weapon"
        assert compendium.version == 1
        assert len(compendium.entries) == 2
        assert "sword" in compendium.entries
        assert "dagger" in compendium.entries

        # Check entry content
        sword = compendium.entries["sword"]
        assert sword["name"] == "Sword"
        assert sword["damage"] == "1d8"
        assert sword["cost"] == 10

    def test_empty_compendium(self):
        """Test compendium with no entries."""
        data = {
            "id": "empty_compendium",
            "kind": "compendium",
            "name": "Empty Compendium",
            "model": "item",
        }

        compendium = CompendiumDefinition.from_dict(data)

        assert compendium.id == "empty_compendium"
        assert len(compendium.entries) == 0
        assert compendium.model == "item"


class TestTableDefinition:
    """Test TableDefinition parsing."""

    def test_basic_table_definition(self):
        """Test basic table definition parsing."""
        data = {
            "id": "random_encounters",
            "kind": "table",
            "name": "Random Encounters",
            "description": "Table of random encounters",
            "version": 1,
            "dice": "1d20",
            "entries": [
                {"roll": "1-5", "result": "Goblin patrol"},
                {"roll": "6-10", "result": "Wild animals"},
                {"roll": "11-15", "result": "Traveling merchants"},
                {"roll": "16-20", "result": "Nothing happens"},
            ],
        }

        table = TableDefinition.from_dict(data)

        assert table.id == "random_encounters"
        assert table.kind == "table"
        assert table.name == "Random Encounters"
        assert table.description == "Table of random encounters"
        assert table.version == 1
        assert table.dice == "1d20"
        assert len(table.entries) == 4

        # Check first entry
        first_entry = table.entries[0]
        assert first_entry["roll"] == "1-5"
        assert first_entry["result"] == "Goblin patrol"

    def test_table_without_dice(self):
        """Test table definition without dice specification."""
        data = {
            "id": "simple_list",
            "kind": "table",
            "name": "Simple List",
            "entries": [{"result": "Option A"}, {"result": "Option B"}],
        }

        table = TableDefinition.from_dict(data)

        assert table.dice is None
        assert len(table.entries) == 2


class TestSourceDefinition:
    """Test SourceDefinition parsing."""

    def test_basic_source_definition(self):
        """Test basic source definition parsing."""
        data = {
            "id": "core_rulebook",
            "kind": "source",
            "name": "Core Rulebook",
            "author": "Game Designer",
            "type": "rulebook",
            "description": "The main rulebook for the game",
            "version": 1,
        }

        source = SourceDefinition.from_dict(data)

        assert source.id == "core_rulebook"
        assert source.kind == "source"
        assert source.name == "Core Rulebook"
        assert source.author == "Game Designer"
        assert source.type == "rulebook"
        assert source.description == "The main rulebook for the game"
        assert source.version == 1


class TestPromptDefinition:
    """Test PromptDefinition parsing."""

    def test_basic_prompt_definition(self):
        """Test basic prompt definition parsing."""
        data = {
            "id": "character_description",
            "kind": "prompt",
            "name": "Character Description Generator",
            "description": "Generates character descriptions",
            "version": 1,
            "template": "Generate a description for a character named {{ character.name }}",
            "variables": {"character": {"type": "character", "required": True}},
        }

        prompt = PromptDefinition.from_dict(data)

        assert prompt.id == "character_description"
        assert prompt.kind == "prompt"
        assert prompt.name == "Character Description Generator"
        assert prompt.description == "Generates character descriptions"
        assert prompt.version == 1
        assert (
            prompt.template
            == "Generate a description for a character named {{ character.name }}"
        )
        assert len(prompt.variables) == 1

        # Check variable (variables is stored as dict)
        assert len(prompt.variables) == 1
        assert "character" in prompt.variables
        variable = prompt.variables["character"]
        assert variable["type"] == "character"
        assert variable["required"] is True


class TestAttributeDefinition:
    """Test AttributeDefinition parsing."""

    def test_basic_attribute_definition(self):
        """Test basic attribute definition parsing."""
        data = {
            "type": "str",
            "optional": False,
            "default": "Unknown",
            "range": "1..100",
        }

        attr = AttributeDefinition.from_dict(data)

        assert attr.type == "str"
        assert attr.optional is False
        assert attr.default == "Unknown"
        assert attr.range == "1..100"

    def test_minimal_attribute_definition(self):
        """Test minimal attribute definition parsing."""
        data = {"type": "int"}

        attr = AttributeDefinition.from_dict(data)

        assert attr.type == "int"
        assert attr.optional is None
        assert attr.default is None
        assert attr.range is None


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_missing_required_fields(self):
        """Test that missing required fields raise appropriate errors."""
        data = {
            "kind": "system",
            "name": "Test System",
            # Missing required 'id' field
        }

        with pytest.raises(KeyError):
            SystemDefinition.from_dict(data)

    def test_default_values(self):
        """Test that default values are properly applied."""
        data = {
            "id": "test_system",
            "kind": "system",
            "name": "Test System",
            # No version specified - should default to 1
        }

        system = SystemDefinition.from_dict(data)
        assert system.version == 1

    def test_empty_collections(self):
        """Test handling of empty collections."""
        data = {
            "id": "test_flow",
            "kind": "flow",
            "name": "Test Flow",
            "inputs": [],
            "outputs": [],
            "variables": [],
            "steps": [],
        }

        flow = FlowDefinition.from_dict(data)

        assert len(flow.inputs) == 0
        assert len(flow.outputs) == 0
        assert len(flow.variables) == 0
        assert len(flow.steps) == 0
        assert len(flow.resume_points) == 0  # Should default to empty list


class TestIntegrationWithRealData:
    """Test integration with real-world GRIMOIRE data structures."""

    def test_knave_style_system(self):
        """Test parsing a Knave-style system definition."""
        data = {
            "id": "knave",
            "kind": "system",
            "name": "Knave (1st Edition)",
            "description": "A rules-light fantasy RPG focused on exploration and creativity",
            "version": 1,
            "currency": {"base_unit": "copper", "conversion_rates": {}},
            "credits": {
                "author": "Ben Milton",
                "version": "1.0",
                "license": "CC BY 4.0",
                "source": "Knave RPG by Ben Milton",
            },
        }

        system = SystemDefinition.from_dict(data)

        assert system.id == "knave"
        assert system.name == "Knave (1st Edition)"
        assert system.currency is not None
        assert system.currency.base_unit == "copper"
        assert system.credits is not None
        assert system.credits.author == "Ben Milton"

    def test_complex_model_structure(self):
        """Test parsing a complex model with nested attributes."""
        data = {
            "id": "character",
            "kind": "model",
            "name": "Knave",
            "description": "A Knave character with abilities, traits, and equipment",
            "extends": [],
            "attributes": {
                "name": {"type": "str", "required": True},
                "abilities": {
                    "strength": {"type": "int", "min": 1, "max": 20},
                    "dexterity": {"type": "int", "min": 1, "max": 20},
                    "constitution": {"type": "int", "min": 1, "max": 20},
                    "intelligence": {"type": "int", "min": 1, "max": 20},
                    "wisdom": {"type": "int", "min": 1, "max": 20},
                    "charisma": {"type": "int", "min": 1, "max": 20},
                },
                "traits": {
                    "physique": {"type": "str"},
                    "face": {"type": "str"},
                    "skin": {"type": "str"},
                    "hair": {"type": "str"},
                    "clothing": {"type": "str"},
                    "virtue": {"type": "str"},
                    "vice": {"type": "str"},
                    "speech": {"type": "str"},
                    "background": {"type": "str"},
                    "misfortune": {"type": "str"},
                },
            },
            "validations": [
                {
                    "expression": "abilities.strength >= 1 and abilities.strength <= 20",
                    "message": "Strength must be 1-20",
                },
                {"expression": "len(name) > 0", "message": "Name cannot be empty"},
            ],
        }

        model = ModelDefinition.from_dict(data)

        assert model.id == "character"
        assert model.name == "Knave"
        assert "abilities" in model.attributes
        assert "traits" in model.attributes
        assert len(model.validations) == 2

        # Check nested structure preservation
        abilities = model.attributes["abilities"]
        assert isinstance(abilities, dict)
        assert "strength" in abilities
        assert "charisma" in abilities

        traits = model.attributes["traits"]
        assert isinstance(traits, dict)
        assert "physique" in traits
        assert "misfortune" in traits
