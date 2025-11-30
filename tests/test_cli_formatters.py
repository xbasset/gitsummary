"""Tests for CLI output formatters.

Tests the formatting functions in gitsummary.cli.formatters.
"""

from __future__ import annotations

import json

import pytest
import yaml

from gitsummary.cli.formatters import (
    format_artifact_brief,
    format_artifact_human,
    format_artifact_json,
    format_artifact_yaml,
    format_commit_status,
)
from gitsummary.core import ChangeCategory, CommitArtifact, CommitInfo, ImpactScope


class TestFormatArtifactHuman:
    """Tests for format_artifact_human function."""

    def test_includes_short_sha(self, feature_artifact: CommitArtifact) -> None:
        """Test that output includes short SHA."""
        output = format_artifact_human(feature_artifact)
        assert "abc1234" in output

    def test_includes_intent_summary(self, feature_artifact: CommitArtifact) -> None:
        """Test that output includes intent summary."""
        output = format_artifact_human(feature_artifact)
        # Summary is truncated to 50 chars
        assert "authentication" in output or "Add user" in output

    def test_includes_category(self, feature_artifact: CommitArtifact) -> None:
        """Test that output includes category."""
        output = format_artifact_human(feature_artifact)
        assert "feature" in output.lower()

    def test_includes_impact_scope(self, feature_artifact: CommitArtifact) -> None:
        """Test that output includes impact scope."""
        output = format_artifact_human(feature_artifact)
        assert "public_api" in output.lower()

    def test_includes_breaking_status(
        self, breaking_artifact: CommitArtifact
    ) -> None:
        """Test that breaking status is shown."""
        output = format_artifact_human(breaking_artifact)
        assert "Yes" in output  # Breaking: Yes

    def test_includes_technical_highlights(
        self, feature_artifact: CommitArtifact
    ) -> None:
        """Test that technical highlights are shown."""
        output = format_artifact_human(feature_artifact)
        assert "Technical" in output

    def test_box_drawing_characters(self, feature_artifact: CommitArtifact) -> None:
        """Test that box drawing characters are used."""
        output = format_artifact_human(feature_artifact)
        assert "╭" in output
        assert "╰" in output
        assert "│" in output

    def test_handles_long_summary(self) -> None:
        """Test that long summaries are truncated."""
        artifact = CommitArtifact(
            commit_hash="abc123",
            intent_summary="A" * 100,  # Very long summary
            category=ChangeCategory.FEATURE,
            impact_scope=ImpactScope.INTERNAL,
        )
        output = format_artifact_human(artifact)
        # Should not break the box formatting
        assert "╭" in output
        assert "╰" in output


class TestFormatArtifactBrief:
    """Tests for format_artifact_brief function."""

    def test_single_line_output(self, feature_artifact: CommitArtifact) -> None:
        """Test that output is a single line."""
        output = format_artifact_brief(feature_artifact)
        assert "\n" not in output

    def test_includes_short_sha(self, feature_artifact: CommitArtifact) -> None:
        """Test that output includes short SHA."""
        output = format_artifact_brief(feature_artifact)
        assert "abc1234" in output

    def test_includes_category_tag(self, feature_artifact: CommitArtifact) -> None:
        """Test that category is shown in brackets."""
        output = format_artifact_brief(feature_artifact)
        assert "[feature]" in output

    def test_includes_intent_summary(self, feature_artifact: CommitArtifact) -> None:
        """Test that intent summary is included."""
        output = format_artifact_brief(feature_artifact)
        assert "authentication" in output.lower()

    def test_truncates_long_summary(self) -> None:
        """Test that long summaries are truncated."""
        artifact = CommitArtifact(
            commit_hash="abc123",
            intent_summary="A" * 100,
            category=ChangeCategory.FIX,
            impact_scope=ImpactScope.INTERNAL,
        )
        output = format_artifact_brief(artifact)
        # Should be truncated to 60 chars
        assert len(output) < 150


class TestFormatArtifactYaml:
    """Tests for format_artifact_yaml function."""

    def test_valid_yaml(self, feature_artifact: CommitArtifact) -> None:
        """Test that output is valid YAML."""
        output = format_artifact_yaml(feature_artifact)
        data = yaml.safe_load(output)
        assert isinstance(data, dict)

    def test_contains_all_fields(self, feature_artifact: CommitArtifact) -> None:
        """Test that all artifact fields are present."""
        output = format_artifact_yaml(feature_artifact)
        data = yaml.safe_load(output)
        
        assert "commit_hash" in data
        assert "intent_summary" in data
        assert "category" in data
        assert "impact_scope" in data

    def test_enum_as_string(self, feature_artifact: CommitArtifact) -> None:
        """Test that enums are serialized as strings."""
        output = format_artifact_yaml(feature_artifact)
        data = yaml.safe_load(output)
        
        assert data["category"] == "feature"
        assert data["impact_scope"] == "public_api"


class TestFormatArtifactJson:
    """Tests for format_artifact_json function."""

    def test_valid_json(self, feature_artifact: CommitArtifact) -> None:
        """Test that output is valid JSON."""
        output = format_artifact_json(feature_artifact)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_contains_all_fields(self, feature_artifact: CommitArtifact) -> None:
        """Test that all artifact fields are present."""
        output = format_artifact_json(feature_artifact)
        data = json.loads(output)
        
        assert "commit_hash" in data
        assert "intent_summary" in data
        assert "category" in data

    def test_pretty_printed(self, feature_artifact: CommitArtifact) -> None:
        """Test that JSON is pretty-printed with indentation."""
        output = format_artifact_json(feature_artifact)
        # Pretty-printed JSON has multiple lines
        assert output.count("\n") > 5


class TestFormatCommitStatus:
    """Tests for format_commit_status function."""

    def test_analyzed_commit(self, simple_commit: CommitInfo) -> None:
        """Test formatting for analyzed commit."""
        output = format_commit_status(simple_commit, analyzed=True)
        assert "✓" in output
        assert simple_commit.short_sha in output

    def test_unanalyzed_commit(self, simple_commit: CommitInfo) -> None:
        """Test formatting for unanalyzed commit."""
        output = format_commit_status(simple_commit, analyzed=False)
        assert "○" in output
        assert simple_commit.short_sha in output

    def test_includes_summary(self, simple_commit: CommitInfo) -> None:
        """Test that commit summary is included."""
        output = format_commit_status(simple_commit, analyzed=True)
        assert "authentication" in output.lower()

    def test_truncates_long_summary(self) -> None:
        """Test that long summaries are truncated."""
        from datetime import datetime, timezone

        commit = CommitInfo(
            sha="abc123",
            short_sha="abc",
            author_name="Test",
            author_email="test@test.com",
            date=datetime.now(timezone.utc),
            summary="A" * 100,
            body="",
            parent_shas=[],
        )
        output = format_commit_status(commit, analyzed=True)
        # Should be truncated to 60 chars for summary
        assert len(output) < 100

