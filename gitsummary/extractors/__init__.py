"""Semantic extraction strategies for gitsummary.

This package contains different strategies for extracting semantic
information from commits. Each extractor implements the same protocol
and can be swapped or combined.

Modules:
    base: The Extractor protocol and result types
    heuristic: Rule-based extraction from commit messages and diffs
    llm: LLM-powered extraction with provider abstraction

For LLM provider configuration, see the gitsummary.llm package.
"""

from __future__ import annotations

from .base import ExtractionResult, Extractor
from .heuristic import HeuristicExtractor
from .llm import (
    LLMExtractor,
    LLMProvider,
    create_openai_provider_function,
    get_llm_provider,
    set_llm_provider,
)

__all__ = [
    # Protocol
    "Extractor",
    "ExtractionResult",
    # Implementations
    "HeuristicExtractor",
    "LLMExtractor",
    # LLM Provider management (legacy interface)
    "LLMProvider",
    "get_llm_provider",
    "set_llm_provider",
    # Convenience functions
    "create_openai_provider_function",
]

