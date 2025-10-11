"""Test for template resolver GrimoireModel string conversion issue.

This test reproduces the issue where GrimoireModel objects are converted to
string representations when resolved through templates with dotted paths.
"""

import pytest
from grimoire_model.resolvers.template import Jinja2TemplateResolver

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompleteSystem,
    ModelDefinition,
    SystemDefinition,
)
from grimoire_studio.resolvers.template import FixedJinja2TemplateResolver
from grimoire_studio.services.object_service import ObjectInstantiationService


@pytest.fixture
def sample_system():
    """Create a simple system for testing."""
    character_model = ModelDefinition(
        id="character",
        kind="model",
        name="Character",
        description="A player character",
        attributes={
            "name": AttributeDefinition(type="str"),
            "level": AttributeDefinition(type="int", default=1),
        },
    )

    system_def = SystemDefinition(id="test_system", kind="system", name="Test System")

    return CompleteSystem(system=system_def, models={"character": character_model})


class TestTemplateResolverIssue:
    """Test cases for template resolver GrimoireModel conversion issue."""

    def test_simple_variable_preserves_grimoire_model(self, sample_system):
        """Test that simple variable references preserve GrimoireModel objects."""
        resolver = Jinja2TemplateResolver()

        # Create a real GrimoireModel object using ObjectInstantiationService
        service = ObjectInstantiationService(sample_system)
        grimoire_obj = service.create_object_without_validation(
            {"model": "character", "name": "Test Character", "level": 5}
        )

        context = {"character": grimoire_obj}

        # This should work - simple variable reference
        result = resolver.resolve_template("{{ character }}", context)

        # Debug: Print what we got
        print(f"Simple variable result type: {type(result)}")
        print(f"Simple variable result: {result}")

        # Check if it's preserved correctly
        if isinstance(result, str):
            print("❌ Simple variable converted to string (unexpected)")
            raise AssertionError(
                f"Simple variable should preserve GrimoireModel, got string: {result}"
            )
        else:
            print("✅ Simple variable preserved GrimoireModel")

    def test_dotted_path_converts_to_string(self, sample_system):
        """Test that demonstrates the issue with dotted paths converting to string."""
        resolver = Jinja2TemplateResolver()

        # Create a real GrimoireModel object using ObjectInstantiationService
        service = ObjectInstantiationService(sample_system)
        grimoire_obj = service.create_object_without_validation(
            {"model": "character", "name": "Test Character", "level": 5}
        )

        context = {"outputs": {"knave": grimoire_obj}}

        # This currently fails - dotted path reference gets converted to string
        result = resolver.resolve_template("{{ outputs.knave }}", context)

        # Debug: Print what we got
        print(f"Dotted path result type: {type(result)}")
        print(f"Dotted path result: {result}")

        # Currently this will be a string representation, not the original object
        assert isinstance(result, str), "Current behavior: converts to string"
        assert "GrimoireModel" in result, (
            "String representation should contain class name"
        )

    def test_dotted_path_should_preserve_grimoire_model(self, sample_system):
        """Test that shows what the expected behavior should be."""
        resolver = Jinja2TemplateResolver()

        # Create a real GrimoireModel object using ObjectInstantiationService
        service = ObjectInstantiationService(sample_system)
        grimoire_obj = service.create_object_without_validation(
            {"model": "character", "name": "Test Character", "level": 5}
        )

        context = {"outputs": {"knave": grimoire_obj}}

        # This should preserve the original object (after fix)
        resolver.resolve_template("{{ outputs.knave }}", context)

        # After the fix, this should be the original GrimoireModel object
        # For now, we'll skip this test as it will fail with current implementation
        pytest.skip("This test will pass after implementing the fixed resolver")


class TestFixedTemplateResolverTypePreservation:
    """Test cases to verify that the fixed resolver preserves all types, not just GrimoireModel."""

    def test_fixed_resolver_preserves_dict(self):
        """Test that fixed resolver preserves dict objects."""
        from grimoire_studio.resolvers.template import FixedJinja2TemplateResolver

        resolver = FixedJinja2TemplateResolver()

        test_dict = {"key1": "value1", "key2": 42, "nested": {"inner": "value"}}
        context = {"outputs": {"data": test_dict}}

        result = resolver.resolve_template("{{ outputs.data }}", context)

        # Should preserve the original dict, not convert to string
        assert isinstance(result, dict)
        assert result == test_dict
        assert result["key1"] == "value1"
        assert result["nested"]["inner"] == "value"

    def test_fixed_resolver_preserves_list(self):
        """Test that fixed resolver preserves list objects."""
        from grimoire_studio.resolvers.template import FixedJinja2TemplateResolver

        resolver = FixedJinja2TemplateResolver()

        test_list = ["item1", "item2", {"nested": "dict"}, 42]
        context = {"outputs": {"items": test_list}}

        result = resolver.resolve_template("{{ outputs.items }}", context)

        # Should preserve the original list, not convert to string
        assert isinstance(result, list)
        assert result == test_list
        assert len(result) == 4
        assert result[2]["nested"] == "dict"

    def test_fixed_resolver_preserves_int(self):
        """Test that fixed resolver preserves integer objects."""
        from grimoire_studio.resolvers.template import FixedJinja2TemplateResolver

        resolver = FixedJinja2TemplateResolver()

        test_int = 42
        context = {"outputs": {"count": test_int}}

        result = resolver.resolve_template("{{ outputs.count }}", context)

        # Should preserve the original int, not convert to string
        assert isinstance(result, int)
        assert result == 42

    def test_fixed_resolver_preserves_none(self):
        """Test that fixed resolver preserves None values."""
        from grimoire_studio.resolvers.template import FixedJinja2TemplateResolver

        resolver = FixedJinja2TemplateResolver()

        context = {"outputs": {"empty": None}}

        result = resolver.resolve_template("{{ outputs.empty }}", context)

        # Should preserve None, not convert to string
        assert result is None

    def test_fixed_resolver_preserves_grimoire_model(self, sample_system):
        """Test that fixed resolver preserves GrimoireModel objects."""
        from grimoire_studio.resolvers.template import FixedJinja2TemplateResolver

        resolver = FixedJinja2TemplateResolver()

        # Create a real GrimoireModel object using ObjectInstantiationService
        service = ObjectInstantiationService(sample_system)
        grimoire_obj = service.create_object_without_validation(
            {"model": "character", "name": "Test Character", "level": 5}
        )

        context = {"outputs": {"knave": grimoire_obj}}

        result = resolver.resolve_template("{{ outputs.knave }}", context)

        # Should preserve the original GrimoireModel object, not convert to string
        assert not isinstance(result, str)
        # Should be the same object reference
        assert result is grimoire_obj

    def test_fixed_resolver_handles_deeper_nesting(self):
        """Test that fixed resolver handles deeper nested paths."""
        from grimoire_studio.resolvers.template import FixedJinja2TemplateResolver

        resolver = FixedJinja2TemplateResolver()

        test_data = {"level1": {"level2": {"level3": {"value": "deep_value"}}}}
        context = {"data": test_data}

        result = resolver.resolve_template("{{ data.level1.level2.level3 }}", context)

        # Should preserve the nested dict
        assert isinstance(result, dict)
        assert result["value"] == "deep_value"

    def test_fixed_resolver_handles_missing_paths_with_explicit_error(self):
        """Test that fixed resolver throws explicit errors for missing paths (correct behavior)."""
        from grimoire_model.core.exceptions import TemplateResolutionError

        from grimoire_studio.resolvers.template import FixedJinja2TemplateResolver

        resolver = FixedJinja2TemplateResolver()

        context = {"data": {"existing": "value"}}

        # Should throw an explicit error for non-existent paths (this is CORRECT behavior)
        with pytest.raises(TemplateResolutionError) as exc_info:
            resolver.resolve_template("{{ data.nonexistent }}", context)

        # Verify the error message is helpful
        assert "nonexistent" in str(exc_info.value)
        assert "data" in str(exc_info.value)

    def test_fixed_resolver_preserves_dotted_paths(self, sample_system):
        """Test that the FixedJinja2TemplateResolver preserves objects for dotted paths."""
        resolver = FixedJinja2TemplateResolver()

        # Create a real GrimoireModel object using ObjectInstantiationService
        service = ObjectInstantiationService(sample_system)
        grimoire_obj = service.create_object_without_validation(
            {"model": "character", "name": "Test Character", "level": 5}
        )

        context = {"outputs": {"knave": grimoire_obj}}

        # This should preserve the original object with the fix
        result = resolver.resolve_template("{{ outputs.knave }}", context)

        # Debug: Print what we got
        print(f"Fixed resolver result type: {type(result)}")
        print(f"Fixed resolver result: {result}")

        # Should preserve the original GrimoireModel object
        assert not isinstance(result, str), (
            "Fixed resolver should preserve GrimoireModel"
        )
        assert result is grimoire_obj, "Should return the exact same object"

    def test_fixed_resolver_still_handles_simple_variables(self, sample_system):
        """Test that the FixedJinja2TemplateResolver still handles simple variables correctly."""
        resolver = FixedJinja2TemplateResolver()

        # Create a real GrimoireModel object using ObjectInstantiationService
        service = ObjectInstantiationService(sample_system)
        grimoire_obj = service.create_object_without_validation(
            {"model": "character", "name": "Test Character", "level": 5}
        )

        context = {"character": grimoire_obj}

        # Simple variable should still work
        result = resolver.resolve_template("{{ character }}", context)

        # Should preserve the original object type
        assert not isinstance(result, str), (
            "Should preserve GrimoireModel for simple vars too"
        )
        assert result is grimoire_obj, "Should return the exact same object"
