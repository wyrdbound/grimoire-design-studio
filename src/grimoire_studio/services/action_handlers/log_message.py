"""Log message action handler."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ..decorators import handle_execution_error

logger = get_logger(__name__)


class LogMessageActionHandler:
    """Handler for log_message actions."""

    @handle_execution_error("Log message failed")
    def execute(
        self,
        action_data: dict[str, Any] | str,
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        """Execute log_message action.

        Args:
            action_data: Action data (dict with 'message' or string)
            context: Current execution context for template resolution
            on_action_execute: Optional callback (unused, handled by caller)

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
            message = context.resolve_template(message)

        logger.info(f"Flow log: {message}")
