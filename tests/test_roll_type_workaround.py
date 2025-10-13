"""Test for 'roll' type workaround in Knave system.

This test demonstrates the current limitation with custom primitive types in grimoire-model
and verifies that using 'str' type as a workaround functions correctly.
"""

import pytest
from grimoire_model import (
    AttributeDefinition,
    ModelDefinition,
    create_model_without_validation,
)
from grimoire_model.core.exceptions import ModelValidationError


class TestRollTypeWorkaround:
    """Test the 'roll' type issue and workaround."""

    def test_roll_type_fails(self):
        """Verify that 'roll' type currently fails in grimoire-model."""
        # Create weapon model with 'roll' type (this should fail)
        weapon_attrs = {
            "name": AttributeDefinition(type="str", required=True),
            "damage": AttributeDefinition(
                type="roll", required=True
            ),  # Custom primitive
        }

        weapon_def = ModelDefinition(
            id="weapon",
            name="Weapon",
            kind="model",
            description="Weapon model for test",
            version=1,
            attributes=weapon_attrs,
        )

        weapon_data = {
            "model": "weapon",
            "name": "Dagger",
            "damage": "1d6",  # Valid dice roll string
        }

        # This should fail with ModelValidationError
        with pytest.raises(ModelValidationError, match="Invalid model type 'roll'"):
            create_model_without_validation(weapon_def, weapon_data)

    def test_str_type_workaround_succeeds(self):
        """Verify that using 'str' type as workaround works."""
        # Create weapon model with 'str' type instead of 'roll'
        weapon_attrs = {
            "name": AttributeDefinition(type="str", required=True),
            "damage": AttributeDefinition(
                type="str", required=True
            ),  # Workaround: use str
        }

        weapon_def = ModelDefinition(
            id="weapon_str",
            name="WeaponStr",
            kind="model",
            description="Weapon model with string damage",
            version=1,
            attributes=weapon_attrs,
        )

        weapon_data = {
            "model": "weapon_str",
            "name": "Dagger",
            "damage": "1d6",  # Still a valid dice roll, just stored as string
        }

        # This should succeed
        weapon_obj = create_model_without_validation(weapon_def, weapon_data)

        # Verify the object was created correctly
        assert weapon_obj.name == "Dagger"
        assert weapon_obj.damage == "1d6"

    def test_inheritance_with_str_type_workaround(self):
        """Verify that inheritance works with str type workaround."""
        # Create base item model
        item_attrs = {
            "name": AttributeDefinition(type="str", required=True),
            "cost": AttributeDefinition(type="int", default=0),
        }

        item_def = ModelDefinition(
            id="item",
            name="Item",
            kind="model",
            description="Base item model",
            version=1,
            attributes=item_attrs,
        )

        # Create weapon model that extends item
        weapon_attrs = {
            "damage": AttributeDefinition(
                type="str", required=True
            ),  # Workaround: str instead of roll
            "weapon_type": AttributeDefinition(
                type="str", enum=["melee", "ranged"], default="melee"
            ),
        }

        weapon_def = ModelDefinition(
            id="weapon_inherit",
            name="WeaponInherit",
            kind="model",
            description="Weapon model with inheritance",
            version=1,
            extends=["item"],
            attributes=weapon_attrs,
        )

        # Register both models (simulating system loading)
        from grimoire_model import register_model

        register_model("test_system", item_def)
        register_model("test_system", weapon_def)

        weapon_data = {
            "model": "weapon_inherit",
            "name": "Dagger",
            "cost": 5,
            "damage": "1d6",
            "weapon_type": "melee",
        }

        # This should succeed with inheritance
        weapon_obj = create_model_without_validation(weapon_def, weapon_data)

        # Verify all attributes work correctly
        assert weapon_obj.name == "Dagger"  # From item
        assert weapon_obj.cost == 5  # From item
        assert weapon_obj.damage == "1d6"  # From weapon (str workaround)
        assert weapon_obj.weapon_type == "melee"  # From weapon

    def test_primitive_type_detection(self):
        """Demonstrate how grimoire-model detects primitive vs custom types."""
        from grimoire_model import (
            AttributeDefinition,
            ModelDefinition,
            create_model_without_validation,
        )

        # Create a simple test object to call _is_custom_model_type
        test_attrs = {"name": AttributeDefinition(type="str", required=True)}
        test_def = ModelDefinition(
            id="test",
            name="Test",
            kind="model",
            description="Test model",
            version=1,
            attributes=test_attrs,
        )

        test_data = {"model": "test", "name": "Test"}
        test_obj = create_model_without_validation(test_def, test_data)

        # Test primitive type detection
        assert not test_obj._is_custom_model_type("str")  # Should be primitive
        assert not test_obj._is_custom_model_type("int")  # Should be primitive
        assert not test_obj._is_custom_model_type("float")  # Should be primitive
        assert not test_obj._is_custom_model_type("bool")  # Should be primitive
        assert not test_obj._is_custom_model_type("list")  # Should be primitive
        assert not test_obj._is_custom_model_type("dict")  # Should be primitive

        # These are treated as custom model types (the issue)
        assert test_obj._is_custom_model_type("roll")  # Should be primitive but isn't
        assert test_obj._is_custom_model_type("weapon")  # Should be custom (correct)
        assert test_obj._is_custom_model_type("item")  # Should be custom (correct)
