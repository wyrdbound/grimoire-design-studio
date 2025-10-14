"""Test to verify that grimoire-model 0.3.1 fixes the template resolver issue."""

import pytest
from grimoire_model.resolvers.template import Jinja2TemplateResolver

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompleteSystem,
    ModelDefinition,
    SystemDefinition,
)
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


def test_grimoire_model_031_fixes_template_resolver_issue(sample_system):
    """Test that grimoire-model 0.3.1 fixes the dotted path string conversion issue."""
    # Create object instantiation service
    object_service = ObjectInstantiationService(sample_system)

    # Create a character object
    character = object_service.create_object_without_validation(
        {"model": "character", "name": "Test Character", "level": 5}
    )

    # Create a context with nested structure like flow outputs
    context = {"outputs": {"knave": character}}

    # Test that the original Jinja2TemplateResolver now preserves objects (fixed in 0.3.1)
    resolver = Jinja2TemplateResolver()
    result = resolver.resolve_template("{{ outputs.knave }}", context)

    # This should now pass with grimoire-model 0.3.1 - the object should be preserved
    assert not isinstance(result, str), (
        f"Expected GrimoireModel object, got string: {result}. "
        f"The fix in grimoire-model 0.3.1 should prevent string conversion."
    )
    assert result is character, "Should return the exact same object reference"

    # Debug: Print what we got to understand the object structure
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")
    print(f"Result dir: {dir(result)}")

    # The main test is that we got back an object, not a string
    # This proves the fix in grimoire-model 0.3.1 is working!
    print("✅ SUCCESS: grimoire-model 0.3.1 fix is working - objects are preserved!")

    # Just verify it's the same object reference
    assert str(result) != str(character) or result is character, (
        "Object should be preserved"
    )


def test_original_resolver_handles_simple_variables_correctly(sample_system):
    """Test that simple variables (non-dotted paths) still work correctly."""
    object_service = ObjectInstantiationService(sample_system)
    character = object_service.create_object_without_validation(
        {"model": "character", "name": "Simple Character", "level": 3}
    )

    context = {"character": character}

    resolver = Jinja2TemplateResolver()
    result = resolver.resolve_template("{{ character }}", context)

    # Simple variables should also preserve objects
    assert not isinstance(result, str), "Simple variables should preserve object type"
    assert result is character, "Should return the exact same object reference"


def test_original_resolver_handles_missing_paths():
    """Test that the resolver handles missing paths correctly with upstream fixes."""
    context = {"outputs": {"other": "value"}}
    resolver = Jinja2TemplateResolver()

    # Missing dotted path should return None gracefully (upstream fix behavior)
    result = resolver.resolve_template("{{ outputs.missing }}", context)
    assert result is None, "Missing attributes should return None gracefully"


def test_original_resolver_handles_complex_templates():
    """Test that complex template expressions still work correctly."""
    context = {"name": "World", "level": 42}

    resolver = Jinja2TemplateResolver()
    result = resolver.resolve_template("Hello {{ name }}! Level: {{ level }}", context)

    # Complex templates should return strings as expected
    assert isinstance(result, str), "Complex templates should return strings"
    assert result == "Hello World! Level: 42", "Complex template rendering should work"
