"""Test prompt field validation fix.

This module tests that the validator correctly handles the 'prompt' field in flow steps
as display text rather than incorrectly treating it as a reference to a prompt component.
"""

from grimoire_studio.core.validator import YamlValidator


class TestPromptFieldValidation:
    """Test cases for prompt field validation fix."""

    def test_prompt_field_is_not_treated_as_reference(self):
        """Test that prompt field in flow steps is treated as display text, not as a reference."""
        validator = YamlValidator()

        # Test flow with prompt field containing display text
        test_flow = {
            "id": "test_flow",
            "kind": "flow",
            "name": "Test Flow",
            "steps": [
                {
                    "id": "input_step",
                    "type": "player_input",
                    "prompt": "What is your character's name?",  # This should NOT cause validation error
                },
                {
                    "id": "choice_step",
                    "type": "player_choice",
                    "prompt": "Choose your starting weapon:",  # This should NOT cause validation error
                },
                {
                    "id": "roll_step",
                    "type": "dice_roll",
                    "prompt": "Rolling for damage...",  # This should NOT cause validation error
                    "roll": "2d6+3",
                },
            ],
        }

        # Validate the flow structure
        results = validator.validate_component_structure(test_flow)

        # Should have no validation errors related to prompt fields
        prompt_errors = [r for r in results if "prompt" in r.message.lower()]
        assert len(prompt_errors) == 0, (
            f"Found unexpected prompt validation errors: {[r.message for r in prompt_errors]}"
        )

        # Should have no errors at all for this valid flow
        errors = [r for r in results if r.is_error]
        assert len(errors) == 0, (
            f"Found unexpected validation errors: {[r.message for r in errors]}"
        )

    def test_prompt_id_references_are_still_validated(self):
        """Test that prompt_id references are still properly validated."""
        validator = YamlValidator()

        # Create a mock complete system without any prompt definitions
        class MockCompleteSystem:
            def __init__(self):
                self.prompts = {}  # No prompts defined
                self.flows = {"test_flow": MockFlow()}
                self.models = {}
                self.compendiums = {}
                self.tables = {}

        class MockFlow:
            def __init__(self):
                self.steps = [MockStep()]

        class MockStep:
            def __init__(self):
                self.id = "llm_step"
                self.prompt = (
                    "Generating description..."  # Display text - should NOT error
                )
                self.prompt_id = (
                    "character_description_prompt"  # Reference - should error
                )
                self.step_config = {
                    "prompt_id": "another_missing_prompt"  # Reference - should error
                }

        mock_system = MockCompleteSystem()
        results = []

        # Run prompt reference validation
        validator._validate_flow_prompt_references(mock_system, results)

        # Should find errors for prompt_id references but NOT for prompt field
        prompt_reference_errors = [
            r for r in results if "unknown prompt" in r.message.lower()
        ]
        assert len(prompt_reference_errors) == 2, (
            f"Expected 2 prompt reference errors, got {len(prompt_reference_errors)}"
        )

        # Verify error messages mention prompt_id, not prompt
        error_messages = [r.message for r in prompt_reference_errors]
        for message in error_messages:
            assert (
                "character_description_prompt" in message
                or "another_missing_prompt" in message
            )

    def test_flow_with_both_prompt_and_prompt_id_fields(self):
        """Test flow step with both prompt (display text) and prompt_id (reference) fields."""
        validator = YamlValidator()

        test_flow = {
            "id": "llm_flow",
            "kind": "flow",
            "name": "LLM Generation Flow",
            "steps": [
                {
                    "id": "generate_step",
                    "type": "llm_generation",
                    "prompt": "Generating your character description...",  # Display text - OK
                    "prompt_id": "character_description_template",  # Reference - would error if not found
                    "prompt_data": {"name": "{{ character.name }}"},
                }
            ],
        }

        # Structure validation should pass (doesn't check cross-references)
        results = validator.validate_component_structure(test_flow)

        # Should have no errors related to the prompt display text
        prompt_text_errors = [
            r
            for r in results
            if "prompt" in r.message.lower() and "display" in r.message.lower()
        ]
        assert len(prompt_text_errors) == 0

        # Should pass structure validation
        errors = [r for r in results if r.is_error]
        assert len(errors) == 0, (
            f"Structure validation failed: {[r.message for r in errors]}"
        )

    def test_various_prompt_text_formats(self):
        """Test that various formats of prompt text are accepted."""
        validator = YamlValidator()

        test_flows = [
            # Simple text
            {
                "id": "simple_flow",
                "kind": "flow",
                "name": "Simple Flow",
                "steps": [
                    {"id": "step1", "type": "player_input", "prompt": "Enter your name"}
                ],
            },
            # Multi-line text
            {
                "id": "multiline_flow",
                "kind": "flow",
                "name": "Multiline Flow",
                "steps": [
                    {
                        "id": "step1",
                        "type": "player_choice",
                        "prompt": "Choose one of the following options:\n1. Attack\n2. Defend\n3. Flee",
                    }
                ],
            },
            # Text with templating
            {
                "id": "template_flow",
                "kind": "flow",
                "name": "Template Flow",
                "steps": [
                    {
                        "id": "step1",
                        "type": "dice_roll",
                        "prompt": "Rolling {{ dice_expression }} for {{ character.name }}...",
                        "roll": "1d20",
                    }
                ],
            },
        ]

        for test_flow in test_flows:
            results = validator.validate_component_structure(test_flow)
            errors = [r for r in results if r.is_error]
            assert len(errors) == 0, (
                f"Flow {test_flow['id']} validation failed: {[r.message for r in errors]}"
            )

    def test_empty_or_none_prompt_values(self):
        """Test that empty or None prompt values don't cause issues."""
        validator = YamlValidator()

        test_flow = {
            "id": "optional_prompt_flow",
            "kind": "flow",
            "name": "Optional Prompt Flow",
            "steps": [
                {
                    "id": "step_with_prompt",
                    "type": "dice_roll",
                    "prompt": "Rolling dice...",
                    "roll": "1d6",
                },
                {
                    "id": "step_without_prompt",
                    "type": "dice_roll",
                    # No prompt field
                    "roll": "1d6",
                },
                {
                    "id": "step_with_empty_prompt",
                    "type": "dice_roll",
                    "prompt": "",  # Empty string
                    "roll": "1d6",
                },
            ],
        }

        results = validator.validate_component_structure(test_flow)
        errors = [r for r in results if r.is_error]
        assert len(errors) == 0, (
            f"Validation failed for optional/empty prompts: {[r.message for r in errors]}"
        )
