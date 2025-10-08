"""Set value action handler."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ..decorators import handle_execution_error

logger = get_logger(__name__)


class SetValueActionHandler:
    """Handler for set_value actions."""

    def __init__(
        self,
        type_getter: Callable[[str], str | None],
        value_coercer: Callable[[Any, str | None, str], Any],
    ) -> None:
        """Initialize the set value action handler.

        Args:
            type_getter: Function to get expected type for a path
            value_coercer: Function to coerce values to expected types
        """
        self.type_getter = type_getter
        self.value_coercer = value_coercer

    @handle_execution_error("Set value failed")
    def execute(
        self,
        action_data: dict[str, Any],
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute set_value action.

        Args:
            action_data: Action data containing 'path' and 'value'
            context: Current execution context
            on_action_execute: Optional callback (unused, handled by caller)

        Returns:
            Updated context with value set

        Raises:
            ValueError: If path or value is invalid
        """
        path = action_data.get("path")
        value = action_data.get("value")

        if not path:
            raise ValueError("set_value action requires 'path' field")

        # Resolve template if value is a string
        if isinstance(value, str):
            value = context.resolve_template(value)

        # Resolve template in path
        resolved_path = context.resolve_template(path)

        # Coerce to expected type based on path
        expected_type = self.type_getter(str(resolved_path))
        value = self.value_coercer(value, expected_type, str(resolved_path))

        logger.debug(f"Setting value at resolved path: {resolved_path}")
        return context.set_variable(str(resolved_path), value)
