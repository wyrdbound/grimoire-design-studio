"""Action handlers for GRIMOIRE flow actions.

This package provides the Strategy Pattern implementation for executing
different types of flow actions. Each action type has its own handler class
that implements the ActionHandler protocol.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from grimoire_context import GrimoireContext


class ActionHandler(Protocol):
    """Protocol for action handlers.

    All action handlers must implement the execute method to process a specific
    action type and return the updated context (or None if no context update).
    """

    def execute(
        self,
        action_data: Any,
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext | None:
        """Execute an action.

        Args:
            action_data: Action-specific data
            context: Current execution context
            on_action_execute: Optional callback when action executes

        Returns:
            Updated context if action modifies context, None otherwise

        Raises:
            FlowExecutionError: If action execution fails
        """
        ...


__all__ = ["ActionHandler"]
