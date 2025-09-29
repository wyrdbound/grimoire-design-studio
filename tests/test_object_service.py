"""Tests for ObjectInstantiationService - simplified for grimoire-model integration."""

import pytest

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompleteSystem,
    ModelDefinition,
    SystemDefinition,
)


@pytest.fixture
def sample_system():
    """Create a sample GRIMOIRE system for testing."""
    character_model = ModelDefinition(
        id="character",
        kind="model",
        name="Character",
        description="A player character",
        attributes={
            "name": AttributeDefinition(type="str"),
            "level": AttributeDefinition(type="int", default=1),
        },
    )

    system_def = SystemDefinition(id="test_system", kind="system", name="Test System")

    return CompleteSystem(system=system_def, models={"character": character_model})


class TestObjectInstantiationService:
    """Test cases for ObjectInstantiationService."""

    def test_service_initialization_success(self, sample_system):
        """Test that service initializes successfully."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_system)
        assert service.system == sample_system

    def test_create_object_invalid_data_type(self, sample_system):
        """Test create_object with invalid data type."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_system)

        with pytest.raises(ValueError, match="Object data must be a dictionary"):
            service.create_object("not a dict")

    def test_create_object_missing_model_field(self, sample_system):
        """Test create_object with missing model field."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_system)
        data = {"name": "Test"}  # Missing model field

        with pytest.raises(ValueError, match="Object data must contain 'model' field"):
            service.create_object(data)

    def test_create_object_unknown_model(self, sample_system):
        """Test create_object with unknown model type."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_system)
        data = {"model": "dragon", "name": "Smaug"}

        with pytest.raises(ValueError, match="Unknown model type: dragon"):
            service.create_object(data)
