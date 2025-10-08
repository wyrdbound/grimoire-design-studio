"""LLM generation step executor."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger

from ...models.grimoire_definitions import CompleteSystem, FlowStep
from ..decorators import handle_execution_error
from ..exceptions import FlowExecutionError
from ..llm_service import LLMConfig, LLMService

logger = get_logger(__name__)


class LLMGenerationStepExecutor:
    """Executor for llm_generation steps."""

    def __init__(
        self,
        system: CompleteSystem,
        llm_service: LLMService,
        template_dict_resolver: Callable[
            [dict[str, Any], GrimoireContext], dict[str, Any]
        ],
    ) -> None:
        """Initialize the LLM generation step executor.

        Args:
            system: Complete GRIMOIRE system with prompt definitions
            llm_service: Service for LLM generation
            template_dict_resolver: Function to resolve templates in dicts
        """
        self.system = system
        self.llm_service = llm_service
        self.template_dict_resolver = template_dict_resolver

    @handle_execution_error("LLM generation")
    def execute(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute an llm_generation step.

        Args:
            step: Step to execute
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Optional callback for user input (unused)
            on_action_execute: Optional callback when actions execute (unused)

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If LLM generation fails
        """
        # Get prompt ID
        prompt_id = step.step_config.get("prompt_id")
        if not prompt_id:
            raise FlowExecutionError(
                f"llm_generation step '{step.id}' missing 'prompt_id' field"
            )

        # Look up prompt in system
        if prompt_id not in self.system.prompts:
            raise FlowExecutionError(f"Prompt '{prompt_id}' not found in system")

        prompt_def = self.system.prompts[prompt_id]

        logger.debug(f"Executing LLM generation with prompt: {prompt_id}")

        # Get prompt data for substitution
        prompt_data = step.step_config.get("prompt_data", {})

        # Resolve templates in prompt data
        resolved_data = self.template_dict_resolver(prompt_data, context)

        # Substitute prompt template
        prompt_text = prompt_def.prompt_template.format(**resolved_data)

        # Get LLM settings (use step config or prompt default)
        llm_settings = step.step_config.get("llm_settings", prompt_def.llm)

        # Update LLM service config if needed
        if llm_settings:
            config = LLMConfig(
                provider=llm_settings.get("provider", "mock"),
                model=llm_settings.get("model", "mock-model"),
                temperature=llm_settings.get("temperature", 0.7),
                max_tokens=llm_settings.get("max_tokens", 500),
                api_key=llm_settings.get("api_key"),
                base_url=llm_settings.get("base_url"),
            )
            self.llm_service.set_config(config)

        # Execute LLM prompt
        llm_result = self.llm_service.execute_prompt(prompt_text)

        # Store result in step namespace
        context = context.set_variable(f"{step_namespace}.result", llm_result.response)

        logger.info(f"LLM generation completed: {len(llm_result.response)} chars")
        return context
