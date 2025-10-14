"""Conditional branch step executor."""

from __future__ import annotations

from typing import Any, Callable

from grimoire_context import GrimoireContext
from grimoire_logging import get_logger
from prefect import task

from ...models.grimoire_definitions import FlowStep
from ..decorators import handle_execution_error
from ..exceptions import FlowExecutionError

logger = get_logger(__name__)


class ConditionalBranchStepExecutor:
    """Executor for conditional_branch steps."""

    def __init__(
        self,
        template_resolver: Callable[[str, GrimoireContext], Any],
        action_executor: Callable[
            [
                dict[str, Any],
                GrimoireContext,
                Callable[[str, dict[str, Any]], None] | None,
            ],
            GrimoireContext,
        ],
    ) -> None:
        """Initialize the conditional branch step executor.

        Args:
            template_resolver: Function to resolve template expressions
            action_executor: Function to execute actions from the flow service
        """
        self.template_resolver = template_resolver
        self.action_executor = action_executor

    @task(
        name="conditional_branch_step",
        task_run_name="branch_{step.id}",
        persist_result=False,
        retries=0,  # Don't retry conditional logic
        log_prints=False,
    )
    @handle_execution_error("Conditional branch")
    def execute(
        self,
        step: FlowStep,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None = None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> GrimoireContext:
        """Execute a conditional_branch step.

        Args:
            step: Step to execute
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Optional callback for user input
            on_action_execute: Optional callback when actions execute

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If conditional logic fails or template resolution fails
        """
        logger.debug(f"Executing conditional branch step: {step.id}")

        # Get conditional structure from step_config
        if_condition = step.step_config.get("if")
        then_actions = step.step_config.get("then", [])
        else_clause = step.step_config.get("else")

        if not if_condition:
            raise FlowExecutionError(
                f"conditional_branch step '{step.id}' missing 'if' condition"
            )

        # Execute the conditional logic
        context = self._evaluate_conditional(
            if_condition,
            then_actions,
            else_clause,
            context,
            step_namespace,
            on_user_input,
            on_action_execute,
        )

        # Execute any additional actions defined in the main step
        if step.actions:
            logger.debug(f"Executing main actions for step: {step.id}")
            context = self._execute_actions(step.actions, context, on_action_execute)

        logger.debug(f"Conditional branch step completed: {step.id}")
        return context

    def _execute_actions(
        self,
        actions: list[dict[str, Any]],
        context: GrimoireContext,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
    ) -> GrimoireContext:
        """Execute a list of actions sequentially.

        Args:
            actions: List of actions to execute
            context: Current execution context
            on_action_execute: Optional callback when action executes

        Returns:
            Updated context after all actions execute
        """
        for action in actions:
            context = self.action_executor(action, context, on_action_execute)
        return context

    def _evaluate_conditional(
        self,
        if_condition: str,
        then_actions: list[dict[str, Any]],
        else_clause: Any,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
    ) -> GrimoireContext:
        """Evaluate a conditional statement and execute appropriate branch.

        Args:
            if_condition: Template expression to evaluate
            then_actions: Actions to execute if condition is true
            else_clause: Either actions list or nested conditional structure
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Optional callback for user input
            on_action_execute: Optional callback when actions execute

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If condition evaluation or action execution fails
        """
        try:
            # Resolve the condition template
            condition_result = self.template_resolver(if_condition, context)
            logger.debug(f"Condition '{if_condition}' evaluated to: {condition_result}")

            # Convert to boolean (handle various truthy/falsy values)
            is_true = bool(condition_result)

            if is_true:
                # Execute then actions
                if then_actions:
                    logger.debug("Executing 'then' branch")
                    context = self._execute_actions(
                        then_actions, context, on_action_execute
                    )
            else:
                # Handle else clause
                if else_clause is not None:
                    logger.debug("Executing 'else' branch")
                    context = self._handle_else_clause(
                        else_clause,
                        context,
                        step_namespace,
                        on_user_input,
                        on_action_execute,
                    )

            return context

        except Exception as e:
            raise FlowExecutionError(
                f"Failed to evaluate conditional '{if_condition}': {e}"
            ) from e

    def _handle_else_clause(
        self,
        else_clause: Any,
        context: GrimoireContext,
        step_namespace: str,
        on_user_input: Callable[[FlowStep, dict[str, Any]], Any] | None,
        on_action_execute: Callable[[str, dict[str, Any]], None] | None,
    ) -> GrimoireContext:
        """Handle the else clause which can be actions or nested conditional.

        Args:
            else_clause: Either list of actions or dict with nested if-then-else
            context: Current execution context
            step_namespace: Unique namespace for this step's data
            on_user_input: Optional callback for user input
            on_action_execute: Optional callback when actions execute

        Returns:
            Updated context

        Raises:
            FlowExecutionError: If else clause processing fails
        """
        if isinstance(else_clause, list):
            # Direct actions list
            context = self._execute_actions(else_clause, context, on_action_execute)
        elif isinstance(else_clause, dict):
            # Check if it's a nested conditional
            if "if" in else_clause:
                # Nested conditional - recurse
                nested_if = else_clause.get("if")
                if not nested_if:
                    raise FlowExecutionError(
                        "Nested conditional missing 'if' condition"
                    )

                nested_then = else_clause.get("then", [])
                nested_else = else_clause.get("else")

                context = self._evaluate_conditional(
                    nested_if,
                    nested_then,
                    nested_else,
                    context,
                    step_namespace,
                    on_user_input,
                    on_action_execute,
                )
            else:
                raise FlowExecutionError(
                    f"Invalid else clause structure: {type(else_clause)}. "
                    "Expected list of actions or dict with 'if' key."
                )
        else:
            raise FlowExecutionError(
                f"Invalid else clause type: {type(else_clause)}. "
                "Expected list of actions or dict with nested conditional."
            )

        return context
