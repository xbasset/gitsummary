"""Base provider interface and types for LLM integration.

This module defines the contract that all LLM providers must follow,
enabling a pluggable architecture where providers can be easily swapped
or added without modifying existing code.

Design Pattern: Strategy Pattern with Protocol-based interface
- Each provider implements the same interface
- Providers are interchangeable at runtime
- Configuration is injected, not hardcoded
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel


class ProviderError(Exception):
    """Base exception for LLM provider errors."""

    pass


class ProviderNotAvailableError(ProviderError):
    """Raised when a provider is not available (e.g., missing API key or dependency)."""

    pass


class ProviderRateLimitError(ProviderError):
    """Raised when the provider's rate limit is exceeded."""

    pass


class ProviderAuthenticationError(ProviderError):
    """Raised when authentication with the provider fails."""

    pass


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider.

    All providers return this common format, regardless of their
    underlying API differences.
    """

    # The parsed structured output (if using structured outputs)
    parsed: Optional[Dict[str, Any]] = None

    # Raw text response (fallback if structured parsing fails)
    raw_text: Optional[str] = None

    # Provider-specific metadata
    model: str = ""
    provider: str = ""

    # Usage statistics
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Refusal message (if model refuses to respond)
    refusal: Optional[str] = None

    # Whether the response was successfully parsed as structured output
    is_structured: bool = False

    @property
    def success(self) -> bool:
        """Return True if we got a valid response (parsed or raw)."""
        return self.parsed is not None or self.raw_text is not None


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider.

    Holds all settings needed to initialize and use a provider.
    Settings are provider-specific but follow common patterns.
    """

    # API authentication
    api_key: Optional[str] = None
    api_base: Optional[str] = None  # For custom endpoints (Ollama, Azure, etc.)

    # Model selection
    model: str = ""
    fallback_model: Optional[str] = None

    # Request parameters
    temperature: float = 0.0  # Low temp for deterministic extraction
    max_tokens: int = 2048
    timeout: float = 30.0

    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0

    # Provider-specific options
    extra: Dict[str, Any] = field(default_factory=dict)


T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All concrete providers (OpenAI, Anthropic, Ollama, etc.) must
    inherit from this class and implement its abstract methods.

    The provider lifecycle:
    1. is_available() - Check if provider can be used
    2. __init__() with config - Initialize the provider
    3. extract_structured() - Make extraction requests

    Example:
        >>> provider = OpenAIProvider(config)
        >>> if provider.is_available():
        ...     response = provider.extract_structured(prompt, schema)
        ...     artifact_data = response.parsed
    """

    # Class-level metadata
    name: str = "base"  # Unique identifier (e.g., "openai", "anthropic")
    display_name: str = "Base Provider"  # Human-readable name
    default_model: str = ""  # Default model to use

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        """Initialize the provider with configuration.

        Args:
            config: Provider configuration. If None, uses defaults.
        """
        self.config = config or ProviderConfig()
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration. Override in subclasses for custom validation."""
        pass

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this provider is available for use.

        Returns True if:
        - Required dependencies are installed
        - API key is configured (if needed)
        - API endpoint is reachable (optional)

        This is called before instantiation to determine which
        providers are viable options.
        """
        ...

    @abstractmethod
    def extract_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Extract structured data from text using an LLM.

        This is the core method for semantic extraction. It sends a prompt
        to the LLM and expects a response conforming to the given Pydantic schema.

        Args:
            prompt: The user prompt containing data to analyze.
            schema: A Pydantic model class defining the expected output structure.
            system_prompt: Optional system prompt for context setting.

        Returns:
            LLMResponse with parsed data or error information.

        Raises:
            ProviderError: On API errors, rate limits, or authentication failures.
        """
        ...

    def extract_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Extract free-form text from an LLM (non-structured).

        Default implementation. Override if provider has a more efficient
        method for unstructured responses.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.

        Returns:
            LLMResponse with raw_text populated.
        """
        # Default: create a simple text schema
        class TextResponse(BaseModel):
            text: str

        response = self.extract_structured(prompt, TextResponse, system_prompt)
        if response.parsed:
            response.raw_text = response.parsed.get("text", "")
        return response

    def get_model(self) -> str:
        """Get the model to use for requests."""
        return self.config.model or self.default_model

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.get_model()}>"



