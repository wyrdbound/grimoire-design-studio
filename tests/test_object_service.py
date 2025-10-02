"""Tests for ObjectInstantiationService - simplified for grimoire-model integration."""

import pytest

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompleteSystem,
    FlowDefinition,
    FlowInputOutput,
    FlowVariable,
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
            service.create_object("not a dict")  # type: ignore[arg-type]

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


@pytest.fixture
def sample_flow_system():
    """Create a sample GRIMOIRE system with flows for testing."""
    character_model = ModelDefinition(
        id="character",
        kind="model",
        name="Character",
        description="A player character",
        attributes={
            "name": AttributeDefinition(type="str"),
            "level": AttributeDefinition(type="int", default=1),
            "strength": AttributeDefinition(type="int", default=10),
        },
    )

    item_model = ModelDefinition(
        id="item",
        kind="model",
        name="Item",
        description="A game item",
        attributes={
            "name": AttributeDefinition(type="str"),
            "value": AttributeDefinition(type="int", default=0),
        },
    )

    flow_def = FlowDefinition(
        id="test_flow",
        kind="flow",
        name="Test Flow",
        description="A test flow",
        inputs=[
            FlowInputOutput(type="str", id="player_name", required=True),
            FlowInputOutput(type="int", id="player_level", required=False),
            FlowInputOutput(type="character", id="player_char", required=True),
        ],
        outputs=[
            FlowInputOutput(type="str", id="result_message", validate=False),
            FlowInputOutput(type="character", id="updated_char", validate=True),
        ],
        variables=[
            FlowVariable(type="int", id="temp_value", validate=False),
            FlowVariable(type="item", id="temp_item", validate=True),
        ],
    )

    system_def = SystemDefinition(id="test_system", kind="system", name="Test System")

    return CompleteSystem(
        system=system_def,
        models={"character": character_model, "item": item_model},
        flows={"test_flow": flow_def},
    )


class TestFlowInstantiation:
    """Test cases for flow-specific instantiation methods."""

    def test_instantiate_flow_input_success(self, sample_flow_system):
        """Test successful flow input instantiation."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_flow_system)
        flow_def = sample_flow_system.flows["test_flow"]

        input_data = {
            "player_name": "Hero",
            "player_level": 5,
            "player_char": {"name": "Hero", "level": 5, "strength": 15},
        }

        # Mock the create_object method to avoid grimoire-model calls
        original_create_object = service.create_object
        service.create_object = lambda data: {"mocked_object": data}

        try:
            result = service.instantiate_flow_input(flow_def, input_data)

            assert result["player_name"] == "Hero"
            assert result["player_level"] == 5
            assert result["player_char"]["mocked_object"]["model"] == "character"
        finally:
            service.create_object = original_create_object

    def test_instantiate_flow_input_missing_required(self, sample_flow_system):
        """Test flow input instantiation with missing required input."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_flow_system)
        flow_def = sample_flow_system.flows["test_flow"]

        input_data = {
            "player_name": "Hero",
            # Missing required player_char
        }

        with pytest.raises(RuntimeError, match="Failed to instantiate flow inputs"):
            service.instantiate_flow_input(flow_def, input_data)

    def test_instantiate_flow_input_optional_missing(self, sample_flow_system):
        """Test flow input instantiation with missing optional input."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_flow_system)
        flow_def = sample_flow_system.flows["test_flow"]

        input_data = {
            "player_name": "Hero",
            "player_char": {"name": "Hero", "level": 1},
            # Missing optional player_level
        }

        # Mock the create_object method
        service.create_object = lambda data: {"mocked_object": data}

        result = service.instantiate_flow_input(flow_def, input_data)

        assert result["player_name"] == "Hero"
        assert "player_level" not in result
        assert "player_char" in result

    def test_instantiate_flow_output_success(self, sample_flow_system):
        """Test successful flow output instantiation."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_flow_system)
        flow_def = sample_flow_system.flows["test_flow"]

        output_data = {
            "result_message": "Success!",
            "updated_char": {"name": "Hero", "level": 6},
        }

        # Mock the create_object method
        service.create_object = lambda data: {"validated_object": data}

        result = service.instantiate_flow_output(flow_def, output_data)

        assert result["result_message"] == "Success!"
        assert result["updated_char"]["validated_object"]["model"] == "character"

    def test_instantiate_flow_output_no_validation(self, sample_flow_system):
        """Test flow output instantiation without validation."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_flow_system)
        flow_def = sample_flow_system.flows["test_flow"]

        output_data = {
            "result_message": "Success!",
        }

        result = service.instantiate_flow_output(flow_def, output_data)

        # result_message should not be validated (validate=False)
        assert result["result_message"] == "Success!"

    def test_instantiate_flow_variable_success(self, sample_flow_system):
        """Test successful flow variable instantiation."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_flow_system)
        flow_def = sample_flow_system.flows["test_flow"]

        variable_data = {
            "temp_value": 42,
            "temp_item": {"name": "Magic Sword", "value": 100},
        }

        # Mock the create_object method
        service.create_object = lambda data: {"validated_object": data}

        result = service.instantiate_flow_variable(flow_def, variable_data)

        assert result["temp_value"] == 42
        assert result["temp_item"]["validated_object"]["model"] == "item"

    def test_instantiate_flow_variable_no_validation(self, sample_flow_system):
        """Test flow variable instantiation without validation."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_flow_system)
        flow_def = sample_flow_system.flows["test_flow"]

        variable_data = {
            "temp_value": 42,
        }

        result = service.instantiate_flow_variable(flow_def, variable_data)

        # temp_value should not be validated (validate=False)
        assert result["temp_value"] == 42

    def test_validate_primitive_type_success(self, sample_system):
        """Test primitive type validation success."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_system)

        # Test all primitive types
        assert service._validate_primitive_type("hello", "str", "test") == "hello"
        assert service._validate_primitive_type(42, "int", "test") == 42
        assert service._validate_primitive_type("42", "int", "test") == 42
        assert service._validate_primitive_type(3.14, "float", "test") == 3.14
        assert service._validate_primitive_type("3.14", "float", "test") == 3.14
        assert service._validate_primitive_type(True, "bool", "test") is True
        assert service._validate_primitive_type("true", "bool", "test") is True
        assert service._validate_primitive_type("false", "bool", "test") is False

    def test_validate_primitive_type_conversion_error(self, sample_system):
        """Test primitive type validation with conversion error."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_system)

        with pytest.raises(
            ValueError, match="Cannot convert test value 'invalid' to type 'int'"
        ):
            service._validate_primitive_type("invalid", "int", "test")

    def test_validate_primitive_type_unsupported_type(self, sample_system):
        """Test primitive type validation with unsupported type."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_system)

        with pytest.raises(ValueError, match="Unsupported primitive type: invalid"):
            service._validate_primitive_type("value", "invalid", "test")

    def test_flow_input_unknown_type(self, sample_flow_system):
        """Test flow input instantiation with unknown type."""
        from grimoire_studio.services.object_service import ObjectInstantiationService

        service = ObjectInstantiationService(sample_flow_system)

        # Create a flow with unknown input type
        flow_def = FlowDefinition(
            id="test_flow",
            kind="flow",
            name="Test Flow",
            inputs=[
                FlowInputOutput(type="unknown_type", id="test_input", required=True)
            ],
        )

        input_data = {"test_input": "some_value"}

        result = service.instantiate_flow_input(flow_def, input_data)

        # Should use value as-is with a warning
        assert result["test_input"] == "some_value"
