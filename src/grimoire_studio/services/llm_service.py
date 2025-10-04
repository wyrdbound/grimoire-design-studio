"""LLM service for GRIMOIRE flows.

This module provides the LLMService class which integrates with LangChain
to handle LLM prompt execution operations in GRIMOIRE flows.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

from grimoire_logging import get_logger

logger = get_logger(__name__)


class LLMConfig:
    """Configuration for LLM service.

    Attributes:
        provider: LLM provider ("ollama", "openai", "mock")
        model: Model name (e.g., "llama2", "gpt-4")
        temperature: Temperature for generation (0.0-2.0)
        max_tokens: Maximum tokens to generate
        api_key: API key for provider (if needed)
        base_url: Base URL for provider (if needed)
    """

    def __init__(
        self,
        provider: str = "mock",
        model: str = "mock-model",
        temperature: float = 0.7,
        max_tokens: int = 500,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initialize LLM configuration.

        Args:
            provider: LLM provider name
            model: Model name
            temperature: Generation temperature
            max_tokens: Maximum tokens
            api_key: API key (optional)
            base_url: Base URL (optional)
        """
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key
        self.base_url = base_url

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key": "***" if self.api_key else None,
            "base_url": self.base_url,
        }


class LLMResult:
    """Result of an LLM prompt execution.

    Attributes:
        prompt: Original prompt text
        response: Generated response text
        provider: Provider used
        model: Model used
        tokens_used: Number of tokens used (if available)
        metadata: Additional metadata
    """

    def __init__(
        self,
        prompt: str,
        response: str,
        provider: str,
        model: str,
        tokens_used: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize LLM result.

        Args:
            prompt: Original prompt
            response: Generated response
            provider: Provider used
            model: Model used
            tokens_used: Tokens used (optional)
            metadata: Additional metadata (optional)
        """
        self.prompt = prompt
        self.response = response
        self.provider = provider
        self.model = model
        self.tokens_used = tokens_used
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "prompt": self.prompt,
            "response": self.response,
            "provider": self.provider,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation.

        Returns:
            Human-readable result string
        """
        return f"LLMResult(provider={self.provider}, model={self.model}, response_length={len(self.response)})"


class LLMService:
    """Service for LLM prompt execution.

    This service integrates with LangChain to provide LLM functionality
    for GRIMOIRE flows. It supports multiple providers (Ollama, OpenAI, etc.)
    and includes variable substitution in prompts.

    Example:
        >>> config = LLMConfig(provider="mock", model="mock-model")
        >>> service = LLMService(config)
        >>> result = service.execute_prompt("Generate a fantasy item name")
        >>> print(result.response)
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        """Initialize the LLM service.

        Args:
            config: LLM configuration (defaults to mock provider)
        """
        self.config = config or LLMConfig()
        logger.info(
            f"LLMService initialized with provider: {self.config.provider}, "
            f"model: {self.config.model}"
        )

    def execute_prompt(
        self, prompt: str, variables: dict[str, Any] | None = None
    ) -> LLMResult:
        """Execute an LLM prompt with variable substitution.

        Args:
            prompt: Prompt text (may contain {variable} placeholders)
            variables: Dictionary of variables for substitution

        Returns:
            LLMResult containing response and metadata

        Raises:
            ValueError: If prompt is empty or variables are invalid
            RuntimeError: If LLM execution fails

        Example:
            >>> result = service.execute_prompt(
            ...     "Generate a {item_type} for level {level}",
            ...     {"item_type": "sword", "level": 5}
            ... )
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        prompt = prompt.strip()
        variables = variables or {}

        # Substitute variables in prompt
        substituted_prompt = self._substitute_variables(prompt, variables)

        logger.debug(f"Executing prompt: {substituted_prompt[:100]}...")

        try:
            # Execute based on provider
            if self.config.provider == "mock":
                response = self._execute_mock(substituted_prompt)
            elif self.config.provider == "ollama":
                response = self._execute_ollama(substituted_prompt)
            elif self.config.provider == "openai":
                response = self._execute_openai(substituted_prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.config.provider}")

            result = LLMResult(
                prompt=substituted_prompt,
                response=response,
                provider=self.config.provider,
                model=self.config.model,
            )

            logger.info(f"LLM execution successful: {len(response)} chars generated")
            return result

        except Exception as e:
            error_msg = f"LLM execution failed: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _substitute_variables(self, prompt: str, variables: dict[str, Any]) -> str:
        """Substitute variables in prompt.

        Args:
            prompt: Prompt with {variable} placeholders
            variables: Variable values

        Returns:
            Prompt with variables substituted
        """
        try:
            return prompt.format(**variables)
        except KeyError as e:
            logger.warning(f"Variable not found in prompt: {e}")
            # Return original prompt if substitution fails
            return prompt

    def _execute_mock(self, prompt: str) -> str:
        """Execute mock LLM (for testing).

        Args:
            prompt: Prompt text

        Returns:
            Mock response
        """
        # Generate a deterministic mock response based on prompt
        word_count = len(prompt.split())
        return (
            f"[MOCK RESPONSE] This is a mock LLM response. "
            f"The prompt contained {word_count} words. "
            f"In a real implementation, this would be generated by {self.config.model}."
        )

    def _execute_ollama(self, prompt: str) -> str:
        """Execute Ollama LLM.

        Args:
            prompt: Prompt text

        Returns:
            Ollama response

        Raises:
            RuntimeError: If Ollama execution fails
        """
        import json

        try:
            # Prepare request to Ollama API
            base_url = self.config.base_url or "http://localhost:11434"
            url = f"{base_url}/api/generate"

            data = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                },
            }

            # Make request to Ollama
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=30) as response:  # nosec B310
                result = json.loads(response.read().decode("utf-8"))
                response_text: str = result.get("response", "")
                return response_text

        except Exception as e:
            error_msg = f"Ollama execution failed: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    @staticmethod
    def is_ollama_available(base_url: str = "http://localhost:11434") -> bool:
        """Check if Ollama is available.

        Args:
            base_url: Ollama base URL

        Returns:
            True if Ollama is running and accessible
        """
        try:
            req = urllib.request.Request(f"{base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as response:  # nosec B310
                is_available: bool = response.status == 200
                return is_available
        except (urllib.error.URLError, TimeoutError):
            return False

    def _execute_openai(self, prompt: str) -> str:
        """Execute OpenAI LLM.

        Args:
            prompt: Prompt text

        Returns:
            OpenAI response

        Raises:
            NotImplementedError: OpenAI not yet integrated
        """
        # Placeholder for OpenAI integration
        raise NotImplementedError(
            "OpenAI integration not yet implemented. Use provider='mock' for testing."
        )

    def get_config(self) -> LLMConfig:
        """Get current LLM configuration.

        Returns:
            Current configuration
        """
        return self.config

    def set_config(self, config: LLMConfig) -> None:
        """Update LLM configuration.

        Args:
            config: New configuration
        """
        logger.info(
            f"Updating LLM config: provider={config.provider}, model={config.model}"
        )
        self.config = config
