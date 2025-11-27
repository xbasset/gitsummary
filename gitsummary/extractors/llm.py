"""LLM-powered semantic extraction.

This module provides LLM-based extraction with a pluggable provider
interface. It enables high-quality semantic understanding while
allowing different LLM backends (OpenAI, Claude, local models, etc.).
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from ..core import ChangeCategory, CommitDiff, CommitInfo, ImpactScope
from .base import ExtractionResult

# Type alias for LLM provider function
# Takes: commit_info, diff_patch -> Returns: dict with extracted fields or None
LLMProvider = Callable[[CommitInfo, str], Optional[Dict[str, object]]]


def _null_provider(commit: CommitInfo, diff_patch: str) -> Optional[Dict[str, object]]:
    """Default null provider that returns None, triggering heuristic fallback."""
    return None


# Global LLM provider (can be set by CLI or tests)
_llm_provider: LLMProvider = _null_provider


def set_llm_provider(provider: LLMProvider) -> None:
    """Set the global LLM provider for artifact extraction.

    Args:
        provider: A callable that takes (CommitInfo, diff_patch) and returns
                  a dict with extracted fields or None.
    """
    global _llm_provider
    _llm_provider = provider


def get_llm_provider() -> LLMProvider:
    """Get the current LLM provider."""
    return _llm_provider


class LLMExtractor:
    """LLM-powered semantic extractor.

    Uses an LLM provider to extract semantic information from commits.
    Falls back to None fields if the provider returns None or fails.
    """

    def __init__(self, provider: Optional[LLMProvider] = None) -> None:
        """Initialize with an optional explicit provider.

        Args:
            provider: LLM provider function. If None, uses the global provider.
        """
        self.provider = provider

    def extract(
        self,
        commit: CommitInfo,
        diff: Optional[CommitDiff] = None,
        diff_patch: str = "",
    ) -> ExtractionResult:
        """Extract semantic information using LLM.

        Args:
            commit: The commit information.
            diff: Optional structured diff data (unused, LLM uses raw patch).
            diff_patch: Raw unified diff text for LLM analysis.

        Returns:
            ExtractionResult with fields populated by LLM, or empty if unavailable.
        """
        provider = self.provider or get_llm_provider()
        llm_result = provider(commit, diff_patch)

        if llm_result is None:
            return ExtractionResult()

        # Parse LLM result into ExtractionResult
        return self._parse_llm_result(llm_result)

    def _parse_llm_result(self, result: Dict[str, object]) -> ExtractionResult:
        """Parse LLM provider result into ExtractionResult."""
        category = None
        if "category" in result:
            try:
                category = ChangeCategory(result["category"])
            except ValueError:
                pass

        impact_scope = None
        if "impact_scope" in result:
            try:
                impact_scope = ImpactScope(result["impact_scope"])
            except ValueError:
                pass

        return ExtractionResult(
            intent_summary=result.get("intent_summary"),  # type: ignore
            category=category,
            behavior_before=result.get("behavior_before"),  # type: ignore
            behavior_after=result.get("behavior_after"),  # type: ignore
            impact_scope=impact_scope,
            is_breaking=result.get("is_breaking"),  # type: ignore
            technical_highlights=result.get("technical_highlights", []),  # type: ignore
        )

