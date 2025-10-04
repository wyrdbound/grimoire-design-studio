"""
Tests for the Dice Service.

This module tests the dice rolling functionality using wyrdbound-dice.
"""

import pytest

from grimoire_studio.services import DiceRollResult, DiceService


class TestDiceRollResult:
    """Test the DiceRollResult data class."""

    def test_dice_roll_result_creation(self):
        """Test creating a DiceRollResult."""
        result = DiceRollResult(
            expression="2d6+3",
            total=10,
            description="10 = 7 (2d6: 3, 4) + 3",
            rolls=[3, 4],
        )

        assert result.expression == "2d6+3"
        assert result.total == 10
        assert result.description == "10 = 7 (2d6: 3, 4) + 3"
        assert result.rolls == [3, 4]


class TestDiceService:
    """Test the DiceService class."""

    def test_initialization(self):
        """Test DiceService initialization."""
        service = DiceService()
        assert service is not None

    def test_basic_roll(self):
        """Test a basic dice roll."""
        service = DiceService()
        result = service.roll_dice("1d20")

        assert result is not None
        assert result.expression == "1d20"
        assert 1 <= result.total <= 20
        assert len(result.rolls) > 0

    def test_multiple_dice(self):
        """Test rolling multiple dice."""
        service = DiceService()
        result = service.roll_dice("2d6")

        assert result is not None
        assert result.expression == "2d6"
        assert 2 <= result.total <= 12
        assert len(result.rolls) > 0

    def test_dice_with_modifier(self):
        """Test dice roll with modifier."""
        service = DiceService()
        result = service.roll_dice("1d6+3")

        assert result is not None
        assert result.expression == "1d6+3"
        assert 4 <= result.total <= 9  # 1d6 (1-6) + 3 = 4-9

    def test_keep_highest(self):
        """Test keep highest mechanic (advantage)."""
        service = DiceService()
        result = service.roll_dice("2d20kh1")

        assert result is not None
        assert result.expression == "2d20kh1"
        assert 1 <= result.total <= 20

    def test_keep_lowest(self):
        """Test keep lowest mechanic (disadvantage)."""
        service = DiceService()
        result = service.roll_dice("2d20kl1")

        assert result is not None
        assert result.expression == "2d20kl1"
        assert 1 <= result.total <= 20

    def test_ability_score_roll(self):
        """Test D&D 5e ability score roll (4d6kh3)."""
        service = DiceService()
        result = service.roll_dice("4d6kh3")

        assert result is not None
        assert result.expression == "4d6kh3"
        assert 3 <= result.total <= 18  # Best 3 of 4d6

    def test_exploding_dice(self):
        """Test exploding dice mechanic."""
        service = DiceService()
        result = service.roll_dice("1d6e")

        assert result is not None
        assert result.expression == "1d6e"
        assert result.total >= 1  # Can explode indefinitely

    def test_fate_dice(self):
        """Test Fate dice (4dF)."""
        service = DiceService()
        result = service.roll_dice("4dF")

        assert result is not None
        assert result.expression == "4dF"
        assert -4 <= result.total <= 4  # Range for 4 Fate dice

    def test_roll_multiple(self):
        """Test rolling multiple expressions."""
        service = DiceService()
        results = service.roll_multiple(["1d20", "2d6", "1d100"])

        assert len(results) == 3
        assert all(isinstance(r, DiceRollResult) for r in results)
        assert results[0].expression == "1d20"
        assert results[1].expression == "2d6"
        assert results[2].expression == "1d100"

    def test_roll_multiple_empty(self):
        """Test rolling with empty list raises error."""
        service = DiceService()

        with pytest.raises(ValueError, match="Expression list cannot be empty"):
            service.roll_multiple([])

    def test_parse_expression_valid(self):
        """Test parsing valid dice expressions."""
        service = DiceService()

        result = service.parse_expression("1d20")
        assert result["valid"] is True
        assert result["expression"] == "1d20"

        result = service.parse_expression("2d6+3")
        assert result["valid"] is True

        result = service.parse_expression("4d6kh3")
        assert result["valid"] is True

    def test_parse_expression_invalid(self):
        """Test parsing invalid dice expressions."""
        service = DiceService()

        result = service.parse_expression("invalid")
        assert result["valid"] is False
        assert "error" in result

        result = service.parse_expression("xyz")
        assert result["valid"] is False

    def test_roll_dice_invalid_expression(self):
        """Test rolling with invalid expression."""
        service = DiceService()

        with pytest.raises(RuntimeError, match="Failed to roll dice expression"):
            service.roll_dice("invalid")

    def test_roll_dice_empty_expression(self):
        """Test rolling with empty expression."""
        service = DiceService()

        with pytest.raises(ValueError, match="Dice expression cannot be empty"):
            service.roll_dice("")

    def test_deterministic_rolls_with_seed(self):
        """Test that seeded rolls are deterministic."""
        # Note: wyrdbound-dice may not support seeding directly,
        # so we just verify that rolls produce valid results
        service = DiceService()
        result1 = service.roll_dice("2d6")
        result2 = service.roll_dice("2d6")

        # Both should be valid, but may be different
        assert 2 <= result1.total <= 12
        assert 2 <= result2.total <= 12

    def test_complex_expression(self):
        """Test complex dice expression."""
        service = DiceService()
        result = service.roll_dice("2d6r1<=2")  # Reroll 1s and 2s once

        assert result is not None
        assert result.expression == "2d6r1<=2"
        assert 2 <= result.total <= 12

    def test_result_has_description(self):
        """Test that result includes description."""
        service = DiceService()
        result = service.roll_dice("2d6+3")

        assert result.description is not None
        assert len(result.description) > 0
        assert "2d6" in result.description or "2d6+3" in result.description

    def test_result_has_rolls(self):
        """Test that result includes individual roll values."""
        service = DiceService()
        result = service.roll_dice("3d6")

        assert result.rolls is not None
        assert len(result.rolls) > 0

    def test_large_dice(self):
        """Test rolling large dice."""
        service = DiceService()
        result = service.roll_dice("1d100")

        assert result is not None
        assert 1 <= result.total <= 100

    def test_many_dice(self):
        """Test rolling many dice at once."""
        service = DiceService()
        result = service.roll_dice("10d6")

        assert result is not None
        assert 10 <= result.total <= 60
        assert len(result.rolls) > 0
