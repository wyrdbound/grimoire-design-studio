"""Flow execution service for GRIMOIRE flows.

This module provides the FlowExecutionService class which manages the execution
of GRIMOIRE flows, including context management, step execution, and action handling.

This service requires grimoire-context to be installed and will fail explicitly
if it is not available, following the principle of explicit errors over fallbacks.

Flow execution is orchestrated by Prefect for enhanced monitoring, parallel execution,
and error handling capabilities.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Callable

from grimoire_context import (
    GrimoireContext,
)  # Explicit import - fail fast if not available
from grimoire_logging import get_logger
from grimoire_model import Jinja2TemplateResolver
from prefect import flow, task

from ..models.grimoire_definitions import CompleteSystem, FlowDefinition, FlowStep
from .action_handlers.display_message import DisplayMessageActionHandler
from .action_handlers.display_value import DisplayValueActionHandler
from .action_handlers.log_event import LogEventActionHandler
from .action_handlers.log_message import LogMessageActionHandler
from .action_handlers.set_value import SetValueActionHandler
from .action_handlers.swap_values import SwapValuesActionHandler
from .action_handlers.validate_value import ValidateValueActionHandler
from .dice_service import DiceService
from .exceptions import FlowExecutionError
from .llm_service import LLMConfig, LLMService
from .name_service import NameService
from .object_service import ObjectInstantiationService
from .step_executors.completion import CompletionStepExecutor
from .step_executors.conditional_branch import ConditionalBranchStepExecutor
from .step_executors.dice_roll import DiceRollStepExecutor
from .step_executors.dice_sequence import DiceSequenceStepExecutor
from .step_executors.flow_call import FlowCallStepExecutor
from .step_executors.llm_generation import LLMGenerationStepExecutor
from .step_executors.name_generation import NameGenerationStepExecutor
from .step_executors.player_choice import PlayerChoiceStepExecutor
from .step_executors.player_input import PlayerInputStepExecutor
from .step_executors.table_roll import TableRollStepExecutor

logger = get_logger(__name__)

# Configure Prefect for optimal GRIMOIRE performance
# Use ephemeral mode - no server needed, minimal overhead
os.environ.setdefault("PREFECT_API_URL", "")  # Ephemeral mode
os.environ.setdefault("PREFECT_LOGGING_LEVEL", "WARNING")  # Reduce noise
os.environ.setdefault("PREFECT_API_ENABLE_HTTP2", "false")  # Better compatibility


class _TemplateResolverAdapter:
    """Adapter to match TemplateResolver protocol parameter naming."""

    def __init__(self, resolver: Jinja2TemplateResolver) -> None:
        self._resolver = resolver

    def resolve_template(self, template_str: str, context_dict: dict[str, Any]) -> Any:
        """Resolve template with protocol-compliant parameter name."""
        return self._resolver.resolve_template(template_str, context_dict)


class FlowExecutionService:
    """Service for executing GRIMOIRE flows with context management.

    This service manages flow execution by:
    - Creating and managing execution contexts using grimoire-context
    - Executing flow steps in sequence
    - Handling actions (set_value, log_message, etc.)
    - Integrating with ObjectInstantiationService for object validation

    Attributes:
        system: The complete GRIMOIRE system with all definitions
        object_service: Service for instantiating and validating game objects
        current_context: Current execution context (or None if no flow running)
        current_flow: Current flow definition (or None if no flow running)
    """

    def __init__(
        self,
        system: CompleteSystem,
        object_service: ObjectInstantiationService,
        dice_service: DiceService | None = None,
        llm_service: LLMService | None = None,
        name_service: NameService | None = None,
    ) -> None:
        """Initialize the flow execution service.

        Args:
            system: Complete GRIMOIRE system with flow definitions
            object_service: Service for object instantiation and validation
            dice_service: Service for dice rolling (creates default if None)
            llm_service: Service for LLM generation (creates default if None)
            name_service: Service for name generation (creates default if None)

        Raises:
            RuntimeError: If initialization fails
        """
        self.system = system
        self.object_service = object_service
        self.template_resolver = _TemplateResolverAdapter(Jinja2TemplateResolver())
        self.current_context: GrimoireContext | None = None
        self.current_flow: FlowDefinition | None = None

        # Initialize services (create defaults if not provided)
        self.dice_service = dice_service or DiceService()
        self.llm_service = llm_service or LLMService(LLMConfig(provider="mock"))
        self.name_service = name_service or NameService()

        # Initialize step executors
        self._step_executors: dict[str, Any] = {
            "completion": CompletionStepExecutor(),
            "dice_roll": DiceRollStepExecutor(self.dice_service),
            "dice_sequence": DiceSequenceStepExecutor(
                self.dice_service, self._execute_action
            ),
            "table_roll": TableRollStepExecutor(
                self.system, self.dice_service, self._execute_action
            ),
            "player_input": PlayerInputStepExecutor(),
            "player_choice": PlayerChoiceStepExecutor(
                self.template_resolver, self._execute_action
            ),
            "llm_generation": LLMGenerationStepExecutor(
                self.system, self.llm_service, self._resolve_templates_in_dict
            ),
            "name_generation": NameGenerationStepExecutor(),
            "flow_call": FlowCallStepExecutor(
                self.system, self, self.template_resolver
            ),
            "conditional_branch": ConditionalBranchStepExecutor(
                lambda template_str, context: context.resolve_template(template_str),
                self._execute_action,
            ),
        }

        # Initialize action handlers
        self._action_handlers: dict[str, Any] = {
            "set_value": SetValueActionHandler(
                self._get_expected_type_for_path, self._coerce_value_to_type
            ),
            "log_message": LogMessageActionHandler(),
            "display_message": DisplayMessageActionHandler(),
            "log_event": LogEventActionHandler(self._resolve_templates_in_dict),
            "display_value": DisplayValueActionHandler(),
            "validate_value": ValidateValueActionHandler(self.object_service),
            "swap_values": SwapValuesActionHandler(),
        }

        logger.info(f"Initialized FlowExecutionService for system: {system.system.id}")

    @flow(
        name="execute_grimoire_flow",
        flow_run_name="{flow_id}",
        persist_result=False,  # No result persistence in ephemeral mode
        validate_parameters=False,  # We do our own validation
        log_prints=False,  # Use grimoire-logging instead
        timeout_seconds=300,  # 5 minute timeout for long flows
    )
    def execute_flow(
        self,
        flow_id: str,
        inputs: dict[str, Any] | None = None,
        on_step_complete: Callable[[str, dict[str, Any]], None] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a flow with the given inputs.

        Args:
            flow_id: ID of the flow to execute
            inputs: Dictionary of input values (or None for no inputs)
            on_step_complete: Optional callback when step completes
            on_action_execute: Optional callback when action executes
            on_user_input: Optional callback for user input/choice steps

        Returns:
            Dictionary containing flow outputs

        Raises:
            ValueError: If flow not found or inputs invalid
            FlowExecutionError: If execution fails
        """
        if flow_id not in self.system.flows:
            raise ValueError(f"Flow not found: {flow_id}")

        flow_def = self.system.flows[flow_id]
        self.current_flow = flow_def
        logger.info(f"Starting flow execution: {flow_id}")

        try:
            # Initialize context with inputs, outputs, and variables
            context = self._initialize_context(flow_def, inputs or {})
            self.current_context = context

            # Execute flow steps
            context = self._execute_steps(
                flow_def, context, on_step_complete, on_action_execute, on_user_input
            )

            # Extract outputs
            outputs = self._extract_outputs(flow_def, context)

            logger.info(f"Flow execution completed: {flow_id}")
            return outputs

        except Exception as e:
            error_msg = f"Flow execution failed for {flow_id}: {e}"
            logger.error(error_msg)
            raise FlowExecutionError(error_msg) from e
        finally:
            self.current_context = None
            self.current_flow = None

    def _initialize_context(
        self, flow_def: FlowDefinition, inputs: dict[str, Any]
    ) -> GrimoireContext:
        """Initialize execution context with inputs, outputs, and variables.

        Args:
            flow_def: Flow definition
            inputs: Input values provided by caller

        Returns:
            Initialized GrimoireContext

        Raises:
            ValueError: If required inputs are missing
        """
        logger.debug(f"Initializing context for flow: {flow_def.id}")

        # Validate and instantiate inputs
        instantiated_inputs = self.object_service.instantiate_flow_input(
            flow_def, inputs
        )

        # Initialize outputs structure
        outputs = {output.id: None for output in flow_def.outputs}

        # Initialize variables structure
        variables = {var.id: None for var in flow_def.variables}

        # Create context with three top-level namespaces
        context_data = {
            "inputs": instantiated_inputs,
            "outputs": outputs,
            "variables": variables,
        }

        context = GrimoireContext(context_data)
        context = context.set_template_resolver(self.template_resolver)
        logger.debug("Context initialized successfully")
        return context

    def _execute_steps(
        self,
        flow_def: FlowDefinition,
        context: GrimoireContext,
        on_step_complete: Callable[[str, dict[str, Any]], None] | None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None,
    ) -> GrimoireContext:
        """Execute flow steps in sequence.

        Args:
            flow_def: Flow definition
            context: Current execution context
            on_step_complete: Optional callback when step completes
            on_action_execute: Optional callback when action executes
            on_user_input: Optional callback for user input/choice steps

        Returns:
            Updated context after all steps execute

        Raises:
            FlowExecutionError: If step execution fails
        """
        logger.debug("Beginning step execution")

        # Track which step to execute (by index or id)
        current_step_index = 0

        while current_step_index < len(flow_def.steps):
            step = flow_def.steps[current_step_index]
            logger.debug(f"Executing step: {step.id} ({step.type})")

            # Execute the step (Prefect task executes synchronously within flow)
            context, step_result = self._execute_step(
                step, context, on_action_execute, on_user_input
            )

            # Notify callback if provided
            if on_step_complete:
                # mypy: Prefect decorators confuse type inference
                on_step_complete(step.id, step_result)  # type: ignore[arg-type]

            # Determine next step
            # Check for next_step_override from player_choice first
            if "next_step_override" in step_result:
                # mypy: Prefect decorators confuse type inference
                next_step_id = step_result["next_step_override"]  # type: ignore[call-overload]
                next_index = next(
                    (i for i, s in enumerate(flow_def.steps) if s.id == next_step_id),
                    None,
                )
                if next_index is None:
                    raise FlowExecutionError(
                        f"Choice in step {step.id} references unknown next_step: {next_step_id}"
                    )
                current_step_index = next_index
            elif step.next_step:
                # Find the step with the specified ID
                next_index = next(
                    (i for i, s in enumerate(flow_def.steps) if s.id == step.next_step),
                    None,
                )
                if next_index is None:
                    raise FlowExecutionError(
                        f"Step {step.id} references unknown next_step: {step.next_step}"
                    )
                current_step_index = next_index
            else:
                # Move to next step in sequence
                current_step_index += 1

        logger.debug("All steps completed")
        return context

    @task(
        name="execute_step",
        # task_run_name="{step.type}__{step.id}",
        task_run_name="{step.name} ({step.type})",
        persist_result=False,  # No persistence in ephemeral mode
        retries=0,  # Default: no retries (configure per step type if needed)
        log_prints=False,  # Use grimoire-logging
    )
    def _execute_step(
        self,
        step: FlowStep,
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None,
    ) -> tuple[GrimoireContext, dict[str, Any]]:
        """Execute a single flow step with proper context management.

        Creates a step-specific context namespace (step_<uuid>) to store
        temporary data like 'result', 'item', and 'config'. This prevents
        collisions in concurrent step execution. The namespace is cleaned
        up after the step completes.

        Args:
            step: Step to execute
            context: Current execution context
            on_action_execute: Optional callback when action executes
            on_user_input: Optional callback for user input/choice steps

        Returns:
            Tuple of (updated context, step result dict with optional next_step_override)

        Raises:
            FlowExecutionError: If step execution fails
        """
        # Create unique step namespace to prevent concurrent step collisions
        step_namespace = f"step_{uuid.uuid4().hex}"
        logger.debug(
            f"Executing step: {step.id} ({step.type}) in namespace {step_namespace}"
        )

        try:
            # Initialize step namespace with config
            context = context.set_variable(f"{step_namespace}.config", step.step_config)

            # Execute pre-actions if any
            if step.pre_actions:
                logger.debug(f"Executing {len(step.pre_actions)} pre-actions")
                for action in step.pre_actions:
                    context = self._execute_action(action, context, on_action_execute)

            # Execute step based on type
            context = self._execute_step_logic(
                step, context, step_namespace, on_user_input, on_action_execute
            )

            # Create convenient top-level aliases for step data
            # This allows templates to use {{ result }} instead of {{ step_<uuid>.result }}
            if context.has_variable(f"{step_namespace}.result"):
                context = context.set_variable(
                    "result", context.get_variable(f"{step_namespace}.result")
                )
            if context.has_variable(f"{step_namespace}.item"):
                context = context.set_variable(
                    "item", context.get_variable(f"{step_namespace}.item")
                )

            # Execute actions if any
            if step.actions:
                # Check if parallel execution is requested
                if step.parallel:
                    # For parallel execution, resolve all templates upfront
                    # (parallel actions can't depend on each other anyway)
                    resolved_actions = []
                    for action in step.actions:
                        resolved_actions.append(
                            self._resolve_templates_in_dict(action, context)
                        )
                    logger.debug(
                        f"Executing {len(resolved_actions)} actions in parallel"
                    )
                    context = self._execute_actions_parallel(
                        resolved_actions, context, on_action_execute
                    )
                else:
                    # For sequential execution, resolve templates just before each action
                    # This allows actions to reference results from previous actions
                    logger.debug(f"Executing {len(step.actions)} actions")
                    for action in step.actions:
                        # Resolve templates with current context (updated by previous actions)
                        resolved_action = self._resolve_templates_in_dict(
                            action, context
                        )
                        context = self._execute_action(
                            resolved_action, context, on_action_execute
                        )  # Build step result for callback (before cleanup)
            step_result = self._build_step_result(step, context, step_namespace)

            # Check for next_step_override from player_choice
            if context.has_variable(f"{step_namespace}.next_step_override"):
                step_result["next_step_override"] = context.get_variable(
                    f"{step_namespace}.next_step_override"
                )

            return context, step_result

        finally:
            # Clean up step namespace AND top-level aliases
            context_dict = context.to_dict()

            # Remove step namespace
            if step_namespace in context_dict:
                del context_dict[step_namespace]

            # Remove top-level aliases
            if "result" in context_dict:
                del context_dict["result"]
            if "item" in context_dict:
                del context_dict["item"]

            context = GrimoireContext(context_dict)
            context = context.set_template_resolver(self.template_resolver)

    def _execute_step_logic(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
    ) -> GrimoireContext:
        """Execute the step-specific logic based on step type.

        Args:
            step: Step to execute
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Optional callback for user input/choice steps
            on_action_execute: Optional callback when actions execute

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If step execution fails
        """
        # Create a copy of the step with templated step_config
        templated_step = self._resolve_step_templates(step, context)

        # Dispatch to appropriate step executor
        executor = self._step_executors.get(step.type)
        if executor:
            return executor.execute(
                templated_step,
                context,
                step_namespace,
                on_user_input,
                on_action_execute,
            )
        else:
            logger.warning(f"Step type '{step.type}' not yet implemented")
            return context

    def _build_step_result(
        self, step: FlowStep, context: GrimoireContext, step_namespace: str
    ) -> dict[str, Any]:
        """Build step result dict for callback.

        Args:
            step: Step that was executed
            context: Current execution context
            step_namespace: Namespace where step data is stored

        Returns:
            Dictionary with step result information
        """
        result: dict[str, Any] = {"step_id": step.id, "step_type": step.type}

        # Try to get result from step namespace
        if context.has_variable(f"{step_namespace}.result"):
            result["result"] = context.get_variable(f"{step_namespace}.result")

        return result

    def _execute_action(
        self,
        action: dict[str, Any],
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
    ) -> GrimoireContext:
        """Execute a single action.

        Args:
            action: Action definition dictionary
            context: Current execution context
            on_action_execute: Optional callback when action executes

        Returns:
            Updated context after action execution

        Raises:
            FlowExecutionError: If action execution fails
        """
        # Determine action type (first key in the dict)
        if not action:
            return context

        action_type = next(iter(action.keys()))
        action_data = action[action_type]

        logger.debug(f"Executing action: {action_type}")

        try:
            # Dispatch to appropriate action handler
            handler = self._action_handlers.get(action_type)
            if handler:
                result = handler.execute(action_data, context, on_action_execute)
                # Handlers return context if modified, None otherwise
                if result is not None:
                    context = result

                # Notify callback if provided (unless already called by handler)
                if on_action_execute and action_type not in (
                    "display_message",
                    "display_value",
                ):
                    on_action_execute(action_type, action_data)
            else:
                logger.warning(f"Unknown action type: {action_type}")

            return context

        except Exception as e:
            error_msg = f"Action execution failed ({action_type}): {e}"
            logger.error(error_msg)
            raise FlowExecutionError(error_msg) from e

    def _execute_actions_parallel(
        self,
        actions: list[dict[str, Any]],
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
    ) -> GrimoireContext:
        """Execute multiple actions in parallel using GrimoireContext.execute_parallel().

        Uses grimoire-context v0.3.0's execute_parallel() with fixed merge semantics
        where None values are treated as "no change" rather than explicit assignments.
        This allows multiple parallel operations to modify nested paths within the same
        parent dictionary without conflicts.

        Args:
            actions: List of action definitions to execute in parallel
            context: Current execution context
            on_action_execute: Optional callback when action executes

        Returns:
            Updated context after all actions complete

        Raises:
            FlowExecutionError: If any action execution fails
        """

        # Create callable operations for each action
        def create_action_operation(
            action: dict[str, Any],
        ) -> Callable[[GrimoireContext], GrimoireContext]:
            """Create a callable operation for an action."""

            def operation(ctx: GrimoireContext) -> GrimoireContext:
                if not action:
                    return ctx

                action_type = next(iter(action.keys()))
                action_data = action[action_type]

                handler = self._action_handlers.get(action_type)
                if handler:
                    result = handler.execute(action_data, ctx, None)
                    return result if result is not None else ctx
                else:
                    logger.warning(f"Unknown action type: {action_type}")
                    return ctx

            return operation

        # Create operations for all actions
        operations = [create_action_operation(action) for action in actions]

        # Execute all operations in parallel using grimoire-context
        context = context.execute_parallel(operations)

        # Notify callbacks for all actions (callbacks are not parallel-safe)
        if on_action_execute:
            for action in actions:
                if action:
                    action_type = next(iter(action.keys()))
                    action_data = action[action_type]
                    if action_type not in ("display_message", "display_value"):
                        on_action_execute(action_type, action_data)

        return context

    def _resolve_templates_in_dict(
        self, data: dict[str, Any], context: GrimoireContext
    ) -> dict[str, Any]:
        """Recursively resolve templates in dictionary values.

        Args:
            data: Dictionary potentially containing template strings
            context: Current execution context

        Returns:
            Dictionary with templates resolved
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = context.resolve_template(value)
            elif isinstance(value, dict):
                result[key] = self._resolve_templates_in_dict(value, context)
            elif isinstance(value, list):
                result[key] = [
                    (
                        context.resolve_template(item)
                        if isinstance(item, str)
                        else (
                            self._resolve_templates_in_dict(item, context)
                            if isinstance(item, dict)
                            else item
                        )
                    )
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _resolve_step_templates(
        self, step: FlowStep, context: GrimoireContext
    ) -> FlowStep:
        """Create a copy of the step with templates resolved in step_config only.

        Actions are resolved separately after step execution when results are available.

        Args:
            step: Original step definition
            context: Current execution context

        Returns:
            New FlowStep with step_config templates resolved
        """
        # Create a copy of the step to avoid modifying the original
        from copy import deepcopy

        step_copy = deepcopy(step)

        # NOTE: step_config is NOT resolved here because it may contain actions
        # that reference step results ({{ result }}), which are not available yet.
        # Each step executor is responsible for resolving its own step_config templates
        # after generating results if needed.

        # Resolve templates in pre_actions
        if step_copy.pre_actions:
            resolved_pre_actions = []
            for action in step_copy.pre_actions:
                resolved_pre_actions.append(
                    self._resolve_templates_in_dict(action, context)
                )
            step_copy.pre_actions = resolved_pre_actions

        # Resolve template in prompt if present
        if step_copy.prompt:
            step_copy.prompt = context.resolve_template(step_copy.prompt)

        # Resolve template in condition if present
        if step_copy.condition:
            step_copy.condition = context.resolve_template(step_copy.condition)

        return step_copy

    def _get_expected_type_for_path(self, path: str) -> str | None:
        """Get the expected type for a flow path, including nested attributes.

        Resolves types through the full path hierarchy, including:
        - Top-level flow definitions (inputs, outputs, variables)
        - Nested model attributes (e.g., variables.character.stats.hp)

        Args:
            path: Path like "variables.counter" or "variables.hero.stats.hp"

        Returns:
            Expected type string or None if path cannot be resolved

        Examples:
            "variables.counter" -> "int"
            "outputs.result" -> "str"
            "variables.character.hp" -> "int"
        """
        if not self.current_flow:
            return None

        parts = path.split(".")
        if len(parts) < 2:
            return None

        namespace = parts[0]
        field_id = parts[1]

        # Get the top-level type from flow definition
        top_level_type: str | None = None

        if namespace == "variables":
            for var in self.current_flow.variables:
                if var.id == field_id:
                    top_level_type = var.type
                    break
        elif namespace == "outputs":
            for output in self.current_flow.outputs:
                if output.id == field_id:
                    top_level_type = output.type
                    break
        elif namespace == "inputs":
            for input_def in self.current_flow.inputs:
                if input_def.id == field_id:
                    top_level_type = input_def.type
                    break

        if not top_level_type:
            return None

        # If it's a simple 2-part path, return the top-level type
        if len(parts) == 2:
            return top_level_type

        # For nested paths, resolve through model definitions
        return self._resolve_nested_type(top_level_type, parts[2:])

    def _resolve_nested_type(
        self, model_type: str, remaining_path: list[str]
    ) -> str | None:
        """Resolve type through nested model attributes.

        Args:
            model_type: The model type to start from (e.g., "character")
            remaining_path: Remaining path parts (e.g., ["stats", "hp"])

        Returns:
            The final type, or None if path cannot be resolved
        """
        # Check if this is a model in our system
        if model_type not in self.system.models:
            # Not a model, can't resolve further
            return None

        current_model = self.system.models[model_type]
        current_field = remaining_path[0]

        # Look up the attribute in the model
        if current_field not in current_model.attributes:
            return None

        attribute = current_model.attributes[current_field]
        attribute_type: str = attribute.type

        # If this is the last part of the path, return the type
        if len(remaining_path) == 1:
            return attribute_type

        # Otherwise, recurse into the next level
        return self._resolve_nested_type(attribute_type, remaining_path[1:])

    def _coerce_value_to_type(
        self, value: Any, expected_type: str | None, path: str
    ) -> Any:
        """Coerce a value to the expected type if needed.

        Delegates to ObjectInstantiationService for primitive type validation
        and model instantiation to ensure consistent type handling across the
        codebase. For model types, creates a GrimoireModel instance which
        applies defaults/derived attributes, then returns the fully-resolved
        dict representation.

        Args:
            value: Value to coerce
            expected_type: Expected type string or None
            path: Path for error context

        Returns:
            Coerced value (primitives or fully-resolved dict for models)

        Raises:
            ValueError: If coercion fails
        """
        if expected_type is None:
            return value

        # Check if it's a primitive type
        primitive_types = {"str", "int", "float", "bool"}
        if expected_type in primitive_types:
            # Delegate to ObjectInstantiationService for consistent type handling
            return self.object_service.validate_primitive_type(
                value, expected_type, f"path '{path}'"
            )

        # For model types, try to instantiate and return fully-resolved dict
        # If instantiation fails (invalid data), return as-is to allow
        # deferred validation via validate_value action
        if expected_type in self.system.models and isinstance(value, dict):
            try:
                # Create GrimoireModel instance (applies defaults/derived attrs)
                model_obj = self.object_service.create_object(value)
                # Convert to fully-resolved dict representation
                return dict(model_obj)
            except Exception:
                # Data is invalid - return as-is and let validate_value catch it
                logger.debug(
                    f"Could not instantiate {expected_type} at {path}, "
                    "storing raw data for deferred validation"
                )
                return value

        # For other types, return as-is
        return value

    def _extract_outputs(
        self, flow_def: FlowDefinition, context: GrimoireContext
    ) -> dict[str, Any]:
        """Extract outputs from execution context.

        Args:
            flow_def: Flow definition
            context: Execution context after flow completion

        Returns:
            Dictionary of flow outputs

        Raises:
            FlowExecutionError: If output extraction fails
        """
        logger.debug("Extracting flow outputs")

        try:
            outputs_data = context.get_variable("outputs", {})
            if not isinstance(outputs_data, dict):
                raise FlowExecutionError(
                    f"Outputs must be a dictionary, got {type(outputs_data)}"
                )

            # Instantiate outputs if needed
            instantiated_outputs = self.object_service.instantiate_flow_output(
                flow_def, outputs_data
            )

            logger.debug(f"Extracted {len(instantiated_outputs)} outputs")
            return instantiated_outputs

        except Exception as e:
            error_msg = f"Failed to extract outputs: {e}"
            logger.error(error_msg)
            raise FlowExecutionError(error_msg) from e
