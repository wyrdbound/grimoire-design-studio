"""Unit tests for action handlers."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from grimoire_context import GrimoireContext

from grimoire_studio.services.action_handlers.display_message import (
    DisplayMessageActionHandler,
)
from grimoire_studio.services.action_handlers.display_value import (
    DisplayValueActionHandler,
)
from grimoire_studio.services.action_handlers.log_event import LogEventActionHandler
from grimoire_studio.services.action_handlers.log_message import (
    LogMessageActionHandler,
)
from grimoire_studio.services.action_handlers.set_value import SetValueActionHandler
from grimoire_studio.services.action_handlers.swap_values import (
    SwapValuesActionHandler,
)
from grimoire_studio.services.action_handlers.validate_value import (
    ValidateValueActionHandler,
)
from grimoire_studio.services.exceptions import FlowExecutionError


class MockTemplateResolver:
    """Mock template resolver for testing."""

    def resolve_template(self, template_str: str, context_dict: dict[str, Any]) -> Any:
        """Simple template resolver that replaces {{var}} with values from context."""
        result = template_str
        # Replace {{var}} patterns with values from context
        import re

        def replace_var(match: re.Match) -> str:
            var_name = match.group(1).strip()
            return str(context_dict.get(var_name, match.group(0)))

        result = re.sub(r"\{\{([^}]+)\}\}", replace_var, result)
        return result


class TestDisplayMessageActionHandler:
    """Tests for DisplayMessageActionHandler."""

    def test_execute_simple_message(self) -> None:
        """Test displaying a simple message."""
        # Arrange
        handler = DisplayMessageActionHandler()
        context = GrimoireContext(template_resolver=MockTemplateResolver())

        action_data = {"message": "Hello, World!"}

        # Mock callback
        mock_callback = Mock()

        # Act
        handler.execute(
            action_data=action_data,
            context=context,
            on_action_execute=mock_callback,
        )

        # Assert
        mock_callback.assert_called_once_with(
            "display_message", {"message": "Hello, World!"}
        )

    def test_execute_message_with_template(self) -> None:
        """Test displaying a message with template variables."""
        # Arrange
        handler = DisplayMessageActionHandler()
        context = GrimoireContext(template_resolver=MockTemplateResolver())
        context = context.set_variable("name", "Alice")

        action_data = {"message": "Hello, {{name}}!"}

        # Mock callback
        mock_callback = Mock()

        # Act
        handler.execute(
            action_data=action_data,
            context=context,
            on_action_execute=mock_callback,
        )

        # Assert
        mock_callback.assert_called_once_with(
            "display_message", {"message": "Hello, Alice!"}
        )

    def test_execute_string_message(self) -> None:
        """Test displaying a message passed as string instead of dict."""
        # Arrange
        handler = DisplayMessageActionHandler()
        context = GrimoireContext(template_resolver=MockTemplateResolver())

        action_data = "Direct string message"

        # Mock callback
        mock_callback = Mock()

        # Act
        handler.execute(
            action_data=action_data,
            context=context,
            on_action_execute=mock_callback,
        )

        # Assert
        mock_callback.assert_called_once_with(
            "display_message", {"message": "Direct string message"}
        )


class TestDisplayValueActionHandler:
    """Tests for DisplayValueActionHandler."""

    def test_execute_display_value(self) -> None:
        """Test displaying a value from context."""
        # Arrange
        handler = DisplayValueActionHandler()
        context = GrimoireContext(template_resolver=MockTemplateResolver())
        context = context.set_variable("character.name", "Gandalf")

        # Action data is just a string path
        action_data = "character.name"

        # Mock callback
        mock_callback = Mock()

        # Act
        handler.execute(
            action_data=action_data,
            context=context,
            on_action_execute=mock_callback,
        )

        # Assert
        mock_callback.assert_called_once_with(
            "display_value", {"message": "character.name: Gandalf"}
        )


class TestLogEventActionHandler:
    """Tests for LogEventActionHandler."""

    def test_execute_log_event(self) -> None:
        """Test logging an event."""

        # Arrange
        # Mock template dict resolver
        def mock_template_dict_resolver(
            template_dict: dict[str, Any],
            ctx: GrimoireContext,
        ) -> dict[str, Any]:
            return template_dict

        handler = LogEventActionHandler(
            template_dict_resolver=mock_template_dict_resolver
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())

        action_data = {"type": "character_created", "data": {"name": "Frodo"}}

        # Act
        handler.execute(
            action_data=action_data,
            context=context,
            on_action_execute=None,
        )

        # Assert - event is logged, no callback needed


class TestLogMessageActionHandler:
    """Tests for LogMessageActionHandler."""

    def test_execute_log_message(self) -> None:
        """Test logging a debug message."""
        # Arrange
        handler = LogMessageActionHandler()
        context = GrimoireContext(template_resolver=MockTemplateResolver())

        action_data = {"message": "Debug: Processing step"}

        # Act
        handler.execute(
            action_data=action_data,
            context=context,
            on_action_execute=None,
        )

        # Assert - message is logged, no callback needed


class TestSetValueActionHandler:
    """Tests for SetValueActionHandler."""

    def test_execute_set_simple_value(self) -> None:
        """Test setting a simple value."""

        # Arrange
        # Mock type getter and value coercer
        def mock_type_getter(path: str) -> str | None:
            return None

        def mock_value_coercer(value: Any, expected_type: str | None, path: str) -> Any:
            return value

        handler = SetValueActionHandler(
            type_getter=mock_type_getter,
            value_coercer=mock_value_coercer,
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())

        action_data = {"path": "character.level", "value": 5}

        # Act
        result_context = handler.execute(
            action_data=action_data,
            context=context,
            on_action_execute=None,
        )

        # Assert
        assert result_context.get_variable("character.level") == 5

    def test_execute_set_value_with_template(self) -> None:
        """Test setting a value with template resolution."""

        # Arrange
        def mock_type_getter(path: str) -> str | None:
            return None

        def mock_value_coercer(value: Any, expected_type: str | None, path: str) -> Any:
            return value

        handler = SetValueActionHandler(
            type_getter=mock_type_getter,
            value_coercer=mock_value_coercer,
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        context = context.set_variable("base_name", "Aragorn")

        action_data = {"path": "character.name", "value": "{{base_name}} the Ranger"}

        # Act
        result_context = handler.execute(
            action_data=action_data,
            context=context,
            on_action_execute=None,
        )

        # Assert
        assert result_context.get_variable("character.name") == "Aragorn the Ranger"

    def test_execute_set_value_missing_path(self) -> None:
        """Test error when path is missing."""

        # Arrange
        def mock_type_getter(path: str) -> str | None:
            return None

        def mock_value_coercer(value: Any, expected_type: str | None, path: str) -> Any:
            return value

        handler = SetValueActionHandler(
            type_getter=mock_type_getter,
            value_coercer=mock_value_coercer,
        )

        context = GrimoireContext(template_resolver=MockTemplateResolver())

        action_data = {"value": 42}  # Missing path

        # Act & Assert
        with pytest.raises(FlowExecutionError, match="requires 'path' field"):
            handler.execute(
                action_data=action_data,
                context=context,
                on_action_execute=None,
            )


class TestSwapValuesActionHandler:
    """Tests for SwapValuesActionHandler."""

    def test_execute_swap_values(self) -> None:
        """Test swapping two values."""
        # Arrange
        handler = SwapValuesActionHandler()
        context = GrimoireContext(template_resolver=MockTemplateResolver())
        context = context.set_variable("a", 10)
        context = context.set_variable("b", 20)

        action_data = {"path1": "a", "path2": "b"}

        # Act
        result_context = handler.execute(
            action_data=action_data,
            context=context,
            on_action_execute=None,
        )

        # Assert
        assert result_context.get_variable("a") == 20
        assert result_context.get_variable("b") == 10

    def test_execute_swap_values_missing_paths(self) -> None:
        """Test error when paths are missing."""
        # Arrange
        handler = SwapValuesActionHandler()
        context = GrimoireContext(template_resolver=MockTemplateResolver())

        action_data = {"path1": "a"}  # Missing path2

        # Act & Assert
        with pytest.raises(FlowExecutionError, match="both 'path1' and 'path2' fields"):
            handler.execute(
                action_data=action_data,
                context=context,
                on_action_execute=None,
            )


class TestValidateValueActionHandler:
    """Tests for ValidateValueActionHandler."""

    def test_execute_validate_value_success(self) -> None:
        """Test validating a value that passes."""
        # Arrange
        from grimoire_studio.services.object_service import ObjectInstantiationService

        mock_object_service = Mock(spec=ObjectInstantiationService)
        mock_object_service.create_object.return_value = None  # Validation passes

        handler = ValidateValueActionHandler(object_service=mock_object_service)

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        context = context.set_variable(
            "character",
            {
                "model": "character",
                "name": "Frodo",
                "level": 5,
            },
        )

        # Action data is just a string path
        action_data = "character"

        # Act
        handler.execute(
            action_data=action_data,
            context=context,
            on_action_execute=None,
        )

        # Assert - validation called with the object data
        mock_object_service.create_object.assert_called_once()

    def test_execute_validate_value_failure(self) -> None:
        """Test validating a value that fails."""
        # Arrange
        from grimoire_studio.services.object_service import ObjectInstantiationService

        mock_object_service = Mock(spec=ObjectInstantiationService)
        mock_object_service.create_object.side_effect = FlowExecutionError(
            "Invalid data"
        )

        handler = ValidateValueActionHandler(object_service=mock_object_service)

        context = GrimoireContext(template_resolver=MockTemplateResolver())
        context = context.set_variable(
            "character",
            {
                "model": "character",
                "name": "Frodo",
            },
        )

        # Action data is just a string path
        action_data = "character"

        # Act & Assert
        with pytest.raises(FlowExecutionError, match="Invalid data"):
            handler.execute(
                action_data=action_data,
                context=context,
                on_action_execute=None,
            )
