#!/usr/bin/env python3
"""Demo script for Support Services (Dice, Name, LLM).

This script demonstrates the dice rolling, name generation, and LLM services
that support GRIMOIRE flow execution.

Usage:
    python tools/demo_support_services.py
"""

from grimoire_logging import get_logger

from grimoire_studio.services import DiceService, LLMConfig, LLMService, NameService

logger = get_logger(__name__)


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def demo_dice_service() -> None:
    """Demo 1: Dice Rolling Service."""
    print_section("Demo 1: Dice Rolling Service")

    service = DiceService()
    print("✓ DiceService initialized\n")

    # Basic rolls
    print("Basic Dice Rolls:")
    print("-" * 40)

    expressions = ["1d20", "2d6", "3d6+5", "1d100"]
    for expr in expressions:
        result = service.roll_dice(expr)
        print(f"  {expr:10} → {result.total:3} ({result.description})")

    # Advanced mechanics
    print("\nAdvanced Dice Mechanics:")
    print("-" * 40)

    advanced = [
        ("4d6kh3", "Ability Score (D&D 5e)"),
        ("2d20kh1", "Advantage (D&D 5e)"),
        ("2d20kl1", "Disadvantage (D&D 5e)"),
        ("1d6e", "Exploding (Savage Worlds)"),
        ("4dF", "Fate Dice"),
        ("2d6r1<=2", "Reroll 1s and 2s once"),
    ]

    for expr, description in advanced:
        result = service.roll_dice(expr)
        print(f"  {expr:12} → {result.total:3} - {description}")
        print(f"               {result.description}")

    # Multiple rolls
    print("\nMultiple Rolls:")
    print("-" * 40)

    expressions = ["1d20", "2d6", "1d100"]
    results = service.roll_multiple(expressions)
    for i, result in enumerate(results, 1):
        print(f"  Roll {i}: {result.expression} → {result.total}")

    # Expression parsing
    print("\nExpression Validation:")
    print("-" * 40)

    test_expressions = ["2d6+3", "invalid", "1d20kh2"]
    for expr in test_expressions:
        info = service.parse_expression(expr)
        if info["valid"]:
            print(f"  ✓ {expr:15} - Valid")
        else:
            print(f"  ✗ {expr:15} - Invalid: {info.get('error', 'Unknown error')}")


def demo_name_service() -> None:
    """Demo 2: Name Generation Service (wyrdbound-rng)."""
    print_section("Demo 2: Name Generation Service (wyrdbound-rng)")

    # Fantasy names with Bayesian algorithm
    service = NameService(seed=42)  # Use seed for reproducible demo
    print("✓ NameService initialized with seed=42")
    print("  Using: generic-fantasy corpus with Bayesian algorithm\n")

    # Generate fantasy names with Bayesian algorithm
    print("Fantasy Names (Bayesian Algorithm):")
    print("-" * 40)

    for i in range(5):
        name = service.generate_name(algorithm="bayesian", max_length=12)
        print(f"  {i + 1}. {name}")

    # Batch generation with different algorithms
    print("\nBatch Generation - Simple Algorithm:")
    print("-" * 40)

    simple_names = service.generate_names(5, algorithm="simple", max_length=10)
    for i, name in enumerate(simple_names, 1):
        print(f"  {i}. {name}")

    print("\nBatch Generation - Bayesian Algorithm:")
    print("-" * 40)

    bayesian_names = service.generate_names(5, algorithm="bayesian", max_length=12)
    for i, name in enumerate(bayesian_names, 1):
        print(f"  {i}. {name}")

    # Japanese names
    print("\nJapanese Samurai Names (Bayesian):")
    print("-" * 40)

    japanese_service = NameService(
        name_list="japanese-sengoku-samurai", segmenter="japanese", seed=42
    )
    japanese_names = japanese_service.generate_names(5, algorithm="bayesian")
    for i, name in enumerate(japanese_names, 1):
        print(f"  {i}. {name}")

    # Service capabilities
    print("\nAvailable Name Lists:")
    print("-" * 40)

    name_lists = service.get_available_name_lists()
    print(f"  Total: {len(name_lists)} built-in corpora")
    print(f"  Examples: {', '.join(name_lists[:4])}...")

    print("\nSupported Types and Styles (legacy API):")
    print("-" * 40)

    types = service.get_supported_types()
    styles = service.get_supported_styles()
    print(f"  Types:  {', '.join(types)}")
    print(f"  Styles: {', '.join(styles)}")


def demo_llm_service() -> None:
    """Demo 3: LLM Service (Ollama or Mock)."""
    # Check if Ollama is available
    ollama_available = LLMService.is_ollama_available()

    if ollama_available:
        print_section("Demo 3: LLM Service (Ollama Provider)")
        config = LLMConfig(
            provider="ollama", model="llama3.1", temperature=0.7, max_tokens=200
        )
        print("✓ Ollama detected - using llama3.1 model")
    else:
        print_section("Demo 3: LLM Service (Mock Provider)")
        config = LLMConfig(provider="mock", model="mock-model", temperature=0.7)
        print("✓ Ollama not available - using mock provider")

    service = LLMService(config)

    print(f"  Provider: {config.provider}")
    print(f"  Model: {config.model}")
    print(f"  Temperature: {config.temperature}")
    print()

    # Simple prompt
    print("Simple Prompt:")
    print("-" * 40)

    prompt = "Generate a fantasy item description"
    print(f"  Prompt:   {prompt}")
    try:
        result = service.execute_prompt(prompt)
        print(f"  Response: {result.response[:100]}...")
    except Exception as e:
        print(f"  Error: {e}")
    print()

    # Prompt with variables
    print("Prompt with Variable Substitution:")
    print("-" * 40)

    prompt = "Generate a {item_type} suitable for level {level} characters"
    variables = {"item_type": "magic sword", "level": 5}

    print(f"  Template: {prompt}")
    print(f"  Variables: {variables}")
    try:
        result = service.execute_prompt(prompt, variables)
        print(f"  Response: {result.response[:100]}...")
    except Exception as e:
        print(f"  Error: {e}")
    print()

    # Multiple variable types
    print("Complex Variable Substitution:")
    print("-" * 40)

    prompt = "Create a {creature} in {location} with {trait} traits"
    variables = {
        "creature": "dragon",
        "location": "mountain fortress",
        "trait": "ancient and wise",
    }

    print(f"  Template: {prompt}")
    print("  Variables:")
    for key, value in variables.items():
        print(f"    {key}: {value}")
    try:
        result = service.execute_prompt(prompt, variables)
        print(f"  Response: {result.response[:100]}...")
    except Exception as e:
        print(f"  Error: {e}")
    print()

    # Configuration
    print("Configuration Management:")
    print("-" * 40)

    current_config = service.get_config()
    print(f"  Current config: {current_config.to_dict()}")

    if ollama_available:
        new_config = LLMConfig(
            provider="ollama", model="llama3.1", temperature=0.9, max_tokens=300
        )
    else:
        new_config = LLMConfig(
            provider="mock", model="mock-model-v2", temperature=0.9, max_tokens=1000
        )
    service.set_config(new_config)

    updated_config = service.get_config()
    print(f"  Updated config: {updated_config.to_dict()}")


def demo_integration() -> None:
    """Demo 4: Integration Example."""
    print_section("Demo 4: Service Integration Example")

    dice_service = DiceService()
    name_service = NameService(seed=123)

    # Use Ollama if available, otherwise mock
    ollama_available = LLMService.is_ollama_available()
    if ollama_available:
        llm_config = LLMConfig(
            provider="ollama", model="llama3.1", temperature=0.7, max_tokens=150
        )
    else:
        llm_config = LLMConfig(provider="mock")

    llm_service = LLMService(llm_config)

    print("Creating a character with all services:\n")

    # Generate character name
    char_name = name_service.generate_name("character", "fantasy")
    print(f"1. Generated character name: {char_name}")

    # Roll ability scores (D&D 5e style)
    print("\n2. Rolling ability scores (4d6kh3):")
    abilities = [
        "Strength",
        "Dexterity",
        "Constitution",
        "Intelligence",
        "Wisdom",
        "Charisma",
    ]
    scores = {}

    for ability in abilities:
        result = dice_service.roll_dice("4d6kh3")
        scores[ability] = result.total
        print(f"   {ability:14} → {result.total:2}")

    # Roll for starting gold
    gold_result = dice_service.roll_dice("5d4×10")
    starting_gold = gold_result.total
    print(f"\n3. Starting gold: {starting_gold} gp")

    # Generate background with LLM
    print("\n4. Generating character background:")
    prompt = "Create a brief background for {name}, a character with {str} Strength and {int} Intelligence"
    variables = {
        "name": char_name,
        "str": scores["Strength"],
        "int": scores["Intelligence"],
    }

    try:
        background_result = llm_service.execute_prompt(prompt, variables)
        print(f"   {background_result.response[:150]}...")
    except Exception as e:
        print(f"   Error generating background: {e}")

    print("\n✓ Character creation complete!")
    print(f"  Name: {char_name}")
    print(f"  Gold: {starting_gold} gp")
    print(f"  Primary Stats: STR {scores['Strength']}, INT {scores['Intelligence']}")


def main() -> int:
    """Run all service demos."""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + " " * 18 + "GRIMOIRE SUPPORT SERVICES DEMO" + " " * 30 + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    try:
        demo_dice_service()
        demo_name_service()
        demo_llm_service()
        demo_integration()

        print("\n" + "=" * 80)
        print(" All Demos Completed Successfully!")
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n✗ Demo failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
