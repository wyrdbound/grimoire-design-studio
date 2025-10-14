"""
Test suite for GrimoireModel Jinja2 template stringification bug.

This test documents and reproduces the issue where Jinja2TemplateResolver
in grimoire-model converts entire data structures to strings when they
contain GrimoireModel objects.

Once the upstream issue is fixed in grimoire-model, these tests should pass.
"""

import pytest
from grimoire_model import (
    AttributeDefinition,
    Jinja2TemplateResolver,
    ModelDefinition,
    create_model_without_validation,
)


class TestGrimoireModelJinja2Stringification:
    """Test cases documenting the GrimoireModel stringification bug."""

    @pytest.fixture
    def weapon_model(self):
        """Create a weapon GrimoireModel for testing."""
        attrs = {
            "name": AttributeDefinition(type="str", required=True),
            "type": AttributeDefinition(type="str", required=True),
            "damage": AttributeDefinition(type="str", default="1d4"),
        }

        weapon_def = ModelDefinition(
            id="weapon",
            name="Weapon",
            kind="model",
            description="Weapon item",
            version=1,
            attributes=attrs,
        )

        weapon_data = {
            "model": "weapon",
            "name": "Dagger",
            "type": "melee",
            "damage": "1d6",
        }
        return create_model_without_validation(weapon_def, weapon_data)

    @pytest.fixture
    def resolver(self):
        """Create Jinja2TemplateResolver instance."""
        return Jinja2TemplateResolver()

    def test_direct_grimoire_model_reference_works(self, resolver, weapon_model):
        """Test that direct GrimoireModel references work correctly."""
        context = {"item": weapon_model}
        result = resolver.resolve_template("{{ item }}", context)

        # This should work correctly
        assert isinstance(result, type(weapon_model))
        assert result.name == "Dagger"

    def test_regular_list_concatenation_works(self, resolver):
        """Test that list concatenation with regular objects works."""
        context = {
            "inventory": [{"name": "Sword", "type": "weapon"}],
            "item": {"name": "Shield", "type": "armor"},
        }
        result = resolver.resolve_template("{{ inventory + [item] }}", context)

        # This should work correctly
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Sword"
        assert result[1]["name"] == "Shield"

    @pytest.mark.xfail(reason="GrimoireModel in list gets stringified - upstream bug")
    def test_list_with_grimoire_model_should_preserve_type(
        self, resolver, weapon_model
    ):
        """Test that lists containing GrimoireModel should stay as lists."""
        context = {"item": weapon_model}
        result = resolver.resolve_template("{{ [item] }}", context)

        # This currently fails - returns string instead of list
        assert isinstance(result, list), f"Expected list, got {type(result)}: {result}"
        assert len(result) == 1
        assert isinstance(result[0], type(weapon_model))
        assert result[0].name == "Dagger"

    @pytest.mark.xfail(
        reason="List concatenation with GrimoireModel gets stringified - upstream bug"
    )
    def test_list_concatenation_with_grimoire_model_should_preserve_type(
        self, resolver, weapon_model
    ):
        """Test that list concatenation with GrimoireModel should stay as list."""
        context = {"inventory": [], "item": weapon_model}
        result = resolver.resolve_template("{{ inventory + [item] }}", context)

        # This currently fails - returns string instead of list
        assert isinstance(result, list), f"Expected list, got {type(result)}: {result}"
        assert len(result) == 1
        assert isinstance(result[0], type(weapon_model))
        assert result[0].name == "Dagger"

    @pytest.mark.xfail(
        reason="Mixed list concatenation with GrimoireModel gets stringified - upstream bug"
    )
    def test_mixed_list_concatenation_with_grimoire_model(self, resolver, weapon_model):
        """Test concatenating existing items with GrimoireModel."""
        existing_item = {"name": "Existing Item", "type": "item"}
        context = {"inventory": [existing_item], "item": weapon_model}
        result = resolver.resolve_template("{{ inventory + [item] }}", context)

        # This currently fails - returns string instead of list
        assert isinstance(result, list), f"Expected list, got {type(result)}: {result}"
        assert len(result) == 2
        assert result[0] == existing_item  # Regular dict should be preserved
        assert isinstance(
            result[1], type(weapon_model)
        )  # GrimoireModel should be preserved

    def test_current_stringification_behavior(self, resolver, weapon_model):
        """Document the current broken behavior for debugging."""
        context = {"inventory": [], "item": weapon_model}
        result = resolver.resolve_template("{{ inventory + [item] }}", context)

        # Currently this returns a string representation
        assert isinstance(result, str)
        assert "GrimoireModel" in result
        assert "Dagger" in result
        # This is the current broken behavior that should be fixed

    @pytest.mark.xfail(reason="Dict with GrimoireModel gets stringified - upstream bug")
    def test_dict_with_grimoire_model_should_preserve_type(
        self, resolver, weapon_model
    ):
        """Test that dicts containing GrimoireModel should stay as dicts."""
        context = {"item": weapon_model}
        result = resolver.resolve_template("{{ {'weapon': item} }}", context)

        # This currently fails - returns string instead of dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result}"
        assert "weapon" in result
        assert isinstance(result["weapon"], type(weapon_model))


class TestWorkaroundStrategies:
    """Test strategies to work around the stringification issue."""

    @pytest.fixture
    def weapon_model(self):
        """Create a weapon GrimoireModel for testing."""
        attrs = {
            "name": AttributeDefinition(type="str", required=True),
            "type": AttributeDefinition(type="str", required=True),
        }

        weapon_def = ModelDefinition(
            id="weapon",
            name="Weapon",
            kind="model",
            description="Weapon item",
            version=1,
            attributes=attrs,
        )

        weapon_data = {"model": "weapon", "name": "Dagger", "type": "melee"}
        return create_model_without_validation(weapon_def, weapon_data)

    def test_workaround_avoid_templates_for_grimoire_model_collections(
        self, weapon_model
    ):
        """Test workaround: avoid Jinja2 templates for GrimoireModel collections."""
        # Instead of using templates, build the list programmatically
        inventory = []
        inventory.append(weapon_model)

        # This works because no template evaluation is involved
        assert isinstance(inventory, list)
        assert len(inventory) == 1
        assert isinstance(inventory[0], type(weapon_model))
        assert inventory[0].name == "Dagger"

    def test_workaround_separate_template_steps(self):
        """Test workaround: use separate template steps to avoid complex structures."""
        from grimoire_context import GrimoireContext
        from grimoire_model import Jinja2TemplateResolver

        class _TemplateResolverAdapter:
            def __init__(self, resolver: Jinja2TemplateResolver) -> None:
                self._resolver = resolver

            def resolve_template(self, template_str: str, context_dict: dict):
                return self._resolver.resolve_template(template_str, context_dict)

        # Set up context with template resolver
        template_resolver = _TemplateResolverAdapter(Jinja2TemplateResolver())
        context = GrimoireContext()
        context = context.set_template_resolver(template_resolver)

        # Instead of: "{{ inventory + [item] }}"
        # Use separate steps:

        # Step 1: Get the inventory
        inventory = []
        context = context.set_variable("temp.inventory", inventory)

        # Step 2: Get the item (regular dict to avoid the bug)
        item = {"name": "Sword", "type": "weapon"}
        context = context.set_variable("temp.item", item)

        # Step 3: Build list programmatically (no templates)
        inventory_copy = context.get_variable("temp.inventory").copy()
        new_item = context.get_variable("temp.item")
        inventory_copy.append(new_item)

        # This avoids the template stringification issue
        assert isinstance(inventory_copy, list)
        assert len(inventory_copy) == 1
        assert inventory_copy[0]["name"] == "Sword"


if __name__ == "__main__":
    # Run with: python test_grimoire_model_jinja2_bug.py
    pytest.main([__file__, "-v"])
