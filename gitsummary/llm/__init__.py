"""LLM Provider abstraction layer for gitsummary.

This package provides a pluggable architecture for multiple LLM providers
(OpenAI, Anthropic, Mistral, local Ollama, etc.) with unified configuration
management and structured output support.

Architecture:
    - BaseLLMProvider: Abstract base class defining the provider contract
    - ProviderRegistry: Factory for instantiating providers by name
    - ConfigManager: Handles API keys from env vars, .env files, and user prompts

Modules:
    base: Abstract provider interface and response types
    config: API key and configuration management
    registry: Provider factory and registration
    providers: Concrete provider implementations
    schemas: Pydantic schemas for structured LLM outputs
    prompts: Prompt templates for commit analysis

Usage:
    >>> from gitsummary.llm import get_provider
    >>> provider = get_provider("openai")
    >>> response = provider.extract_structured(prompt, MySchema)

Environment Variables:
    OPENAI_API_KEY: API key for OpenAI provider
    ANTHROPIC_API_KEY: API key for Anthropic provider
    GITSUMMARY_PROVIDER: Default provider to use (default: "openai")
    GITSUMMARY_MODEL: Override model for the selected provider
"""

from __future__ import annotations

from .base import (
    BaseLLMProvider,
    LLMResponse,
    ProviderConfig,
    ProviderError,
    ProviderNotAvailableError,
)
from .config import ConfigManager, get_config_manager
from .registry import (
    ProviderRegistry,
    get_provider,
    list_all_providers,
    list_available_providers,
)

__all__ = [
    # Base types
    "BaseLLMProvider",
    "LLMResponse",
    "ProviderConfig",
    "ProviderError",
    "ProviderNotAvailableError",
    # Configuration
    "ConfigManager",
    "get_config_manager",
    # Registry
    "ProviderRegistry",
    "get_provider",
    "list_available_providers",
    "list_all_providers",
]

