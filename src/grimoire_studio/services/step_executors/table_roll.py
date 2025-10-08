"""Table roll step executor."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ...models.grimoire_definitions import CompleteSystem, FlowStep
from ..decorators import handle_execution_error
from ..dice_service import DiceService
from ..exceptions import FlowExecutionError

logger = get_logger(__name__)


class TableRollStepExecutor:
    """Executor for table_roll steps."""

    def __init__(
        self,
        system: CompleteSystem,
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
        """Initialize the table roll step executor.

        Args:
            system: Complete GRIMOIRE system with table definitions
            dice_service: Service for dice rolling
            action_executor: Function to execute actions
        """
        self.system = system
        self.dice_service = dice_service
        self.action_executor = action_executor

    @handle_execution_error("Table roll")
    def execute(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute a table_roll step.

        Args:
            step: Step to execute
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Optional callback for user input (unused)
            on_action_execute: Optional callback when actions execute

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If table roll fails
        """
        # Get tables config
        tables_config = step.step_config.get("tables", [])
        if not tables_config:
            raise FlowExecutionError(
                f"table_roll step '{step.id}' missing 'tables' field"
            )

        logger.debug(f"Rolling on {len(tables_config)} tables")

        # Process each table
        for table_config in tables_config:
            table_id = table_config.get("table")
            if not table_id:
                raise FlowExecutionError(
                    f"table_roll step '{step.id}' has table config "
                    "without 'table' field"
                )

            # Look up table in system
            if table_id not in self.system.tables:
                raise FlowExecutionError(f"Table '{table_id}' not found in system")

            table_def = self.system.tables[table_id]

            # Roll dice for the table
            if not table_def.roll:
                raise FlowExecutionError(
                    f"Table '{table_id}' has no roll expression defined"
                )

            dice_result = self.dice_service.roll_dice(table_def.roll)
            roll_total = dice_result.total

            # Find matching entry
            entry_value = None
            for entry in table_def.entries:
                entry_range = entry.get("range", "")
                entry_val = entry.get("value")

                # Parse range (e.g., "1-5", "6", "7-10")
                if "-" in str(entry_range):
                    low, high = map(int, str(entry_range).split("-"))
                    if low <= roll_total <= high:
                        entry_value = entry_val
                        break
                elif str(roll_total) == str(entry_range):
                    entry_value = entry_val
                    break

            if entry_value is None:
                logger.warning(
                    f"No matching entry for roll {roll_total} in table '{table_id}'"
                )
                entry_value = f"<no match for {roll_total}>"

            # Store result in step namespace
            result_dict = {
                "entry": entry_value,
                "roll_result": {
                    "total": dice_result.total,
                    "detail": dice_result.description,
                },
            }
            context = context.set_variable(f"{step_namespace}.result", result_dict)

            # Create top-level alias for table actions to use
            context = context.set_variable("result", result_dict)

            # Execute table-specific actions if any
            table_actions = table_config.get("actions", [])
            for action in table_actions:
                context = self.action_executor(action, context, on_action_execute)

        return context
