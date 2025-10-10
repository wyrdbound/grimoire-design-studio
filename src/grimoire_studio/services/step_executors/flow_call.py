"""Flow call step executor for invoking sub-flows.

This module provides the FlowCallStepExecutor class which handles
the execution of flow_call steps, including proper sub-flow invocation
with Prefect integration and isolated context management.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger
from prefect import task

from ...models.grimoire_definitions import CompleteSystem, FlowDefinition, FlowStep
from ..exceptions import FlowExecutionError

logger = get_logger(__name__)


class FlowCallStepExecutor:
    """Executor for flow_call step type.

    Handles invocation of sub-flows as Prefect sub-flows with proper
    context isolation and result handling.
    """

    def __init__(
        self,
        system: CompleteSystem,
        flow_execution_service: Any,  # Avoid circular import
        template_resolver: Any,
    ) -> None:
        """Initialize the flow call step executor.

        Args:
            system: Complete GRIMOIRE system with flow definitions
            flow_execution_service: Main flow execution service for sub-flow calls
            template_resolver: Template resolver for input processing
        """
        self.system = system
        self.flow_execution_service = flow_execution_service
        self.template_resolver = template_resolver

    @task(
        name="flow_call_step",
        task_run_name="flow_call_{step.id}",
        persist_result=False,
        retries=0,
        log_prints=False,
    )
    def execute(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
    ) -> GrimoireContext:
        """Execute a flow_call step.

        Creates an isolated sub-context, invokes the target flow as a Prefect
        sub-flow, and merges the results back into the main context.

        Args:
            step: Flow call step definition
            context: Current execution context
            step_namespace: Unique namespace for this step
            on_user_input: Callback for user input steps
            on_action_execute: Callback for action execution

        Returns:
            Updated context with sub-flow results

        Raises:
            FlowExecutionError: If sub-flow execution fails
        """
        try:
            # Get the target flow from step_config
            flow_id = step.step_config.get("flow_id")
            if not flow_id:
                raise FlowExecutionError(
                    f"Step {step.id}: 'flow_id' field is required in step_config"
                )

            if flow_id not in self.system.flows:
                raise FlowExecutionError(f"Step {step.id}: Flow '{flow_id}' not found")

            target_flow = self.system.flows[flow_id]

            # Process inputs with template resolution
            inputs = step.step_config.get("inputs", {})
            resolved_inputs = {}

            for input_key, input_value in inputs.items():
                if isinstance(input_value, str):
                    resolved_inputs[input_key] = (
                        self.template_resolver.resolve_template(
                            input_value, context.to_dict()
                        )
                    )
                else:
                    resolved_inputs[input_key] = input_value

            logger.info(f"Calling sub-flow '{flow_id}' with inputs: {resolved_inputs}")

            # Create isolated sub-context with unique flow namespace
            flow_uuid = uuid.uuid4().hex
            sub_context_key = f"flow-{flow_uuid}"

            # Start with the main context but add isolation
            sub_context_dict = context.to_dict().copy()

            # Create sub-context namespace for isolation
            if "sub_flows" not in sub_context_dict:
                sub_context_dict["sub_flows"] = {}
            sub_context_dict["sub_flows"][sub_context_key] = {
                "flow_id": flow_id,
                "inputs": resolved_inputs,
                "variables": {},
                "outputs": {},
            }

            sub_context = GrimoireContext(sub_context_dict)

            # Execute the sub-flow as a Prefect sub-flow
            sub_flow_result = self._execute_sub_flow(
                target_flow,
                resolved_inputs,
                sub_context,
                on_user_input,
                on_action_execute,
            )

            # Store the sub-flow result in the step namespace for actions
            context = context.set_variable(f"{step_namespace}.result", sub_flow_result)

            # Process output mappings if specified
            outputs = step.step_config.get("outputs", {})
            if outputs:
                for output_key, target_path in outputs.items():
                    if output_key in sub_flow_result:
                        output_value = sub_flow_result[output_key]
                        context = context.set_variable(target_path, output_value)
                        logger.info(
                            f"Mapped output '{output_key}' -> '{target_path}': {output_value}"
                        )

            logger.info(f"Sub-flow '{flow_id}' completed successfully")
            return context

        except Exception as e:
            logger.error(f"Flow call step '{step.id}' failed: {e}")
            raise FlowExecutionError(f"Step {step.id}: {e}") from e

    def _execute_sub_flow(
        self,
        flow_def: FlowDefinition,
        inputs: dict[str, Any],
        sub_context: GrimoireContext,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
    ) -> dict[str, Any]:
        """Execute a sub-flow with proper Prefect integration.

        This creates a true Prefect sub-flow for proper monitoring and
        orchestration while maintaining context isolation.

        Args:
            flow_def: Flow definition to execute
            inputs: Resolved input values
            sub_context: Isolated context for sub-flow execution
            on_user_input: User input callback
            on_action_execute: Action execution callback

        Returns:
            Dictionary containing sub-flow outputs
        """
        # Use the main flow execution service to run the sub-flow
        # This will create a proper Prefect sub-flow
        result: dict[str, Any] = self.flow_execution_service.execute_flow(
            flow_def.id,
            inputs,
            None,  # on_step_complete - not needed for sub-flows
            on_action_execute,
            on_user_input,
        )
        return result
