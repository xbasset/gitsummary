"""Impact report builder."""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Tuple

from ..core import CommitArtifact, CommitInfo


class ImpactReport:
    """Structured impact analysis data ready for formatting."""

    def __init__(
        self,
        total_commits: int,
        analyzed_count: int,
        scope_distribution: Dict[str, int],
        breaking_changes: List[Tuple[CommitInfo, CommitArtifact]],
        technical_highlights: List[str],
    ) -> None:
        self.total_commits = total_commits
        self.analyzed_count = analyzed_count
        self.scope_distribution = scope_distribution
        self.breaking_changes = breaking_changes
        self.technical_highlights = technical_highlights

    @property
    def breaking_count(self) -> int:
        return len(self.breaking_changes)


class ImpactBuilder:
    """Builder for impact reports."""

    def build(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
    ) -> ImpactReport:
        scope_counts: Counter[str] = Counter()
        breaking_changes: List[Tuple[CommitInfo, CommitArtifact]] = []
        all_highlights: List[str] = []

        for commit in commits:
            artifact = artifacts.get(commit.sha)
            if artifact is None:
                continue

            scope_counts[artifact.impact_scope.value] += 1
            if artifact.is_breaking:
                breaking_changes.append((commit, artifact))
            all_highlights.extend(artifact.technical_highlights)

        return ImpactReport(
            total_commits=len(commits),
            analyzed_count=sum(1 for a in artifacts.values() if a is not None),
            scope_distribution=dict(scope_counts),
            breaking_changes=breaking_changes,
            technical_highlights=all_highlights,
        )
