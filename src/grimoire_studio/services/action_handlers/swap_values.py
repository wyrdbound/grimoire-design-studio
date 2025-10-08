"""Swap values action handler."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ..decorators import handle_execution_error

logger = get_logger(__name__)


class SwapValuesActionHandler:
    """Handler for swap_values actions."""

    @handle_execution_error("Failed to swap values")
    def execute(
        self,
        action_data: dict[str, Any],
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute swap_values action.

        Swaps the values at two specified paths in the context.

        Args:
            action_data: Action data containing 'path1' and 'path2'
            context: Current execution context for value access and updates
            on_action_execute: Optional callback (unused, handled by caller)

        Returns:
            Updated context with swapped values

        Raises:
            FlowExecutionError: If swap operation fails
        """
        path1 = action_data.get("path1")
        path2 = action_data.get("path2")

        if not path1 or not path2:
            raise ValueError("swap_values requires both 'path1' and 'path2' fields")

        # Resolve template paths
        resolved_path1 = context.resolve_template(path1)
        resolved_path2 = context.resolve_template(path2)

        # Get current values
        value1 = context.get_variable(str(resolved_path1))
        value2 = context.get_variable(str(resolved_path2))

        # Swap the values
        context = context.set_variable(str(resolved_path1), value2)
        context = context.set_variable(str(resolved_path2), value1)

        logger.info(f"Swapped values: {resolved_path1} <-> {resolved_path2}")

        return context
