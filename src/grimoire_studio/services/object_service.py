"""Object instantiation service for GRIMOIRE game objects.

This module provides the ObjectInstantiationService class which integrates
with grimoire-model to create and validate game objects from YAML data.

This service requires grimoire-model to be installed and will fail explicitly
if it is not available, following the principle of explicit errors over fallbacks.
"""

from __future__ import annotations

from typing import Any

from grimoire_logging import get_logger
from grimoire_model import (  # Explicit import - fail fast if not available
    create_model,
    get_default_registry,
    register_model,
    register_primitive_type,
    validate_model_data,
)
from grimoire_model.core.model import GrimoireModel

from ..models.grimoire_definitions import CompleteSystem, FlowDefinition

logger = get_logger(__name__)


class ObjectInstantiationService:
    """Service for instantiating GRIMOIRE game objects using grimoire-model.

    This service provides methods to create validated game objects from YAML data
    by integrating with the grimoire-model library. It handles model type detection
    and object validation.

    Attributes:
        system: The complete GRIMOIRE system with all model definitions
        model_registry: Initialized ModelRegistry instance
    """

    def __init__(self, system: CompleteSystem) -> None:
        """Initialize the object instantiation service.

        Args:
            system: Complete GRIMOIRE system with model definitions

        Raises:
            RuntimeError: If model registration fails
        """
        self.system = system
        try:
            # Get the model registry
            self.model_registry = get_default_registry()

            # Register domain-specific primitive types for TTRPG systems
            self._register_primitive_types()

            # Register all models from the system (they're already grimoire-model objects)
            for _model_id, model_def in system.models.items():
                register_model(system.system.id, model_def)

            logger.info(
                f"Initialized ObjectInstantiationService for system: {system.system.id}"
            )
        except Exception as e:
            error_msg = f"Failed to initialize model registry: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _register_primitive_types(self) -> None:
        """Register domain-specific primitive types for TTRPG systems.

        This registers common primitive types used in tabletop RPG systems
        so they are treated as primitive values instead of custom models.
        """
        try:
            # Register dice roll notation type (e.g., "1d6", "2d10+3")
            register_primitive_type("roll")

            logger.debug("Registered custom primitive types in grimoire-model registry")

        except Exception as e:
            logger.warning(f"Failed to register some primitive types: {e}")
            # Continue anyway - this is not critical for basic functionality

    def _determine_model_type(self, data: dict[str, Any]) -> str:
        """Determine the model type from object data.

        Args:
            data: Object data dictionary

        Returns:
            Model type identifier

        Raises:
            ValueError: If model type cannot be determined
        """
        if "model" not in data:
            raise ValueError("Object data must contain 'model' field")

        model_type = data["model"]
        if not isinstance(model_type, str):
            raise ValueError(f"Model field must be a string, got {type(model_type)}")

        if model_type not in self.system.models:
            raise ValueError(f"Unknown model type: {model_type}")

        logger.debug(f"Determined model type: {model_type}")
        return model_type

    def create_object(self, data: dict[str, Any]) -> Any:
        """Create a game object from data using the appropriate model.

        Args:
            data: Object data dictionary with 'model' field

        Returns:
            Validated game object instance

        Raises:
            ValueError: If data is invalid or model type unknown
            RuntimeError: If object creation fails
        """
        if not isinstance(data, dict):
            raise ValueError("Object data must be a dictionary")

        model_type = self._determine_model_type(data)
        logger.debug(f"Creating {model_type} object")

        try:
            # Get the model definition and create the object
            model_def = self.system.models[model_type]
            game_object = create_model(model_def, data)
            logger.info(f"Successfully created {model_type} object")
            return game_object
        except Exception as e:
            error_msg = f"Failed to create {model_type} object: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def create_object_without_validation(self, data: dict[str, Any]) -> Any:
        """Create a game object from data without validation.

        This method creates GrimoireModel objects without validation,
        allowing for incremental object building during flow execution.
        Validation should be performed later using validate_value actions
        or at appropriate checkpoints.

        Args:
            data: Object data dictionary with 'model' field

        Returns:
            GrimoireModel instance without validation

        Raises:
            ValueError: If data is invalid or model type unknown
            RuntimeError: If object creation fails
        """

        logger.info(f"Data received with type {type(data)}")
        logger.info(f"Data: {data}")
        if isinstance(data, GrimoireModel):
            logger.debug(
                "Data is already a GrimoireModel instance, returning as-is without validation"
            )
            return data

        if not isinstance(data, dict):
            raise ValueError("Object data must be a dictionary")

        model_type = self._determine_model_type(data)
        logger.debug(f"Creating {model_type} object without validation")

        try:
            # Import the new function from grimoire-model
            from grimoire_model import create_model_without_validation

            # Get the model definition and create the object without validation
            model_def = self.system.models[model_type]
            game_object = create_model_without_validation(model_def, data)
            logger.info(f"Successfully created {model_type} object without validation")
            return game_object
        except Exception as e:
            error_msg = f"Failed to create {model_type} object without validation: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def create_character(self, data: dict[str, Any]) -> Any:
        """Create a character object (backward compatibility method).

        Args:
            data: Character data dictionary

        Returns:
            Validated character object instance
        """
        character_data = {"model": "character", **data}
        return self.create_object(character_data)

    def create_item(self, data: dict[str, Any]) -> Any:
        """Create an item object (backward compatibility method).

        Args:
            data: Item data dictionary

        Returns:
            Validated item object instance
        """
        item_data = {"model": "item", **data}
        return self.create_object(item_data)

    def validate_object(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate object data without creating an instance.

        Args:
            data: Object data dictionary

        Returns:
            Tuple of (is_valid, error_messages)
        """
        logger.debug("Validating object data")
        try:
            model_type = self._determine_model_type(data)
            model_def = self.system.models[model_type]
            # Use grimoire-model's validation function
            errors = validate_model_data(data, model_def.attributes)
            if errors:
                logger.debug(f"Object data validation failed: {errors}")
                return False, errors
            else:
                logger.debug("Object data validation passed")
                return True, []
        except Exception as e:
            error_msg = str(e)
            logger.debug(f"Object data validation failed: {error_msg}")
            return False, [error_msg]

    def update_object(self, game_object: Any, data: dict[str, Any]) -> Any:
        """Update an existing object with new data and re-validate.

        Args:
            game_object: Existing game object instance (GrimoireModel)
            data: Updated data dictionary

        Returns:
            Updated and validated game object instance

        Raises:
            RuntimeError: If update fails
        """
        logger.debug("Updating game object")
        try:
            # Use the GrimoireModel's update method
            game_object.update(data)
            # Validate after update
            game_object.validate()
            logger.info("Successfully updated game object")
            return game_object
        except Exception as e:
            error_msg = f"Failed to update game object: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def instantiate_flow_input(
        self, flow_def: FlowDefinition, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Instantiate flow input objects based on flow definition types.

        Args:
            flow_def: Flow definition containing input specifications
            input_data: Dictionary mapping input IDs to their values

        Returns:
            Dictionary of instantiated and validated input objects

        Raises:
            ValueError: If required inputs are missing or invalid
            RuntimeError: If instantiation fails
        """
        logger.debug(f"Instantiating flow inputs for flow: {flow_def.id}")
        instantiated_inputs = {}

        try:
            for flow_input in flow_def.inputs:
                input_id = flow_input.id
                input_type = flow_input.type

                # Check if required input is provided
                if flow_input.required and input_id not in input_data:
                    raise ValueError(f"Required input '{input_id}' not provided")

                # Skip optional inputs that aren't provided
                if input_id not in input_data:
                    logger.debug(f"Optional input '{input_id}' not provided, skipping")
                    continue

                value = input_data[input_id]

                # Handle primitive types directly
                if input_type in ("str", "int", "float", "bool"):
                    instantiated_inputs[input_id] = self.validate_primitive_type(
                        value, input_type, f"input '{input_id}'"
                    )
                # Handle model types
                elif input_type in self.system.models:
                    # Check if it's already a GrimoireModel - pass through without validation
                    if isinstance(value, GrimoireModel):
                        logger.debug(
                            f"Input '{input_id}' is already a GrimoireModel, passing through without validation"
                        )
                        instantiated_inputs[input_id] = value
                    else:
                        # Ensure the value has the model type specified
                        if isinstance(value, dict) and "model" not in value:
                            value = {"model": input_type, **value}
                        # Use create_object_without_validation for flow inputs to allow partial objects
                        instantiated_inputs[input_id] = (
                            self.create_object_without_validation(value)
                        )
                else:
                    # For other types, validate as-is but log a warning
                    logger.warning(
                        f"Unknown input type '{input_type}' for input '{input_id}', "
                        "using value as-is"
                    )
                    instantiated_inputs[input_id] = value

            logger.info(
                f"Successfully instantiated {len(instantiated_inputs)} flow inputs"
            )
            return instantiated_inputs

        except Exception as e:
            error_msg = f"Failed to instantiate flow inputs: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def instantiate_flow_output(
        self, flow_def: FlowDefinition, output_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Instantiate flow output objects based on flow definition types.

        Args:
            flow_def: Flow definition containing output specifications
            output_data: Dictionary mapping output IDs to their values

        Returns:
            Dictionary of instantiated and validated output objects

        Raises:
            RuntimeError: If instantiation fails
        """
        logger.debug(f"Instantiating flow outputs for flow: {flow_def.id}")
        instantiated_outputs = {}

        try:
            for flow_output in flow_def.outputs:
                output_id = flow_output.id
                output_type = flow_output.type

                # Skip outputs not present in data
                if output_id not in output_data:
                    logger.debug(f"Output '{output_id}' not present in data, skipping")
                    continue

                value = output_data[output_id]

                # Handle primitive types directly
                if output_type in ("str", "int", "float", "bool"):
                    instantiated_outputs[output_id] = self.validate_primitive_type(
                        value, output_type, f"output '{output_id}'"
                    )
                # Handle model types
                elif output_type in self.system.models:
                    # Ensure the value has the model type specified
                    if isinstance(value, dict) and "model" not in value:
                        value = {"model": output_type, **value}

                    # Only validate if specified in flow definition
                    if flow_output.validate:
                        instantiated_outputs[output_id] = self.create_object(value)
                    else:
                        instantiated_outputs[output_id] = value
                else:
                    # For other types, use value as-is
                    logger.debug(
                        f"Using output type '{output_type}' for output '{output_id}' "
                        "as-is"
                    )
                    instantiated_outputs[output_id] = value

            logger.info(
                f"Successfully instantiated {len(instantiated_outputs)} flow outputs"
            )
            return instantiated_outputs

        except Exception as e:
            error_msg = f"Failed to instantiate flow outputs: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def instantiate_flow_variable(
        self, flow_def: FlowDefinition, variable_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Instantiate flow variable objects based on flow definition types.

        Args:
            flow_def: Flow definition containing variable specifications
            variable_data: Dictionary mapping variable IDs to their values

        Returns:
            Dictionary of instantiated and validated variable objects

        Raises:
            RuntimeError: If instantiation fails
        """
        logger.debug(f"Instantiating flow variables for flow: {flow_def.id}")
        instantiated_variables = {}

        try:
            for flow_var in flow_def.variables:
                var_id = flow_var.id
                var_type = flow_var.type

                # Skip variables not present in data
                if var_id not in variable_data:
                    logger.debug(f"Variable '{var_id}' not present in data, skipping")
                    continue

                value = variable_data[var_id]

                # Handle primitive types directly
                if var_type in ("str", "int", "float", "bool"):
                    instantiated_variables[var_id] = self.validate_primitive_type(
                        value, var_type, f"variable '{var_id}'"
                    )
                # Handle model types
                elif var_type in self.system.models:
                    # Ensure the value has the model type specified
                    if isinstance(value, dict) and "model" not in value:
                        value = {"model": var_type, **value}

                    # Only validate if specified in flow definition
                    if flow_var.validate:
                        instantiated_variables[var_id] = self.create_object(value)
                    else:
                        instantiated_variables[var_id] = value
                else:
                    # For other types, use value as-is
                    logger.debug(
                        f"Using variable type '{var_type}' for variable '{var_id}' "
                        "as-is"
                    )
                    instantiated_variables[var_id] = value

            logger.info(
                f"Successfully instantiated {len(instantiated_variables)} flow variables"
            )
            return instantiated_variables

        except Exception as e:
            error_msg = f"Failed to instantiate flow variables: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def validate_primitive_type(
        self, value: Any, expected_type: str, context: str = "value"
    ) -> Any:
        """Validate and convert primitive type values.

        This is a public method that can be used by other services to ensure
        type consistency when working with flow variables, outputs, etc.

        Args:
            value: Value to validate
            expected_type: Expected primitive type (str, int, float, bool)
            context: Context string for error messages (default: "value")

        Returns:
            Validated and converted value

        Raises:
            ValueError: If value cannot be converted to expected type
        """
        try:
            if expected_type == "str":
                return str(value)
            elif expected_type == "int":
                return int(value)
            elif expected_type == "float":
                return float(value)
            elif expected_type == "bool":
                # Handle common boolean representations
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ("true", "yes", "1", "on")
                return bool(value)
            else:
                raise ValueError(f"Unsupported primitive type: {expected_type}")
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Cannot convert {context} value '{value}' to type '{expected_type}': {e}"
            ) from e
