"""Unit tests for step executors."""

from __future__ import annotations

from typing import Any, Callable
from unittest.mock import MagicMock, Mock, patch

import pytest
from grimoire_context import GrimoireContext

from grimoire_studio.models.grimoire_definitions import CompleteSystem, FlowStep
from grimoire_studio.services.dice_service import DiceRollResult, DiceService
from grimoire_studio.services.exceptions import FlowExecutionError
from grimoire_studio.services.llm_service import LLMResult
from grimoire_studio.services.name_service import NameService
from grimoire_studio.services.step_executors.completion import CompletionStepExecutor
from grimoire_studio.services.step_executors.dice_roll import DiceRollStepExecutor
from grimoire_studio.services.step_executors.dice_sequence import (
    DiceSequenceStepExecutor,
)
from grimoire_studio.services.step_executors.llm_generation import (
    LLMGenerationStepExecutor,
)
from grimoire_studio.services.step_executors.name_generation import (
    NameGenerationStepExecutor,
)
from grimoire_studio.services.step_executors.player_choice import (
    PlayerChoiceStepExecutor,
)
from grimoire_studio.services.step_executors.player_input import (
    PlayerInputStepExecutor,
)
from grimoire_studio.services.step_executors.table_roll import TableRollStepExecutor


class MockTemplateResolver:
    """Mock template resolver for testing."""

    def resolve_template(self, template_str: str, context_dict: dict[str, Any]) -> Any:
        """Simple template resolver that replaces {{var}} with values from context."""
        result = template_str
        # Replace {{var}} patterns with values from context
        import re

        def replace_var(match: re.Match) -> str:
            var_name = match.group(1).strip()
            return str(context_dict.get(var_name, match.group(0)))

        result = re.sub(r"\{\{([^}]+)\}\}", replace_var, result)
        return result


class TestDiceRollStepExecutor:
    """Tests for DiceRollStepExecutor."""

    def test_execute_simple_roll(self) -> None:
        """Test executing a simple dice roll."""
        # Arrange
        mock_dice_service = Mock(spec=DiceService)
        mock_dice_service.roll_dice.return_value = DiceRollResult(
            expression="2d6",
            total=7,
            description="2d6: [3, 4] = 7",
            rolls=[3, 4],
        )

        executor = DiceRollStepExecutor(dice_service=mock_dice_service)

        step = FlowStep(
            id="roll1",
            name="Roll Dice",
            type="dice_roll",
            step_config={"roll": "2d6"},
            actions=[],
        )

        # Create context with mock template resolver
        context = GrimoireContext(template_resolver=MockTemplateResolver())
        step_namespace = "steps.roll1"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
        )

        # Assert
        mock_dice_service.roll_dice.assert_called_once_with("2d6")
        assert result_context.get_variable(f"{step_namespace}.result.total") == 7
        assert (
            result_context.get_variable(f"{step_namespace}.result.detail")
            == "2d6: [3, 4] = 7"
        )

    def test_execute_with_template_resolution(self) -> None:
        """Test dice roll with template resolution."""
        # Arrange
        mock_dice_service = Mock(spec=DiceService)
        mock_dice_service.roll_dice.return_value = DiceRollResult(
            expression="1d20+5",
            total=18,
            description="1d20+5: [13] + 5 = 18",
            rolls=[13],
        )

        executor = DiceRollStepExecutor(dice_service=mock_dice_service)

        step = FlowStep(
            id="roll2",
            name="Roll with Modifier",
            type="dice_roll",
            step_config={"roll": "1d20+{{modifier}}"},
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        context = context.set_variable("modifier", 5)
        step_namespace = "steps.roll2"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
        )

        # Assert
        mock_dice_service.roll_dice.assert_called_once_with("1d20+5")
        assert result_context.get_variable(f"{step_namespace}.result.total") == 18

    def test_execute_missing_roll_field(self) -> None:
        """Test error when roll field is missing."""
        # Arrange
        mock_dice_service = Mock(spec=DiceService)
        executor = DiceRollStepExecutor(dice_service=mock_dice_service)

        step = FlowStep(
            id="roll3",
            name="Bad Roll",
            type="dice_roll",
            step_config={},  # Missing 'roll' field
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())

        # Act & Assert
        with pytest.raises(FlowExecutionError, match="missing 'roll' field"):
            executor.execute(
                step=step,
                context=context,
                step_namespace="steps.roll3",
            )


class TestDiceSequenceStepExecutor:
    """Tests for DiceSequenceStepExecutor."""

    def test_execute_simple_sequence(self) -> None:
        """Test executing a dice sequence."""
        # Arrange
        mock_dice_service = Mock(spec=DiceService)
        mock_dice_service.roll_dice.return_value = DiceRollResult(
            expression="3d6",
            total=12,
            description="3d6: [4, 3, 5] = 12",
            rolls=[4, 3, 5],
        )

        # Mock action executor
        def mock_action_executor(
            action: dict[str, Any],
            ctx: GrimoireContext,
            callback: Callable[[str, dict[str, Any]], None] | None,
        ) -> GrimoireContext:
            return ctx

        executor = DiceSequenceStepExecutor(
            dice_service=mock_dice_service,
            action_executor=mock_action_executor,
        )

        step = FlowStep(
            id="seq1",
            name="Roll Sequence",
            type="dice_sequence",
            step_config={
                "sequence": {
                    "items": ["item1", "item2", "item3"],
                    "roll": "1d6",
                }
            },
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        step_namespace = "steps.seq1"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
        )

        # Assert
        assert result_context.get_variable(f"{step_namespace}.result.total") == 12
        assert (
            result_context.get_variable(f"{step_namespace}.result.detail")
            == "3d6: [4, 3, 5] = 12"
        )


class TestTableRollStepExecutor:
    """Tests for TableRollStepExecutor."""

    def test_execute_table_roll(self) -> None:
        """Test executing a table roll."""
        # Arrange
        mock_dice_service = Mock(spec=DiceService)
        mock_dice_service.roll_dice.return_value = DiceRollResult(
            expression="1d6",
            total=4,
            description="1d6: [4] = 4",
            rolls=[4],
        )

        # Mock system with table definition
        from grimoire_studio.models.grimoire_definitions import TableDefinition

        mock_table = Mock(spec=TableDefinition)
        mock_table.roll = "1d6"
        mock_table.entries = [
            {"range": "1-2", "value": "coins"},
            {"range": "3-4", "value": "gems"},
            {"range": "5-6", "value": "magic item"},
        ]

        mock_system = Mock(spec=CompleteSystem)
        mock_system.tables = {"treasure": mock_table}

        # Mock action executor
        def mock_action_executor(
            action: dict[str, Any],
            ctx: GrimoireContext,
            callback: Callable[[str, dict[str, Any]], None] | None,
        ) -> GrimoireContext:
            return ctx

        executor = TableRollStepExecutor(
            system=mock_system,
            dice_service=mock_dice_service,
            action_executor=mock_action_executor,
        )

        step = FlowStep(
            id="table1",
            name="Table Roll",
            type="table_roll",
            step_config={"tables": [{"table": "treasure"}]},
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        step_namespace = "steps.table1"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
        )

        # Assert
        mock_dice_service.roll_dice.assert_called_once_with("1d6")
        result = result_context.get_variable(f"{step_namespace}.result")
        assert result["entry"] == "gems"
        assert result["roll_result"]["total"] == 4


class TestPlayerInputStepExecutor:
    """Tests for PlayerInputStepExecutor."""

    def test_execute_player_input(self) -> None:
        """Test executing a player input step."""
        # Arrange
        executor = PlayerInputStepExecutor()

        step = FlowStep(
            id="input1",
            name="Get Name",
            type="player_input",
            prompt="Enter your name:",
            step_config={},
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        step_namespace = "steps.input1"

        # Mock callback
        def mock_input_callback(step: FlowStep, config: dict) -> str:
            return "Gandalf"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
            on_user_input=mock_input_callback,
        )

        # Assert
        assert result_context.get_variable(f"{step_namespace}.result") == "Gandalf"

    def test_execute_without_callback_raises_error(self) -> None:
        """Test that missing callback raises error."""
        # Arrange
        executor = PlayerInputStepExecutor()

        step = FlowStep(
            id="input2",
            name="Get Input",
            type="player_input",
            prompt="Enter something:",
            step_config={},
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())

        # Act & Assert
        with pytest.raises(FlowExecutionError, match="requires on_user_input callback"):
            executor.execute(
                step=step,
                context=context,
                step_namespace="steps.input2",
                on_user_input=None,
            )


class TestPlayerChoiceStepExecutor:
    """Tests for PlayerChoiceStepExecutor."""

    def test_execute_static_choices(self) -> None:
        """Test executing player choice with static options."""
        # Arrange
        # Mock template resolver
        mock_template_resolver = Mock()

        # Mock action executor
        def mock_action_executor(
            action: dict[str, Any],
            ctx: GrimoireContext,
            callback: Callable[[str, dict[str, Any]], None] | None,
        ) -> GrimoireContext:
            return ctx

        executor = PlayerChoiceStepExecutor(
            template_resolver=mock_template_resolver,
            action_executor=mock_action_executor,
        )

        step = FlowStep(
            id="choice1",
            name="Choose Path",
            type="player_choice",
            prompt="Which way?",
            step_config={
                "choices": [
                    {"label": "Left", "value": "left"},
                    {"label": "Right", "value": "right"},
                ]
            },
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        step_namespace = "steps.choice1"

        # Mock callback
        def mock_choice_callback(step: FlowStep, config: dict) -> dict:
            return {"label": "Right", "value": "right"}

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
            on_user_input=mock_choice_callback,
        )

        # Assert
        result = result_context.get_variable(f"{step_namespace}.result")
        assert result["label"] == "Right"
        assert result["value"] == "right"

    def test_execute_dynamic_choices(self) -> None:
        """Test executing player choice with dynamic options from context."""
        # Arrange
        # Mock template resolver
        mock_template_resolver = Mock()

        # Mock action executor
        def mock_action_executor(
            action: dict[str, Any],
            ctx: GrimoireContext,
            callback: Callable[[str, dict[str, Any]], None] | None,
        ) -> GrimoireContext:
            return ctx

        executor = PlayerChoiceStepExecutor(
            template_resolver=mock_template_resolver,
            action_executor=mock_action_executor,
        )

        step = FlowStep(
            id="choice2",
            name="Choose Item",
            type="player_choice",
            prompt="Select an item:",
            step_config={
                "choices_from": "inventory.items",
            },
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        context = context.set_variable(
            "inventory.items",
            [
                {"label": "Sword", "value": "sword"},
                {"label": "Shield", "value": "shield"},
            ],
        )
        step_namespace = "steps.choice2"

        # Mock callback
        def mock_choice_callback(step: FlowStep, config: dict) -> dict:
            return {"label": "Sword", "value": "sword"}

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
            on_user_input=mock_choice_callback,
        )

        # Assert
        result = result_context.get_variable(f"{step_namespace}.result")
        assert result["value"] == "sword"


class TestNameGenerationStepExecutor:
    """Tests for NameGenerationStepExecutor."""

    @patch("grimoire_studio.services.step_executors.name_generation.NameService")
    def test_execute_name_generation(self, mock_name_service_class: Mock) -> None:
        """Test executing name generation step."""
        # Arrange
        mock_name_service = Mock(spec=NameService)
        mock_name_service.generate_name.return_value = "Thorin"
        mock_name_service_class.return_value = mock_name_service

        executor = NameGenerationStepExecutor()

        step = FlowStep(
            id="name1",
            name="Generate Name",
            type="name_generation",
            step_config={
                "settings": {
                    "max_length": 10,
                    "corpus": "dwarf-names",
                    "segmenter": "fantasy",
                    "algorithm": "bayesian",
                }
            },
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        step_namespace = "steps.name1"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
        )

        # Assert
        mock_name_service_class.assert_called_once_with(
            name_list="dwarf-names",
            segmenter="fantasy",
        )
        mock_name_service.generate_name.assert_called_once_with(
            max_length=10,
            algorithm="bayesian",
        )
        assert result_context.get_variable(f"{step_namespace}.result.name") == "Thorin"

    @patch("grimoire_studio.services.step_executors.name_generation.NameService")
    def test_execute_with_defaults(self, mock_name_service_class: Mock) -> None:
        """Test name generation with default settings."""
        # Arrange
        mock_name_service = Mock(spec=NameService)
        mock_name_service.generate_name.return_value = "Elrond"
        mock_name_service_class.return_value = mock_name_service

        executor = NameGenerationStepExecutor()

        step = FlowStep(
            id="name2",
            name="Generate Default Name",
            type="name_generation",
            step_config={},  # No settings
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        step_namespace = "steps.name2"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
        )

        # Assert
        mock_name_service_class.assert_called_once_with(
            name_list="generic-fantasy",  # default
            segmenter="fantasy",  # default
        )
        mock_name_service.generate_name.assert_called_once_with(
            max_length=15,  # default
            algorithm="bayesian",  # default
        )
        assert result_context.get_variable(f"{step_namespace}.result.name") == "Elrond"


class TestLLMGenerationStepExecutor:
    """Tests for LLMGenerationStepExecutor."""

    def test_execute_llm_generation(self) -> None:
        """Test executing LLM generation step."""
        # Arrange
        from grimoire_studio.models.grimoire_definitions import PromptDefinition

        mock_llm_service = MagicMock()
        mock_llm_service.execute_prompt.return_value = LLMResult(
            prompt="Describe a dragon",
            response="A majestic red dragon with scales like rubies",
            provider="openai",
            model="gpt-4",
        )

        # Mock prompt definition
        mock_prompt = Mock(spec=PromptDefinition)
        mock_prompt.prompt_template = "Describe a {creature}"
        mock_prompt.llm = {"provider": "openai", "model": "gpt-4"}

        mock_system = Mock(spec=CompleteSystem)
        mock_system.prompts = {"describe_creature": mock_prompt}

        # Mock template dict resolver
        def mock_template_dict_resolver(
            template_dict: dict[str, Any],
            ctx: GrimoireContext,
        ) -> dict[str, Any]:
            return template_dict

        executor = LLMGenerationStepExecutor(
            system=mock_system,
            llm_service=mock_llm_service,
            template_dict_resolver=mock_template_dict_resolver,
        )

        step = FlowStep(
            id="llm1",
            name="Generate Description",
            type="llm_generation",
            step_config={
                "prompt_id": "describe_creature",
                "prompt_data": {"creature": "dragon"},
            },
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        step_namespace = "steps.llm1"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
        )

        # Assert
        mock_llm_service.execute_prompt.assert_called_once_with("Describe a dragon")
        result = result_context.get_variable(f"{step_namespace}.result")
        assert result == "A majestic red dragon with scales like rubies"

    def test_execute_with_template_prompt(self) -> None:
        """Test LLM generation with template in prompt."""
        # Arrange
        from grimoire_studio.models.grimoire_definitions import PromptDefinition

        mock_llm_service = MagicMock()
        mock_llm_service.execute_prompt.return_value = LLMResult(
            prompt="Describe a blue dragon",
            response="An azure dragon soaring through clouds",
            provider="openai",
            model="gpt-4",
        )

        # Mock prompt definition
        mock_prompt = Mock(spec=PromptDefinition)
        mock_prompt.prompt_template = "Describe a {color} {creature}"
        mock_prompt.llm = {"provider": "openai", "model": "gpt-4"}

        mock_system = Mock(spec=CompleteSystem)
        mock_system.prompts = {"describe_colored_creature": mock_prompt}

        # Mock template dict resolver that resolves templates
        def mock_template_dict_resolver(
            template_dict: dict[str, Any],
            ctx: GrimoireContext,
        ) -> dict[str, Any]:
            # Resolve any template strings in the dict
            result = {}
            for key, value in template_dict.items():
                if isinstance(value, str) and "{{" in value:
                    # Simple template resolution
                    result[key] = ctx.resolve_template(value)
                else:
                    result[key] = value
            return result

        executor = LLMGenerationStepExecutor(
            system=mock_system,
            llm_service=mock_llm_service,
            template_dict_resolver=mock_template_dict_resolver,
        )

        step = FlowStep(
            id="llm2",
            name="Generate with Template",
            type="llm_generation",
            step_config={
                "prompt_id": "describe_colored_creature",
                "prompt_data": {
                    "color": "{{color}}",
                    "creature": "dragon",
                },
            },
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        context = context.set_variable("color", "blue")
        step_namespace = "steps.llm2"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
        )

        # Assert
        mock_llm_service.execute_prompt.assert_called_once_with(
            "Describe a blue dragon"
        )
        result = result_context.get_variable(f"{step_namespace}.result")
        assert result == "An azure dragon soaring through clouds"


class TestCompletionStepExecutor:
    """Tests for CompletionStepExecutor."""

    def test_execute_completion(self) -> None:
        """Test executing completion step."""
        # Arrange
        executor = CompletionStepExecutor()

        step = FlowStep(
            id="complete1",
            name="Complete Flow",
            type="completion",
            step_config={
                "output_object": "character",
            },
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        context = context.set_variable("character.name", "Aragorn")
        context = context.set_variable("character.class", "Ranger")
        step_namespace = "steps.complete1"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
        )

        # Assert
        result = result_context.get_variable(f"{step_namespace}.result")
        assert result["completed"] is True

    def test_execute_completion_without_object(self) -> None:
        """Test completion without output object."""
        # Arrange
        executor = CompletionStepExecutor()

        step = FlowStep(
            id="complete2",
            name="Complete Simple",
            type="completion",
            step_config={},  # No output_object
            actions=[],
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        step_namespace = "steps.complete2"

        # Act
        result_context = executor.execute(
            step=step,
            context=context,
            step_namespace=step_namespace,
        )

        # Assert
        result = result_context.get_variable(f"{step_namespace}.result")
        assert result["completed"] is True
