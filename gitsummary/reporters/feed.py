"""Artifact feed report builder.

Generates a scroll-friendly feed representation of commits and their
artifacts. Designed for HTML rendering where both analyzed and missing
artifacts can be presented with rich context.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..core import ChangeCategory, CommitArtifact, CommitInfo, ImpactScope


@dataclass(frozen=True)
class FeedItem:
    """One entry in the artifact feed."""

    commit: CommitInfo
    artifact: Optional[CommitArtifact]
    analyzed: bool
    category: Optional[ChangeCategory]
    impact_scope: Optional[ImpactScope]
    is_breaking: bool
    intent_summary: Optional[str]
    behavior_before: Optional[str]
    behavior_after: Optional[str]
    technical_highlights: List[str]


class ArtifactFeedReport:
    """Aggregate feed data ready for formatting."""

    def __init__(self, items: List[FeedItem]) -> None:
        self.items = items
        self.total_commits = len(items)
        self.analyzed_count = sum(1 for item in items if item.analyzed)
        self.missing_count = self.total_commits - self.analyzed_count
        self.breaking_count = sum(1 for item in items if item.is_breaking)
        self.category_counts = Counter(
            item.category for item in items if item.category is not None
        )
        self.impact_counts = Counter(
            item.impact_scope for item in items if item.impact_scope is not None
        )


class ArtifactFeedBuilder:
    """Builds artifact feed reports from commits and artifacts."""

    def build(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
        *,
        include_unanalyzed: bool = True,
    ) -> ArtifactFeedReport:
        items: List[FeedItem] = []

        for commit in commits:
            artifact = artifacts.get(commit.sha)
            if artifact is None and not include_unanalyzed:
                continue

            items.append(
                FeedItem(
                    commit=commit,
                    artifact=artifact,
                    analyzed=artifact is not None,
                    category=artifact.category if artifact else None,
                    impact_scope=artifact.impact_scope if artifact else None,
                    is_breaking=artifact.is_breaking if artifact else False,
                    intent_summary=artifact.intent_summary if artifact else None,
                    behavior_before=artifact.behavior_before if artifact else None,
                    behavior_after=artifact.behavior_after if artifact else None,
                    technical_highlights=artifact.technical_highlights
                    if artifact
                    else [],
                )
            )

        return ArtifactFeedReport(items)
