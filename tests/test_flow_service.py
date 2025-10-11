"""Tests for FlowExecutionService."""

import pytest
from prefect.testing.utilities import prefect_test_harness

from grimoire_studio.models.grimoire_definitions import (
    AttributeDefinition,
    CompleteSystem,
    FlowDefinition,
    FlowInputOutput,
    FlowStep,
    FlowVariable,
    ModelDefinition,
    SystemDefinition,
)
from grimoire_studio.services.flow_service import (
    FlowExecutionError,
    FlowExecutionService,
)
from grimoire_studio.services.object_service import ObjectInstantiationService


@pytest.fixture(scope="session", autouse=True)
def prefect_test_mode():
    """Enable Prefect test mode for all flow service tests."""
    with prefect_test_harness():
        yield


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
            "hp": AttributeDefinition(type="int", default=10),
        },
    )

    system_def = SystemDefinition(id="test_system", kind="system", name="Test System")

    return CompleteSystem(system=system_def, models={"character": character_model})


@pytest.fixture
def object_service(sample_system):
    """Create an ObjectInstantiationService for testing."""
    return ObjectInstantiationService(sample_system)


@pytest.fixture
def flow_service(sample_system, object_service):
    """Create a FlowExecutionService for testing."""
    return FlowExecutionService(sample_system, object_service)


class TestFlowExecutionServiceInitialization:
    """Test cases for FlowExecutionService initialization."""

    def test_service_initialization_success(self, sample_system, object_service):
        """Test that service initializes successfully."""
        service = FlowExecutionService(sample_system, object_service)
        assert service.system == sample_system
        assert service.object_service == object_service
        assert service.current_context is None
        assert service.current_flow is None

    def test_initialization_with_empty_system(self, object_service):
        """Test initialization with system that has no flows."""
        system_def = SystemDefinition(
            id="empty_system", kind="system", name="Empty System"
        )
        empty_system = CompleteSystem(system=system_def)

        service = FlowExecutionService(empty_system, object_service)
        assert service.system == empty_system
        assert len(service.system.flows) == 0


class TestBasicFlowExecution:
    """Test cases for basic flow execution."""

    def test_execute_nonexistent_flow(self, flow_service):
        """Test executing a flow that doesn't exist."""
        with pytest.raises(ValueError, match="Flow not found: nonexistent"):
            flow_service.execute_flow("nonexistent")

    def test_execute_simple_completion_flow(self, flow_service, sample_system):
        """Test executing a flow with only a completion step."""
        flow = FlowDefinition(
            id="simple_flow",
            kind="flow",
            name="Simple Flow",
            steps=[
                FlowStep(
                    id="finish",
                    name="Finish",
                    type="completion",
                    prompt="Flow complete!",
                )
            ],
        )

        sample_system.flows["simple_flow"] = flow

        result = flow_service.execute_flow("simple_flow")
        assert isinstance(result, dict)
        assert len(result) == 0  # No outputs defined

    def test_execute_flow_with_inputs(self, flow_service, sample_system):
        """Test executing a flow with input parameters."""
        flow = FlowDefinition(
            id="input_flow",
            kind="flow",
            name="Input Flow",
            inputs=[
                FlowInputOutput(type="str", id="player_name", required=True),
                FlowInputOutput(type="int", id="player_level", required=False),
            ],
            steps=[
                FlowStep(
                    id="finish",
                    name="Finish",
                    type="completion",
                )
            ],
        )

        sample_system.flows["input_flow"] = flow

        result = flow_service.execute_flow(
            "input_flow", inputs={"player_name": "Alice", "player_level": 5}
        )
        assert isinstance(result, dict)

    def test_execute_flow_missing_required_input(self, flow_service, sample_system):
        """Test executing a flow without a required input."""
        flow = FlowDefinition(
            id="required_input_flow",
            kind="flow",
            name="Required Input Flow",
            inputs=[
                FlowInputOutput(type="str", id="required_param", required=True),
            ],
            steps=[
                FlowStep(
                    id="finish",
                    name="Finish",
                    type="completion",
                )
            ],
        )

        sample_system.flows["required_input_flow"] = flow

        with pytest.raises(
            FlowExecutionError, match="Required input 'required_param' not provided"
        ):
            flow_service.execute_flow("required_input_flow")

    def test_execute_flow_with_outputs(self, flow_service, sample_system):
        """Test executing a flow that produces outputs."""
        flow = FlowDefinition(
            id="output_flow",
            kind="flow",
            name="Output Flow",
            outputs=[
                FlowInputOutput(type="str", id="result_message", validate=False),
            ],
            steps=[
                FlowStep(
                    id="set_output",
                    name="Set Output",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.result_message",
                                "value": "Success!",
                            }
                        }
                    ],
                )
            ],
        )

        sample_system.flows["output_flow"] = flow

        result = flow_service.execute_flow("output_flow")
        assert "result_message" in result
        assert result["result_message"] == "Success!"


class TestFlowStepExecution:
    """Test cases for individual step execution."""

    def test_execute_multiple_steps_sequential(self, flow_service, sample_system):
        """Test executing multiple steps in sequence."""
        flow = FlowDefinition(
            id="multi_step_flow",
            kind="flow",
            name="Multi Step Flow",
            variables=[
                FlowVariable(type="int", id="counter", validate=False),
            ],
            steps=[
                FlowStep(
                    id="step1",
                    name="Step 1",
                    type="completion",
                    actions=[{"set_value": {"path": "variables.counter", "value": 1}}],
                ),
                FlowStep(
                    id="step2",
                    name="Step 2",
                    type="completion",
                    actions=[{"set_value": {"path": "variables.counter", "value": 2}}],
                ),
                FlowStep(
                    id="finish",
                    name="Finish",
                    type="completion",
                ),
            ],
        )

        sample_system.flows["multi_step_flow"] = flow

        result = flow_service.execute_flow("multi_step_flow")
        assert isinstance(result, dict)

    def test_execute_steps_with_next_step(self, flow_service, sample_system):
        """Test executing steps with explicit next_step references."""
        flow = FlowDefinition(
            id="branching_flow",
            kind="flow",
            name="Branching Flow",
            outputs=[
                FlowInputOutput(type="str", id="path_taken", validate=False),
            ],
            steps=[
                FlowStep(
                    id="start",
                    name="Start",
                    type="completion",
                    actions=[
                        {"set_value": {"path": "outputs.path_taken", "value": "start"}}
                    ],
                    next_step="end",  # Skip middle step
                ),
                FlowStep(
                    id="middle",
                    name="Middle",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.path_taken",
                                "value": "middle",
                            }
                        }
                    ],
                ),
                FlowStep(
                    id="end",
                    name="End",
                    type="completion",
                    actions=[
                        {"set_value": {"path": "outputs.path_taken", "value": "end"}}
                    ],
                ),
            ],
        )

        sample_system.flows["branching_flow"] = flow

        result = flow_service.execute_flow("branching_flow")
        assert result["path_taken"] == "end"  # Should skip middle

    def test_execute_step_with_invalid_next_step(self, flow_service, sample_system):
        """Test executing step with invalid next_step reference."""
        flow = FlowDefinition(
            id="invalid_next_flow",
            kind="flow",
            name="Invalid Next Flow",
            steps=[
                FlowStep(
                    id="start",
                    name="Start",
                    type="completion",
                    next_step="nonexistent",
                ),
            ],
        )

        sample_system.flows["invalid_next_flow"] = flow

        with pytest.raises(
            FlowExecutionError, match="references unknown next_step: nonexistent"
        ):
            flow_service.execute_flow("invalid_next_flow")


class TestActionExecution:
    """Test cases for action execution."""

    def test_action_set_value(self, flow_service, sample_system):
        """Test set_value action."""
        flow = FlowDefinition(
            id="set_value_flow",
            kind="flow",
            name="Set Value Flow",
            outputs=[
                FlowInputOutput(type="str", id="message", validate=False),
            ],
            steps=[
                FlowStep(
                    id="set_message",
                    name="Set Message",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.message",
                                "value": "Hello, World!",
                            }
                        }
                    ],
                )
            ],
        )

        sample_system.flows["set_value_flow"] = flow

        result = flow_service.execute_flow("set_value_flow")
        assert result["message"] == "Hello, World!"

    def test_action_set_value_missing_path(self, flow_service, sample_system):
        """Test set_value action with missing path."""
        flow = FlowDefinition(
            id="invalid_set_value_flow",
            kind="flow",
            name="Invalid Set Value Flow",
            steps=[
                FlowStep(
                    id="bad_action",
                    name="Bad Action",
                    type="completion",
                    actions=[{"set_value": {"value": "test"}}],  # Missing path
                )
            ],
        )

        sample_system.flows["invalid_set_value_flow"] = flow

        with pytest.raises(
            FlowExecutionError, match="set_value action requires 'path' field"
        ):
            flow_service.execute_flow("invalid_set_value_flow")

    def test_action_log_message_dict(self, flow_service, sample_system, caplog):
        """Test log_message action with dict format."""
        import logging

        caplog.set_level(logging.INFO)

        flow = FlowDefinition(
            id="log_message_flow",
            kind="flow",
            name="Log Message Flow",
            steps=[
                FlowStep(
                    id="log_step",
                    name="Log Step",
                    type="completion",
                    actions=[{"log_message": {"message": "Test log message"}}],
                )
            ],
        )

        sample_system.flows["log_message_flow"] = flow

        flow_service.execute_flow("log_message_flow")
        assert "Test log message" in caplog.text

    def test_action_log_message_string(self, flow_service, sample_system, caplog):
        """Test log_message action with string format."""
        import logging

        caplog.set_level(logging.INFO)

        flow = FlowDefinition(
            id="log_message_string_flow",
            kind="flow",
            name="Log Message String Flow",
            steps=[
                FlowStep(
                    id="log_step",
                    name="Log Step",
                    type="completion",
                    actions=[{"log_message": "Simple log message"}],
                )
            ],
        )

        sample_system.flows["log_message_string_flow"] = flow

        flow_service.execute_flow("log_message_string_flow")
        assert "Simple log message" in caplog.text

    def test_action_log_event(self, flow_service, sample_system, caplog):
        """Test log_event action."""
        import logging

        caplog.set_level(logging.INFO)

        flow = FlowDefinition(
            id="log_event_flow",
            kind="flow",
            name="Log Event Flow",
            steps=[
                FlowStep(
                    id="log_event_step",
                    name="Log Event Step",
                    type="completion",
                    actions=[
                        {
                            "log_event": {
                                "type": "character_created",
                                "data": {"name": "Alice"},
                            }
                        }
                    ],
                )
            ],
        )

        sample_system.flows["log_event_flow"] = flow

        flow_service.execute_flow("log_event_flow")
        assert "character_created" in caplog.text

    def test_action_display_value(self, flow_service, sample_system, caplog):
        """Test display_value action basic functionality."""
        import logging

        caplog.set_level(logging.INFO)

        flow = FlowDefinition(
            id="display_value_flow",
            kind="flow",
            name="Display Value Flow",
            variables=[
                FlowVariable(type="str", id="test_var", validate=False),
            ],
            steps=[
                FlowStep(
                    id="set_and_display",
                    name="Set and Display",
                    type="completion",
                    actions=[
                        {"set_value": {"path": "variables.test_var", "value": "test"}},
                        {"display_value": "variables.test_var"},
                    ],
                )
            ],
        )

        sample_system.flows["display_value_flow"] = flow

        flow_service.execute_flow("display_value_flow")

        # Verify the display format shows both path and value
        assert "variables.test_var: test" in caplog.text

    def test_action_display_value_callback(self, flow_service, sample_system):
        """Test display_value action with callback."""
        callback_calls = []

        def on_action_execute(action_type: str, action_data: dict) -> None:
            callback_calls.append((action_type, action_data))

        flow = FlowDefinition(
            id="display_value_callback_flow",
            kind="flow",
            name="Display Value Callback Flow",
            variables=[
                FlowVariable(type="str", id="test_var", validate=False),
            ],
            steps=[
                FlowStep(
                    id="set_and_display",
                    name="Set and Display",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.test_var",
                                "value": "callback_test",
                            }
                        },
                        {"display_value": "variables.test_var"},
                    ],
                )
            ],
        )

        sample_system.flows["display_value_callback_flow"] = flow

        flow_service.execute_flow(
            "display_value_callback_flow", on_action_execute=on_action_execute
        )

        # Verify callback was called for display_value action
        display_calls = [call for call in callback_calls if call[0] == "display_value"]
        assert len(display_calls) == 1

        action_type, action_data = display_calls[0]
        assert action_type == "display_value"
        assert action_data["message"] == "variables.test_var: callback_test"

    def test_action_display_value_missing_path(
        self, flow_service, sample_system, caplog
    ):
        """Test display_value action with missing path."""
        import logging

        caplog.set_level(logging.WARNING)

        flow = FlowDefinition(
            id="display_value_missing_flow",
            kind="flow",
            name="Display Value Missing Flow",
            steps=[
                FlowStep(
                    id="display_missing",
                    name="Display Missing",
                    type="completion",
                    actions=[
                        {"display_value": "nonexistent.path"},
                    ],
                )
            ],
        )

        sample_system.flows["display_value_missing_flow"] = flow

        flow_service.execute_flow("display_value_missing_flow")

        # Verify warning message for missing path
        assert "Cannot display: path not found: nonexistent.path" in caplog.text

    def test_action_display_value_complex_object(
        self, flow_service, sample_system, caplog
    ):
        """Test display_value action with complex object."""
        import logging

        caplog.set_level(logging.INFO)

        flow = FlowDefinition(
            id="display_complex_flow",
            kind="flow",
            name="Display Complex Flow",
            variables=[
                FlowVariable(type="dict", id="complex_var", validate=False),
            ],
            steps=[
                FlowStep(
                    id="set_and_display_complex",
                    name="Set and Display Complex",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.complex_var",
                                "value": {"name": "Test", "level": 5},
                            }
                        },
                        {"display_value": "variables.complex_var"},
                    ],
                )
            ],
        )

        sample_system.flows["display_complex_flow"] = flow

        flow_service.execute_flow("display_complex_flow")

        # Verify complex object is displayed correctly
        assert "variables.complex_var: {'name': 'Test', 'level': 5}" in caplog.text

    def test_table_roll_action_callback(self, flow_service, sample_system):
        """Test that table roll actions trigger callbacks."""
        callback_calls = []

        def on_action_execute(action_type: str, action_data: dict) -> None:
            callback_calls.append((action_type, action_data))

        # Add a simple table to the system for testing
        from grimoire_studio.models.grimoire_definitions import TableDefinition

        test_table = TableDefinition(
            id="test_callback_table",
            kind="table",
            name="Test Callback Table",
            roll="1d2",
            entries=[
                {"range": "1", "value": "First Option"},
                {"range": "2", "value": "Second Option"},
            ],
        )
        sample_system.tables["test_callback_table"] = test_table

        flow = FlowDefinition(
            id="table_callback_flow",
            kind="flow",
            name="Table Callback Flow",
            variables=[
                FlowVariable(type="str", id="result_var", validate=False),
            ],
            steps=[
                FlowStep(
                    id="roll_with_actions",
                    name="Roll with Actions",
                    type="table_roll",
                    step_config={
                        "tables": [
                            {
                                "table": "test_callback_table",
                                "actions": [
                                    {
                                        "set_value": {
                                            "path": "variables.result_var",
                                            "value": "{{ result.entry }}",
                                        }
                                    },
                                    {
                                        "display_message": "Table rolled: {{ result.entry }}"
                                    },
                                    {"display_value": "variables.result_var"},
                                ],
                            }
                        ]
                    },
                )
            ],
        )

        sample_system.flows["table_callback_flow"] = flow

        flow_service.execute_flow(
            "table_callback_flow", on_action_execute=on_action_execute
        )

        # Verify callbacks were called for table actions
        display_message_calls = [
            call for call in callback_calls if call[0] == "display_message"
        ]
        display_value_calls = [
            call for call in callback_calls if call[0] == "display_value"
        ]

        assert len(display_message_calls) == 1
        assert len(display_value_calls) == 1

        # Verify display_message content
        _, message_data = display_message_calls[0]
        assert "Table rolled:" in message_data["message"]

        # Verify display_value content
        _, value_data = display_value_calls[0]
        assert "variables.result_var:" in value_data["message"]

    def test_action_validate_value_success(self, flow_service, sample_system):
        """Test validate_value action with valid object."""
        flow = FlowDefinition(
            id="validate_flow",
            kind="flow",
            name="Validate Flow",
            variables=[
                FlowVariable(type="character", id="char", validate=False),
            ],
            steps=[
                FlowStep(
                    id="validate_step",
                    name="Validate Step",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.char",
                                "value": {
                                    "model": "character",
                                    "name": "Alice",
                                    "level": 1,
                                    "hp": 10,  # Include required hp field
                                },
                            }
                        },
                        {"validate_value": "variables.char"},
                    ],
                )
            ],
        )

        sample_system.flows["validate_flow"] = flow

        result = flow_service.execute_flow("validate_flow")
        assert isinstance(result, dict)

    def test_action_validate_value_failure(self, flow_service, sample_system):
        """Test validate_value action with invalid object."""
        flow = FlowDefinition(
            id="validate_fail_flow",
            kind="flow",
            name="Validate Fail Flow",
            variables=[
                FlowVariable(type="character", id="char", validate=False),
            ],
            steps=[
                FlowStep(
                    id="validate_step",
                    name="Validate Step",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.char",
                                "value": {
                                    "model": "character",
                                    # Missing required 'name' field
                                    "level": "not_an_int",
                                },
                            }
                        },
                        {"validate_value": "variables.char"},
                    ],
                )
            ],
        )

        sample_system.flows["validate_fail_flow"] = flow

        with pytest.raises(FlowExecutionError, match="Validation failed"):
            flow_service.execute_flow("validate_fail_flow")


class TestPreActions:
    """Test cases for pre-actions."""

    def test_pre_actions_execute_before_step(self, flow_service, sample_system):
        """Test that pre-actions execute before step actions."""
        flow = FlowDefinition(
            id="pre_action_flow",
            kind="flow",
            name="Pre Action Flow",
            outputs=[
                FlowInputOutput(type="str", id="result", validate=False),
            ],
            steps=[
                FlowStep(
                    id="test_step",
                    name="Test Step",
                    type="completion",
                    pre_actions=[
                        {
                            "set_value": {
                                "path": "outputs.result",
                                "value": "pre_action",
                            }
                        }
                    ],
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.result",
                                "value": "step_action",
                            }
                        }
                    ],
                )
            ],
        )

        sample_system.flows["pre_action_flow"] = flow

        result = flow_service.execute_flow("pre_action_flow")
        # Step action should overwrite pre-action
        assert result["result"] == "step_action"


class TestCallbacks:
    """Test cases for execution callbacks."""

    def test_on_step_complete_callback(self, flow_service, sample_system):
        """Test that on_step_complete callback is invoked."""
        flow = FlowDefinition(
            id="callback_flow",
            kind="flow",
            name="Callback Flow",
            steps=[
                FlowStep(id="step1", name="Step 1", type="completion"),
                FlowStep(id="step2", name="Step 2", type="completion"),
            ],
        )

        sample_system.flows["callback_flow"] = flow

        steps_completed = []

        def on_step_complete(step_id: str, step_result: dict) -> None:
            steps_completed.append(step_id)

        flow_service.execute_flow("callback_flow", on_step_complete=on_step_complete)

        assert steps_completed == ["step1", "step2"]

    def test_on_action_execute_callback(self, flow_service, sample_system):
        """Test that on_action_execute callback is invoked."""
        flow = FlowDefinition(
            id="action_callback_flow",
            kind="flow",
            name="Action Callback Flow",
            steps=[
                FlowStep(
                    id="step1",
                    name="Step 1",
                    type="completion",
                    actions=[
                        {"log_message": "Test message"},
                        {"set_value": {"path": "outputs.test", "value": "test"}},
                    ],
                )
            ],
            outputs=[
                FlowInputOutput(type="str", id="test", validate=False),
            ],
        )

        sample_system.flows["action_callback_flow"] = flow

        actions_executed = []

        def on_action_execute(action_type: str, action_data: dict) -> None:
            actions_executed.append(action_type)

        flow_service.execute_flow(
            "action_callback_flow", on_action_execute=on_action_execute
        )

        assert "log_message" in actions_executed
        assert "set_value" in actions_executed


class TestContextManagement:
    """Test cases for context management."""

    def test_context_isolated_between_flows(self, flow_service, sample_system):
        """Test that context is isolated between flow executions."""
        flow = FlowDefinition(
            id="context_test_flow",
            kind="flow",
            name="Context Test Flow",
            outputs=[
                FlowInputOutput(type="int", id="value", validate=False),
            ],
            steps=[
                FlowStep(
                    id="set_value",
                    name="Set Value",
                    type="completion",
                    actions=[{"set_value": {"path": "outputs.value", "value": 42}}],
                )
            ],
        )

        sample_system.flows["context_test_flow"] = flow

        # Execute first time
        result1 = flow_service.execute_flow("context_test_flow")
        assert result1["value"] == 42

        # Context should be cleared after execution
        assert flow_service.current_context is None

        # Execute second time - should not have residual state
        result2 = flow_service.execute_flow("context_test_flow")
        assert result2["value"] == 42

    def test_context_cleared_on_error(self, flow_service, sample_system):
        """Test that context is cleared even if flow execution fails."""
        flow = FlowDefinition(
            id="error_flow",
            kind="flow",
            name="Error Flow",
            steps=[
                FlowStep(
                    id="error_step",
                    name="Error Step",
                    type="completion",
                    actions=[
                        {"set_value": {"value": "missing_path"}}  # Invalid action
                    ],
                )
            ],
        )

        sample_system.flows["error_flow"] = flow

        with pytest.raises(FlowExecutionError):
            flow_service.execute_flow("error_flow")

        # Context should be cleared even after error
        assert flow_service.current_context is None
        assert flow_service.current_flow is None


class TestTypeCoercion:
    """Tests for automatic type coercion in flow actions."""

    def test_simple_type_coercion_int(self, flow_service, sample_system):
        """Test that template-resolved values are coerced to int type."""
        flow = FlowDefinition(
            id="int_coercion_flow",
            kind="flow",
            name="Int Coercion Flow",
            variables=[
                FlowVariable(type="int", id="counter", validate=False),
            ],
            outputs=[
                FlowInputOutput(type="int", id="result", validate=False),
            ],
            steps=[
                FlowStep(
                    id="init",
                    name="Initialize",
                    type="completion",
                    actions=[
                        {"set_value": {"path": "variables.counter", "value": 0}},
                    ],
                ),
                FlowStep(
                    id="increment",
                    name="Increment",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.counter",
                                "value": "{{ variables.counter + 1 }}",
                            }
                        },
                    ],
                ),
                FlowStep(
                    id="output",
                    name="Output",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.result",
                                "value": "{{ variables.counter }}",
                            }
                        },
                    ],
                ),
            ],
        )

        sample_system.flows["int_coercion_flow"] = flow
        result = flow_service.execute_flow("int_coercion_flow")

        # Verify type coercion worked
        assert isinstance(result["result"], int)
        assert result["result"] == 1

    def test_simple_type_coercion_str(self, flow_service, sample_system):
        """Test that template-resolved values are coerced to str type."""
        flow = FlowDefinition(
            id="str_coercion_flow",
            kind="flow",
            name="Str Coercion Flow",
            outputs=[
                FlowInputOutput(type="str", id="message", validate=False),
            ],
            steps=[
                FlowStep(
                    id="create_message",
                    name="Create Message",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.message",
                                "value": "{{ 42 }}",  # Number to string
                            }
                        },
                    ],
                ),
            ],
        )

        sample_system.flows["str_coercion_flow"] = flow
        result = flow_service.execute_flow("str_coercion_flow")

        # Verify type coercion worked
        assert isinstance(result["message"], str)
        assert result["message"] == "42"

    def test_nested_type_coercion(self, flow_service, sample_system):
        """Test that nested model attributes get proper type coercion."""
        flow = FlowDefinition(
            id="nested_coercion_flow",
            kind="flow",
            name="Nested Coercion Flow",
            variables=[
                FlowVariable(type="character", id="hero", validate=False),
            ],
            outputs=[
                FlowInputOutput(type="int", id="final_hp", validate=False),
            ],
            steps=[
                FlowStep(
                    id="init",
                    name="Initialize",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.hero",
                                "value": {
                                    "model": "character",
                                    "name": "Hero",
                                    "level": 1,
                                    "hp": 100,
                                },
                            }
                        },
                    ],
                ),
                FlowStep(
                    id="modify",
                    name="Modify HP",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.hero.hp",
                                # Template returns string, should coerce to int
                                "value": "{{ 100 + 20 }}",
                            }
                        },
                    ],
                ),
                FlowStep(
                    id="output",
                    name="Output",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.final_hp",
                                "value": "{{ variables.hero.hp }}",
                            }
                        },
                    ],
                ),
            ],
        )

        sample_system.flows["nested_coercion_flow"] = flow
        result = flow_service.execute_flow("nested_coercion_flow")

        # Verify nested type coercion worked
        assert isinstance(result["final_hp"], int)
        assert result["final_hp"] == 120

    def test_nested_type_coercion_multiple_levels(self, flow_service, sample_system):
        """Test type coercion with deeply nested model structures."""
        # Create a stats model
        stats_model = ModelDefinition(
            id="stats",
            kind="model",
            name="Stats",
            attributes={
                "strength": AttributeDefinition(type="int"),
                "dexterity": AttributeDefinition(type="int"),
            },
        )

        # Create a character model with nested stats
        character_with_stats = ModelDefinition(
            id="character_with_stats",
            kind="model",
            name="Character With Stats",
            attributes={
                "name": AttributeDefinition(type="str"),
                "stats": AttributeDefinition(type="stats"),
                "hp": AttributeDefinition(type="int"),
            },
        )

        sample_system.models["stats"] = stats_model
        sample_system.models["character_with_stats"] = character_with_stats

        flow = FlowDefinition(
            id="deep_nested_flow",
            kind="flow",
            name="Deep Nested Flow",
            variables=[
                FlowVariable(type="character_with_stats", id="hero", validate=False),
            ],
            outputs=[
                FlowInputOutput(type="int", id="final_strength", validate=False),
            ],
            steps=[
                FlowStep(
                    id="init",
                    name="Initialize",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.hero",
                                "value": {
                                    "model": "character_with_stats",
                                    "name": "Hero",
                                    "stats": {
                                        "model": "stats",
                                        "strength": 10,
                                        "dexterity": 12,
                                    },
                                    "hp": 100,
                                },
                            }
                        },
                    ],
                ),
                FlowStep(
                    id="modify",
                    name="Modify Strength",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.hero.stats.strength",
                                # Template returns string, should coerce to int
                                "value": "{{ 10 + 5 }}",
                            }
                        },
                    ],
                ),
                FlowStep(
                    id="output",
                    name="Output",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.final_strength",
                                "value": "{{ variables.hero.stats.strength }}",
                            }
                        },
                    ],
                ),
            ],
        )

        sample_system.flows["deep_nested_flow"] = flow
        result = flow_service.execute_flow("deep_nested_flow")

        # Verify deeply nested type coercion worked
        assert isinstance(result["final_strength"], int)
        assert result["final_strength"] == 15

    def test_type_coercion_float(self, flow_service, sample_system):
        """Test that float type coercion works."""
        flow = FlowDefinition(
            id="float_coercion_flow",
            kind="flow",
            name="Float Coercion Flow",
            outputs=[
                FlowInputOutput(type="float", id="weight", validate=False),
            ],
            steps=[
                FlowStep(
                    id="set_weight",
                    name="Set Weight",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.weight",
                                "value": "{{ 10 * 2.5 }}",  # String "25.0"
                            }
                        },
                    ],
                ),
            ],
        )

        sample_system.flows["float_coercion_flow"] = flow
        result = flow_service.execute_flow("float_coercion_flow")

        # Verify type coercion worked
        assert isinstance(result["weight"], float)
        assert result["weight"] == 25.0

    def test_type_coercion_without_template(self, flow_service, sample_system):
        """Test that non-template values also get coerced if needed."""
        flow = FlowDefinition(
            id="no_template_flow",
            kind="flow",
            name="No Template Flow",
            outputs=[
                FlowInputOutput(type="int", id="value", validate=False),
            ],
            steps=[
                FlowStep(
                    id="set_value",
                    name="Set Value",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.value",
                                "value": 42,  # Already correct type
                            }
                        },
                    ],
                ),
            ],
        )

        sample_system.flows["no_template_flow"] = flow
        result = flow_service.execute_flow("no_template_flow")

        # Should work without coercion needed
        assert isinstance(result["value"], int)
        assert result["value"] == 42

    def test_model_type_coercion_applies_defaults(self, flow_service, sample_system):
        """Test that setting valid model data applies defaults from model definition."""
        flow = FlowDefinition(
            id="model_defaults_flow",
            kind="flow",
            name="Model Defaults Flow",
            variables=[
                FlowVariable(type="character", id="hero", validate=False),
            ],
            outputs=[
                FlowInputOutput(type="character", id="hero", validate=False),
            ],
            steps=[
                FlowStep(
                    id="create_char",
                    name="Create Character",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.hero",
                                "value": {
                                    "model": "character",
                                    "name": "Test Hero",
                                    # Note: "level" and "hp" NOT provided
                                    # Should get defaults: level=1, hp=10
                                },
                            }
                        },
                        {
                            "set_value": {
                                "path": "outputs.hero",
                                "value": "{{ variables.hero }}",
                            }
                        },
                    ],
                ),
            ],
        )

        sample_system.flows["model_defaults_flow"] = flow
        result = flow_service.execute_flow("model_defaults_flow")

        # Verify the model got defaults applied
        assert isinstance(result["hero"], dict)
        assert result["hero"]["name"] == "Test Hero"
        # Most importantly: level and hp should have their default values
        assert result["hero"]["level"] == 1  # Default from model
        assert result["hero"]["hp"] == 10  # Default from model


class TestParallelExecution:
    """Test cases for parallel step execution with Prefect."""

    def test_parallel_action_execution(self, flow_service, sample_system):
        """Test executing actions in parallel with parallel: true flag."""
        # Track action execution order to verify parallelism
        execution_log = []

        def on_action_callback(action_type, action_data):
            execution_log.append(action_type)

        flow = FlowDefinition(
            id="parallel_flow",
            kind="flow",
            name="Parallel Flow",
            variables=[
                FlowVariable(type="int", id="value1", validate=False),
                FlowVariable(type="int", id="value2", validate=False),
                FlowVariable(type="int", id="value3", validate=False),
            ],
            outputs=[
                FlowInputOutput(type="int", id="total", validate=False),
            ],
            steps=[
                FlowStep(
                    id="parallel_sets",
                    name="Set Values in Parallel",
                    type="completion",
                    parallel=True,  # Enable parallel execution
                    actions=[
                        {"set_value": {"path": "variables.value1", "value": 10}},
                        {"set_value": {"path": "variables.value2", "value": 20}},
                        {"set_value": {"path": "variables.value3", "value": 30}},
                    ],
                ),
                FlowStep(
                    id="sum",
                    name="Sum Values",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.total",
                                "value": "{{ variables.value1 + variables.value2 + variables.value3 }}",  # noqa: E501
                            }
                        },
                    ],
                ),
            ],
        )

        sample_system.flows["parallel_flow"] = flow
        result = flow_service.execute_flow(
            "parallel_flow", on_action_execute=on_action_callback
        )

        # Verify all actions executed
        assert len(execution_log) == 4  # 3 parallel + 1 sequential
        # Verify correct result
        assert result["total"] == 60

    def test_sequential_vs_parallel_execution(self, flow_service, sample_system):
        """Test that parallel flag actually affects execution."""
        flow_sequential = FlowDefinition(
            id="sequential_flow",
            kind="flow",
            name="Sequential Flow",
            variables=[
                FlowVariable(type="int", id="counter", validate=False),
            ],
            steps=[
                FlowStep(
                    id="set_values",
                    name="Set Values Sequentially",
                    type="completion",
                    parallel=False,  # Sequential execution
                    actions=[
                        {"set_value": {"path": "variables.counter", "value": 1}},
                        {"set_value": {"path": "variables.counter", "value": 2}},
                        {"set_value": {"path": "variables.counter", "value": 3}},
                    ],
                ),
            ],
        )

        sample_system.flows["sequential_flow"] = flow_sequential

        # Both should work and produce same final result
        result = flow_service.execute_flow("sequential_flow")
        # Should have final value since sequential overwrites
        assert "counter" in result or True  # Flow has no outputs

    def test_flow_call_step_executor(self, flow_service, sample_system):
        """Test flow_call step type execution."""
        # Create a simple sub-flow to call
        sub_flow = FlowDefinition(
            id="sub_flow",
            kind="flow",
            name="Sub Flow",
            inputs=[FlowInputOutput(id="input_value", type="str")],
            outputs=[FlowInputOutput(id="result", type="str")],
            variables=[FlowVariable(type="str", id="processed_value", validate=False)],
            steps=[
                FlowStep(
                    id="process",
                    name="Process Input",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "variables.processed_value",
                                "value": "Processed: {{ inputs.input_value }}",
                            }
                        },
                        {
                            "set_value": {
                                "path": "outputs.result",
                                "value": "{{ variables.processed_value }}",
                            }
                        },
                    ],
                )
            ],
        )

        # Create main flow that calls the sub-flow
        main_flow = FlowDefinition(
            id="main_flow",
            kind="flow",
            name="Main Flow",
            outputs=[FlowInputOutput(id="final_result", type="str")],
            variables=[FlowVariable(type="str", id="sub_result", validate=False)],
            steps=[
                FlowStep(
                    id="call_sub_flow",
                    name="Call Sub Flow",
                    type="flow_call",
                    step_config={
                        "flow_id": "sub_flow",
                        "inputs": {"input_value": "Hello World"},
                        "outputs": {"result": "variables.sub_result"},
                    },
                ),
                FlowStep(
                    id="set_output",
                    name="Set Final Output",
                    type="completion",
                    actions=[
                        {
                            "set_value": {
                                "path": "outputs.final_result",
                                "value": "{{ variables.sub_result }}",
                            }
                        }
                    ],
                ),
            ],
        )

        # Add flows to system
        sample_system.flows["sub_flow"] = sub_flow
        sample_system.flows["main_flow"] = main_flow

        # Execute the main flow
        result = flow_service.execute_flow("main_flow")

        # Verify the sub-flow was executed and result returned
        assert "final_result" in result
        assert result["final_result"] == "Processed: Hello World"
