"""Decorators for flow execution components.

This module provides decorators to simplify common patterns in step executors
and action handlers, particularly error handling.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from .exceptions import FlowExecutionError

F = TypeVar("F", bound=Callable[..., Any])


def handle_execution_error(error_context: str) -> Callable[[F], F]:
    """Decorator to wrap exceptions in FlowExecutionError.

    This decorator handles the common pattern of catching exceptions during
    step/action execution and wrapping them in FlowExecutionError with
    contextual information.

    Args:
        error_context: Description of what failed (e.g., "Dice roll",
            "Name generation", "Set value action")

    Returns:
        Decorator function

    Example:
        @handle_execution_error("Dice roll")
        def execute(self, step, context, step_namespace, ...):
            # Implementation that may raise exceptions
            result = self.dice_service.roll_dice(expression)
            return context.set_variable(f"{step_namespace}.result", result)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except FlowExecutionError:
                # Already a FlowExecutionError, re-raise as-is
                raise
            except Exception as e:
                # Wrap other exceptions with context
                # Try to get step_id from args if available (for step executors)
                step_id = None
                if len(args) > 1 and hasattr(args[1], "id"):
                    step_id = args[1].id

                if step_id:
                    error_msg = f"{error_context} failed in step '{step_id}': {e}"
                else:
                    error_msg = f"{error_context} failed: {e}"

                raise FlowExecutionError(error_msg) from e

        return wrapper  # type: ignore

    return decorator
