"""Display value action handler."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ..decorators import handle_execution_error

logger = get_logger(__name__)


class DisplayValueActionHandler:
    """Handler for display_value actions."""

    @handle_execution_error("Display value failed")
    def execute(
        self,
        action_data: str,
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        """Execute display_value action.

        Displays a value from the context to the user in the execution output.
        Shows both the path and the value for clarity.

        Args:
            action_data: Path to value to display
            context: Current execution context
            on_action_execute: Callback for UI display (called with message)

        Returns:
            None (no context update)
        """
        if not context.has_variable(action_data):
            warning_msg = f"Cannot display: path not found: {action_data}"
            logger.warning(warning_msg)
            if on_action_execute:
                on_action_execute("display_value", {"message": warning_msg})
            return

        value = context.get_variable(action_data)
        display_msg = f"{action_data}: {value}"
        logger.info(f"Display value - {display_msg}")

        # Call callback with display message for UI
        if on_action_execute:
            on_action_execute("display_value", {"message": display_msg})
