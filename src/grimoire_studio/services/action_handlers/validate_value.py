"""Validate value action handler."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ..decorators import handle_execution_error
from ..exceptions import FlowExecutionError
from ..object_service import ObjectInstantiationService

logger = get_logger(__name__)


class ValidateValueActionHandler:
    """Handler for validate_value actions."""

    def __init__(self, object_service: ObjectInstantiationService) -> None:
        """Initialize the validate value action handler.

        Args:
            object_service: Service for object instantiation and validation
        """
        self.object_service = object_service

    @handle_execution_error("Validation failed")
    def execute(
        self,
        action_data: str,
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        """Execute validate_value action.

        Creates a GrimoireModel instance from the data and validates it using
        the model's built-in validate() method, which properly applies defaults
        before validation.

        Args:
            action_data: Path to value to validate
            context: Current execution context
            on_action_execute: Optional callback (unused, handled by caller)

        Returns:
            None (no context update)

        Raises:
            FlowExecutionError: If validation fails
        """
        if not context.has_variable(action_data):
            raise FlowExecutionError(f"Cannot validate: path not found: {action_data}")

        value = context.get_variable(action_data)

        # If it's a dict with a 'model' field, create and validate it
        if isinstance(value, dict) and "model" in value:
            # Use create_object which creates a GrimoireModel instance
            # The GrimoireModel's __init__ calls validate() internally,
            # which applies defaults before validation
            self.object_service.create_object(value)
            logger.debug(f"Validation passed for {action_data}")
        else:
            logger.debug(f"No validation needed for {action_data}")
