"""Flow execution service for GRIMOIRE flows.

This module provides the FlowExecutionService class which manages the execution
of GRIMOIRE flows, including context management, step execution, and action handling.

This service requires grimoire-context to be installed and will fail explicitly
if it is not available, following the principle of explicit errors over fallbacks.
"""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import (
    GrimoireContext,
)  # Explicit import - fail fast if not available
from grimoire_logging import get_logger
from grimoire_model import Jinja2TemplateResolver

from ..models.grimoire_definitions import CompleteSystem, FlowDefinition, FlowStep
from .object_service import ObjectInstantiationService

logger = get_logger(__name__)


class _TemplateResolverAdapter:
    """Adapter to match TemplateResolver protocol parameter naming."""

    def __init__(self, resolver: Jinja2TemplateResolver) -> None:
        self._resolver = resolver

    def resolve_template(self, template_str: str, context_dict: dict[str, Any]) -> Any:
        """Resolve template with protocol-compliant parameter name."""
        return self._resolver.resolve_template(template_str, context_dict)


class FlowExecutionError(Exception):
    """Exception raised when flow execution fails."""

    pass


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
        self, system: CompleteSystem, object_service: ObjectInstantiationService
    ) -> None:
        """Initialize the flow execution service.

        Args:
            system: Complete GRIMOIRE system with flow definitions
            object_service: Service for object instantiation and validation

        Raises:
            RuntimeError: If initialization fails
        """
        self.system = system
        self.object_service = object_service
        self.template_resolver = _TemplateResolverAdapter(Jinja2TemplateResolver())
        self.current_context: GrimoireContext | None = None
        self.current_flow: FlowDefinition | None = None
        logger.info(f"Initialized FlowExecutionService for system: {system.system.id}")

    def execute_flow(
        self,
        flow_id: str,
        inputs: dict[str, Any] | None = None,
        on_step_complete: Callable[[str, dict[str, Any]], None] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Execute a flow with the given inputs.

        Args:
            flow_id: ID of the flow to execute
            inputs: Dictionary of input values (or None for no inputs)
            on_step_complete: Optional callback when step completes
            on_action_execute: Optional callback when action executes

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
                flow_def, context, on_step_complete, on_action_execute
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
    ) -> GrimoireContext:
        """Execute flow steps in sequence.

        Args:
            flow_def: Flow definition
            context: Current execution context
            on_step_complete: Optional callback when step completes
            on_action_execute: Optional callback when action executes

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

            # Execute the step
            context, step_result = self._execute_step(step, context, on_action_execute)

            # Notify callback if provided
            if on_step_complete:
                on_step_complete(step.id, step_result)

            # Determine next step
            if step.next_step:
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

    def _execute_step(
        self,
        step: FlowStep,
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
    ) -> tuple[GrimoireContext, dict[str, Any]]:
        """Execute a single flow step.

        Args:
            step: Step to execute
            context: Current execution context
            on_action_execute: Optional callback when action executes

        Returns:
            Tuple of (updated context, step result dict)

        Raises:
            FlowExecutionError: If step execution fails
        """
        step_result: dict[str, Any] = {"step_id": step.id, "step_type": step.type}

        # Execute pre-actions if any
        if step.pre_actions:
            logger.debug(f"Executing {len(step.pre_actions)} pre-actions")
            for action in step.pre_actions:
                context = self._execute_action(action, context, on_action_execute)

        # Execute step based on type
        if step.type == "completion":
            logger.debug("Completion step reached")
            step_result["completed"] = True

        elif step.type == "player_input":
            # For now, we'll store a placeholder
            # In a real UI integration, this would trigger a UI prompt
            logger.debug("Player input step (placeholder)")
            step_result["result"] = None

        else:
            # For other step types, we'll implement handlers later
            logger.warning(f"Step type '{step.type}' not yet implemented")
            step_result["result"] = None

        # Execute actions if any
        if step.actions:
            logger.debug(f"Executing {len(step.actions)} actions")
            for action in step.actions:
                context = self._execute_action(action, context, on_action_execute)

        return context, step_result

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
            if action_type == "set_value":
                context = self._action_set_value(action_data, context)

            elif action_type == "log_message":
                self._action_log_message(action_data, context)

            elif action_type == "log_event":
                self._action_log_event(action_data, context)

            elif action_type == "display_value":
                self._action_display_value(action_data, context)

            elif action_type == "validate_value":
                self._action_validate_value(action_data, context)

            else:
                logger.warning(f"Unknown action type: {action_type}")

            # Notify callback if provided
            if on_action_execute:
                on_action_execute(action_type, action_data)

            return context

        except Exception as e:
            error_msg = f"Action execution failed ({action_type}): {e}"
            logger.error(error_msg)
            raise FlowExecutionError(error_msg) from e

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

    def _action_set_value(
        self, action_data: dict[str, Any], context: GrimoireContext
    ) -> GrimoireContext:
        """Execute set_value action.

        Args:
            action_data: Action data containing 'path' and 'value'
            context: Current execution context

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

        # Coerce to expected type based on path
        expected_type = self._get_expected_type_for_path(path)
        value = self._coerce_value_to_type(value, expected_type, path)

        logger.debug(f"Setting value at path: {path}")
        return context.set_variable(path, value)

    def _action_log_message(
        self, action_data: dict[str, Any] | str, context: GrimoireContext
    ) -> None:
        """Execute log_message action.

        Args:
            action_data: Action data (dict with 'message' or string)
            context: Current execution context for template resolution
        """
        # Handle both dict and string formats
        if isinstance(action_data, str):
            message = action_data
        else:
            message = action_data.get("message", "")

        # Resolve template if message is a string
        if isinstance(message, str):
            message = context.resolve_template(message)

        logger.info(f"Flow log: {message}")

    def _action_log_event(
        self, action_data: dict[str, Any], context: GrimoireContext
    ) -> None:
        """Execute log_event action.

        Args:
            action_data: Action data containing 'type' and 'data'
            context: Current execution context
        """
        event_type = action_data.get("type", "unknown")
        event_data = action_data.get("data", {})

        # Resolve templates in event_type and event_data
        if isinstance(event_type, str):
            event_type = context.resolve_template(event_type)

        # Recursively resolve templates in event_data
        if isinstance(event_data, dict):
            event_data = self._resolve_templates_in_dict(event_data, context)
        elif isinstance(event_data, str):
            event_data = context.resolve_template(event_data)

        logger.info(f"Flow event: {event_type}", extra={"event_data": event_data})

    def _action_display_value(self, action_data: str, context: GrimoireContext) -> None:
        """Execute display_value action.

        Args:
            action_data: Path to value to display
            context: Current execution context
        """
        if not context.has_variable(action_data):
            logger.warning(f"Cannot display: path not found: {action_data}")
            return

        value = context.get_variable(action_data)
        logger.info(f"Display value at {action_data}: {value}")

    def _action_validate_value(
        self, action_data: str, context: GrimoireContext
    ) -> None:
        """Execute validate_value action.

        Creates a GrimoireModel instance from the data and validates it using
        the model's built-in validate() method, which properly applies defaults
        before validation.

        Args:
            action_data: Path to value to validate
            context: Current execution context

        Raises:
            FlowExecutionError: If validation fails
        """
        if not context.has_variable(action_data):
            raise FlowExecutionError(f"Cannot validate: path not found: {action_data}")

        value = context.get_variable(action_data)

        # If it's a dict with a 'model' field, create and validate it
        if isinstance(value, dict) and "model" in value:
            try:
                # Use create_object which creates a GrimoireModel instance
                # The GrimoireModel's __init__ calls validate() internally,
                # which applies defaults before validation
                self.object_service.create_object(value)
                logger.debug(f"Validation passed for {action_data}")
            except Exception as e:
                raise FlowExecutionError(
                    f"Validation failed for {action_data}: {e}"
                ) from e
        else:
            logger.debug(f"No validation needed for {action_data}")

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
