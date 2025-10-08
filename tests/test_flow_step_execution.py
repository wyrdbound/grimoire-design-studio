"""Tests for flow step execution with proper context management."""

from __future__ import annotations

import pytest
from grimoire_model import AttributeDefinition, ModelDefinition

from grimoire_studio.models.grimoire_definitions import (
    CompleteSystem,
    FlowDefinition,
    FlowInputOutput,
    FlowStep,
    FlowVariable,
    PromptDefinition,
    SystemDefinition,
    TableDefinition,
)
from grimoire_studio.services.dice_service import DiceService
from grimoire_studio.services.flow_service import FlowExecutionService
from grimoire_studio.services.llm_service import LLMConfig, LLMService
from grimoire_studio.services.name_service import NameService
from grimoire_studio.services.object_service import ObjectInstantiationService


@pytest.fixture
def basic_system():
    """Create a basic test system."""
    system_def = SystemDefinition(
        id="test_system", kind="system", name="Test System", version=1
    )

    # Create a simple model for testing
    model_def = ModelDefinition(
        id="character",
        kind="model",
        name="Character",
        version=1,
        attributes={
            "name": AttributeDefinition(type="str", required=True),
            "hp": AttributeDefinition(type="int", required=True),
            "level": AttributeDefinition(type="int", required=True),
        },
    )

    # Create a test table
    table_def = TableDefinition(
        id="test_table",
        kind="table",
        name="Test Table",
        version=1,
        roll="1d6",
        entries=[
            {"range": "1-2", "value": "common"},
            {"range": "3-4", "value": "uncommon"},
            {"range": "5-6", "value": "rare"},
        ],
    )

    # Create a test prompt
    prompt_def = PromptDefinition(
        id="test_prompt",
        kind="prompt",
        name="Test Prompt",
        version=1,
        prompt_template="Generate a description for {name}",
    )

    return CompleteSystem(
        system=system_def,
        models={"character": model_def},
        tables={"test_table": table_def},
        prompts={"test_prompt": prompt_def},
    )


@pytest.fixture
def flow_service(basic_system):
    """Create a flow execution service."""
    object_service = ObjectInstantiationService(basic_system)
    dice_service = DiceService()
    llm_service = LLMService(LLMConfig(provider="mock"))
    name_service = NameService()

    return FlowExecutionService(
        system=basic_system,
        object_service=object_service,
        dice_service=dice_service,
        llm_service=llm_service,
        name_service=name_service,
    )


class TestDiceRollStep:
    """Tests for dice_roll step type."""

    def test_dice_roll_basic(self, flow_service, basic_system):
        """Test basic dice roll step."""
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            version=1,
            outputs=[FlowInputOutput(type="int", id="damage")],
            steps=[
                FlowStep.from_dict(
                    {
                        "id": "roll_damage",
                        "name": "Roll Damage",
                        "type": "dice_roll",
                        "roll": "2d6+3",
                        "actions": [
                            {
                                "set_value": {
                                    "path": "outputs.damage",
                                    "value": "{{ result.total }}",
                                }
                            }
                        ],
                    }
                )
            ],
        )

        basic_system.flows = {"test_flow": flow_def}

        # Track step completions
        completed_steps = []

        def on_step_complete(step_id, step_result):
            completed_steps.append((step_id, step_result))

        outputs = flow_service.execute_flow(
            "test_flow", on_step_complete=on_step_complete
        )

        # Verify dice roll executed
        assert len(completed_steps) == 1
        assert completed_steps[0][0] == "roll_damage"
        assert "result" in completed_steps[0][1]
        assert "total" in completed_steps[0][1]["result"]
        assert "detail" in completed_steps[0][1]["result"]

        # Verify result is within expected range (2d6+3 = 5-15)
        total = completed_steps[0][1]["result"]["total"]
        assert 5 <= total <= 15

        # Verify output was set correctly
        assert "damage" in outputs
        assert outputs["damage"] == total

    def test_dice_roll_with_template(self, flow_service, basic_system):
        """Test dice roll with template resolution."""
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            version=1,
            variables=[FlowVariable(type="str", id="dice_expr")],
            steps=[
                FlowStep.from_dict(
                    {
                        "id": "set_dice",
                        "name": "Set Dice",
                        "type": "completion",
                        "pre_actions": [
                            {
                                "set_value": {
                                    "path": "variables.dice_expr",
                                    "value": "1d20",
                                }
                            }
                        ],
                    }
                ),
                FlowStep.from_dict(
                    {
                        "id": "roll_dice",
                        "name": "Roll Dice",
                        "type": "dice_roll",
                        "roll": "{{ variables.dice_expr }}",
                    }
                ),
            ],
        )

        basic_system.flows = {"test_flow": flow_def}

        completed_steps = []

        def on_step_complete(step_id, step_result):
            completed_steps.append((step_id, step_result))

        flow_service.execute_flow("test_flow", on_step_complete=on_step_complete)

        # Verify both steps completed
        assert len(completed_steps) == 2
        assert completed_steps[1][0] == "roll_dice"
        assert "result" in completed_steps[1][1]

        # Result should be in valid range for 1d20
        total = completed_steps[1][1]["result"]["total"]
        assert 1 <= total <= 20


class TestDiceSequenceStep:
    """Tests for dice_sequence step type."""

    def test_dice_sequence_basic(self, flow_service, basic_system):
        """Test basic dice sequence step."""
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            version=1,
            outputs=[FlowInputOutput(type="dict", id="abilities")],
            steps=[
                FlowStep.from_dict(
                    {
                        "id": "roll_abilities",
                        "name": "Roll Abilities",
                        "type": "dice_sequence",
                        "sequence": {
                            "items": ["strength", "dexterity", "constitution"],
                            "roll": "3d6",
                            "actions": [],
                        },
                    }
                )
            ],
        )

        basic_system.flows = {"test_flow": flow_def}

        completed_steps = []

        def on_step_complete(step_id, step_result):
            completed_steps.append((step_id, step_result))

        flow_service.execute_flow("test_flow", on_step_complete=on_step_complete)

        # Verify step completed
        assert len(completed_steps) == 1
        assert completed_steps[0][0] == "roll_abilities"


class TestTableRollStep:
    """Tests for table_roll step type."""

    def test_table_roll_basic(self, flow_service, basic_system):
        """Test basic table roll step."""
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            version=1,
            variables=[FlowVariable(type="str", id="rarity")],
            steps=[
                FlowStep.from_dict(
                    {
                        "id": "roll_rarity",
                        "name": "Roll Rarity",
                        "type": "table_roll",
                        "tables": [
                            {
                                "table": "test_table",
                                "actions": [
                                    {
                                        "set_value": {
                                            "path": "variables.rarity",
                                            "value": "{{ result.entry }}",
                                        }
                                    }
                                ],
                            }
                        ],
                    }
                )
            ],
        )

        basic_system.flows = {"test_flow": flow_def}

        completed_steps = []

        def on_step_complete(step_id, step_result):
            completed_steps.append((step_id, step_result))

        flow_service.execute_flow("test_flow", on_step_complete=on_step_complete)

        # Verify step completed
        assert len(completed_steps) == 1
        assert completed_steps[0][0] == "roll_rarity"
        assert "result" in completed_steps[0][1]
        assert "entry" in completed_steps[0][1]["result"]
        assert "roll_result" in completed_steps[0][1]["result"]

        # Entry should be one of the valid values
        entry = completed_steps[0][1]["result"]["entry"]
        assert entry in ["common", "uncommon", "rare"]


class TestPlayerInputStep:
    """Tests for player_input step type."""

    def test_player_input_basic(self, flow_service, basic_system):
        """Test basic player input step."""
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            version=1,
            variables=[FlowVariable(type="str", id="character_name")],
            steps=[
                FlowStep.from_dict(
                    {
                        "id": "get_name",
                        "name": "Get Name",
                        "type": "player_input",
                        "prompt": "Enter character name",
                        "actions": [
                            {
                                "set_value": {
                                    "path": "variables.character_name",
                                    "value": "{{ result }}",
                                }
                            }
                        ],
                    }
                )
            ],
        )

        basic_system.flows = {"test_flow": flow_def}

        # Mock user input callback
        def on_user_input(step, context):
            return "TestHero"

        flow_service.execute_flow("test_flow", on_user_input=on_user_input)

        # Flow should complete without errors


class TestPlayerChoiceStep:
    """Tests for player_choice step type."""

    def test_player_choice_basic(self, flow_service, basic_system):
        """Test basic player choice step."""
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            version=1,
            variables=[FlowVariable(type="str", id="chosen_action")],
            steps=[
                FlowStep.from_dict(
                    {
                        "id": "choose_action",
                        "name": "Choose Action",
                        "type": "player_choice",
                        "prompt": "What do you want to do?",
                        "choices": [
                            {
                                "id": "attack",
                                "label": "Attack",
                                "actions": [
                                    {
                                        "set_value": {
                                            "path": "variables.chosen_action",
                                            "value": "attack",
                                        }
                                    }
                                ],
                            },
                            {
                                "id": "defend",
                                "label": "Defend",
                                "actions": [
                                    {
                                        "set_value": {
                                            "path": "variables.chosen_action",
                                            "value": "defend",
                                        }
                                    }
                                ],
                            },
                        ],
                    }
                )
            ],
        )

        basic_system.flows = {"test_flow": flow_def}

        # Mock user choice callback
        def on_user_input(step, context):
            return "attack"

        flow_service.execute_flow("test_flow", on_user_input=on_user_input)

        # Flow should complete without errors


class TestLLMGenerationStep:
    """Tests for llm_generation step type."""

    def test_llm_generation_basic(self, flow_service, basic_system):
        """Test basic LLM generation step."""
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            version=1,
            variables=[FlowVariable(type="str", id="description")],
            steps=[
                FlowStep.from_dict(
                    {
                        "id": "generate_description",
                        "name": "Generate Description",
                        "type": "llm_generation",
                        "prompt_id": "test_prompt",
                        "prompt_data": {"name": "TestCharacter"},
                        "actions": [
                            {
                                "set_value": {
                                    "path": "variables.description",
                                    "value": "{{ result }}",
                                }
                            }
                        ],
                    }
                )
            ],
        )

        basic_system.flows = {"test_flow": flow_def}

        completed_steps = []

        def on_step_complete(step_id, step_result):
            completed_steps.append((step_id, step_result))

        flow_service.execute_flow("test_flow", on_step_complete=on_step_complete)

        # Verify step completed
        assert len(completed_steps) == 1
        assert completed_steps[0][0] == "generate_description"
        assert "result" in completed_steps[0][1]
        assert isinstance(completed_steps[0][1]["result"], str)


class TestNameGenerationStep:
    """Tests for name_generation step type."""

    def test_name_generation_basic(self, flow_service, basic_system):
        """Test basic name generation step."""
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            version=1,
            variables=[FlowVariable(type="str", id="character_name")],
            steps=[
                FlowStep.from_dict(
                    {
                        "id": "generate_name",
                        "name": "Generate Name",
                        "type": "name_generation",
                        "settings": {
                            "max_length": 12,
                            "corpus": "generic-fantasy",
                            "segmenter": "fantasy",
                            "algorithm": "simple",
                        },
                        "actions": [
                            {
                                "set_value": {
                                    "path": "variables.character_name",
                                    "value": "{{ result.name }}",
                                }
                            }
                        ],
                    }
                )
            ],
        )

        basic_system.flows = {"test_flow": flow_def}

        completed_steps = []

        def on_step_complete(step_id, step_result):
            completed_steps.append((step_id, step_result))

        flow_service.execute_flow("test_flow", on_step_complete=on_step_complete)

        # Verify step completed
        assert len(completed_steps) == 1
        assert completed_steps[0][0] == "generate_name"
        assert "result" in completed_steps[0][1]
        assert "name" in completed_steps[0][1]["result"]
        assert isinstance(completed_steps[0][1]["result"]["name"], str)
        assert len(completed_steps[0][1]["result"]["name"]) <= 12


class TestContextCleanup:
    """Tests for context cleanup after step execution."""

    def test_context_cleanup_after_dice_roll(self, flow_service, basic_system):
        """Test that step namespace is cleaned up after dice roll."""
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            version=1,
            steps=[
                FlowStep.from_dict(
                    {
                        "id": "roll1",
                        "name": "Roll 1",
                        "type": "dice_roll",
                        "roll": "1d6",
                    }
                ),
                FlowStep.from_dict(
                    {
                        "id": "roll2",
                        "name": "Roll 2",
                        "type": "dice_roll",
                        "roll": "1d6",
                    }
                ),
            ],
        )

        basic_system.flows = {"test_flow": flow_def}

        completed_steps = []

        def on_step_complete(step_id, step_result):
            completed_steps.append((step_id, step_result))

        flow_service.execute_flow("test_flow", on_step_complete=on_step_complete)

        # Both steps should complete
        assert len(completed_steps) == 2

        # Each should have its own result
        assert "result" in completed_steps[0][1]
        assert "result" in completed_steps[1][1]

        # Results should be independent (might be same value, but different objects)
        # This test just ensures no crashes from context pollution


class TestCompletionStep:
    """Tests for completion step type."""

    def test_completion_step(self, flow_service, basic_system):
        """Test completion step."""
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            version=1,
            steps=[
                FlowStep.from_dict(
                    {
                        "id": "finish",
                        "name": "Finish",
                        "type": "completion",
                        "actions": [{"log_message": "Flow completed"}],
                    }
                )
            ],
        )

        basic_system.flows = {"test_flow": flow_def}

        completed_steps = []

        def on_step_complete(step_id, step_result):
            completed_steps.append((step_id, step_result))

        flow_service.execute_flow("test_flow", on_step_complete=on_step_complete)

        # Verify completion step executed
        assert len(completed_steps) == 1
        assert completed_steps[0][0] == "finish"
        assert "result" in completed_steps[0][1]
        assert completed_steps[0][1]["result"]["completed"] is True
