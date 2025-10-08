"""Player choice step executor."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ...models.grimoire_definitions import FlowStep
from ..decorators import handle_execution_error
from ..exceptions import FlowExecutionError

logger = get_logger(__name__)


class PlayerChoiceStepExecutor:
    """Executor for player_choice steps."""

    def __init__(
        self,
        template_resolver: Any,
        action_executor: Callable[
            [
                dict[str, Any],
                GrimoireContext,
                Callable[[str, dict[str, Any]], None] | None,
            ],
            GrimoireContext,
        ],
    ) -> None:
        """Initialize the player choice step executor.

        Args:
            template_resolver: Template resolver adapter
            action_executor: Function to execute actions
        """
        self.template_resolver = template_resolver
        self.action_executor = action_executor

    @handle_execution_error("Player choice")
    def execute(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute a player_choice step.

        Args:
            step: Step to execute
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Callback for user input
            on_action_execute: Optional callback when actions execute

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If player choice fails
        """
        logger.debug("Player choice step")

        if not on_user_input:
            raise FlowExecutionError(
                f"player_choice step '{step.id}' requires on_user_input callback"
            )

        # Generate choices from choice_source or use static choices
        choice_source = step.step_config.get("choice_source")
        if choice_source:
            choices = self._generate_dynamic_choices(choice_source, context)
        else:
            choices = step.step_config.get("choices", [])

        # Store generated choices in step config so UI can access them
        step.step_config["choices"] = choices

        # Get current context data for callback
        callback_context = context.to_dict()

        # Call user choice callback (choice ID or array of choice IDs)
        user_choice = on_user_input(step, callback_context)

        # Handle single vs multi-selection
        selection_count = (
            choice_source.get("selection_count", 1) if choice_source else 1
        )

        if selection_count > 1:
            # Multi-selection: store as 'results' array
            if not isinstance(user_choice, list):
                raise FlowExecutionError(
                    f"Multi-selection expected list, got {type(user_choice)}"
                )
            if len(user_choice) != selection_count:
                raise FlowExecutionError(
                    f"Expected {selection_count} selections, got {len(user_choice)}"
                )
            context = context.set_variable(f"{step_namespace}.results", user_choice)
            # Create top-level alias for results (needed for actions)
            context = context.set_variable("results", user_choice)
            # For compatibility, also store first selection as result
            context = context.set_variable(f"{step_namespace}.result", user_choice[0])
            selected_choice = None  # No single choice actions
        else:
            # Single selection: store as 'result'
            context = context.set_variable(f"{step_namespace}.result", user_choice)

            # Find the selected choice for action execution
            selected_choice = None
            for choice in choices:
                if (
                    choice.get("id") == user_choice
                    or choice.get("label") == user_choice
                ):
                    selected_choice = choice
                    break

        if selected_choice:
            # Execute choice actions
            choice_actions = selected_choice.get("actions", [])
            for action in choice_actions:
                context = self.action_executor(action, context, on_action_execute)

            # Note: next_step handling is done in _execute_steps method
            # We store it in the result for the caller to handle
            if selected_choice.get("next_step"):
                context = context.set_variable(
                    f"{step_namespace}.next_step_override",
                    selected_choice["next_step"],
                )

        logger.info(f"Player choice: {user_choice}")
        return context

    @handle_execution_error("Failed to generate dynamic choices")
    def _generate_dynamic_choices(
        self, choice_source: dict[str, Any], context: GrimoireContext
    ) -> list[dict[str, Any]]:
        """Generate choices from a choice_source configuration.

        Args:
            choice_source: Configuration for dynamic choice generation
            context: Current execution context for data access

        Returns:
            List of choice dictionaries with id and label

        Raises:
            FlowExecutionError: If choice generation fails
        """
        table_from_values = choice_source.get("table_from_values")
        display_format = choice_source.get("display_format", "{{ key }}: {{ value }}")

        if not table_from_values:
            raise ValueError("choice_source requires 'table_from_values' field")

        # Resolve the data path
        data = context.resolve_template(f"{{{{ {table_from_values} }}}}")

        if not isinstance(data, dict):
            raise ValueError(f"Data at '{table_from_values}' is not a dictionary")

        choices = []
        for key, value in data.items():
            # Set temporary variables for template rendering
            temp_context = context.set_variable("key", key)
            temp_context = temp_context.set_variable("value", value)

            # Ensure template resolver is set
            temp_context = temp_context.set_template_resolver(self.template_resolver)

            # Resolve the display format template
            label = temp_context.resolve_template(display_format)

            choices.append(
                {
                    "id": key,
                    "label": str(label) if label is not None else key,
                }
            )

        return choices
