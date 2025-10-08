"""Name generation step executor."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ...models.grimoire_definitions import FlowStep
from ..decorators import handle_execution_error
from ..name_service import NameService

logger = get_logger(__name__)


class NameGenerationStepExecutor:
    """Executor for name_generation steps."""

    @handle_execution_error("Name generation")
    def execute(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute a name_generation step.

        Args:
            step: Step to execute
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Optional callback for user input (unused)
            on_action_execute: Optional callback when actions execute (unused)

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If name generation fails
        """
        logger.debug("Executing name generation")

        # Get settings from step config
        settings = step.step_config.get("settings", {})

        # Extract settings
        max_length = settings.get("max_length", 15)
        corpus = settings.get("corpus", "generic-fantasy")
        segmenter = settings.get("segmenter", "fantasy")
        algorithm = settings.get("algorithm", "bayesian")

        # Create name service with the specified corpus
        # Note: We create a new instance per step to allow different corpora
        name_service = NameService(
            name_list=corpus,
            segmenter=segmenter,
        )

        # Generate name
        generated_name = name_service.generate_name(
            max_length=max_length,
            algorithm=algorithm,
        )

        # Store result in step namespace
        result_dict = {"name": generated_name}
        context = context.set_variable(f"{step_namespace}.result", result_dict)

        logger.info(f"Name generated: {generated_name}")
        return context
