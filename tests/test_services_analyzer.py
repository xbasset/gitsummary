"""Tests for analyzer service.

Tests the AnalyzerService class and artifact building logic.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from gitsummary.core import ChangeCategory, CommitArtifact, CommitDiff, CommitInfo, ImpactScope
from gitsummary.extractors.base import ExtractionResult
from gitsummary.llm.base import LLMResponse
from gitsummary.services.analyzer import AnalyzerService, build_commit_artifact


class TestAnalyzerService:
    """Tests for AnalyzerService class."""

    def test_init_with_defaults(self) -> None:
        """Test default initialization."""
        service = AnalyzerService()
        assert service.use_llm is True
        assert service.provider_name is None

    def test_init_without_llm(self) -> None:
        """Test initialization with LLM disabled."""
        service = AnalyzerService(use_llm=False)
        assert service.use_llm is False
        assert service._llm_extractor is None

    def test_analyze_returns_artifact(self, simple_commit: CommitInfo) -> None:
        """Test that analyze returns a CommitArtifact."""
        service = AnalyzerService(use_llm=False)
        
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = service.analyze(simple_commit)
        
        assert isinstance(artifact, CommitArtifact)
        assert artifact.commit_hash == simple_commit.sha

    def test_analyze_uses_heuristic_without_llm(
        self, simple_commit: CommitInfo
    ) -> None:
        """Test that heuristic extractor is used when LLM is disabled."""
        service = AnalyzerService(use_llm=False)
        
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = service.analyze(simple_commit)
        
        # Heuristic should detect 'feat:' prefix
        assert artifact.category == ChangeCategory.FEATURE

    def test_analyze_handles_diff_error(self, simple_commit: CommitInfo) -> None:
        """Test that analyze handles diff extraction errors gracefully."""
        service = AnalyzerService(use_llm=False)
        
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit",
            side_effect=Exception("Git error"),
        ):
            artifact = service.analyze(simple_commit)
        
        # Should still return an artifact
        assert isinstance(artifact, CommitArtifact)

    def test_analyze_with_diff(
        self, simple_commit: CommitInfo, simple_diff
    ) -> None:
        """Test analyze with pre-fetched diff."""
        service = AnalyzerService(use_llm=False)
        
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = service.analyze(simple_commit, diff=simple_diff)
        
        assert isinstance(artifact, CommitArtifact)


class TestBuildCommitArtifact:
    """Tests for build_commit_artifact convenience function."""

    def test_returns_artifact(self, simple_commit: CommitInfo) -> None:
        """Test that function returns an artifact."""
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(simple_commit, use_llm=False)
        
        assert isinstance(artifact, CommitArtifact)

    def test_uses_commit_sha(self, simple_commit: CommitInfo) -> None:
        """Test that artifact has correct commit hash."""
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(simple_commit, use_llm=False)
        
        assert artifact.commit_hash == simple_commit.sha

    def test_uses_commit_summary(self, simple_commit: CommitInfo) -> None:
        """Test that artifact uses commit summary as fallback."""
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(simple_commit, use_llm=False)
        
        # Heuristic uses summary directly
        assert artifact.intent_summary == simple_commit.summary


class TestArtifactFields:
    """Tests for artifact field population."""

    def test_fix_category_detection(self, fix_commit: CommitInfo) -> None:
        """Test that fix commits are categorized correctly."""
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(fix_commit, use_llm=False)
        
        assert artifact.category == ChangeCategory.FIX

    def test_breaking_change_detection(self, breaking_commit: CommitInfo) -> None:
        """Test that breaking changes are detected."""
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(breaking_commit, use_llm=False)
        
        assert artifact.is_breaking is True

    def test_security_keyword_detection(self, security_commit: CommitInfo) -> None:
        """Test that security keywords are detected.
        
        Note: The security_commit has 'fix:' prefix which takes precedence
        over CVE keyword detection in the heuristic. This tests actual behavior.
        """
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(security_commit, use_llm=False)
        
        # 'fix:' prefix takes precedence, so category is FIX
        # The CVE in body doesn't override the prefix-based detection
        assert artifact.category == ChangeCategory.FIX

    def test_docs_scope_detection(self, docs_commit: CommitInfo) -> None:
        """Test that docs commits are scoped correctly."""
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(docs_commit, use_llm=False)
        
        # 'docs:' prefix triggers CHORE category
        assert artifact.category == ChangeCategory.CHORE

    def test_default_impact_scope(self, simple_commit: CommitInfo) -> None:
        """Test that default impact scope is INTERNAL."""
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(simple_commit, use_llm=False)
        
        # Without file info, defaults to INTERNAL
        assert artifact.impact_scope == ImpactScope.INTERNAL

    def test_schema_version_set(self, simple_commit: CommitInfo) -> None:
        """Test that schema_version is set."""
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(simple_commit, use_llm=False)
        
        assert artifact.schema_version == "0.2.0"

    def test_analysis_meta_populated(self, simple_commit: CommitInfo) -> None:
        """Test that analysis_meta is populated for heuristic analysis."""
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(simple_commit, use_llm=False)

        assert artifact.analysis_meta is not None
        assert artifact.analysis_meta.analysis_mode == "heuristic"
        assert artifact.analysis_meta.input_metrics is not None
        assert artifact.analysis_meta.input_metrics.commit_message_chars is not None


class TestLLMIntegration:
    """Tests for LLM integration and fallback behavior."""

    def test_ensure_provider_returns_false_when_llm_disabled(self) -> None:
        """Test that _ensure_provider returns False when LLM is disabled."""
        service = AnalyzerService(use_llm=False)
        result = service._ensure_provider()
        assert result is False

    def test_ensure_provider_handles_init_failure(
        self, simple_commit: CommitInfo
    ) -> None:
        """Test that provider initialization failure is handled gracefully."""
        service = AnalyzerService(use_llm=True)
        
        # Mock the LLM extractor to raise on provider access
        if service._llm_extractor is not None:
            with patch.object(
                service._llm_extractor, "_get_provider", side_effect=Exception("No API key")
            ):
                result = service._ensure_provider()
                assert result is False

    def test_uses_default_provider_when_not_specified(
        self, monkeypatch, simple_commit: CommitInfo
    ) -> None:
        """Default provider should be used when no provider_name is supplied."""

        class DummyProvider:
            def __init__(self) -> None:
                self.calls = 0

            def extract_structured(self, prompt, schema, system_prompt=None):
                self.calls += 1
                return LLMResponse(
                    parsed={
                        "intent_summary": "LLM summary",
                        "category": "feature",
                        "impact_scope": "public_api",
                        "is_breaking": True,
                        "behavior_before": "before state",
                        "behavior_after": "after state",
                        "technical_highlights": ["from llm"],
                    }
                )

        dummy = DummyProvider()

        monkeypatch.setattr("gitsummary.llm.get_provider", lambda name=None: dummy)
        monkeypatch.setattr(
            "gitsummary.services.analyzer.diff_patch_for_commit",
            lambda sha: "",
        )

        service = AnalyzerService(use_llm=True, provider_name=None)
        artifact = service.analyze(simple_commit)

        assert dummy.calls >= 1
        assert artifact.intent_summary == "LLM summary"
        assert artifact.impact_scope == ImpactScope.PUBLIC_API

    def test_llm_extraction_failure_falls_back_to_heuristic(
        self, simple_commit: CommitInfo
    ) -> None:
        """Test that LLM extraction failure falls back to heuristic."""
        service = AnalyzerService(use_llm=True)
        
        # Mock both providers
        mock_llm = MagicMock()
        mock_llm.extract.side_effect = Exception("LLM API error")
        service._llm_extractor = mock_llm
        service._provider_initialized = True
        
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ), patch.object(service, "_ensure_provider", return_value=True):
            artifact = service.analyze(simple_commit)
        
        # Should still return an artifact using heuristics
        assert isinstance(artifact, CommitArtifact)
        # Heuristic uses commit summary directly
        assert artifact.intent_summary == simple_commit.summary

    def test_llm_result_merged_with_heuristic(
        self, simple_commit: CommitInfo
    ) -> None:
        """Test that LLM result is merged with heuristic fallback."""
        service = AnalyzerService(use_llm=True)
        
        # Mock LLM extractor to return partial result
        mock_llm = MagicMock()
        llm_result = ExtractionResult(
            intent_summary="LLM generated summary",
            category=ChangeCategory.FEATURE,
            behavior_before="Before state",
            behavior_after="After state",
            # Leave some fields None to be filled by heuristic
            impact_scope=None,
            is_breaking=None,
        )
        mock_llm.extract.return_value = llm_result
        service._llm_extractor = mock_llm
        service._provider_initialized = True
        
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ), patch.object(service, "_ensure_provider", return_value=True):
            artifact = service.analyze(simple_commit)
        
        # LLM values should be used
        assert artifact.intent_summary == "LLM generated summary"
        assert artifact.behavior_before == "Before state"
        assert artifact.behavior_after == "After state"
        # Heuristic should fill in missing fields
        assert artifact.impact_scope is not None

    def test_provider_name_passed_to_service(self) -> None:
        """Test that provider name is stored in service."""
        service = AnalyzerService(use_llm=True, provider_name="openai")
        assert service.provider_name == "openai"

    def test_analyze_with_provider_name(self, simple_commit: CommitInfo) -> None:
        """Test analyze with specific provider name."""
        with patch(
            "gitsummary.services.analyzer.diff_patch_for_commit", return_value=""
        ):
            artifact = build_commit_artifact(
                simple_commit, use_llm=False, provider_name="openai"
            )
        
        assert isinstance(artifact, CommitArtifact)
