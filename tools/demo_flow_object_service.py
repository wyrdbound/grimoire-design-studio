#!/usr/bin/env python3
"""Demo of Flow-Specific Object Instantiation functionality.

This script demonstrates the new flow-specific methods added to ObjectInstantiationService
in Step 5.2, including flow input/output/variable instantiation and primitive type validation.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import the grimoire_studio modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompleteSystem,
    FlowDefinition,
    FlowInputOutput,
    FlowVariable,
    ModelDefinition,
    SystemDefinition,
)


def create_sample_flow_system() -> CompleteSystem:
    """Create a sample GRIMOIRE system with flows for demonstration."""
    # Create model definitions
    character_model = ModelDefinition(
        id="character",
        kind="model",
        name="Character",
        description="A player character",
        attributes={
            "name": AttributeDefinition(type="str"),
            "level": AttributeDefinition(type="int", default=1, range="1..20"),
            "class": AttributeDefinition(type="str", enum=["warrior", "mage", "rogue"]),
            "hitpoints": AttributeDefinition(type="int", range="1.."),
            "experience": AttributeDefinition(type="int", default=0),
        },
    )

    item_model = ModelDefinition(
        id="item",
        kind="model",
        name="Item",
        description="A game item",
        attributes={
            "name": AttributeDefinition(type="str"),
            "type": AttributeDefinition(
                type="str", enum=["weapon", "armor", "consumable", "misc"]
            ),
            "value": AttributeDefinition(type="int", range="0.."),
            "rarity": AttributeDefinition(
                type="str", enum=["common", "rare", "legendary"]
            ),
        },
    )

    # Create a comprehensive flow definition
    character_creation_flow = FlowDefinition(
        id="character_creation",
        kind="flow",
        name="Character Creation Flow",
        description="A comprehensive character creation workflow",
        inputs=[
            FlowInputOutput(type="str", id="player_name", required=True),
            FlowInputOutput(type="str", id="character_class", required=True),
            FlowInputOutput(type="int", id="starting_level", required=False),
            FlowInputOutput(type="character", id="base_template", required=False),
        ],
        outputs=[
            FlowInputOutput(type="character", id="final_character", validate=True),
            FlowInputOutput(type="str", id="creation_summary", validate=False),
            FlowInputOutput(type="bool", id="creation_successful", validate=False),
        ],
        variables=[
            FlowVariable(type="int", id="rolled_hp", validate=False),
            FlowVariable(type="item", id="starting_weapon", validate=True),
            FlowVariable(type="dict", id="ability_scores", validate=False),
            FlowVariable(type="str", id="background_story", validate=False),
        ],
    )

    # Create a simpler flow for additional demonstration
    item_enchantment_flow = FlowDefinition(
        id="item_enchantment",
        kind="flow",
        name="Item Enchantment Flow",
        description="Enchant items with magical properties",
        inputs=[
            FlowInputOutput(type="item", id="base_item", required=True),
            FlowInputOutput(type="str", id="enchantment_type", required=True),
        ],
        outputs=[
            FlowInputOutput(type="item", id="enchanted_item", validate=True),
        ],
        variables=[
            FlowVariable(type="int", id="enchantment_power", validate=False),
            FlowVariable(type="bool", id="enchantment_success", validate=False),
        ],
    )

    # Create the system
    system_def = SystemDefinition(
        id="flow_demo_system", kind="system", name="Flow Demo RPG System"
    )

    return CompleteSystem(
        system=system_def,
        models={
            "character": character_model,
            "item": item_model,
        },
        flows={
            "character_creation": character_creation_flow,
            "item_enchantment": item_enchantment_flow,
        },
    )


def demo_flow_object_service():
    """Demonstrate the new flow-specific ObjectInstantiationService methods."""
    print("🌟 GRIMOIRE Flow-Specific Object Instantiation Demo")
    print("=" * 60)
    print()
    print(
        "This demo showcases the new Step 5.2 functionality with real grimoire-model integration:"
    )
    print("• instantiate_flow_input() - Handle flow inputs with type validation")
    print("• instantiate_flow_output() - Process flow outputs with optional validation")
    print("• instantiate_flow_variable() - Manage flow variables with type safety")
    print("• _validate_primitive_type() - Convert and validate primitive types")
    print("• Real grimoire-model object creation and validation")
    print()

    # Import the service
    print("1️⃣ Importing ObjectInstantiationService:")
    try:
        from grimoire_studio.services.object_service import ObjectInstantiationService

        print("  ✅ Service imported successfully!")
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return

    # Create system
    print()
    print("2️⃣ Creating sample system with flows:")
    system = create_sample_flow_system()
    print(
        f"  ✅ Created system with {len(system.models)} models and {len(system.flows)} flows:"
    )
    for flow_id, flow in system.flows.items():
        print(f"     - {flow_id}: {flow.name}")

    # Initialize service
    print()
    print("3️⃣ Initializing ObjectInstantiationService:")

    # Initialize with real grimoire-model integration
    try:
        service = ObjectInstantiationService(system)
        print("  ✅ Service initialized with real grimoire-model integration!")
    except Exception as e:
        print(f"  ❌ Service initialization failed: {e}")
        print("  💡 Ensure grimoire-model is installed: pip install grimoire-model")
        return

    # Demo flow input instantiation
    print()
    print("4️⃣ Demonstrating Flow Input Instantiation:")
    print("  📥 Testing character_creation flow inputs...")

    flow_def = system.flows["character_creation"]
    input_data = {
        "player_name": "Aragorn",
        "character_class": "warrior",
        "starting_level": 5,
        "base_template": {
            "name": "Human Warrior Template",
            "level": 1,
            "class": "warrior",
            "hitpoints": 25,
            "experience": 0,
        },
    }

    try:
        instantiated_inputs = service.instantiate_flow_input(flow_def, input_data)
        print("  ✅ Flow inputs instantiated successfully:")
        for input_id, value in instantiated_inputs.items():
            print(f"     • {input_id}: {type(value).__name__} = {value}")
    except Exception as e:
        print(f"  ❌ Flow input instantiation failed: {e}")

    # Test missing required input
    print()
    print("  📥 Testing missing required input handling...")
    incomplete_data = {"player_name": "Legolas"}  # Missing required character_class

    try:
        service.instantiate_flow_input(flow_def, incomplete_data)
        print("  ❌ Should have failed with missing required input!")
    except Exception as e:
        print(
            f"  ✅ Correctly handled missing required input: {type(e).__name__} - {e}"
        )

    # Demo flow output instantiation
    print()
    print("5️⃣ Demonstrating Flow Output Instantiation:")
    print("  📤 Testing character_creation flow outputs...")

    output_data = {
        "final_character": {
            "name": "Aragorn the Ranger",
            "level": 5,
            "class": "warrior",
            "hitpoints": 65,
            "experience": 1500,
        },
        "creation_summary": "Successfully created a level 5 warrior character",
        "creation_successful": True,
    }

    try:
        instantiated_outputs = service.instantiate_flow_output(flow_def, output_data)
        print("  ✅ Flow outputs instantiated successfully:")
        for output_id, value in instantiated_outputs.items():
            print(f"     • {output_id}: {type(value).__name__} = {value}")
    except Exception as e:
        print(f"  ❌ Flow output instantiation failed: {e}")

    # Demo flow variable instantiation
    print()
    print("6️⃣ Demonstrating Flow Variable Instantiation:")
    print("  🔧 Testing character_creation flow variables...")

    variable_data = {
        "rolled_hp": 18,
        "starting_weapon": {
            "name": "Iron Sword",
            "type": "weapon",
            "value": 50,
            "rarity": "common",
        },
        "ability_scores": {
            "strength": 16,
            "dexterity": 14,
            "constitution": 15,
            "intelligence": 12,
            "wisdom": 13,
            "charisma": 10,
        },
        "background_story": "A ranger from the North, trained in combat and survival.",
    }

    try:
        instantiated_variables = service.instantiate_flow_variable(
            flow_def, variable_data
        )
        print("  ✅ Flow variables instantiated successfully:")
        for var_id, value in instantiated_variables.items():
            print(f"     • {var_id}: {type(value).__name__} = {value}")
    except Exception as e:
        print(f"  ❌ Flow variable instantiation failed: {e}")

    # Demo primitive type validation
    print()
    print("7️⃣ Demonstrating Primitive Type Validation:")
    print("  🔧 Testing _validate_primitive_type() method...")

    test_cases = [
        ("42", "int", "String to int conversion"),
        ("3.14", "float", "String to float conversion"),
        ("true", "bool", "String to bool conversion"),
        ("false", "bool", "False string to bool"),
        ("yes", "bool", "Yes string to bool"),
        (123, "str", "Number to string conversion"),
        (True, "bool", "Boolean passthrough"),
    ]

    for value, target_type, description in test_cases:
        try:
            result = service._validate_primitive_type(value, target_type, "test")
            print(
                f"  ✅ {description}: {value} ({type(value).__name__}) → {result} ({type(result).__name__})"
            )
        except Exception as e:
            print(f"  ❌ {description}: {value} → Error: {e}")

    # Test error cases
    print()
    print("  🔧 Testing validation error handling...")
    error_cases = [
        ("not-a-number", "int", "Invalid int conversion"),
        ("invalid-float", "float", "Invalid float conversion"),
        ("value", "unsupported_type", "Unsupported type"),
    ]

    for value, target_type, description in error_cases:
        try:
            service._validate_primitive_type(value, target_type, "test")
            print(f"  ❌ {description}: Should have failed but didn't!")
        except Exception as e:
            print(f"  ✅ {description}: Correctly caught {type(e).__name__}")

    # Demo with second flow
    print()
    print("8️⃣ Demonstrating Item Enchantment Flow:")
    print("  ⚡ Testing simpler flow with item_enchantment...")

    enchant_flow = system.flows["item_enchantment"]
    enchant_inputs = {
        "base_item": {
            "name": "Steel Sword",
            "type": "weapon",
            "value": 100,
            "rarity": "common",
        },
        "enchantment_type": "fire_damage",
    }

    try:
        enchant_input_result = service.instantiate_flow_input(
            enchant_flow, enchant_inputs
        )
        print("  ✅ Enchantment inputs processed:")
        for input_id, value in enchant_input_result.items():
            print(f"     • {input_id}: {value}")

        # Process variables
        enchant_vars = {
            "enchantment_power": 25,
            "enchantment_success": True,
        }
        enchant_var_result = service.instantiate_flow_variable(
            enchant_flow, enchant_vars
        )
        print("  ✅ Enchantment variables processed:")
        for var_id, value in enchant_var_result.items():
            print(f"     • {var_id}: {value}")

    except Exception as e:
        print(f"  ❌ Enchantment flow processing failed: {e}")

    # Summary
    print()
    print("🎯 Demo Summary - Step 5.2 Features Demonstrated:")
    print("=" * 60)
    print("✅ Flow Input Instantiation:")
    print("   • Type validation for primitive and model types")
    print("   • Required vs optional input handling")
    print("   • Automatic model type injection")
    print("   • Error handling for missing required inputs")
    print()
    print("✅ Flow Output Instantiation:")
    print("   • Conditional validation based on flow definition")
    print("   • Support for validated and unvalidated outputs")
    print("   • Graceful handling of missing outputs")
    print()
    print("✅ Flow Variable Instantiation:")
    print("   • Type-safe variable processing")
    print("   • Validation control per variable")
    print("   • Mixed primitive and model type support")
    print()
    print("✅ Primitive Type Validation:")
    print("   • Robust type conversion (str, int, float, bool)")
    print("   • Intelligent boolean parsing (true/false/yes/no/1/0)")
    print("   • Clear error messages for invalid conversions")
    print("   • Unsupported type detection")
    print()
    print("🚀 The ObjectInstantiationService now provides comprehensive")
    print("   flow-specific object handling for GRIMOIRE flow execution!")


if __name__ == "__main__":
    demo_flow_object_service()
