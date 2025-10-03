#!/usr/bin/env python3
"""Demo script for FlowExecutionService.

This script demonstrates the basic flow execution capabilities including:
- Simple flows with completion steps
- Flows with inputs and outputs
- Sequential and branching step execution
- Pre-actions and step actions
- Context management with variables
- Action types: set_value, log_message, log_event, display_value, validate_value
- Callbacks for monitoring execution

Usage:
    source .venv/bin/activate && python tools/demo_flow_service.py
"""

from grimoire_logging import get_logger

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompleteSystem,
    FlowDefinition,
    FlowInputOutput,
    FlowStep,
    FlowVariable,
    ModelDefinition,
    SystemDefinition,
)
from grimoire_studio.services.flow_service import FlowExecutionService
from grimoire_studio.services.object_service import ObjectInstantiationService

logger = get_logger(__name__)


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def create_demo_system() -> CompleteSystem:
    """Create a demo GRIMOIRE system for testing flows."""
    print_section("Creating Demo System")

    # Define a character model
    character_model = ModelDefinition(
        id="character",
        kind="model",
        name="Character",
        description="A player character",
        attributes={
            "name": AttributeDefinition(type="str"),
            "level": AttributeDefinition(type="int", default=1),
            "hp": AttributeDefinition(type="int", default=10),
            "xp": AttributeDefinition(type="int", default=0),
            "status": AttributeDefinition(type="str", default="active"),
        },
    )

    # Define an item model
    item_model = ModelDefinition(
        id="item",
        kind="model",
        name="Item",
        description="A game item",
        attributes={
            "name": AttributeDefinition(type="str"),
            "value": AttributeDefinition(type="int", default=0),
            "weight": AttributeDefinition(type="float", default=0.0),
        },
    )

    system_def = SystemDefinition(
        id="demo_system", kind="system", name="Demo System for Flow Testing"
    )

    system = CompleteSystem(
        system=system_def, models={"character": character_model, "item": item_model}
    )

    print(f"✓ Created system: {system.system.name}")
    print(f"✓ Models: {', '.join(system.models.keys())}")
    return system


def demo_simple_flow(service: FlowExecutionService, system: CompleteSystem) -> None:
    """Demo 1: Simple flow with just a completion step."""
    print_section("Demo 1: Simple Completion Flow")

    flow = FlowDefinition(
        id="simple_flow",
        kind="flow",
        name="Simple Flow",
        description="A minimal flow with just a completion step",
        steps=[
            FlowStep(
                id="finish",
                name="Finish",
                type="completion",
                prompt="Flow execution complete!",
                actions=[{"log_message": "Simple flow completed successfully"}],
            )
        ],
    )

    system.flows["simple_flow"] = flow
    print("Flow definition:")
    print(f"  ID: {flow.id}")
    print(f"  Name: {flow.name}")
    print(f"  Steps: {len(flow.steps)}")

    print("\nExecuting flow...")
    result = service.execute_flow("simple_flow")

    print("\n✓ Flow completed successfully")
    print(f"  Result: {result}")


def demo_flow_with_inputs_outputs(
    service: FlowExecutionService, system: CompleteSystem
) -> None:
    """Demo 2: Flow with inputs and outputs."""
    print_section("Demo 2: Flow with Inputs and Outputs")

    flow = FlowDefinition(
        id="greet_player_flow",
        kind="flow",
        name="Greet Player Flow",
        description="Takes player info and creates a greeting message",
        inputs=[
            FlowInputOutput(type="str", id="player_name", required=True),
            FlowInputOutput(type="int", id="player_level", required=False),
        ],
        outputs=[
            FlowInputOutput(type="str", id="greeting", validate=False),
        ],
        steps=[
            FlowStep(
                id="create_greeting",
                name="Create Greeting",
                type="completion",
                actions=[
                    {
                        "set_value": {
                            "path": "outputs.greeting",
                            "value": "Welcome to the game, {{ inputs.player_name }} (Level {{ inputs.player_level }})!",
                        }
                    },
                    {"log_message": "Greeting created"},
                ],
            )
        ],
    )

    system.flows["greet_player_flow"] = flow
    print("Flow definition:")
    print("  Inputs: player_name (str), player_level (int, optional)")
    print("  Outputs: greeting (str)")

    print("\nExecuting flow with inputs...")
    flow_inputs = {"player_name": "Alice", "player_level": 5}
    flow_outputs = service.execute_flow(
        "greet_player_flow",
        inputs=flow_inputs,
    )

    print("\n✓ Flow completed successfully")
    print("  Inputs:")
    for key, value in flow_inputs.items():
        print(f"    {key}: {value}")
    print("  Outputs:")
    for key, value in flow_outputs.items():
        print(f"    {key}: {value}")


def demo_flow_with_variables(
    service: FlowExecutionService, system: CompleteSystem
) -> None:
    """Demo 3: Flow with variables and multiple steps."""
    print_section("Demo 3: Flow with Variables and Multiple Steps")

    flow = FlowDefinition(
        id="counter_flow",
        kind="flow",
        name="Counter Flow",
        description="Demonstrates variables with sequential steps",
        variables=[
            FlowVariable(type="int", id="counter", validate=False),
            FlowVariable(type="str", id="message", validate=False),
        ],
        outputs=[
            FlowInputOutput(type="int", id="final_count", validate=False),
        ],
        steps=[
            FlowStep(
                id="step1",
                name="Initialize Counter",
                type="completion",
                actions=[
                    {"set_value": {"path": "variables.counter", "value": 0}},
                    {"log_message": "Counter initialized to 0"},
                ],
            ),
            FlowStep(
                id="step2",
                name="Increment Counter",
                type="completion",
                actions=[
                    {
                        "set_value": {
                            "path": "variables.counter",
                            "value": "{{ variables.counter + 1 }}",
                        }
                    },
                    {"log_message": "Counter incremented to 1"},
                ],
            ),
            FlowStep(
                id="step3",
                name="Increment Again",
                type="completion",
                actions=[
                    {
                        "set_value": {
                            "path": "variables.counter",
                            "value": "{{ variables.counter + 1 }}",
                        }
                    },
                    {"log_message": "Counter incremented to 2"},
                ],
            ),
            FlowStep(
                id="finish",
                name="Finalize",
                type="completion",
                actions=[
                    {
                        "set_value": {
                            "path": "variables.message",
                            "value": "Counting complete",
                        }
                    },
                    {"set_value": {"path": "outputs.final_count", "value": 2}},
                    {"display_value": "variables.counter"},
                    {"display_value": "variables.message"},
                ],
            ),
        ],
    )

    system.flows["counter_flow"] = flow
    print("Flow definition:")
    print(f"  Steps: {len(flow.steps)}")
    print("  Variables: counter (int), message (str)")

    print("\nExecuting flow with step monitoring...")
    steps_completed = []

    def on_step_complete(step_id: str, step_result: dict) -> None:
        steps_completed.append(step_id)
        print(f"  ✓ Step completed: {step_id} => {step_result}")

    result = service.execute_flow("counter_flow", on_step_complete=on_step_complete)

    print("\n✓ Flow completed successfully")
    print(f"  Steps executed: {' → '.join(steps_completed)}")
    print(f"  Final count: {result['final_count']}")


def demo_branching_flow(service: FlowExecutionService, system: CompleteSystem) -> None:
    """Demo 4: Flow with branching using next_step."""
    print_section("Demo 4: Branching Flow with next_step")

    flow = FlowDefinition(
        id="branching_flow",
        kind="flow",
        name="Branching Flow",
        description="Demonstrates flow control with next_step",
        outputs=[
            FlowInputOutput(type="str", id="path_taken", validate=False),
        ],
        steps=[
            FlowStep(
                id="start",
                name="Start",
                type="completion",
                actions=[
                    {
                        "set_value": {
                            "path": "outputs.path_taken",
                            "value": "start",
                        }
                    },
                    {"log_message": "Flow started, jumping to end"},
                ],
                next_step="end",  # Skip middle step
            ),
            FlowStep(
                id="middle",
                name="Middle (Skipped)",
                type="completion",
                actions=[
                    {
                        "set_value": {
                            "path": "outputs.path_taken",
                            "value": "middle",
                        }
                    },
                    {"log_message": "This should not be executed"},
                ],
            ),
            FlowStep(
                id="end",
                name="End",
                type="completion",
                actions=[
                    {"set_value": {"path": "outputs.path_taken", "value": "end"}},
                    {"log_message": "Jumped directly to end"},
                ],
            ),
        ],
    )

    system.flows["branching_flow"] = flow
    print("Flow definition:")
    print("  start → [skips middle] → end")

    print("\nExecuting branching flow...")
    result = service.execute_flow("branching_flow")

    print("\n✓ Flow completed successfully")
    print(f"  Path taken: {result['path_taken']}")
    print("  (Note: 'middle' step was skipped)")


def demo_pre_actions(service: FlowExecutionService, system: CompleteSystem) -> None:
    """Demo 5: Flow with pre-actions."""
    print_section("Demo 5: Pre-Actions")

    flow = FlowDefinition(
        id="pre_actions_flow",
        kind="flow",
        name="Pre-Actions Flow",
        description="Demonstrates pre-actions executing before step actions",
        outputs=[
            FlowInputOutput(type="str", id="result", validate=False),
        ],
        steps=[
            FlowStep(
                id="demo_step",
                name="Demo Step",
                type="completion",
                pre_actions=[
                    {
                        "set_value": {
                            "path": "outputs.result",
                            "value": "from pre-action",
                        }
                    },
                    {"log_message": "Pre-action executed first"},
                ],
                actions=[
                    {
                        "set_value": {
                            "path": "outputs.result",
                            "value": "from step action",
                        }
                    },
                    {"log_message": "Step action executed second"},
                ],
            )
        ],
    )

    system.flows["pre_actions_flow"] = flow
    print("Flow definition:")
    print("  Pre-actions set result to 'from pre-action'")
    print("  Step actions overwrite result to 'from step action'")

    print("\nExecuting flow...")
    result = service.execute_flow("pre_actions_flow")

    print("\n✓ Flow completed successfully")
    print(f"  Final result: {result['result']}")


def demo_validation(service: FlowExecutionService, system: CompleteSystem) -> None:
    """Demo 6: Flow with object validation."""
    print_section("Demo 6: Object Validation")

    flow = FlowDefinition(
        id="validation_flow",
        kind="flow",
        name="Validation Flow",
        description="Demonstrates object validation using validate_value action",
        variables=[
            FlowVariable(type="character", id="hero", validate=False),
        ],
        outputs=[
            FlowInputOutput(type="character", id="hero", validate=False),
            FlowInputOutput(type="bool", id="validation_passed", validate=False),
        ],
        steps=[
            FlowStep(
                id="create_character",
                name="Create Character",
                type="completion",
                actions=[
                    {
                        "set_value": {
                            "path": "variables.hero",
                            "value": {
                                "model": "character",
                                "name": "Brave Hero",
                                "level": 5,
                                "hp": 50,
                                "xp": 1000,
                            },
                        }
                    },
                    {"log_message": "Character created"},
                    {"display_value": "variables.hero"},
                ],
            ),
            FlowStep(
                id="validate_character",
                name="Validate Character",
                type="completion",
                actions=[
                    {"validate_value": "variables.hero"},
                    {
                        "set_value": {
                            "path": "outputs.hero",
                            "value": "{{ variables.hero }}",
                        }
                    },
                    {"log_message": "Character validation passed"},
                    {
                        "set_value": {
                            "path": "outputs.validation_passed",
                            "value": True,
                        }
                    },
                ],
            ),
        ],
    )

    system.flows["validation_flow"] = flow
    print("Flow definition:")
    print("  Creates a character object")
    print("  Validates it against the character model")

    print("\nExecuting flow...")
    result = service.execute_flow("validation_flow")

    print("\n✓ Flow completed successfully")
    print(f"  Validation passed: {result['validation_passed']}")
    print(f"  Character data: {dict(result['hero'])}")


def demo_action_callbacks(
    service: FlowExecutionService, system: CompleteSystem
) -> None:
    """Demo 7: Action callbacks for monitoring."""
    print_section("Demo 7: Action Callbacks")

    flow = FlowDefinition(
        id="callback_demo_flow",
        kind="flow",
        name="Callback Demo Flow",
        description="Demonstrates action execution callbacks",
        steps=[
            FlowStep(
                id="multi_action_step",
                name="Multi-Action Step",
                type="completion",
                actions=[
                    {"log_message": "First action"},
                    {"log_event": {"type": "demo_event", "data": {"count": 1}}},
                    {"log_message": "Second action"},
                    {"log_event": {"type": "demo_event", "data": {"count": 2}}},
                    {"log_message": "Third action"},
                ],
            )
        ],
    )

    system.flows["callback_demo_flow"] = flow
    print("Flow definition:")
    print("  Single step with 5 actions")

    print("\nExecuting flow with action monitoring...")
    actions_executed = []

    def on_action_execute(action_type: str, action_data: dict) -> None:
        actions_executed.append(action_type)
        print(f"  → Action executed: {action_type}")

    service.execute_flow("callback_demo_flow", on_action_execute=on_action_execute)

    print("\n✓ Flow completed successfully")
    print(f"  Actions executed: {len(actions_executed)}")
    print(f"  Action types: {', '.join(set(actions_executed))}")


def demo_character_creation_flow(
    service: FlowExecutionService, system: CompleteSystem
) -> None:
    """Demo 8: Realistic character creation flow."""
    print_section("Demo 8: Character Creation Flow")

    flow = FlowDefinition(
        id="create_character_flow",
        kind="flow",
        name="Create Character Flow",
        description="A realistic character creation workflow",
        inputs=[
            FlowInputOutput(type="str", id="player_name", required=True),
        ],
        outputs=[
            FlowInputOutput(type="character", id="new_character", validate=True),
        ],
        variables=[
            FlowVariable(type="int", id="starting_hp", validate=False),
            FlowVariable(type="int", id="starting_level", validate=False),
        ],
        steps=[
            FlowStep(
                id="initialize_stats",
                name="Initialize Character Stats",
                type="completion",
                actions=[
                    {"set_value": {"path": "variables.starting_hp", "value": 10}},
                    {"set_value": {"path": "variables.starting_level", "value": 1}},
                    {"log_message": "Character stats initialized"},
                ],
            ),
            FlowStep(
                id="create_character",
                name="Create Character Object",
                type="completion",
                actions=[
                    {
                        "set_value": {
                            "path": "outputs.new_character",
                            "value": {
                                "model": "character",
                                "name": "Placeholder",
                                "level": 1,
                                "hp": 10,
                                "xp": 0,
                                "status": "active",
                            },
                        }
                    },
                    {"log_message": "Character object created"},
                ],
            ),
            FlowStep(
                id="finalize",
                name="Finalize Character",
                type="completion",
                actions=[
                    {"display_value": "outputs.new_character"},
                    {
                        "log_event": {
                            "type": "character_created",
                            "data": {"name": "New Character"},
                        }
                    },
                ],
            ),
        ],
    )

    system.flows["create_character_flow"] = flow
    print("Flow definition:")
    print("  A multi-step character creation process")
    print("  Input: player_name")
    print("  Output: validated character object")

    print("\nExecuting character creation flow...")

    def on_step_complete(step_id: str, step_result: dict) -> None:
        print(f"  ✓ Completed: {step_id}")

    result = service.execute_flow(
        "create_character_flow",
        inputs={"player_name": "Alice"},
        on_step_complete=on_step_complete,
    )

    print("\n✓ Character created successfully")
    print(f"  Character data: {result['new_character']}")


def main() -> int:
    """Run all flow execution demos."""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + " " * 20 + "FLOW EXECUTION SERVICE DEMO" + " " * 31 + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    # Create the demo system and services
    system = create_demo_system()
    object_service = ObjectInstantiationService(system)
    flow_service = FlowExecutionService(system, object_service)

    print("\n✓ Services initialized")
    print("  - ObjectInstantiationService")
    print("  - FlowExecutionService")

    try:
        # Run all demos
        demo_simple_flow(flow_service, system)
        demo_flow_with_inputs_outputs(flow_service, system)
        demo_flow_with_variables(flow_service, system)
        demo_branching_flow(flow_service, system)
        demo_pre_actions(flow_service, system)
        demo_validation(flow_service, system)
        demo_action_callbacks(flow_service, system)
        demo_character_creation_flow(flow_service, system)

        # Final summary
        print_section("Demo Summary")
        print(f"✓ All {len(system.flows)} demo flows executed successfully")
        print("\nDemonstrated capabilities:")
        print("  • Simple completion flows")
        print("  • Flows with inputs and outputs")
        print("  • Variable management and context isolation")
        print("  • Branching with next_step")
        print("  • Pre-actions and step actions")
        print("  • Object validation with grimoire-model")
        print("  • Step and action callbacks")
        print("  • Realistic multi-step workflows")
        print("\nFlow execution service is ready for advanced step types!")
        print("  (Next: dice_roll, table_roll, llm_generation, etc.)")

    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        logger.error(f"Demo execution failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main() or 0)
