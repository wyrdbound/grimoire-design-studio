"""Display message action handler."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ..decorators import handle_execution_error

logger = get_logger(__name__)


class DisplayMessageActionHandler:
    """Handler for display_message actions."""

    @handle_execution_error("Display message failed")
    def execute(
        self,
        action_data: dict[str, Any] | str,
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        """Execute display_message action.

        Displays a message to the user in the execution output. This is similar
        to log_message but intended for user-facing output rather than debug
        logs.

        Args:
            action_data: Action data (dict with 'message' or string)
            context: Current execution context for template resolution
            on_action_execute: Callback for UI display (called with message)

        Returns:
            None (no context update)
        """
        # Handle both dict and string formats
        if isinstance(action_data, str):
            message = action_data
        else:
            message = action_data.get("message", "")

        # Resolve template if message is a string
        if isinstance(message, str):
            resolved = context.resolve_template(message)
            message = str(resolved) if resolved is not None else message

        # Log at INFO level - picked up by the output console
        logger.info(f"Display: {message}")

        # Call callback with resolved message for UI display
        if on_action_execute:
            on_action_execute("display_message", {"message": str(message)})
