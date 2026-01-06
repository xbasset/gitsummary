"""Tests for CommitArtifact model.

Tests the Pydantic model in gitsummary.core.artifact.
"""

from __future__ import annotations

import json

import pytest
import yaml

from gitsummary.core import ChangeCategory, CommitArtifact, ImpactScope


class TestCommitArtifact:
    """Tests for CommitArtifact Pydantic model."""

    def test_creation_with_required_fields(self) -> None:
        """Test creating artifact with only required fields."""
        artifact = CommitArtifact(
            commit_hash="abc123",
            intent_summary="Test commit",
            category=ChangeCategory.FIX,
            impact_scope=ImpactScope.INTERNAL,
        )
        assert artifact.commit_hash == "abc123"
        assert artifact.intent_summary == "Test commit"
        assert artifact.category == ChangeCategory.FIX
        assert artifact.impact_scope == ImpactScope.INTERNAL
        assert artifact.is_breaking is False  # default
        assert artifact.technical_highlights == []  # default
        assert artifact.behavior_before is None  # default
        assert artifact.behavior_after is None  # default

    def test_creation_with_all_fields(self, feature_artifact: CommitArtifact) -> None:
        """Test creating artifact with all fields populated."""
        assert feature_artifact.commit_hash == "abc1234567890abcdef1234567890abcdef123456"
        assert "authentication" in feature_artifact.intent_summary
        assert feature_artifact.category == ChangeCategory.FEATURE
        assert feature_artifact.impact_scope == ImpactScope.PUBLIC_API
        assert feature_artifact.is_breaking is False
        assert len(feature_artifact.technical_highlights) == 2
        assert feature_artifact.behavior_before is not None
        assert feature_artifact.behavior_after is not None

    def test_breaking_change_artifact(self, breaking_artifact: CommitArtifact) -> None:
        """Test artifact with breaking change flag."""
        assert breaking_artifact.is_breaking is True

    def test_schema_version_default(self) -> None:
        """Test that schema_version has a default value."""
        artifact = CommitArtifact(
            commit_hash="abc123",
            intent_summary="Test",
            category=ChangeCategory.CHORE,
            impact_scope=ImpactScope.INTERNAL,
        )
        assert artifact.schema_version == "0.2.0"

    def test_model_dump_json(self, feature_artifact: CommitArtifact) -> None:
        """Test JSON serialization via model_dump_json."""
        json_str = feature_artifact.model_dump_json()
        data = json.loads(json_str)
        
        assert data["commit_hash"] == feature_artifact.commit_hash
        assert data["category"] == "feature"  # enum serialized as string
        assert data["impact_scope"] == "public_api"

    def test_model_dump(self, feature_artifact: CommitArtifact) -> None:
        """Test dict serialization via model_dump."""
        data = feature_artifact.model_dump()
        
        assert isinstance(data, dict)
        assert data["commit_hash"] == feature_artifact.commit_hash
        # Enum values are enum instances unless mode='json'
        assert data["category"] == ChangeCategory.FEATURE

    def test_model_dump_json_mode(self, feature_artifact: CommitArtifact) -> None:
        """Test dict serialization with JSON mode for enum values."""
        data = feature_artifact.model_dump(mode="json")
        
        assert data["category"] == "feature"  # string, not enum
        assert data["impact_scope"] == "public_api"

    def test_yaml_serialization(self, feature_artifact: CommitArtifact) -> None:
        """Test YAML serialization works correctly."""
        data = feature_artifact.model_dump(mode="json")
        yaml_str = yaml.dump(data, default_flow_style=False)
        
        assert "commit_hash:" in yaml_str
        assert "category:" in yaml_str
        assert "feature" in yaml_str

    def test_yaml_deserialization(self, feature_artifact: CommitArtifact) -> None:
        """Test YAML round-trip serialization."""
        data = feature_artifact.model_dump(mode="json")
        yaml_str = yaml.dump(data, default_flow_style=False)
        loaded = yaml.safe_load(yaml_str)
        
        restored = CommitArtifact(**loaded)
        assert restored.commit_hash == feature_artifact.commit_hash
        assert restored.category == feature_artifact.category

    def test_category_enum_validation(self) -> None:
        """Test that invalid category raises validation error."""
        with pytest.raises(Exception):  # Pydantic validation error
            CommitArtifact(
                commit_hash="abc",
                intent_summary="Test",
                category="invalid",  # type: ignore[arg-type]
                impact_scope=ImpactScope.INTERNAL,
            )

    def test_impact_scope_enum_validation(self) -> None:
        """Test that invalid impact_scope raises validation error."""
        with pytest.raises(Exception):  # Pydantic validation error
            CommitArtifact(
                commit_hash="abc",
                intent_summary="Test",
                category=ChangeCategory.FIX,
                impact_scope="invalid",  # type: ignore[arg-type]
            )

    def test_technical_highlights_list(self) -> None:
        """Test technical_highlights is properly a list."""
        artifact = CommitArtifact(
            commit_hash="abc",
            intent_summary="Test",
            category=ChangeCategory.FEATURE,
            impact_scope=ImpactScope.PUBLIC_API,
            technical_highlights=["Highlight 1", "Highlight 2"],
        )
        assert len(artifact.technical_highlights) == 2
        assert "Highlight 1" in artifact.technical_highlights

    def test_optional_behavior_fields(self) -> None:
        """Test that behavior fields are truly optional."""
        artifact = CommitArtifact(
            commit_hash="abc",
            intent_summary="Test",
            category=ChangeCategory.FIX,
            impact_scope=ImpactScope.INTERNAL,
            behavior_before=None,
            behavior_after="Now it works",
        )
        assert artifact.behavior_before is None
        assert artifact.behavior_after == "Now it works"
