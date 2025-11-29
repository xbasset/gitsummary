"""Analyzer service for building commit artifacts.

This service orchestrates the extraction of semantic information
from commits, combining multiple extractors with fallback logic.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..core import ChangeCategory, CommitArtifact, CommitDiff, CommitInfo, ImpactScope
from ..extractors import HeuristicExtractor, LLMExtractor
from ..infrastructure import diff_patch_for_commit

logger = logging.getLogger(__name__)


class AnalyzerService:
    """Service for analyzing commits and building artifacts.

    Combines LLM and heuristic extractors with fallback logic
    to produce complete CommitArtifacts.

    The analyzer supports multiple LLM providers and gracefully
    falls back to heuristics when LLM is unavailable or fails.
    """

    def __init__(
        self,
        use_llm: bool = True,
        provider_name: Optional[str] = None,
    ) -> None:
        """Initialize the analyzer service.

        Args:
            use_llm: Whether to attempt LLM extraction (default: True).
            provider_name: Name of LLM provider to use (e.g., "openai", "anthropic").
                          If None, uses the default provider from configuration.
        """
        self.use_llm = use_llm
        self.provider_name = provider_name
        self._llm_extractor = LLMExtractor(provider_name=provider_name) if use_llm else None
        self._heuristic_extractor = HeuristicExtractor()
        self._provider_initialized = False

    def _ensure_provider(self) -> bool:
        """Ensure the LLM provider is initialized.

        Returns True if LLM is available, False otherwise.
        """
        if not self.use_llm:
            return False

        if self._provider_initialized:
            return self._llm_extractor is not None

        self._provider_initialized = True

        # Try to initialize the provider
        if self._llm_extractor is not None:
            try:
                # Trigger provider initialization
                self._llm_extractor._get_provider()
                return True
            except Exception as e:
                logger.warning(f"LLM provider not available: {e}")
                return False

        return False

    def analyze(
        self,
        commit: CommitInfo,
        diff: Optional[CommitDiff] = None,
    ) -> CommitArtifact:
        """Analyze a commit and build an artifact.

        Uses LLM extraction if available and enabled, with heuristic
        fallback for any fields the LLM doesn't populate.

        Args:
            commit: The commit to analyze.
            diff: Optional pre-fetched diff data.

        Returns:
            A fully populated CommitArtifact.
        """
        # Get the diff patch text
        try:
            diff_patch = diff_patch_for_commit(commit.sha)
        except Exception:
            diff_patch = ""

        # Try LLM extraction first if enabled
        llm_result = None
        if self._ensure_provider() and self._llm_extractor is not None:
            try:
                llm_result = self._llm_extractor.extract(commit, diff, diff_patch)
            except Exception as e:
                logger.warning(f"LLM extraction failed for {commit.short_sha}: {e}")
                llm_result = None

        # Always run heuristic extraction as fallback
        heuristic_result = self._heuristic_extractor.extract(commit, diff, diff_patch)

        # Merge results (LLM takes precedence where available)
        if llm_result and llm_result.intent_summary:
            merged = llm_result.merge_with(heuristic_result)
        else:
            merged = heuristic_result

        # Build the artifact
        return CommitArtifact(
            commit_hash=commit.sha,
            intent_summary=merged.intent_summary or commit.summary,
            category=merged.category or ChangeCategory.CHORE,
            behavior_before=merged.behavior_before,
            behavior_after=merged.behavior_after,
            impact_scope=merged.impact_scope or ImpactScope.INTERNAL,
            is_breaking=merged.is_breaking or False,
            technical_highlights=merged.technical_highlights,
        )


# Module-level convenience function
def build_commit_artifact(
    commit: CommitInfo,
    diff: Optional[CommitDiff] = None,
    *,
    use_llm: bool = True,
    provider_name: Optional[str] = None,
) -> CommitArtifact:
    """Build a CommitArtifact from commit info and optional diff data.

    This is a convenience function that creates an AnalyzerService
    and calls analyze(). For batch operations, prefer creating
    an AnalyzerService instance directly.

    Args:
        commit: The commit information.
        diff: Optional pre-fetched diff data.
        use_llm: Whether to attempt LLM extraction (default: True).
        provider_name: Name of LLM provider (e.g., "openai", "anthropic").

    Returns:
        A fully populated CommitArtifact.
    """
    service = AnalyzerService(use_llm=use_llm, provider_name=provider_name)
    return service.analyze(commit, diff)
