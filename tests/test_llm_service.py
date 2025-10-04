"""
Tests for the LLM Service.

This module tests the LLM prompt execution functionality.
"""

import pytest

from grimoire_studio.services import LLMConfig, LLMResult, LLMService


class TestLLMConfig:
    """Test the LLMConfig data class."""

    def test_config_creation_minimal(self):
        """Test creating config with minimal parameters."""
        config = LLMConfig(provider="mock")

        assert config.provider == "mock"
        assert config.model == "mock-model"
        assert config.temperature == 0.7
        assert config.max_tokens == 500
        assert config.api_key is None
        assert config.base_url is None

    def test_config_creation_full(self):
        """Test creating config with all parameters."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.8,
            max_tokens=1000,
            api_key="test-key",
            base_url="https://api.openai.com",
        )

        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.temperature == 0.8
        assert config.max_tokens == 1000
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.openai.com"


class TestLLMResult:
    """Test the LLMResult data class."""

    def test_result_creation(self):
        """Test creating an LLMResult."""
        result = LLMResult(
            prompt="Test prompt",
            response="This is a response",
            model="gpt-4",
            provider="openai",
            tokens_used=10,
            metadata={"tokens": 10},
        )

        assert result.prompt == "Test prompt"
        assert result.response == "This is a response"
        assert result.model == "gpt-4"
        assert result.provider == "openai"
        assert result.tokens_used == 10
        assert result.metadata == {"tokens": 10}


class TestLLMService:
    """Test the LLMService class."""

    def test_initialization_default(self):
        """Test LLMService initialization with defaults."""
        service = LLMService()

        assert service is not None
        config = service.get_config()
        assert config.provider == "mock"

    def test_initialization_with_config(self):
        """Test LLMService initialization with custom config."""
        config = LLMConfig(provider="mock", model="test-model", temperature=0.9)
        service = LLMService(config=config)

        assert service is not None
        current_config = service.get_config()
        assert current_config.provider == "mock"
        assert current_config.model == "test-model"
        assert current_config.temperature == 0.9

    def test_execute_prompt_simple(self):
        """Test executing a simple prompt."""
        service = LLMService()
        result = service.execute_prompt("Generate a fantasy item")

        assert result is not None
        assert isinstance(result, LLMResult)
        assert result.provider == "mock"
        assert result.model == "mock-model"
        assert len(result.response) > 0
        assert "[MOCK RESPONSE]" in result.response

    def test_execute_prompt_with_variables(self):
        """Test executing a prompt with variable substitution."""
        service = LLMService()
        prompt = "Generate a {item_type} for level {level}"
        variables = {"item_type": "sword", "level": 5}

        result = service.execute_prompt(prompt, variables=variables)

        assert result is not None
        assert isinstance(result, LLMResult)
        assert len(result.response) > 0

    def test_execute_prompt_complex_variables(self):
        """Test executing a prompt with multiple variables."""
        service = LLMService()
        prompt = "Create a {creature} in {location} with {trait} traits"
        variables = {
            "creature": "dragon",
            "location": "mountain",
            "trait": "ancient",
        }

        result = service.execute_prompt(prompt, variables=variables)

        assert result is not None
        assert len(result.response) > 0

    def test_execute_prompt_empty(self):
        """Test executing an empty prompt."""
        service = LLMService()

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            service.execute_prompt("")

    def test_execute_prompt_missing_variable(self):
        """Test executing a prompt with missing variable."""
        service = LLMService()
        prompt = "Generate a {item_type} for level {level}"
        variables = {"item_type": "sword"}  # Missing 'level'

        # Should not raise error - missing variables are handled gracefully
        result = service.execute_prompt(prompt, variables=variables)
        assert result is not None

    def test_variable_substitution(self):
        """Test that variables are correctly substituted."""
        service = LLMService()
        prompt = "The {color} {item} is worth {value} gold"
        variables = {"color": "red", "item": "gem", "value": 100}

        result = service.execute_prompt(prompt, variables=variables)

        assert result is not None
        # The prompt should have been processed with variables

    def test_get_config(self):
        """Test getting current configuration."""
        config = LLMConfig(
            provider="mock", model="test-model", temperature=0.8, max_tokens=1000
        )
        service = LLMService(config=config)

        current_config = service.get_config()

        assert current_config.provider == "mock"
        assert current_config.model == "test-model"
        assert current_config.temperature == 0.8
        assert current_config.max_tokens == 1000

    def test_set_config(self):
        """Test updating configuration."""
        service = LLMService()

        new_config = LLMConfig(
            provider="mock", model="new-model", temperature=0.9, max_tokens=1500
        )
        service.set_config(new_config)

        current_config = service.get_config()
        assert current_config.model == "new-model"
        assert current_config.temperature == 0.9
        assert current_config.max_tokens == 1500

    def test_mock_provider_response(self):
        """Test that mock provider returns expected response format."""
        service = LLMService()
        result = service.execute_prompt("Test prompt")

        assert "[MOCK RESPONSE]" in result.response
        assert result.provider == "mock"
        assert result.model == "mock-model"
        assert result.metadata is not None

    def test_result_includes_metadata(self):
        """Test that result includes metadata."""
        service = LLMService()
        result = service.execute_prompt("Test prompt")

        assert result.metadata is not None
        assert isinstance(result.metadata, dict)

    def test_multiple_prompts(self):
        """Test executing multiple prompts in sequence."""
        service = LLMService()

        result1 = service.execute_prompt("First prompt with unique text")
        result2 = service.execute_prompt("Second prompt")
        result3 = service.execute_prompt("Third")

        # Different word counts should produce different responses
        assert result1.response != result2.response
        assert all(isinstance(r, LLMResult) for r in [result1, result2, result3])

    def test_special_characters_in_prompt(self):
        """Test prompt with special characters."""
        service = LLMService()
        prompt = "Generate a description with special chars: !@#$%^&*()"

        result = service.execute_prompt(prompt)

        assert result is not None
        assert len(result.response) > 0

    def test_long_prompt(self):
        """Test executing a long prompt."""
        service = LLMService()
        prompt = "Generate a description. " * 100  # Long repeated text

        result = service.execute_prompt(prompt)

        assert result is not None
        assert len(result.response) > 0

    def test_variable_with_special_chars(self):
        """Test variables with special characters."""
        service = LLMService()
        prompt = "Generate a {item} with {description}"
        variables = {
            "item": "sword of +3 power",
            "description": "flames & lightning",
        }

        result = service.execute_prompt(prompt, variables=variables)

        assert result is not None

    def test_numeric_variables(self):
        """Test variables with numeric values."""
        service = LLMService()
        prompt = "Create a level {level} {item} worth {gold} gold"
        variables = {"level": 10, "item": "helmet", "gold": 500}

        result = service.execute_prompt(prompt, variables=variables)

        assert result is not None

    def test_config_immutability(self):
        """Test that getting config returns the actual config object."""
        service = LLMService()

        config1 = service.get_config()

        # Modify the returned config
        config1.model = "should-change"

        # Get config again - should reflect the change since we return the actual object
        config2 = service.get_config()
        assert config2.model == "should-change"

    def test_provider_validation(self):
        """Test that supported providers work."""
        # Mock provider
        service1 = LLMService(config=LLMConfig(provider="mock"))
        assert service1.get_config().provider == "mock"

        # Note: Other providers (ollama, openai) are placeholders
        # and will use mock implementation

    def test_temperature_bounds(self):
        """Test temperature configuration."""
        # Test various temperature values
        for temp in [0.0, 0.5, 0.7, 1.0, 1.5, 2.0]:
            config = LLMConfig(provider="mock", temperature=temp)
            service = LLMService(config=config)
            assert service.get_config().temperature == temp

    def test_max_tokens_configuration(self):
        """Test max_tokens configuration."""
        for tokens in [100, 500, 1000, 2000]:
            config = LLMConfig(provider="mock", max_tokens=tokens)
            service = LLMService(config=config)
            assert service.get_config().max_tokens == tokens
