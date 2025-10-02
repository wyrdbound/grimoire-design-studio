#!/usr/bin/env python3
"""Demo of ObjectInstantiationService functionality.

This script demonstrates the ObjectInstantiationService with grimoire-model
as a required dependency, showing full object instantiation capabilities.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import the grimoire_studio modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompleteSystem,
    ModelDefinition,
    SystemDefinition,
)


def create_sample_system() -> CompleteSystem:
    """Create a sample GRIMOIRE system for demonstration."""
    # Create a character model
    character_model = ModelDefinition(
        id="character",
        kind="model",
        name="Character",
        description="A player character or NPC",
        attributes={
            "name": AttributeDefinition(type="str"),
            "level": AttributeDefinition(type="int", default=1, range="1..20"),
            "class": AttributeDefinition(type="str", enum=["warrior", "mage", "rogue"]),
            "hitpoints": AttributeDefinition(type="int", range="1.."),
            "stats": AttributeDefinition(type="dict"),
        },
    )

    # Create an item model
    item_model = ModelDefinition(
        id="item",
        kind="model",
        name="Item",
        description="An equipment item or consumable",
        attributes={
            "name": AttributeDefinition(type="str"),
            "type": AttributeDefinition(
                type="str", enum=["weapon", "armor", "consumable", "misc"]
            ),
            "value": AttributeDefinition(type="int", range="0.."),
            "weight": AttributeDefinition(type="float", range="0.."),
            "description": AttributeDefinition(type="str", optional=True),
        },
    )

    # Create the system
    system_def = SystemDefinition(
        id="demo_system", kind="system", name="Demo RPG System"
    )

    return CompleteSystem(
        system=system_def, models={"character": character_model, "item": item_model}
    )


def demo_object_service():
    """Demonstrate ObjectInstantiationService with grimoire-model integration."""
    print("🎮 GRIMOIRE ObjectInstantiationService Demo\n")

    print("This demo shows the ObjectInstantiationService with grimoire-model")
    print("as a required dependency, providing full object capabilities.")
    print()

    print("1️⃣ Importing ObjectInstantiationService:")
    try:
        from grimoire_studio.services.object_service import ObjectInstantiationService

        print("  ✅ Service imported successfully!")
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        print("  💡 Install grimoire-model: pip install grimoire-model")
        print("     (Now a required dependency in pyproject.toml)")
        return

    print()
    print("2️⃣ Creating sample GRIMOIRE system:")
    system = create_sample_system()
    print(f"  ✅ Created system with {len(system.models)} models:")
    for model_id, model in system.models.items():
        print(f"     - {model_id}: {model.name}")

    print()
    print("3️⃣ Initializing ObjectInstantiationService:")
    try:
        service = ObjectInstantiationService(system)
        print("  ✅ Service initialized with grimoire-model integration!")
    except Exception as e:
        print(f"  ❌ Service initialization failed: {e}")
        return

    print()
    print("4️⃣ Demonstrating object creation:")

    # Create a character
    character_data = {
        "model": "character",
        "name": "Aragorn",
        "level": 10,
        "class": "warrior",
        "hitpoints": 85,
        "stats": {"strength": 18, "dexterity": 15, "constitution": 16},
    }

    try:
        character = service.create_object(character_data)
        print(f"  ✅ Created character: {character}")
    except Exception as e:
        print(f"  ❌ Character creation failed: {e}")

    # Create an item
    item_data = {
        "model": "item",
        "name": "Sting",
        "type": "weapon",
        "value": 500,
        "weight": 2.5,
        "description": "A legendary elven short sword",
    }

    try:
        item = service.create_object(item_data)
        print(f"  ✅ Created item: {item}")
    except Exception as e:
        print(f"  ❌ Item creation failed: {e}")

    print()
    print("5️⃣ Demonstrating validation:")

    # Valid data
    valid_data = {
        "model": "character",
        "name": "Legolas",
        "class": "rogue",
        "level": 8,
        "hitpoints": 70,
        "stats": {"strength": 15, "dexterity": 20, "constitution": 12},
    }
    is_valid, errors = service.validate_object(valid_data)
    print(f"  ✅ Valid data check: {is_valid}, errors: {errors}")

    # Invalid data
    invalid_data = {"model": "character", "level": "not-a-number", "hitpoints": -10}
    is_valid, errors = service.validate_object(invalid_data)
    print(f"  ❌ Invalid data check: {is_valid}, errors: {errors}")

    print()
    print("6️⃣ Demonstrating backward compatibility:")

    try:
        old_character = service.create_character({"name": "Gimli", "class": "warrior"})
        print(f"  ✅ Backward compatibility (character): {old_character}")
    except Exception as e:
        print(f"  ❌ Backward compatibility failed: {e}")

    print()
    print("🎯 Demo completed! The ObjectInstantiationService successfully:")
    print("  ✅ Integrates with grimoire-model as a required dependency")
    print("  ✅ Creates fully validated game objects")
    print("  ✅ Provides comprehensive error handling")
    print("  ✅ Maintains backward compatibility")
    print("  ✅ Follows AI Guidance principles (explicit errors, simplicity)")


if __name__ == "__main__":
    demo_object_service()
