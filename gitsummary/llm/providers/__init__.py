"""Concrete LLM provider implementations.

This package contains provider implementations for various LLM backends.
Each provider implements the BaseLLMProvider interface and can be
registered with the ProviderRegistry.

Available Providers:
    - OpenAIProvider: OpenAI API (GPT-4o, GPT-4, etc.) with structured outputs
    - AnthropicProvider: Anthropic Claude API (placeholder)
    - OllamaProvider: Local Ollama models (placeholder)
"""

from __future__ import annotations

# Providers are imported lazily in registry.py to handle missing dependencies
__all__: list[str] = []



