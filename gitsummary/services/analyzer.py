"""Analyzer service for building commit artifacts.

This service orchestrates the extraction of semantic information
from commits, combining multiple extractors with fallback logic.
"""

from __future__ import annotations

from typing import Optional

from ..core import ChangeCategory, CommitArtifact, CommitDiff, CommitInfo, ImpactScope
from ..extractors import HeuristicExtractor, LLMExtractor
from ..infrastructure import diff_patch_for_commit


class AnalyzerService:
    """Service for analyzing commits and building artifacts.

    Combines LLM and heuristic extractors with fallback logic
    to produce complete CommitArtifacts.
    """

    def __init__(self, use_llm: bool = True) -> None:
        """Initialize the analyzer service.

        Args:
            use_llm: Whether to attempt LLM extraction (default: True).
        """
        self.use_llm = use_llm
        self._llm_extractor = LLMExtractor()
        self._heuristic_extractor = HeuristicExtractor()

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
        if self.use_llm:
            llm_result = self._llm_extractor.extract(commit, diff, diff_patch)
        else:
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
) -> CommitArtifact:
    """Build a CommitArtifact from commit info and optional diff data.

    This is a convenience function that creates an AnalyzerService
    and calls analyze(). For batch operations, prefer creating
    an AnalyzerService instance directly.

    Args:
        commit: The commit information.
        diff: Optional pre-fetched diff data.
        use_llm: Whether to attempt LLM extraction (default: True).

    Returns:
        A fully populated CommitArtifact.
    """
    service = AnalyzerService(use_llm=use_llm)
    return service.analyze(commit, diff)

