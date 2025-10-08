"""Dice sequence step executor."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ...models.grimoire_definitions import FlowStep
from ..decorators import handle_execution_error
from ..dice_service import DiceService
from ..exceptions import FlowExecutionError

logger = get_logger(__name__)


class DiceSequenceStepExecutor:
    """Executor for dice_sequence steps."""

    def __init__(
        self,
        dice_service: DiceService,
        action_executor: Callable[
            [
                dict[str, Any],
                GrimoireContext,
                Callable[[str, dict[str, Any]], None] | None,
            ],
            GrimoireContext,
        ],
    ) -> None:
        """Initialize the dice sequence step executor.

        Args:
            dice_service: Service for dice rolling
            action_executor: Function to execute actions
        """
        self.dice_service = dice_service
        self.action_executor = action_executor

    @handle_execution_error("Dice sequence")
    def execute(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute a dice_sequence step.

        Args:
            step: Step to execute
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Optional callback for user input (unused)
            on_action_execute: Optional callback when actions execute

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If dice sequence fails
        """
        # Get sequence config
        sequence = step.step_config.get("sequence", {})
        items = sequence.get("items", [])
        roll_expr = sequence.get("roll")
        sequence_actions = sequence.get("actions", [])

        if not items:
            raise FlowExecutionError(
                f"dice_sequence step '{step.id}' missing 'items' in sequence"
            )
        if not roll_expr:
            raise FlowExecutionError(
                f"dice_sequence step '{step.id}' missing 'roll' in sequence"
            )

        logger.debug(f"Rolling dice sequence for {len(items)} items")

        # Iterate over items and roll dice for each
        for item in items:
            # Set current item in step namespace
            context = context.set_variable(f"{step_namespace}.item", item)

            # Create top-level alias for item
            context = context.set_variable("item", item)

            # Resolve template in roll expression (may reference item)
            resolved_roll = context.resolve_template(str(roll_expr))

            # Execute dice roll
            dice_result = self.dice_service.roll_dice(resolved_roll)

            # Store result in step namespace
            result_dict = {
                "total": dice_result.total,
                "detail": dice_result.description,
            }
            context = context.set_variable(f"{step_namespace}.result", result_dict)

            # Create top-level alias for result
            context = context.set_variable("result", result_dict)

            # Execute sequence actions for this item
            for action in sequence_actions:
                context = self.action_executor(action, context, on_action_execute)

        return context
