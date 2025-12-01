"""Tests for reporter service.

Tests the ReporterService class and report generation.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from gitsummary.core import (
    ChangeCategory,
    CommitArtifact,
    CommitInfo,
    ImpactScope,
    ReleaseNote,
)
from gitsummary.services.reporter import (
    ChangelogReport,
    ImpactReport,
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


# ─────────────────────────────────────────────────────────────────────────────
# LLM Release Notes Generation Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLLMReleaseNotesGeneration:
    """Tests for generate_llm_release_notes method."""

    def test_generates_release_note_heuristic(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test release note generation with heuristics (no LLM)."""
        commits, artifacts = commits_with_artifacts
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
            provider=None,  # Heuristic mode
        )
        
        assert isinstance(release_note, ReleaseNote)
        assert release_note.schema_version == "1.0.0"
        assert release_note.artifact_type == "release-note"

    def test_release_note_header(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that release note header is populated correctly."""
        commits, artifacts = commits_with_artifacts
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="MyProduct",
            version="v2.0.0",
            revision_range="v1.0.0..v2.0.0",
        )
        
        assert release_note.header.product_name == "MyProduct"
        assert release_note.header.version == "v2.0.0"
        assert release_note.header.release_date is not None

    def test_release_note_metadata(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that release note metadata is populated correctly."""
        commits, artifacts = commits_with_artifacts
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
        )
        
        assert release_note.metadata.revision_range == "v0.9.0..v1.0.0"
        assert release_note.metadata.commit_count == 4
        assert release_note.metadata.analyzed_count == 3
        assert release_note.metadata.llm_provider is None  # Heuristic mode

    def test_release_note_source_commits(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that source commits are tracked."""
        commits, artifacts = commits_with_artifacts
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
        )
        
        # Should have source commits for analyzed commits (3 out of 4)
        assert len(release_note.metadata.source_commits) == 3

    def test_heuristic_generates_highlights(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that heuristic mode generates highlights."""
        commits, artifacts = commits_with_artifacts
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
        )
        
        # Should have at least one highlight
        assert len(release_note.highlights) > 0

    def test_heuristic_generates_features(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that heuristic mode extracts features."""
        commits, artifacts = commits_with_artifacts
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
        )
        
        # Should have features from feature artifacts
        assert len(release_note.features) >= 1

    def test_heuristic_generates_fixes(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that heuristic mode extracts fixes."""
        commits, artifacts = commits_with_artifacts
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
        )
        
        # Should have fixes from fix artifacts
        assert len(release_note.fixes) >= 1

    def test_heuristic_generates_deprecations_for_breaking(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that breaking changes become deprecations."""
        commits, artifacts = commits_with_artifacts
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
        )
        
        # Should have deprecation from breaking artifact
        assert len(release_note.deprecations) >= 1

    def test_generates_theme(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that a theme is generated."""
        commits, artifacts = commits_with_artifacts
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
        )
        
        assert release_note.header.theme is not None
        assert len(release_note.header.theme) > 0

    def test_release_note_to_yaml(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that release note can be serialized to YAML."""
        commits, artifacts = commits_with_artifacts
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
        )
        
        yaml_str = release_note.to_yaml()
        assert "schema_version: 1.0.0" in yaml_str
        assert "artifact_type: release-note" in yaml_str
        assert "TestApp" in yaml_str


class TestLLMReleaseNotesWithProvider:
    """Tests for generate_llm_release_notes with LLM provider."""

    def test_uses_llm_provider_when_provided(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that LLM provider is used when provided."""
        commits, artifacts = commits_with_artifacts
        
        # Create mock provider
        mock_provider = MagicMock()
        mock_provider.name = "test-provider"
        mock_provider.get_model.return_value = "test-model"
        mock_provider.extract_structured.return_value = MagicMock(
            parsed={
                "theme": "Test theme from LLM",
                "highlights": [
                    {"emoji": "🚀", "type": "new", "summary": "LLM feature"}
                ],
                "features": [],
                "improvements": [],
                "fixes": [],
                "deprecations": [],
            }
        )
        
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
            provider=mock_provider,
        )
        
        # LLM provider should be called
        mock_provider.extract_structured.assert_called_once()
        
        # Metadata should reflect LLM usage
        assert release_note.metadata.llm_provider == "test-provider"
        assert release_note.metadata.llm_model == "test-model"
        
        # Content should come from LLM
        assert release_note.header.theme == "Test theme from LLM"

    def test_falls_back_to_heuristic_on_llm_failure(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test fallback to heuristic when LLM returns None."""
        commits, artifacts = commits_with_artifacts
        
        # Create mock provider that returns empty response
        mock_provider = MagicMock()
        mock_provider.name = "test-provider"
        mock_provider.get_model.return_value = "test-model"
        mock_provider.extract_structured.return_value = MagicMock(parsed=None)
        
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
            provider=mock_provider,
        )
        
        # Should still produce a valid release note (from heuristics)
        assert isinstance(release_note, ReleaseNote)
        assert release_note.header.theme is not None


class TestPrepareArtifactsForSynthesis:
    """Tests for _prepare_artifacts_for_synthesis helper."""

    def test_prepares_artifacts_data(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that artifacts are prepared correctly for synthesis."""
        commits, artifacts = commits_with_artifacts
        
        data = reporter._prepare_artifacts_for_synthesis(commits, artifacts)
        
        # Should only include analyzed commits (3 out of 4)
        assert len(data) == 3
        
        # Each item should have required fields
        for item in data:
            assert "sha" in item
            assert "category" in item
            assert "intent_summary" in item
            assert "is_breaking" in item

    def test_skips_unanalyzed_commits(
        self,
        reporter: ReporterService,
        commits_with_artifacts: tuple[
            List[CommitInfo], Dict[str, Optional[CommitArtifact]]
        ],
    ) -> None:
        """Test that unanalyzed commits are skipped."""
        commits, artifacts = commits_with_artifacts
        
        data = reporter._prepare_artifacts_for_synthesis(commits, artifacts)
        
        # docs_commit has None artifact, should be skipped
        shas = [item["sha"] for item in data]
        assert "doc0987" not in shas  # Unanalyzed commit's short SHA


class TestHeuristicSynthesis:
    """Tests for heuristic synthesis logic."""

    def test_groups_by_category(
        self,
        reporter: ReporterService,
        feature_artifact: CommitArtifact,
        fix_artifact: CommitArtifact,
        simple_commit: CommitInfo,
        fix_commit: CommitInfo,
    ) -> None:
        """Test that artifacts are grouped by category."""
        commits = [simple_commit, fix_commit]
        artifacts = {
            simple_commit.sha: feature_artifact,
            fix_commit.sha: fix_artifact,
        }
        
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
        )
        
        # Should have both features and fixes
        assert len(release_note.features) >= 1
        assert len(release_note.fixes) >= 1

    def test_highlight_types(
        self,
        reporter: ReporterService,
        feature_artifact: CommitArtifact,
        fix_artifact: CommitArtifact,
        breaking_artifact: CommitArtifact,
        simple_commit: CommitInfo,
        fix_commit: CommitInfo,
        breaking_commit: CommitInfo,
    ) -> None:
        """Test that different highlight types are generated."""
        commits = [simple_commit, fix_commit, breaking_commit]
        artifacts = {
            simple_commit.sha: feature_artifact,
            fix_commit.sha: fix_artifact,
            breaking_commit.sha: breaking_artifact,
        }
        
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name="TestApp",
            version="v1.0.0",
            revision_range="v0.9.0..v1.0.0",
        )
        
        highlight_types = [h.type for h in release_note.highlights]
        
        # Should have new and fixed at minimum
        assert "new" in highlight_types or "fixed" in highlight_types

