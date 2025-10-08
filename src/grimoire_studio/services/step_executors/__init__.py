"""Step executors for GRIMOIRE flow steps.

This package provides the Strategy Pattern implementation for executing
different types of flow steps. Each step type has its own executor class
that implements the StepExecutor protocol.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from grimoire_context import GrimoireContext

from ...models.grimoire_definitions import FlowStep


class StepExecutor(Protocol):
    """Protocol for step executors.

    All step executors must implement the execute method to process a specific
    step type and return the updated context.
    """

    def execute(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute a flow step.

        Args:
            step: Step to execute
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Optional callback for user input/choice steps
            on_action_execute: Optional callback when actions execute

        Returns:
            Updated context after step execution

        Raises:
            FlowExecutionError: If step execution fails
        """
        ...


__all__ = ["StepExecutor"]
