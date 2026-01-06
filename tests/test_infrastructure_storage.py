"""Tests for infrastructure storage module.

Tests the YAML serialization and deserialization of artifacts,
as well as the storage operations (save, load, exists, remove, list).
"""

from __future__ import annotations

from unittest.mock import patch
import os

import pytest
import yaml

from gitsummary.core import ChangeCategory, CommitArtifact, ImpactScope
from gitsummary.infrastructure.storage import (
    artifact_to_yaml,
    yaml_to_artifact,
    save_artifact_to_notes,
    load_artifact_from_notes,
    artifact_exists_in_notes,
    remove_artifact_from_notes,
    list_analyzed_commits,
    load_artifacts_for_range,
    _get_notes_ref,
    SCHEMA_VERSION,
)


class TestArtifactToYaml:
    """Tests for artifact_to_yaml function."""

    def test_basic_serialization(self, feature_artifact: CommitArtifact) -> None:
        """Test that artifact is serialized to valid YAML."""
        yaml_str = artifact_to_yaml(feature_artifact)
        
        # Should be valid YAML
        data = yaml.safe_load(yaml_str)
        assert isinstance(data, dict)

    def test_contains_all_fields(self, feature_artifact: CommitArtifact) -> None:
        """Test that all artifact fields are present in YAML."""
        yaml_str = artifact_to_yaml(feature_artifact)
        data = yaml.safe_load(yaml_str)
        
        assert "commit_hash" in data
        assert "intent_summary" in data
        assert "category" in data
        assert "impact_scope" in data
        assert "is_breaking" in data
        assert "technical_highlights" in data

    def test_includes_metadata(self, feature_artifact: CommitArtifact) -> None:
        """Test that schema and tool versions are included."""
        yaml_str = artifact_to_yaml(feature_artifact)
        data = yaml.safe_load(yaml_str)
        
        assert "schema_version" in data
        assert "tool_version" in data
        assert data["schema_version"] == SCHEMA_VERSION

    def test_enum_values_serialized_as_strings(
        self, feature_artifact: CommitArtifact
    ) -> None:
        """Test that enum values are serialized as strings."""
        yaml_str = artifact_to_yaml(feature_artifact)
        data = yaml.safe_load(yaml_str)
        
        assert data["category"] == "feature"
        assert data["impact_scope"] == "public_api"

    def test_technical_highlights_as_list(
        self, feature_artifact: CommitArtifact
    ) -> None:
        """Test that technical_highlights is serialized as a YAML list."""
        yaml_str = artifact_to_yaml(feature_artifact)
        data = yaml.safe_load(yaml_str)
        
        assert isinstance(data["technical_highlights"], list)
        assert len(data["technical_highlights"]) == 2

    def test_optional_fields_when_none(self) -> None:
        """Test serialization when optional fields are None."""
        artifact = CommitArtifact(
            commit_hash="abc123",
            intent_summary="Test commit",
            category=ChangeCategory.FIX,
            impact_scope=ImpactScope.INTERNAL,
            behavior_before=None,
            behavior_after=None,
        )
        yaml_str = artifact_to_yaml(artifact)
        data = yaml.safe_load(yaml_str)
        
        assert data["behavior_before"] is None
        assert data["behavior_after"] is None

    def test_human_readable_format(self, feature_artifact: CommitArtifact) -> None:
        """Test that YAML is human-readable (block style, not inline)."""
        yaml_str = artifact_to_yaml(feature_artifact)
        
        # Should not have inline list/dict syntax
        assert "{" not in yaml_str or "{{" in yaml_str  # Allow Jinja-like templates
        # Should have newlines (block style)
        assert yaml_str.count("\n") > 5


class TestYamlToArtifact:
    """Tests for yaml_to_artifact function."""

    def test_basic_deserialization(self, feature_artifact: CommitArtifact) -> None:
        """Test round-trip serialization/deserialization."""
        yaml_str = artifact_to_yaml(feature_artifact)
        restored = yaml_to_artifact(yaml_str)
        
        assert restored.commit_hash == feature_artifact.commit_hash
        assert restored.intent_summary == feature_artifact.intent_summary

    def test_enum_values_restored(self, feature_artifact: CommitArtifact) -> None:
        """Test that enum values are properly restored."""
        yaml_str = artifact_to_yaml(feature_artifact)
        restored = yaml_to_artifact(yaml_str)
        
        assert restored.category == ChangeCategory.FEATURE
        assert restored.impact_scope == ImpactScope.PUBLIC_API

    def test_metadata_stripped(self, feature_artifact: CommitArtifact) -> None:
        """Test that schema_version and tool_version are stripped."""
        yaml_str = artifact_to_yaml(feature_artifact)
        restored = yaml_to_artifact(yaml_str)
        
        # The artifact should have its own schema_version field
        # but the metadata fields from storage are removed
        assert restored.schema_version == "0.2.0"  # artifact's own field

    def test_optional_fields_restored_as_none(self) -> None:
        """Test that None values are properly restored."""
        artifact = CommitArtifact(
            commit_hash="abc123",
            intent_summary="Test",
            category=ChangeCategory.CHORE,
            impact_scope=ImpactScope.INTERNAL,
        )
        yaml_str = artifact_to_yaml(artifact)
        restored = yaml_to_artifact(yaml_str)
        
        assert restored.behavior_before is None
        assert restored.behavior_after is None

    def test_technical_highlights_list(self, feature_artifact: CommitArtifact) -> None:
        """Test that technical_highlights list is preserved."""
        yaml_str = artifact_to_yaml(feature_artifact)
        restored = yaml_to_artifact(yaml_str)
        
        assert len(restored.technical_highlights) == len(
            feature_artifact.technical_highlights
        )

    def test_breaking_flag_preserved(self, breaking_artifact: CommitArtifact) -> None:
        """Test that is_breaking flag is preserved."""
        yaml_str = artifact_to_yaml(breaking_artifact)
        restored = yaml_to_artifact(yaml_str)
        
        assert restored.is_breaking is True

    def test_invalid_yaml_raises(self) -> None:
        """Test that invalid YAML raises an error."""
        with pytest.raises(Exception):
            yaml_to_artifact("not: valid: yaml: {{")

    def test_missing_required_field_raises(self) -> None:
        """Test that missing required fields raise validation error."""
        yaml_content = """
commit_hash: abc123
# missing intent_summary
category: fix
impact_scope: internal
"""
        with pytest.raises(Exception):  # Pydantic validation error
            yaml_to_artifact(yaml_content)


class TestRoundTrip:
    """Tests for complete round-trip serialization."""

    def test_feature_artifact_roundtrip(
        self, feature_artifact: CommitArtifact
    ) -> None:
        """Test complete round-trip for feature artifact."""
        yaml_str = artifact_to_yaml(feature_artifact)
        restored = yaml_to_artifact(yaml_str)
        
        assert restored.commit_hash == feature_artifact.commit_hash
        assert restored.intent_summary == feature_artifact.intent_summary
        assert restored.category == feature_artifact.category
        assert restored.impact_scope == feature_artifact.impact_scope
        assert restored.is_breaking == feature_artifact.is_breaking
        assert (
            restored.technical_highlights == feature_artifact.technical_highlights
        )

    def test_fix_artifact_roundtrip(self, fix_artifact: CommitArtifact) -> None:
        """Test complete round-trip for fix artifact."""
        yaml_str = artifact_to_yaml(fix_artifact)
        restored = yaml_to_artifact(yaml_str)
        
        assert restored.category == ChangeCategory.FIX
        assert restored.behavior_before == fix_artifact.behavior_before
        assert restored.behavior_after == fix_artifact.behavior_after

    def test_security_artifact_roundtrip(
        self, security_artifact: CommitArtifact
    ) -> None:
        """Test complete round-trip for security artifact."""
        yaml_str = artifact_to_yaml(security_artifact)
        restored = yaml_to_artifact(yaml_str)
        
        assert restored.category == ChangeCategory.SECURITY

    def test_breaking_artifact_roundtrip(
        self, breaking_artifact: CommitArtifact
    ) -> None:
        """Test complete round-trip for breaking change artifact."""
        yaml_str = artifact_to_yaml(breaking_artifact)
        restored = yaml_to_artifact(yaml_str)
        
        assert restored.is_breaking is True
        assert restored.impact_scope == ImpactScope.PUBLIC_API

    def test_minimal_artifact_roundtrip(self) -> None:
        """Test round-trip for artifact with only required fields."""
        artifact = CommitArtifact(
            commit_hash="minimal123",
            intent_summary="Minimal commit",
            category=ChangeCategory.CHORE,
            impact_scope=ImpactScope.UNKNOWN,
        )
        yaml_str = artifact_to_yaml(artifact)
        restored = yaml_to_artifact(yaml_str)
        
        assert restored.commit_hash == artifact.commit_hash
        assert restored.technical_highlights == []
        assert restored.is_breaking is False


class TestGetNotesRef:
    """Tests for _get_notes_ref function."""

    def test_returns_default_when_no_env(self) -> None:
        """Test that default notes ref is returned."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear the GITSUMMARY_NOTES_REF if it exists
            os.environ.pop("GITSUMMARY_NOTES_REF", None)
            result = _get_notes_ref()
            assert result == "refs/notes/intent"

    def test_returns_env_value_when_set(self) -> None:
        """Test that env var value is used when set."""
        with patch.dict(os.environ, {"GITSUMMARY_NOTES_REF": "refs/notes/custom"}):
            result = _get_notes_ref()
            assert result == "refs/notes/custom"


class TestSaveArtifactToNotes:
    """Tests for save_artifact_to_notes function."""

    def test_saves_artifact(self, feature_artifact: CommitArtifact) -> None:
        """Test that artifact is saved to notes."""
        with patch("gitsummary.infrastructure.storage.notes_write") as mock_write, \
             patch("gitsummary.infrastructure.storage.notes_exists") as mock_exists:
            mock_exists.return_value = False
            result = save_artifact_to_notes(feature_artifact)

            assert result == feature_artifact.commit_hash
            mock_write.assert_called_once()
            # Check that YAML content is passed
            call_args = mock_write.call_args
            assert "commit_hash:" in call_args[0][1]

    def test_overwrites_with_force_true(self, feature_artifact: CommitArtifact) -> None:
        """Test that existing notes are overwritten with force=True."""
        with patch("gitsummary.infrastructure.storage.notes_write") as mock_write, \
             patch("gitsummary.infrastructure.storage.notes_exists") as mock_exists:
            mock_exists.return_value = True
            # force=True is default
            result = save_artifact_to_notes(feature_artifact)

            assert result == feature_artifact.commit_hash
            mock_write.assert_called_once()

    def test_raises_when_exists_and_not_force(
        self, feature_artifact: CommitArtifact
    ) -> None:
        """Test that FileExistsError is raised when note exists and force=False."""
        with patch("gitsummary.infrastructure.storage.notes_exists") as mock_exists:
            mock_exists.return_value = True
            with pytest.raises(FileExistsError):
                save_artifact_to_notes(feature_artifact, force=False)

    def test_uses_custom_notes_ref(self, feature_artifact: CommitArtifact) -> None:
        """Test that custom notes ref is passed through."""
        with patch("gitsummary.infrastructure.storage.notes_write") as mock_write, \
             patch("gitsummary.infrastructure.storage.notes_exists") as mock_exists:
            mock_exists.return_value = False
            save_artifact_to_notes(
                feature_artifact, notes_ref="refs/notes/custom"
            )

            call_args = mock_write.call_args
            assert call_args[0][2] == "refs/notes/custom"


class TestLoadArtifactFromNotes:
    """Tests for load_artifact_from_notes function."""

    def test_loads_artifact(self, feature_artifact: CommitArtifact) -> None:
        """Test that artifact is loaded from notes."""
        yaml_content = artifact_to_yaml(feature_artifact)
        with patch("gitsummary.infrastructure.storage.notes_read") as mock_read:
            mock_read.return_value = yaml_content
            result = load_artifact_from_notes(feature_artifact.commit_hash)

            assert result is not None
            assert result.commit_hash == feature_artifact.commit_hash
            assert result.intent_summary == feature_artifact.intent_summary

    def test_returns_none_when_not_found(self) -> None:
        """Test that None is returned when note doesn't exist."""
        with patch("gitsummary.infrastructure.storage.notes_read") as mock_read:
            mock_read.return_value = None
            result = load_artifact_from_notes("nonexistent")

            assert result is None

    def test_uses_custom_notes_ref(self) -> None:
        """Test that custom notes ref is passed through."""
        with patch("gitsummary.infrastructure.storage.notes_read") as mock_read:
            mock_read.return_value = None
            load_artifact_from_notes("abc123", notes_ref="refs/notes/custom")

            mock_read.assert_called_once_with("abc123", "refs/notes/custom")


class TestArtifactExistsInNotes:
    """Tests for artifact_exists_in_notes function."""

    def test_returns_true_when_exists(self) -> None:
        """Test that True is returned when artifact exists."""
        with patch("gitsummary.infrastructure.storage.notes_exists") as mock_exists:
            mock_exists.return_value = True
            result = artifact_exists_in_notes("abc123")

            assert result is True

    def test_returns_false_when_not_exists(self) -> None:
        """Test that False is returned when artifact doesn't exist."""
        with patch("gitsummary.infrastructure.storage.notes_exists") as mock_exists:
            mock_exists.return_value = False
            result = artifact_exists_in_notes("abc123")

            assert result is False


class TestRemoveArtifactFromNotes:
    """Tests for remove_artifact_from_notes function."""

    def test_returns_true_when_removed(self) -> None:
        """Test that True is returned when artifact is removed."""
        with patch("gitsummary.infrastructure.storage.notes_remove") as mock_remove:
            mock_remove.return_value = True
            result = remove_artifact_from_notes("abc123")

            assert result is True

    def test_returns_false_when_not_found(self) -> None:
        """Test that False is returned when artifact doesn't exist."""
        with patch("gitsummary.infrastructure.storage.notes_remove") as mock_remove:
            mock_remove.return_value = False
            result = remove_artifact_from_notes("abc123")

            assert result is False


class TestListAnalyzedCommits:
    """Tests for list_analyzed_commits function."""

    def test_returns_dict_of_status(self) -> None:
        """Test that dict mapping SHA to analyzed status is returned."""
        with patch("gitsummary.infrastructure.storage.notes_exists") as mock_exists:
            mock_exists.side_effect = [True, False, True]
            result = list_analyzed_commits(["sha1", "sha2", "sha3"])

            assert result == {"sha1": True, "sha2": False, "sha3": True}

    def test_empty_list_returns_empty_dict(self) -> None:
        """Test that empty list returns empty dict."""
        result = list_analyzed_commits([])
        assert result == {}


class TestLoadArtifactsForRange:
    """Tests for load_artifacts_for_range function."""

    def test_loads_all_artifacts(self, feature_artifact: CommitArtifact) -> None:
        """Test that all artifacts are loaded for a range."""
        yaml_content = artifact_to_yaml(feature_artifact)
        with patch("gitsummary.infrastructure.storage.notes_read") as mock_read:
            # First sha has artifact, second doesn't
            mock_read.side_effect = [yaml_content, None]
            result = load_artifacts_for_range(["sha1", "sha2"])

            assert len(result) == 2
            assert result["sha1"] is not None
            assert result["sha2"] is None

    def test_empty_list_returns_empty_dict(self) -> None:
        """Test that empty list returns empty dict."""
        result = load_artifacts_for_range([])
        assert result == {}
