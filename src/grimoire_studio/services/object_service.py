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
    validate_model_data,
)

from ..models.grimoire_definitions import CompleteSystem

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
