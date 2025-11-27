"""Reporter service for generating reports from artifacts.

This service provides high-level report generation capabilities,
transforming stored artifacts into various output formats.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from ..core import ChangeCategory, CommitArtifact, CommitInfo, ImpactScope


class ReporterService:
    """Service for generating reports from commit artifacts.

    Provides methods for generating changelogs, release notes,
    and impact analyses from stored artifacts.
    """

    def generate_changelog(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
        *,
        include_unanalyzed: bool = False,
    ) -> "ChangelogReport":
        """Generate a changelog report from commits and their artifacts.

        Args:
            commits: List of commits in the range.
            artifacts: Dict mapping SHA to artifact (or None if not analyzed).
            include_unanalyzed: Whether to include commits without artifacts.

        Returns:
            A ChangelogReport ready for formatting.
        """
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

        return ChangelogReport(
            by_category=dict(by_category),
            unanalyzed=unanalyzed,
        )

    def generate_release_notes(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
    ) -> "ReleaseNotesReport":
        """Generate release notes focusing on user-facing changes.

        Args:
            commits: List of commits in the range.
            artifacts: Dict mapping SHA to artifact (or None if not analyzed).

        Returns:
            A ReleaseNotesReport ready for formatting.
        """
        user_facing: List[Tuple[CommitInfo, CommitArtifact]] = []
        internal: List[Tuple[CommitInfo, CommitArtifact]] = []

        for commit in commits:
            artifact = artifacts.get(commit.sha)
            if artifact is None:
                continue

            # Determine if user-facing
            if artifact.impact_scope in (ImpactScope.PUBLIC_API, ImpactScope.CONFIG):
                user_facing.append((commit, artifact))
            elif artifact.category in (
                ChangeCategory.FEATURE,
                ChangeCategory.FIX,
                ChangeCategory.SECURITY,
            ):
                if artifact.impact_scope != ImpactScope.TEST:
                    user_facing.append((commit, artifact))
            else:
                internal.append((commit, artifact))

        return ReleaseNotesReport(
            user_facing=user_facing,
            internal=internal,
            total_commits=len(commits),
            analyzed_count=sum(1 for a in artifacts.values() if a is not None),
        )

    def generate_impact_report(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
    ) -> "ImpactReport":
        """Generate an impact analysis report.

        Args:
            commits: List of commits in the range.
            artifacts: Dict mapping SHA to artifact (or None if not analyzed).

        Returns:
            An ImpactReport ready for formatting.
        """
        from collections import Counter

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


# ─────────────────────────────────────────────────────────────────────────────
# Report Data Classes
# ─────────────────────────────────────────────────────────────────────────────


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


class ReleaseNotesReport:
    """Structured release notes data ready for formatting."""

    def __init__(
        self,
        user_facing: List[Tuple[CommitInfo, CommitArtifact]],
        internal: List[Tuple[CommitInfo, CommitArtifact]],
        total_commits: int,
        analyzed_count: int,
    ) -> None:
        self.user_facing = user_facing
        self.internal = internal
        self.total_commits = total_commits
        self.analyzed_count = analyzed_count


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

