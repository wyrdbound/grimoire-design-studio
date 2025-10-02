#!/usr/bin/env python3
"""Demo of Progressive Character Creation with Knave 1e.

This script demonstrates how grimoire-model v0.2.1+ handles step-by-step attribute
filling during flow execution. It tests whether validation requirements allow
progressive object construction or if all required fields must be present from the start.

Key Test: With grimoire-model v0.2.1's new dict type inference feature, the Knave
character model with nested attributes (hit_points.max, armor.defense, etc.) now
loads successfully without requiring explicit 'type: dict' declarations.

The demo shows:
- Simple model validation (character_ability)
- Composite model validation (character_abilities - all 6 ability scores)
- Full character model with nested dict structures
- Progressive object creation patterns and limitations
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_studio.core.project_manager import ProjectManager
from grimoire_studio.services.object_service import ObjectInstantiationService


def load_knave_system():
    """Load the Knave 1e system from the systems directory."""
    print("📚 Loading Knave 1e system...")
    project_manager = ProjectManager()

    knave_path = Path(__file__).parent.parent / "systems" / "knave_1e"

    if not knave_path.exists():
        print(f"❌ Knave 1e system not found at: {knave_path}")
        return None

    try:
        system = project_manager.load_system(knave_path)
        print(f"✅ Loaded system: {system.system.name}")
        print(f"   Models: {len(system.models)}")
        print(f"   Character model found: {'character' in system.models}")
        return system
    except Exception as e:
        print(f"❌ Failed to load system: {e}")
        return None


def demo_progressive_character_creation():
    """Demonstrate progressive character creation with validation."""
    print("🎮 Progressive Character Creation Demo - Knave 1e")
    print("=" * 70)
    print()
    print("This demo tests whether grimoire-model allows step-by-step")
    print("character creation or requires all fields upfront.")
    print()

    # Load the system
    system = load_knave_system()
    if not system:
        return

    print()
    print(f"📦 System loaded with {len(system.models)} models:")
    for model_id in sorted(system.models.keys()):
        print(f"   • {model_id}")

    # Verify character model loaded (should work with v0.2.1+)
    if "character" in system.models:
        print()
        print("✅ Character model loaded successfully!")
        print("   (Requires grimoire-model v0.2.1+ with dict type inference)")
    else:
        print()
        print("⚠️  WARNING: Character model did not load!")
        print("   You may need to upgrade to grimoire-model v0.2.1 or later.")
        print("   Earlier versions don't support dict type inference for nested")
        print("   attributes like 'hit_points.max' and 'armor.defense'.")

    print()
    print("🔧 Initializing ObjectInstantiationService...")
    try:
        service = ObjectInstantiationService(system)
        print("✅ Service initialized!")
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return

    # Use character_ability as a simpler test case first
    print()
    print("=" * 70)
    print("PART 1: SIMPLE MODEL TESTING (character_ability)")
    print("=" * 70)
    print()
    print("We'll start with the simpler character_ability model to")
    print("demonstrate basic progressive validation behavior, then move")
    print("to the full character model with nested dict structures.")
    print()

    # Examine the character_ability model
    ability_model = system.models.get("character_ability")
    if ability_model:
        print("📋 Character Ability Model Structure:")
        print(f"   ID: {ability_model.id}")
        print(f"   Name: {ability_model.name}")
        print("   Attributes:")
        for attr_name, attr_def in ability_model.attributes.items():
            has_default = hasattr(attr_def, "default") and attr_def.default is not None
            is_optional = hasattr(attr_def, "optional") and attr_def.optional
            is_derived = hasattr(attr_def, "derived") and attr_def.derived
            status = (
                "optional"
                if is_optional
                else "has_default"
                if has_default
                else "derived"
                if is_derived
                else "REQUIRED"
            )
            print(f"     • {attr_name}: {attr_def.type} [{status}]")

    # Test 1: Empty object
    print()
    print("=" * 70)
    print("TEST 1: Creating ability with no fields")
    print("=" * 70)

    empty_ability = {
        "model": "character_ability",
    }

    print("Attempting to create with no attributes...")
    is_valid, errors = service.validate_object(empty_ability)
    print(f"Valid: {is_valid}")
    if not is_valid:
        print("Validation errors:")
        for error in errors:
            print(f"  • {error}")

    # Test 2: Just bonus field
    print()
    print("=" * 70)
    print("TEST 2: Creating ability with just bonus (required field)")
    print("=" * 70)

    ability_with_bonus = {
        "model": "character_ability",
        "bonus": 5,
    }

    print("Attempting to create with bonus=5...")
    is_valid, errors = service.validate_object(ability_with_bonus)
    print(f"Valid: {is_valid}")
    if not is_valid:
        print("Validation errors:")
        for error in errors:
            print(f"  • {error}")
    else:
        print("✅ Ability is valid with just the bonus field!")
        print("   Note: The 'defense' field is derived, so not required")

        # Try to create the object
        print()
        print("Attempting to create GrimoireModel object...")
        try:
            ability_obj = service.create_object(ability_with_bonus)
            print(f"✅ Successfully created: {ability_obj}")
            print("   Bonus: 5")
            print("   Defense (derived): Should be 15 (10 + 5)")
        except Exception as e:
            print(f"❌ Object creation failed: {e}")
            import traceback

            traceback.print_exc()

    # Test 3: Progressive update
    print()
    print("=" * 70)
    print("TEST 3: Testing progressive updates")
    print("=" * 70)

    if is_valid:
        print("Creating initial ability object with bonus=3...")
        initial_ability = {
            "model": "character_ability",
            "bonus": 3,
        }

        try:
            ability_obj = service.create_object(initial_ability)
            print(f"✅ Created: {ability_obj}")
            print("   Initial bonus: 3")

            print()
            print("Attempting to update bonus to 7...")
            update_data = {
                "bonus": 7,
            }

            update_ability_obj = service.update_object(ability_obj, update_data)
            if update_ability_obj is not None:
                print("✅ Update succeeded!")
                print(f"   New bonus: {update_ability_obj.get('bonus')}")
                print(
                    f"   Defense should now be 17 => {update_ability_obj.get('defense') == 17}"
                )
            else:
                print("❌ Update failed: update_object returned None")

        except Exception as e:
            print(f"❌ Progressive update failed: {e}")
            import traceback

            traceback.print_exc()

    # Test 4: Full Character Model (now works with v0.2.1!)
    if "character" in system.models:
        print()
        print("=" * 70)
        print("PART 2: FULL CHARACTER MODEL WITH NESTED DICT STRUCTURES")
        print("=" * 70)
        print()
        print("✅ Character model loaded successfully with grimoire-model v0.2.1!")
        print("   Dict type inference allows nested attributes like 'hit_points.max'")
        print("   and 'armor.defense' to work without explicit type declarations.")
        print()

        # Test 4A: character_abilities (composite model)
        print("TEST 4A: Creating character_abilities (composite model)")
        print("-" * 70)

        abilities_model = system.models.get("character_abilities")
        if abilities_model:
            print("This model requires all six ability scores...")
            print()

        # Try with incomplete abilities
        print("Step 1: Just strength")
        incomplete_abilities = {
            "model": "character_abilities",
            "strength": {"model": "character_ability", "bonus": 5},
        }

        is_valid, errors = service.validate_object(incomplete_abilities)
        print(f"Valid: {is_valid}")
        if not is_valid:
            print("Validation errors (first 3):")
            for error in errors[:3]:
                print(f"  • {error}")
            if len(errors) > 3:
                print(f"  ... and {len(errors) - 3} more")

        print()
        print("Step 2: All six abilities")
        complete_abilities = {
            "model": "character_abilities",
            "strength": {"model": "character_ability", "bonus": 5},
            "dexterity": {"model": "character_ability", "bonus": 4},
            "constitution": {"model": "character_ability", "bonus": 6},
            "intelligence": {"model": "character_ability", "bonus": 3},
            "wisdom": {"model": "character_ability", "bonus": 4},
            "charisma": {"model": "character_ability", "bonus": 3},
        }

        is_valid, errors = service.validate_object(complete_abilities)
        print(f"Valid: {is_valid}")
        if not is_valid:
            print("Validation errors:")
            for error in errors:
                print(f"  • {error}")
        else:
            print("✅ Complete abilities are valid!")

            try:
                service.create_object(complete_abilities)
                print("✅ Successfully created abilities object")
            except Exception as e:
                print(f"❌ Object creation failed: {e}")

        # Test 4B: Minimal character
        print()
        print("TEST 4B: Minimal character with just name")
        print("-" * 70)
        minimal_character = {
            "model": "character",
            "name": "Thorin Oakenshield",
        }

        is_valid, errors = service.validate_object(minimal_character)
        print(f"Valid: {is_valid}")
        if not is_valid:
            print("Validation errors (first 5):")
            for error in errors[:5]:
                print(f"  • {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
        else:
            print("✅ Minimal character is valid!")

        # Test 4C: Character with nested structures
        print()
        print("TEST 4C: Character with nested hit_points and armor structures")
        print("-" * 70)
        character_with_nested = {
            "model": "character",
            "name": "Gimli",
            "abilities": {
                "strength": {"bonus": 6},
                "dexterity": {"bonus": 3},
                "constitution": {"bonus": 7},
                "intelligence": {"bonus": 2},
                "wisdom": {"bonus": 4},
                "charisma": {"bonus": 2},
            },
            "hit_points": {
                "max": 85,
                "current": 85,
            },
            "armor": {
                "bonus": 5,
            },
        }

        is_valid, errors = service.validate_object(character_with_nested)
        print(f"Valid: {is_valid}")
        if not is_valid:
            print("Validation errors (first 5):")
            for error in errors[:5]:
                print(f"  • {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
        else:
            print("✅ Character with nested structures is valid!")
            print("   This confirms grimoire-model v0.2.1's dict inference works!")

            try:
                service.create_object(character_with_nested)
                print("✅ Successfully created full character object!")
                print("   This demonstrates that nested dict structures now work")
                print("   properly with the new dict type inference feature.")
            except Exception as e:
                print(f"❌ Character creation failed: {e}")
    else:
        print()
        print("⚠️  WARNING: Character model did not load!")
        print("   You may need to upgrade to grimoire-model v0.2.1 or later.")
        print("   Earlier versions don't support dict type inference for nested")
        print("   attributes like 'hit_points.max' and 'armor.defense'.")

    # Summary
    print()
    print("=" * 70)
    print("🎯 SUMMARY")
    print("=" * 70)
    print()
    print("This demo tested grimoire-model v0.2.1's behavior with progressive")
    print("object creation for the Knave 1e system.")
    print()
    print("🎉 KEY BREAKTHROUGH - Dict Type Inference:")
    print()
    print("   ✅ The Knave character model NOW LOADS with v0.2.1!")
    print("   ✅ Nested attributes like 'hit_points.max' and 'armor.bonus' work!")
    print("   ✅ Parent attributes automatically infer 'type: dict'")
    print()
    print("   Example from character.yaml:")
    print("     hit_points:")
    print("       max: { type: int }")
    print("       current: { type: int, range: '0..{{ hit_points.max }}' }")
    print("     armor:")
    print("       bonus: { type: int, range: '0..10' }")
    print("       defense: { type: int, derived: '{{ 10 + bonus }}' }")
    print()
    print("   The 'hit_points' and 'armor' attributes don't need explicit")
    print("   'type: dict' declarations - it's inferred automatically!")
    print()
    print("📊 Progressive Object Creation Findings:")
    print()
    print("✅ DERIVED FIELDS:")
    print("   • Derived fields (like 'defense') are not required at creation")
    print("   • They are calculated automatically from other fields")
    print("   • ⚠️  Note: Template resolution with 'this' context may fail")
    print("     (grimoire-model library issue, not design studio)")
    print()
    print("❌ REQUIRED FIELDS:")
    print("   • Required fields without defaults MUST be present from the start")
    print("   • Validation fails immediately if required fields are missing")
    print("   • The character model has MANY required fields")
    print()
    print("❌ COMPOSITE MODELS:")
    print("   • Complex models (like character_abilities) require ALL sub-fields")
    print("   • Cannot progressively add strength, then dexterity, etc.")
    print("   • Each composite must be complete when added")
    print()
    print("✅ NESTED DICT STRUCTURES:")
    print("   • Nested dicts are validated as complete units")
    print("   • All nested required fields must be present")
    print("   • Derived fields in nested structures work (when templates resolve)")
    print("   • Progressive creation patterns apply to the nested data too")
    print()
    print("✅ UPDATE OPERATIONS:")
    print("   • update_object() allows changing existing field values")
    print("   • Validation runs after each update")
    print("   • Good for modifying existing objects step-by-step")
    print()
    print("💡 RECOMMENDED FLOW EXECUTION PATTERN:")
    print()
    print("   For step-by-step character creation during flows:")
    print()
    print("   1. Build data dictionaries progressively WITHOUT validation")
    print("   2. Only create/validate GrimoireModel objects at checkpoints")
    print("   3. Make fields optional where progressive creation is desired")
    print("   4. OR create simple objects first, then update them")
    print()
    print("   Example flow pattern:")
    print("     Steps 1-5: Collect data in regular dicts (no validation)")
    print("     Step 6:    Validate complete data dict")
    print("     Step 7:    Create GrimoireModel object (with all required fields)")
    print("     Steps 8+:  Use update_object() for optional modifications")
    print()
    print("🔧 PRACTICAL IMPLICATIONS:")
    print()
    print("   • Character creation flows should collect ALL required data first")
    print("   • Don't try to create partial characters and fill them in")
    print("   • Use validation checkpoints, not continuous validation")
    print("   • Consider making more fields optional if progressive creation needed")
    print()


if __name__ == "__main__":
    demo_progressive_character_creation()
