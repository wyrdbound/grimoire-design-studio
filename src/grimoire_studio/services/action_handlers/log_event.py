"""Log event action handler."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ..decorators import handle_execution_error

logger = get_logger(__name__)


class LogEventActionHandler:
    """Handler for log_event actions."""

    def __init__(
        self,
        template_dict_resolver: Callable[
            [dict[str, Any], GrimoireContext], dict[str, Any]
        ],
    ) -> None:
        """Initialize the log event action handler.

        Args:
            template_dict_resolver: Function to resolve templates in dicts
        """
        self.template_dict_resolver = template_dict_resolver

    @handle_execution_error("Log event failed")
    def execute(
        self,
        action_data: dict[str, Any],
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        """Execute log_event action.

        Args:
            action_data: Action data containing 'type' and 'data'
            context: Current execution context
            on_action_execute: Optional callback (unused, handled by caller)

        Returns:
            None (no context update)
        """
        event_type = action_data.get("type", "unknown")
        event_data = action_data.get("data", {})

        # Resolve templates in event_type and event_data
        if isinstance(event_type, str):
            event_type = context.resolve_template(event_type)

        # Recursively resolve templates in event_data
        if isinstance(event_data, dict):
            event_data = self.template_dict_resolver(event_data, context)
        elif isinstance(event_data, str):
            event_data = context.resolve_template(event_data)

        logger.info(f"Flow event: {event_type}", extra={"event_data": event_data})
