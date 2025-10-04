"""Dice rolling service for GRIMOIRE flows.

This module provides the DiceService class which integrates with wyrdbound-dice
to handle dice rolling operations in GRIMOIRE flows.
"""

from __future__ import annotations

from typing import Any

from grimoire_logging import get_logger
from wyrdbound_dice import Dice

logger = get_logger(__name__)


class DiceRollResult:
    """Result of a dice roll operation.

    Attributes:
        expression: The original dice expression string
        total: Total result of the roll
        description: Full description from wyrdbound-dice
        rolls: Individual die roll results (if available)
    """

    def __init__(
        self,
        expression: str,
        total: int,
        description: str,
        rolls: list[int] | None = None,
    ) -> None:
        """Initialize dice roll result.

        Args:
            expression: Original dice expression
            total: Total result
            description: Detailed description from wyrdbound-dice
            rolls: Individual die results (optional)
        """
        self.expression = expression
        self.total = total
        self.description = description
        self.rolls = rolls or []

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary.

        Returns:
            Dictionary representation of the roll result
        """
        return {
            "expression": self.expression,
            "total": self.total,
            "description": self.description,
            "rolls": self.rolls,
        }

    def __str__(self) -> str:
        """String representation of result.

        Returns:
            Human-readable result string
        """
        return self.description

    def __repr__(self) -> str:
        """Detailed string representation.

        Returns:
            Detailed result string
        """
        return f"DiceRollResult(expression='{self.expression}', total={self.total})"


class DiceService:
    """Service for dice rolling operations.

    This service integrates with wyrdbound-dice to provide dice rolling
    functionality for GRIMOIRE flows. It supports standard dice notation
    (e.g., "2d6+3", "1d20") and provides detailed roll results.

    Example:
        >>> service = DiceService()
        >>> result = service.roll_dice("2d6+3")
        >>> print(f"Total: {result.total}")
        >>> print(f"Rolls: {result.rolls}")
    """

    def __init__(self) -> None:
        """Initialize the dice service."""
        logger.info("DiceService initialized")

    def roll_dice(self, expression: str) -> DiceRollResult:
        """Roll dice using a dice expression.

        Args:
            expression: Dice expression (e.g., "2d6+3", "1d20", "4d6kh3")

        Returns:
            DiceRollResult containing total and detailed breakdown

        Raises:
            ValueError: If expression is invalid or empty
            RuntimeError: If dice rolling fails

        Example:
            >>> result = service.roll_dice("2d6+3")
            >>> print(result.total)
            9
        """
        if not expression:
            raise ValueError("Dice expression cannot be empty")

        expression = expression.strip()
        logger.debug(f"Rolling dice: {expression}")

        try:
            # Use wyrdbound-dice to roll
            result_set = Dice.roll(expression)

            # Extract result details
            total = result_set.total
            description = str(result_set)

            # Try to extract individual rolls if available
            rolls = []
            if hasattr(result_set, "results") and result_set.results:
                for roll_result in result_set.results:
                    if hasattr(roll_result, "rolls"):
                        rolls.extend(roll_result.rolls)

            roll_result = DiceRollResult(
                expression=expression,
                total=total,
                description=description,
                rolls=rolls,
            )

            logger.info(f"Dice roll result: {roll_result.total}")
            return roll_result

        except Exception as e:
            error_msg = f"Failed to roll dice expression '{expression}': {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def roll_multiple(self, expressions: list[str]) -> list[DiceRollResult]:
        """Roll multiple dice expressions.

        Args:
            expressions: List of dice expressions to roll

        Returns:
            List of DiceRollResult objects

        Raises:
            ValueError: If any expression is invalid
            RuntimeError: If any dice roll fails

        Example:
            >>> results = service.roll_multiple(["2d6", "1d20", "3d6+5"])
            >>> for result in results:
            ...     print(f"{result.notation}: {result.total}")
        """
        if not expressions:
            raise ValueError("Expression list cannot be empty")

        logger.debug(f"Rolling {len(expressions)} dice expressions")
        results = []

        for expr in expressions:
            result = self.roll_dice(expr)
            results.append(result)

        logger.info(f"Rolled {len(results)} dice expressions successfully")
        return results

    def parse_expression(self, expression: str) -> dict[str, Any]:
        """Parse a dice expression without rolling.

        Args:
            expression: Dice expression to parse

        Returns:
            Dictionary with expression components

        Raises:
            ValueError: If expression is invalid

        Example:
            >>> info = service.parse_expression("2d6+3")
            >>> print(info)
            {'expression': '2d6+3', 'valid': True}
        """
        if not expression:
            raise ValueError("Dice expression cannot be empty")

        expression = expression.strip()
        logger.debug(f"Parsing dice expression: {expression}")

        try:
            # Try to roll the expression to validate it
            # wyrdbound-dice doesn't have a separate parse method
            Dice.roll(expression)

            return {
                "expression": expression,
                "valid": True,
            }

        except Exception as e:
            logger.warning(f"Invalid dice expression '{expression}': {e}")
            return {
                "expression": expression,
                "valid": False,
                "error": str(e),
            }
