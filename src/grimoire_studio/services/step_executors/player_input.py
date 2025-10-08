"""Player input step executor."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ...models.grimoire_definitions import FlowStep
from ..decorators import handle_execution_error
from ..exceptions import FlowExecutionError

logger = get_logger(__name__)


class PlayerInputStepExecutor:
    """Executor for player_input steps."""

    @handle_execution_error("Player input")
    def execute(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute a player_input step.

        Args:
            step: Step to execute
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Callback for user input
            on_action_execute: Optional callback when actions execute (unused)

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If user input fails
        """
        logger.debug("Player input step")

        if not on_user_input:
            raise FlowExecutionError(
                f"player_input step '{step.id}' requires on_user_input callback"
            )

        # Get current context data for callback
        callback_context = context.to_dict()

        # Call user input callback
        user_input = on_user_input(step, callback_context)

        # Store result in step namespace
        context = context.set_variable(f"{step_namespace}.result", user_input)

        logger.info(f"Player input received: {user_input}")
        return context
