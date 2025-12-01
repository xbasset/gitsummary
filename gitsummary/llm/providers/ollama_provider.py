"""Ollama local LLM provider implementation (placeholder).

This module provides a placeholder for the Ollama provider,
which enables running local LLM models without cloud API calls.

Requires:
- ollama Python package (pip install ollama)
- Ollama service running locally (https://ollama.ai)
- A compatible model pulled (e.g., ollama pull llama3.2)

Features (planned):
- Local execution with no API keys
- Support for structured outputs via JSON mode
- Compatible with llama3, mistral, codellama, etc.
"""

from __future__ import annotations

import os
from typing import Optional, Type, TypeVar

from pydantic import BaseModel

from ..base import (
    BaseLLMProvider,
    LLMResponse,
    ProviderConfig,
    ProviderNotAvailableError,
)

# Check for Ollama availability
try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None  # type: ignore


T = TypeVar("T", bound=BaseModel)


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider (placeholder implementation).

    This provider enables using locally-running Ollama models
    for commit analysis without requiring cloud API access.

    Note: This is a placeholder for future implementation.

    Example:
        >>> provider = OllamaProvider(ProviderConfig(model="llama3.2"))
        >>> response = provider.extract_structured(prompt, MySchema)
    """

    name = "ollama"
    display_name = "Ollama (Local)"
    default_model = "llama3.2"  # Good balance of capability and speed

    # Recommended models for code analysis
    RECOMMENDED_MODELS = [
        "llama3.2",  # Latest Llama 3.2
        "codellama",  # Specialized for code
        "mistral",  # Good general performance
        "deepseek-coder",  # Code-focused
    ]

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        """Initialize the Ollama provider.

        Args:
            config: Provider configuration with model settings.
                   No API key needed for local Ollama.

        Raises:
            ProviderNotAvailableError: If ollama package is not installed.
        """
        if not OLLAMA_AVAILABLE:
            raise ProviderNotAvailableError(
                "Ollama provider requires the 'ollama' package. "
                "Install it with: pip install ollama\n"
                "Also ensure the Ollama service is running: https://ollama.ai"
            )

        super().__init__(config)

    def _validate_config(self) -> None:
        """Validate Ollama-specific configuration."""
        # Ollama doesn't require an API key for local models
        pass

    @classmethod
    def is_available(cls) -> bool:
        """Check if Ollama provider is available.

        Returns True if:
        - ollama package is installed
        - Ollama service appears to be running (optional check)
        """
        if not OLLAMA_AVAILABLE:
            return False

        # Check if explicitly enabled
        if os.environ.get("GITSUMMARY_OLLAMA_ENABLED", "").lower() == "true":
            return True

        # Try to connect to Ollama service
        try:
            import ollama

            # Quick check if service is reachable
            ollama.list()
            return True
        except Exception:
            return False

    def extract_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Extract structured data using a local Ollama model.

        Note: This is a placeholder implementation.

        Args:
            prompt: The user prompt with content to analyze.
            schema: Pydantic model class for the expected output.
            system_prompt: Optional system prompt for context.

        Returns:
            LLMResponse with parsed data or error information.

        Raises:
            NotImplementedError: This provider is not yet implemented.
        """
        # TODO: Implement Ollama structured output extraction
        # Ollama supports JSON mode for structured outputs
        raise NotImplementedError(
            "Ollama provider is not yet implemented. "
            "Please use 'openai' provider for now, or contribute an implementation!\n"
            "See: https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion"
        )



