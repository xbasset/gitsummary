"""Base protocol and types for semantic extractors.

This module defines the contract that all extractors must follow,
enabling a pluggable extraction architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol

from ..core import ChangeCategory, CommitDiff, CommitInfo, ImpactScope


@dataclass
class ExtractionResult:
    """Result of semantic extraction from a commit.

    Contains all the semantic fields that an extractor can determine.
    Fields left as None will be filled by fallback extractors or defaults.
    """

    intent_summary: Optional[str] = None
    category: Optional[ChangeCategory] = None
    behavior_before: Optional[str] = None
    behavior_after: Optional[str] = None
    impact_scope: Optional[ImpactScope] = None
    is_breaking: Optional[bool] = None
    technical_highlights: List[str] = field(default_factory=list)

    def merge_with(self, fallback: "ExtractionResult") -> "ExtractionResult":
        """Merge with a fallback result, using fallback for missing fields.

        This enables chaining extractors (e.g., LLM with heuristic fallback).
        """
        return ExtractionResult(
            intent_summary=self.intent_summary or fallback.intent_summary,
            category=self.category or fallback.category,
            behavior_before=self.behavior_before or fallback.behavior_before,
            behavior_after=self.behavior_after or fallback.behavior_after,
            impact_scope=self.impact_scope or fallback.impact_scope,
            is_breaking=(
                self.is_breaking if self.is_breaking is not None else fallback.is_breaking
            ),
            technical_highlights=(
                self.technical_highlights or fallback.technical_highlights
            ),
        )


class Extractor(Protocol):
    """Protocol for semantic extraction from commits.

    Extractors analyze commit information and diffs to extract
    semantic understanding. They can be chained or composed.
    """

    def extract(
        self,
        commit: CommitInfo,
        diff: Optional[CommitDiff] = None,
        diff_patch: str = "",
    ) -> ExtractionResult:
        """Extract semantic information from a commit.

        Args:
            commit: The commit information.
            diff: Optional structured diff data.
            diff_patch: Optional raw unified diff text.

        Returns:
            ExtractionResult with populated fields.
        """
        ...

