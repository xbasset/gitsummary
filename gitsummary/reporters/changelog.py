"""Changelog report builder."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from ..core import ChangeCategory, CommitArtifact, CommitInfo


class ChangelogReport:
    """Structured changelog data ready for formatting."""

    def __init__(
        self,
        by_category: Dict[ChangeCategory, List[Tuple[CommitInfo, CommitArtifact]]],
        unanalyzed: List[CommitInfo],
    ) -> None:
        self.by_category = by_category
        self.unanalyzed = unanalyzed

    @property
    def features(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.FEATURE, [])

    @property
    def fixes(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.FIX, [])

    @property
    def security(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.SECURITY, [])

    @property
    def performance(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.PERFORMANCE, [])

    @property
    def refactors(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.REFACTOR, [])

    @property
    def chores(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.CHORE, [])

    @property
    def breaking_changes(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        """All breaking changes across categories."""
        return [
            (c, a)
            for items in self.by_category.values()
            for c, a in items
            if a.is_breaking
        ]


class ChangelogBuilder:
    """Builder for changelog reports."""

    def build(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
        *,
        include_unanalyzed: bool = False,
    ) -> ChangelogReport:
        by_category: Dict[ChangeCategory, List[Tuple[CommitInfo, CommitArtifact]]] = (
            defaultdict(list)
        )
        unanalyzed: List[CommitInfo] = []

        for commit in commits:
            artifact = artifacts.get(commit.sha)
            if artifact is None:
                if include_unanalyzed:
                    unanalyzed.append(commit)
                continue
            by_category[artifact.category].append((commit, artifact))

        return ChangelogReport(by_category=dict(by_category), unanalyzed=unanalyzed)
