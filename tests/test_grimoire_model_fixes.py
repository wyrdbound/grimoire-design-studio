"""
Test that verifies both GitHub issues are resolved in grimoire-model 0.3.2.

This test confirms:
1. Custom primitive types (like 'roll') work correctly
2. GrimoireModel attribute access works with both dict and attribute access
3. Template engine compatibility is restored
4. The Knave weapon model works end-to-end
"""

from unittest.mock import Mock

import pytest
from grimoire_model import AttributeDefinition, ModelDefinition

from grimoire_studio.models.grimoire_definitions import CompleteSystem
from grimoire_studio.services.object_service import ObjectInstantiationService


class TestGrimoireModelIssuesFixed:
    """Test that both grimoire-model issues are resolved."""

    def setup_method(self):
        """Create test system with models that replicate Knave patterns."""
        # Create test models that replicate Knave system patterns

        # Base item model
        item_model = ModelDefinition(
            id="item",
            name="Item",
            description="Base item model",
            version=1,
            attributes={
                "name": AttributeDefinition(type="str", required=True),
                "cost": AttributeDefinition(type="int", default=0),
                "description": AttributeDefinition(type="str", optional=True),
            },
        )

        # Breakable model (mixin)
        breakable_model = ModelDefinition(
            id="breakable",
            name="Breakable",
            description="Breakable item mixin",
            version=1,
            attributes={
                "quality": AttributeDefinition(type="int", default=3),
            },
        )

        # Weapon model (extends item + breakable, uses 'roll' type)
        weapon_model = ModelDefinition(
            id="weapon",
            name="Weapon",
            description="Weapon model with roll damage type",
            version=1,
            extends=["item", "breakable"],
            attributes={
                "damage": AttributeDefinition(type="roll", required=True),
                "type": AttributeDefinition(
                    type="str", enum=["melee", "ranged"], default="melee"
                ),
                "hands": AttributeDefinition(type="int", default=1),
            },
        )

        # Create mock system
        self.system = Mock(spec=CompleteSystem)
        self.system.models = {
            "item": item_model,
            "breakable": breakable_model,
            "weapon": weapon_model,
        }
        self.system.system = Mock()
        self.system.system.id = "test_system"

        self.obj_service = ObjectInstantiationService(self.system)

    def test_roll_primitive_type_registration(self):
        """Test that 'roll' primitive type is registered and works."""
        from grimoire_model import is_primitive_type

        # Verify roll is now registered as primitive type
        assert is_primitive_type("roll"), (
            "'roll' should be registered as primitive type"
        )

    def test_weapon_creation_with_roll_type(self):
        """Test that weapon objects can be created with 'roll' damage type."""
        weapon_data = {
            "model": "weapon",
            "name": "Dagger",
            "damage": "1d6",  # 'roll' type attribute
            "quality": 3,
            "cost": 5,
            "description": "A short, double-edged blade.",
            "type": "melee",
            "hands": 1,
        }

        # This should succeed without ModelValidationError
        weapon = self.obj_service.create_object_without_validation(weapon_data)

        # Verify all data is correct
        assert weapon["name"] == "Dagger"
        assert weapon["damage"] == "1d6"
        assert weapon["cost"] == 5
        assert weapon["type"] == "melee"

    def test_attribute_access_works(self):
        """Test that both dict and attribute access work."""
        weapon_data = {
            "model": "weapon",
            "name": "Longsword",
            "damage": "1d8+1",
            "cost": 15,
            "type": "melee",
        }

        weapon = self.obj_service.create_object_without_validation(weapon_data)

        # Test attribute access (new functionality)
        assert weapon.name == "Longsword"
        assert weapon.damage == "1d8+1"
        assert weapon.cost == 15
        assert weapon.type == "melee"

        # Test dictionary access (existing functionality)
        assert weapon["name"] == "Longsword"
        assert weapon["damage"] == "1d8+1"
        assert weapon["cost"] == 15
        assert weapon["type"] == "melee"

        # Test both give same results
        assert weapon.name == weapon["name"]
        assert weapon.damage == weapon["damage"]
        assert weapon.cost == weapon["cost"]

    def test_getattr_works_correctly(self):
        """Test that getattr returns actual values, not defaults."""
        weapon_data = {"model": "weapon", "name": "Rapier", "damage": "1d6", "cost": 20}

        weapon = self.obj_service.create_object_without_validation(weapon_data)

        # getattr should return actual values
        assert weapon.name == "Rapier"
        assert weapon.damage == "1d6"
        assert weapon.cost == 20

        # getattr should return default for non-existent attributes
        assert getattr(weapon, "nonexistent", "DEFAULT") == "DEFAULT"

    def test_hasattr_works_correctly(self):
        """Test that hasattr correctly detects model attributes."""
        weapon_data = {
            "model": "weapon",
            "name": "Scimitar",
            "damage": "1d6",
        }

        weapon = self.obj_service.create_object_without_validation(weapon_data)

        # hasattr should return True for model attributes
        assert hasattr(weapon, "name")
        assert hasattr(weapon, "damage")
        assert hasattr(weapon, "cost")  # Default value attributes should also work

        # hasattr should return False for non-existent attributes
        assert not hasattr(weapon, "nonexistent")

    def test_template_engine_compatibility(self):
        """Test that template engines can use attribute access."""
        try:
            from jinja2 import Template
        except ImportError:
            pytest.skip("Jinja2 not available")

        weapon_data = {
            "model": "weapon",
            "name": "Battleaxe",
            "damage": "1d8",
            "cost": 10,
        }

        weapon = self.obj_service.create_object_without_validation(weapon_data)

        # Template using attribute access should work
        template_str = "{{ weapon.name }} deals {{ weapon.damage }} damage for {{ weapon.cost }} gold"
        template = Template(template_str)

        result = template.render(weapon=weapon)
        assert result == "Battleaxe deals 1d8 damage for 10 gold"

    def test_inheritance_with_custom_primitive_types(self):
        """Test that inheritance works with custom primitive types."""
        # This tests the original failing scenario: weapon extends item + breakable with roll type
        weapon_data = {
            "model": "weapon",
            "name": "Greatsword",  # From item inheritance
            "cost": 50,  # From item inheritance
            "quality": 4,  # From breakable inheritance
            "damage": "2d6",  # Custom roll primitive type
            "type": "melee",  # Weapon-specific
            "hands": 2,  # Weapon-specific
        }

        # This should work with full inheritance chain and custom primitive type
        weapon = self.obj_service.create_object_without_validation(weapon_data)

        # Verify inherited attributes work
        assert weapon.name == "Greatsword"  # item
        assert weapon.cost == 50  # item
        assert weapon.quality == 4  # breakable

        # Verify weapon-specific attributes work
        assert weapon.damage == "2d6"  # roll primitive type
        assert weapon.type == "melee"
        assert weapon.hands == 2

    def test_original_error_scenario_resolved(self):
        """Test the exact scenario from the original error report."""
        # This recreates the failing compendium lookup scenario
        dagger_data = {
            "model": "weapon",
            "name": "Dagger",
            "damage": "1d6",
            "quality": 3,
            "cost": 5,
            "description": "A short, double-edged blade. Easily concealed and quick to draw, useful for both combat and utility tasks.",
        }

        # This was failing before with:
        # "Invalid model type 'roll' in model 'weapon'"
        # Now it should work
        dagger = self.obj_service.create_object_without_validation(dagger_data)

        # Template access that was failing with:
        # "'grimoire_model.core.model.GrimoireModel object' has no attribute 'name'"
        # Now it should work
        assert dagger.name == "Dagger"

        # Verify the template string that was failing now works
        template_vars = {"inputs": {"item": dagger}}
        item_name = getattr(template_vars["inputs"]["item"], "name", None)
        assert item_name == "Dagger", (
            "Template resolution should work for {{ inputs.item.name }}"
        )
