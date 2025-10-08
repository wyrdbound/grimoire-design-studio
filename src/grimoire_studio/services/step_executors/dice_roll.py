"""Dice roll step executor."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ...models.grimoire_definitions import FlowStep
from ..decorators import handle_execution_error
from ..dice_service import DiceService
from ..exceptions import FlowExecutionError

logger = get_logger(__name__)


class DiceRollStepExecutor:
    """Executor for dice_roll steps."""

    def __init__(self, dice_service: DiceService) -> None:
        """Initialize the dice roll step executor.

        Args:
            dice_service: Service for dice rolling
        """
        self.dice_service = dice_service

    @handle_execution_error("Dice roll")
    def execute(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute a dice_roll step.

        Args:
            step: Step to execute
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Optional callback for user input (unused)
            on_action_execute: Optional callback when actions execute (unused)

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If dice roll fails
        """
        # Get roll expression from step config
        roll_expr = step.step_config.get("roll")
        if not roll_expr:
            raise FlowExecutionError(f"dice_roll step '{step.id}' missing 'roll' field")

        # Resolve template in roll expression
        if isinstance(roll_expr, str):
            roll_expr = context.resolve_template(roll_expr)

        logger.debug(f"Rolling dice: {roll_expr}")

        # Execute dice roll
        dice_result = self.dice_service.roll_dice(roll_expr)

        # Store result in step namespace
        result_dict = {
            "total": dice_result.total,
            "detail": dice_result.description,
        }
        context = context.set_variable(f"{step_namespace}.result", result_dict)

        logger.info(f"Dice roll result: {dice_result.total}")
        return context
