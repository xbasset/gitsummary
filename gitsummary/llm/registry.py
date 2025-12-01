"""Provider registry and factory for LLM providers.

This module implements the Factory pattern for LLM providers,
enabling runtime provider selection based on configuration,
environment, or CLI flags.

The registry is designed to:
- Auto-discover available providers
- Gracefully handle missing dependencies
- Support provider aliases
- Provide helpful error messages
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from .base import BaseLLMProvider, ProviderConfig, ProviderNotAvailableError
from .config import ConfigManager, get_config_manager


class ProviderRegistry:
    """Registry for LLM providers.

    Maintains a mapping of provider names to provider classes,
    and handles instantiation with proper configuration.

    Example:
        >>> registry = ProviderRegistry()
        >>> registry.register("openai", OpenAIProvider)
        >>> provider = registry.get("openai")
    """

    def __init__(self) -> None:
        self._providers: Dict[str, Type[BaseLLMProvider]] = {}
        self._aliases: Dict[str, str] = {}

    def register(
        self,
        name: str,
        provider_class: Type[BaseLLMProvider],
        aliases: Optional[List[str]] = None,
    ) -> None:
        """Register a provider class.

        Args:
            name: Primary identifier for the provider
            provider_class: The provider class to register
            aliases: Optional list of alternative names
        """
        self._providers[name.lower()] = provider_class

        if aliases:
            for alias in aliases:
                self._aliases[alias.lower()] = name.lower()

    def get(
        self,
        name: str,
        config: Optional[ProviderConfig] = None,
        config_manager: Optional[ConfigManager] = None,
    ) -> BaseLLMProvider:
        """Get an instantiated provider by name.

        Args:
            name: Provider name or alias
            config: Optional explicit configuration
            config_manager: Optional config manager for API key discovery

        Returns:
            An instantiated provider ready for use.

        Raises:
            ProviderNotAvailableError: If provider is not registered or not available.
        """
        # Resolve aliases
        canonical_name = self._aliases.get(name.lower(), name.lower())

        if canonical_name not in self._providers:
            available = ", ".join(self.list_registered())
            raise ProviderNotAvailableError(
                f"Unknown provider: {name}. Available providers: {available}"
            )

        provider_class = self._providers[canonical_name]

        # Check if provider is available
        if not provider_class.is_available():
            raise ProviderNotAvailableError(
                f"Provider '{name}' is not available. "
                f"Check that required dependencies are installed and API key is configured."
            )

        # Build configuration if not provided
        if config is None:
            cm = config_manager or get_config_manager()
            api_key = cm.get_api_key(canonical_name, prompt_if_missing=True)
            model = cm.get_provider_model(canonical_name)

            config = ProviderConfig(
                api_key=api_key,
                model=model or "",
            )

        return provider_class(config)

    def get_if_available(
        self,
        name: str,
        config: Optional[ProviderConfig] = None,
    ) -> Optional[BaseLLMProvider]:
        """Get a provider if available, otherwise return None.

        Unlike get(), this doesn't raise an exception if the provider
        is unavailable. Useful for optional LLM enhancement.
        """
        try:
            return self.get(name, config)
        except ProviderNotAvailableError:
            return None

    def list_registered(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def list_available(self) -> List[str]:
        """List providers that are currently available for use."""
        return [
            name
            for name, cls in self._providers.items()
            if cls.is_available()
        ]

    def is_registered(self, name: str) -> bool:
        """Check if a provider is registered."""
        canonical = self._aliases.get(name.lower(), name.lower())
        return canonical in self._providers

    def is_available(self, name: str) -> bool:
        """Check if a provider is available for use."""
        canonical = self._aliases.get(name.lower(), name.lower())
        if canonical not in self._providers:
            return False
        return self._providers[canonical].is_available()


# Global registry instance
_registry: Optional[ProviderRegistry] = None


def _get_registry() -> ProviderRegistry:
    """Get the global provider registry, initializing if needed."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
        _register_builtin_providers(_registry)
    return _registry


def _register_builtin_providers(registry: ProviderRegistry) -> None:
    """Register all built-in providers.

    This function imports and registers provider classes.
    Import errors are caught to allow graceful degradation
    when optional dependencies are missing.
    """
    # OpenAI provider
    try:
        from .providers.openai_provider import OpenAIProvider

        registry.register("openai", OpenAIProvider, aliases=["gpt", "gpt-4", "gpt-4o"])
    except ImportError:
        pass  # openai package not installed

    # Anthropic provider (placeholder for future implementation)
    try:
        from .providers.anthropic_provider import AnthropicProvider

        registry.register("anthropic", AnthropicProvider, aliases=["claude"])
    except ImportError:
        pass

    # Ollama provider (placeholder for future implementation)
    try:
        from .providers.ollama_provider import OllamaProvider

        registry.register("ollama", OllamaProvider, aliases=["local"])
    except ImportError:
        pass


# Public API functions


def get_provider(
    name: Optional[str] = None,
    config: Optional[ProviderConfig] = None,
) -> BaseLLMProvider:
    """Get an LLM provider by name.

    If no name is provided, uses the default provider from configuration.

    Args:
        name: Provider name (e.g., "openai", "anthropic", "ollama")
        config: Optional explicit configuration

    Returns:
        An instantiated provider ready for use.

    Raises:
        ProviderNotAvailableError: If provider is not available.

    Example:
        >>> provider = get_provider("openai")
        >>> response = provider.extract_structured(prompt, MySchema)
    """
    registry = _get_registry()

    if name is None:
        cm = get_config_manager()
        name = cm.get_default_provider()

    return registry.get(name, config)


def list_available_providers() -> List[str]:
    """List all providers that are currently available for use.

    Returns:
        List of provider names that can be instantiated.
    """
    return _get_registry().list_available()


def list_all_providers() -> List[str]:
    """List all registered providers (available or not).

    Returns:
        List of all registered provider names.
    """
    return _get_registry().list_registered()



