"""Tests for reporter service.

Tests the ReporterService class and report generation.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import pytest

from gitsummary.core import ChangeCategory, CommitArtifact, CommitInfo, ImpactScope
from gitsummary.services.reporter import (
    ChangelogReport,
    ImpactReport,
    ReleaseNotesReport,
    ReporterService,
)


@pytest.fixture
def reporter() -> ReporterService:
    """Create a ReporterService instance."""
    return ReporterService()


@pytest.fixture
def commits_with_artifacts(
    simple_commit: CommitInfo,
    fix_commit: CommitInfo,
    breaking_commit: CommitInfo,
    docs_commit: CommitInfo,
    feature_artifact: CommitArtifact,
    fix_artifact: CommitArtifact,
    breaking_artifact: CommitArtifact,
) -> tuple[List[CommitInfo], Dict[str, Optional[CommitArtifact]]]:
    """Create commits and matching artifacts dict."""
    commits = [simple_commit, fix_commit, breaking_commit, docs_commit]
    artifacts = {
        simple_commit.sha: feature_artifact,
        fix_commit.sha: fix_artifact,
        breaking_commit.sha: breaking_artifact,
        docs_commit.sha: None,  # Unanalyzed
    }
    return commits, artifacts


class TestChangelogGeneration:
    """Tests for generate_changelog method."""

    def test_groups_by_category(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that commits are grouped by category."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_changelog(commits, artifacts)
        
        assert len(report.features) >= 1
        assert len(report.fixes) >= 1

    def test_excludes_unanalyzed_by_default(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that unanalyzed commits are excluded by default."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_changelog(commits, artifacts)
        
        total_in_report = (
            len(report.features)
            + len(report.fixes)
            + len(report.security)
            + len(report.performance)
            + len(report.refactors)
            + len(report.chores)
        )
        
        # Should not include the unanalyzed commit
        assert total_in_report == 3  # feature, fix, breaking (feature)
        assert len(report.unanalyzed) == 0

    def test_includes_unanalyzed_when_requested(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that unanalyzed commits can be included."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_changelog(
            commits, artifacts, include_unanalyzed=True
        )
        
        assert len(report.unanalyzed) == 1

    def test_breaking_changes_property(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that breaking_changes property works."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_changelog(commits, artifacts)
        
        assert len(report.breaking_changes) == 1
        _, artifact = report.breaking_changes[0]
        assert artifact.is_breaking is True


class TestChangelogReport:
    """Tests for ChangelogReport data class."""

    def test_category_properties(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test all category property accessors."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_changelog(commits, artifacts)
        
        # Just test that all properties work without error
        _ = report.features
        _ = report.fixes
        _ = report.security
        _ = report.performance
        _ = report.refactors
        _ = report.chores

    def test_empty_categories_return_empty_list(self) -> None:
        """Test that missing categories return empty lists."""
        report = ChangelogReport(by_category={}, unanalyzed=[])
        
        assert report.features == []
        assert report.fixes == []
        assert report.security == []


class TestReleaseNotesGeneration:
    """Tests for generate_release_notes method."""

    def test_separates_user_facing(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that user-facing changes are separated."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_release_notes(commits, artifacts)
        
        # Features with PUBLIC_API impact should be user-facing
        assert len(report.user_facing) >= 1

    def test_tracks_totals(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that totals are tracked correctly."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_release_notes(commits, artifacts)
        
        assert report.total_commits == 4
        assert report.analyzed_count == 3

    def test_public_api_is_user_facing(
        self,
        reporter: ReporterService,
        simple_commit: CommitInfo,
    ) -> None:
        """Test that PUBLIC_API changes are user-facing."""
        artifact = CommitArtifact(
            commit_hash=simple_commit.sha,
            intent_summary="Add public endpoint",
            category=ChangeCategory.FEATURE,
            impact_scope=ImpactScope.PUBLIC_API,
        )
        commits = [simple_commit]
        artifacts = {simple_commit.sha: artifact}
        
        report = reporter.generate_release_notes(commits, artifacts)
        assert len(report.user_facing) == 1

    def test_internal_refactor_not_user_facing(
        self,
        reporter: ReporterService,
        simple_commit: CommitInfo,
    ) -> None:
        """Test that internal refactors are not user-facing."""
        artifact = CommitArtifact(
            commit_hash=simple_commit.sha,
            intent_summary="Refactor internal code",
            category=ChangeCategory.REFACTOR,
            impact_scope=ImpactScope.INTERNAL,
        )
        commits = [simple_commit]
        artifacts = {simple_commit.sha: artifact}
        
        report = reporter.generate_release_notes(commits, artifacts)
        assert len(report.user_facing) == 0
        assert len(report.internal) == 1


class TestImpactReportGeneration:
    """Tests for generate_impact_report method."""

    def test_scope_distribution(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that scope distribution is calculated."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_impact_report(commits, artifacts)
        
        assert len(report.scope_distribution) > 0
        assert isinstance(report.scope_distribution, dict)

    def test_breaking_changes_collected(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that breaking changes are collected."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_impact_report(commits, artifacts)
        
        assert report.breaking_count == 1

    def test_technical_highlights_aggregated(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that technical highlights are aggregated."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_impact_report(commits, artifacts)
        
        # All artifacts have highlights
        assert len(report.technical_highlights) > 0

    def test_totals_tracked(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that totals are tracked."""
        commits, artifacts = commits_with_artifacts
        report = reporter.generate_impact_report(commits, artifacts)
        
        assert report.total_commits == 4
        assert report.analyzed_count == 3


class TestImpactReport:
    """Tests for ImpactReport data class."""

    def test_breaking_count_property(self) -> None:
        """Test breaking_count property."""
        report = ImpactReport(
            total_commits=10,
            analyzed_count=8,
            scope_distribution={"internal": 5, "public_api": 3},
            breaking_changes=[("commit", "artifact")],  # type: ignore[list-item]
            technical_highlights=["highlight"],
        )
        
        assert report.breaking_count == 1

    def test_empty_report(self) -> None:
        """Test empty impact report."""
        report = ImpactReport(
            total_commits=0,
            analyzed_count=0,
            scope_distribution={},
            breaking_changes=[],
            technical_highlights=[],
        )
        
        assert report.breaking_count == 0
        assert report.total_commits == 0

