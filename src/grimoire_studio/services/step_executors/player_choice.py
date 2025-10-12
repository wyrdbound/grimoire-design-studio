"""Player choice step executor."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ...models.grimoire_definitions import CompleteSystem, FlowStep
from ..decorators import handle_execution_error
from ..exceptions import FlowExecutionError

logger = get_logger(__name__)


class PlayerChoiceStepExecutor:
    """Executor for player_choice steps."""

    def __init__(
        self,
        system: CompleteSystem,
        template_resolver: Any,
        action_executor: Callable[
            [
                dict[str, Any],
                GrimoireContext,
                Callable[[str, dict[str, Any]], None] | None,
            ],
            GrimoireContext,
        ],
        object_service: Any = None,
    ) -> None:
        """Initialize the player choice step executor.

        Args:
            system: Complete GRIMOIRE system with table definitions
            template_resolver: Template resolver adapter
            action_executor: Function to execute actions
            object_service: Object instantiation service for creating GrimoireModel objects
        """
        self.system = system
        self.template_resolver = template_resolver
        self.action_executor = action_executor
        self.object_service = object_service

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

            # Process each selection to instantiate proper objects if needed
            processed_choices = []
            for choice_id in user_choice:
                processed_choice = self._process_table_selection(
                    choice_source, choice_id
                )
                processed_choices.append(processed_choice)

            context = context.set_variable(
                f"{step_namespace}.results", processed_choices
            )
            # Create top-level alias for results (needed for actions)
            context = context.set_variable("results", processed_choices)
            # For compatibility, also store first selection as result
            context = context.set_variable(
                f"{step_namespace}.result", processed_choices[0]
            )
            selected_choice = None  # No single choice actions
        else:
            # Single selection: process to instantiate proper object if needed
            processed_choice = self._process_table_selection(choice_source, user_choice)
            context = context.set_variable(f"{step_namespace}.result", processed_choice)

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
        table_id = choice_source.get("table")
        table_from_values = choice_source.get("table_from_values")
        display_format = choice_source.get("display_format", "{{ entry|title }}")

        if table_id:
            # Generate choices from a predefined table
            return self._generate_choices_from_table(table_id, display_format, context)
        elif table_from_values:
            # Generate choices from context values
            return self._generate_choices_from_values(
                table_from_values, display_format, context
            )
        else:
            raise ValueError(
                "choice_source requires either 'table' or 'table_from_values' field"
            )

    def _generate_choices_from_table(
        self, table_id: str, display_format: str, context: GrimoireContext
    ) -> list[dict[str, Any]]:
        """Generate choices from a predefined table.

        Args:
            table_id: ID of the table to use
            display_format: Template for choice labels
            context: Current execution context

        Returns:
            List of choice dictionaries

        Raises:
            ValueError: If table is not found
        """
        if table_id not in self.system.tables:
            raise ValueError(f"Table '{table_id}' not found in system")

        table_def = self.system.tables[table_id]
        choices = []

        for entry in table_def.entries:
            entry_value = entry.get("value")
            if entry_value is None:
                continue

            # Set temporary variables for template rendering
            temp_context = context.set_variable("entry", entry_value)
            temp_context = temp_context.set_template_resolver(self.template_resolver)

            # Resolve the display format template
            try:
                label = temp_context.resolve_template(display_format)
            except Exception:
                # Fallback to simple string representation
                label = str(entry_value)

            choices.append(
                {
                    "id": str(entry_value),
                    "label": str(label) if label is not None else str(entry_value),
                }
            )

        return choices

    def _process_table_selection(
        self, choice_source: dict[str, Any] | None, selection_id: str
    ) -> Any:
        """Process a table selection to instantiate proper object if needed.

        Args:
            choice_source: Choice source configuration (may be None for static choices)
            selection_id: The selected choice ID

        Returns:
            Either the string ID (for str entry_type) or instantiated GrimoireModel object

        Raises:
            FlowExecutionError: If object instantiation fails
        """
        # If no choice_source or not a table selection, return as string
        if not choice_source or not choice_source.get("table"):
            return selection_id

        table_id = choice_source["table"]

        # Get the table definition
        if table_id not in self.system.tables:
            raise FlowExecutionError(
                f"Table '{table_id}' referenced in choice_source not found in system. "
                f"Available tables: {list(self.system.tables.keys())}"
            )

        table_def = self.system.tables[table_id]

        # If entry_type is "str", just return the selection ID
        if table_def.entry_type == "str":
            return selection_id

        # Find the selected entry in the table
        selected_entry = None
        for entry in table_def.entries:
            entry_value = entry.get("value")
            if str(entry_value) == selection_id:
                selected_entry = entry
                break

        if not selected_entry:
            # Get available entry IDs for error message
            available_entries = [
                str(entry.get("value", ""))
                for entry in table_def.entries
                if entry.get("value") is not None
            ]
            raise FlowExecutionError(
                f"Selected entry '{selection_id}' not found in table '{table_id}'. "
                f"Available entries: {available_entries}"
            )

        # Get the entry value (this could be a string ID or object data)
        entry_value = selected_entry["value"]

        # If we have an object_service, instantiate the proper object
        if self.object_service:
            try:
                # If entry_value is a string, create object from that ID
                if isinstance(entry_value, str):
                    object_data = {
                        "model": table_def.entry_type,
                        "id": entry_value,
                    }
                else:
                    # If entry_value is a dict, use it as object attributes
                    object_data = {
                        "model": table_def.entry_type,
                        **entry_value,
                    }

                logger.info(
                    f"Creating {table_def.entry_type} object from table selection: {object_data}"
                )
                return self.object_service.create_object_without_validation(object_data)

            except Exception as e:
                logger.error(
                    f"Failed to instantiate {table_def.entry_type} object: {e}"
                )
                raise FlowExecutionError(
                    f"Failed to create {table_def.entry_type} object from table selection: {e}"
                ) from e
        else:
            logger.warning("No object_service available, returning selection as string")
            return selection_id

    def _generate_choices_from_values(
        self, table_from_values: str, display_format: str, context: GrimoireContext
    ) -> list[dict[str, Any]]:
        """Generate choices from context values.

        Args:
            table_from_values: Path to data in context
            display_format: Template for choice labels
            context: Current execution context

        Returns:
            List of choice dictionaries

        Raises:
            ValueError: If data is not found or invalid
        """
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
