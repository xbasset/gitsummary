"""Tests for ReleaseNote model.

Tests the Pydantic models in gitsummary.core.release_note.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
import yaml

from gitsummary.core import (
    BugFix,
    CallToAction,
    Deprecation,
    Feature,
    Highlight,
    Improvement,
    KnownIssue,
    ReleaseNote,
    ReleaseNoteHeader,
    ReleaseNoteMetadata,
    SourceCommit,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_metadata() -> ReleaseNoteMetadata:
    """Sample metadata for tests."""
    return ReleaseNoteMetadata(
        generated_at=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        generator_version="0.2.0",
        llm_provider="openai",
        llm_model="gpt-4o",
        revision_range="v0.1.0..v0.2.0",
        tip_commit="abc123def456789012345678901234567890abcd",
        commit_count=15,
        analyzed_count=14,
        source_commits=[
            SourceCommit(sha="abc1234", category="feature"),
            SourceCommit(sha="def5678", category="fix"),
        ],
    )


@pytest.fixture
def sample_header() -> ReleaseNoteHeader:
    """Sample header for tests."""
    return ReleaseNoteHeader(
        product_name="TestApp",
        version="v0.2.0",
        release_date="2025-01-15",
        theme="Faster syncing and major stability improvements.",
    )


@pytest.fixture
def sample_release_note(
    sample_metadata: ReleaseNoteMetadata,
    sample_header: ReleaseNoteHeader,
) -> ReleaseNote:
    """A fully populated release note for tests."""
    return ReleaseNote(
        metadata=sample_metadata,
        header=sample_header,
        highlights=[
            Highlight(emoji="🚀", type="new", summary="Smart Search feature"),
            Highlight(emoji="✨", type="improved", summary="2x faster sync"),
            Highlight(emoji="🛠️", type="fixed", summary="Login crash fixed"),
            Highlight(emoji="⚠️", type="breaking", summary="API v1 deprecated"),
        ],
        features=[
            Feature(
                title="Smart Search",
                description="Find files even with typos.",
                user_benefit="Locate content faster in large workspaces.",
                commits=["abc1234"],
            ),
        ],
        improvements=[
            Improvement(summary="Sync speed improved by 100%", commits=["def5678"]),
        ],
        fixes=[
            BugFix(summary="Fixed login crash on Android 14", commits=["ghi9012"]),
        ],
        deprecations=[
            Deprecation(
                what="API v1 tokens",
                reason="Migrating to OAuth for better security",
                migration="Use the new Developer Portal",
                deadline="2025-08-01",
                commits=["jkl3456"],
            ),
        ],
        known_issues=[
            KnownIssue(
                issue="Duplicated items in Recent Files",
                status="Fix coming next week",
            ),
        ],
        call_to_action=CallToAction(
            documentation_url="https://docs.example.com",
            migration_guide_url="https://docs.example.com/migrate",
            support_url="https://support.example.com",
        ),
    )


@pytest.fixture
def minimal_release_note() -> ReleaseNote:
    """A minimal release note with only required fields."""
    return ReleaseNote(
        metadata=ReleaseNoteMetadata(
            revision_range="HEAD~5..HEAD",
            tip_commit="abc123def456789012345678901234567890abcd",
            commit_count=5,
            analyzed_count=5,
        ),
        header=ReleaseNoteHeader(
            product_name="MinimalApp",
            version="v1.0.0",
            release_date="2025-01-15",
            theme="Initial release.",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# SourceCommit Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestSourceCommit:
    """Tests for SourceCommit model."""

    def test_creation(self) -> None:
        """Test creating a source commit reference."""
        sc = SourceCommit(sha="abc1234", category="feature")
        assert sc.sha == "abc1234"
        assert sc.category == "feature"

    def test_serialization(self) -> None:
        """Test JSON serialization."""
        sc = SourceCommit(sha="abc1234", category="fix")
        data = sc.model_dump(mode="json")
        assert data["sha"] == "abc1234"
        assert data["category"] == "fix"


# ─────────────────────────────────────────────────────────────────────────────
# ReleaseNoteMetadata Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestReleaseNoteMetadata:
    """Tests for ReleaseNoteMetadata model."""

    def test_required_fields(self) -> None:
        """Test creating metadata with required fields."""
        meta = ReleaseNoteMetadata(
            revision_range="v0.1.0..v0.2.0",
            tip_commit="abc123",
            commit_count=10,
            analyzed_count=8,
        )
        assert meta.revision_range == "v0.1.0..v0.2.0"
        assert meta.commit_count == 10
        assert meta.analyzed_count == 8

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        meta = ReleaseNoteMetadata(
            revision_range="HEAD~5..HEAD",
            tip_commit="abc123",
            commit_count=5,
            analyzed_count=5,
        )
        assert meta.generator_version == "0.2.0"
        assert meta.llm_provider is None
        assert meta.llm_model is None
        assert meta.source_commits == []
        # generated_at should be auto-set
        assert meta.generated_at is not None

    def test_llm_metadata(self, sample_metadata: ReleaseNoteMetadata) -> None:
        """Test LLM provider metadata."""
        assert sample_metadata.llm_provider == "openai"
        assert sample_metadata.llm_model == "gpt-4o"

    def test_source_commits(self, sample_metadata: ReleaseNoteMetadata) -> None:
        """Test source commits list."""
        assert len(sample_metadata.source_commits) == 2
        assert sample_metadata.source_commits[0].sha == "abc1234"


# ─────────────────────────────────────────────────────────────────────────────
# ReleaseNoteHeader Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestReleaseNoteHeader:
    """Tests for ReleaseNoteHeader model."""

    def test_all_fields(self, sample_header: ReleaseNoteHeader) -> None:
        """Test all header fields."""
        assert sample_header.product_name == "TestApp"
        assert sample_header.version == "v0.2.0"
        assert sample_header.release_date == "2025-01-15"
        assert "stability" in sample_header.theme


# ─────────────────────────────────────────────────────────────────────────────
# Highlight Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHighlight:
    """Tests for Highlight model."""

    def test_creation(self) -> None:
        """Test creating a highlight."""
        hl = Highlight(emoji="🚀", type="new", summary="New feature added")
        assert hl.emoji == "🚀"
        assert hl.type == "new"
        assert hl.summary == "New feature added"

    def test_all_types(self) -> None:
        """Test all valid highlight types."""
        valid_types = ["new", "improved", "fixed", "deprecated", "breaking", "security"]
        for hl_type in valid_types:
            hl = Highlight(emoji="📝", type=hl_type, summary="Test")  # type: ignore[arg-type]
            assert hl.type == hl_type

    def test_invalid_type_rejected(self) -> None:
        """Test that invalid highlight types are rejected."""
        with pytest.raises(Exception):  # Pydantic validation error
            Highlight(emoji="📝", type="invalid", summary="Test")  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# Feature Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFeature:
    """Tests for Feature model."""

    def test_creation(self) -> None:
        """Test creating a feature."""
        feat = Feature(
            title="Smart Search",
            description="Find files with typos.",
            user_benefit="Faster file discovery.",
            commits=["abc1234"],
        )
        assert feat.title == "Smart Search"
        assert feat.description == "Find files with typos."
        assert feat.user_benefit == "Faster file discovery."
        assert feat.commits == ["abc1234"]

    def test_default_commits_list(self) -> None:
        """Test that commits defaults to empty list."""
        feat = Feature(
            title="Test",
            description="Test feature",
            user_benefit="Test benefit",
        )
        assert feat.commits == []


# ─────────────────────────────────────────────────────────────────────────────
# Improvement Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestImprovement:
    """Tests for Improvement model."""

    def test_creation(self) -> None:
        """Test creating an improvement."""
        imp = Improvement(summary="50% faster startup", commits=["abc1234"])
        assert imp.summary == "50% faster startup"
        assert imp.commits == ["abc1234"]

    def test_default_commits_list(self) -> None:
        """Test that commits defaults to empty list."""
        imp = Improvement(summary="Test improvement")
        assert imp.commits == []


# ─────────────────────────────────────────────────────────────────────────────
# BugFix Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBugFix:
    """Tests for BugFix model."""

    def test_creation(self) -> None:
        """Test creating a bug fix."""
        fix = BugFix(summary="Fixed crash on login", commits=["abc1234"])
        assert fix.summary == "Fixed crash on login"
        assert fix.commits == ["abc1234"]


# ─────────────────────────────────────────────────────────────────────────────
# Deprecation Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDeprecation:
    """Tests for Deprecation model."""

    def test_creation(self) -> None:
        """Test creating a deprecation."""
        dep = Deprecation(
            what="API v1",
            reason="Migrating to v2",
            migration="Use API v2 instead",
            deadline="2025-08-01",
            commits=["abc1234"],
        )
        assert dep.what == "API v1"
        assert dep.reason == "Migrating to v2"
        assert dep.migration == "Use API v2 instead"
        assert dep.deadline == "2025-08-01"

    def test_optional_deadline(self) -> None:
        """Test that deadline is optional."""
        dep = Deprecation(
            what="Old feature",
            reason="No longer needed",
            migration="Remove usage",
        )
        assert dep.deadline is None


# ─────────────────────────────────────────────────────────────────────────────
# KnownIssue Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestKnownIssue:
    """Tests for KnownIssue model."""

    def test_creation(self) -> None:
        """Test creating a known issue."""
        issue = KnownIssue(
            issue="Search may timeout on large datasets",
            status="Fix in progress",
        )
        assert issue.issue == "Search may timeout on large datasets"
        assert issue.status == "Fix in progress"


# ─────────────────────────────────────────────────────────────────────────────
# CallToAction Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCallToAction:
    """Tests for CallToAction model."""

    def test_creation(self) -> None:
        """Test creating a call to action."""
        cta = CallToAction(
            documentation_url="https://docs.example.com",
            migration_guide_url="https://docs.example.com/migrate",
            support_url="https://support.example.com",
        )
        assert cta.documentation_url == "https://docs.example.com"
        assert cta.migration_guide_url is not None
        assert cta.support_url is not None

    def test_all_optional(self) -> None:
        """Test that all fields are optional."""
        cta = CallToAction()
        assert cta.documentation_url is None
        assert cta.migration_guide_url is None
        assert cta.support_url is None


# ─────────────────────────────────────────────────────────────────────────────
# ReleaseNote Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestReleaseNote:
    """Tests for ReleaseNote model."""

    def test_creation_with_all_fields(
        self, sample_release_note: ReleaseNote
    ) -> None:
        """Test creating a release note with all fields."""
        assert sample_release_note.schema_version == "1.0.0"
        assert sample_release_note.artifact_type == "release-note"
        assert sample_release_note.metadata.revision_range == "v0.1.0..v0.2.0"
        assert sample_release_note.header.product_name == "TestApp"
        assert len(sample_release_note.highlights) == 4
        assert len(sample_release_note.features) == 1
        assert len(sample_release_note.improvements) == 1
        assert len(sample_release_note.fixes) == 1
        assert len(sample_release_note.deprecations) == 1
        assert len(sample_release_note.known_issues) == 1
        assert sample_release_note.call_to_action is not None

    def test_creation_minimal(self, minimal_release_note: ReleaseNote) -> None:
        """Test creating a minimal release note."""
        assert minimal_release_note.schema_version == "1.0.0"
        assert minimal_release_note.highlights == []
        assert minimal_release_note.features == []
        assert minimal_release_note.call_to_action is None

    def test_schema_version_default(self, minimal_release_note: ReleaseNote) -> None:
        """Test that schema_version has correct default."""
        assert minimal_release_note.schema_version == "1.0.0"

    def test_artifact_type_default(self, minimal_release_note: ReleaseNote) -> None:
        """Test that artifact_type has correct default."""
        assert minimal_release_note.artifact_type == "release-note"


class TestReleaseNoteYamlSerialization:
    """Tests for ReleaseNote YAML serialization."""

    def test_to_yaml(self, sample_release_note: ReleaseNote) -> None:
        """Test YAML serialization."""
        yaml_str = sample_release_note.to_yaml()
        
        assert "schema_version: 1.0.0" in yaml_str
        assert "artifact_type: release-note" in yaml_str
        assert "product_name: TestApp" in yaml_str
        assert "Smart Search" in yaml_str

    def test_from_yaml(self, sample_release_note: ReleaseNote) -> None:
        """Test YAML deserialization."""
        yaml_str = sample_release_note.to_yaml()
        restored = ReleaseNote.from_yaml(yaml_str)
        
        assert restored.schema_version == sample_release_note.schema_version
        assert restored.header.product_name == sample_release_note.header.product_name
        assert len(restored.highlights) == len(sample_release_note.highlights)
        assert len(restored.features) == len(sample_release_note.features)

    def test_yaml_round_trip(self, sample_release_note: ReleaseNote) -> None:
        """Test complete YAML round-trip serialization."""
        yaml_str = sample_release_note.to_yaml()
        restored = ReleaseNote.from_yaml(yaml_str)
        
        # Re-serialize and compare
        yaml_str2 = restored.to_yaml()
        restored2 = ReleaseNote.from_yaml(yaml_str2)
        
        assert restored2.header.version == sample_release_note.header.version
        assert restored2.metadata.revision_range == sample_release_note.metadata.revision_range

    def test_yaml_minimal(self, minimal_release_note: ReleaseNote) -> None:
        """Test YAML with minimal release note."""
        yaml_str = minimal_release_note.to_yaml()
        restored = ReleaseNote.from_yaml(yaml_str)
        
        assert restored.header.product_name == "MinimalApp"
        assert restored.highlights == []

    def test_yaml_is_valid_yaml(self, sample_release_note: ReleaseNote) -> None:
        """Test that output is valid YAML."""
        yaml_str = sample_release_note.to_yaml()
        data = yaml.safe_load(yaml_str)
        
        assert isinstance(data, dict)
        assert "schema_version" in data
        assert "metadata" in data
        assert "header" in data

    def test_yaml_datetime_serialization(
        self, sample_release_note: ReleaseNote
    ) -> None:
        """Test that datetime is serialized correctly."""
        yaml_str = sample_release_note.to_yaml()
        data = yaml.safe_load(yaml_str)
        
        # Datetime should be serialized as ISO string
        generated_at = data["metadata"]["generated_at"]
        assert isinstance(generated_at, str)
        # Should be parseable back to datetime
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))


class TestReleaseNoteJsonSerialization:
    """Tests for ReleaseNote JSON serialization."""

    def test_model_dump_json(self, sample_release_note: ReleaseNote) -> None:
        """Test JSON serialization."""
        json_str = sample_release_note.model_dump_json()
        data = json.loads(json_str)
        
        assert data["schema_version"] == "1.0.0"
        assert data["artifact_type"] == "release-note"
        assert data["header"]["product_name"] == "TestApp"

    def test_model_dump(self, sample_release_note: ReleaseNote) -> None:
        """Test dict serialization."""
        data = sample_release_note.model_dump()
        
        assert isinstance(data, dict)
        assert data["schema_version"] == "1.0.0"

    def test_json_mode_dump(self, sample_release_note: ReleaseNote) -> None:
        """Test dict serialization with JSON mode."""
        data = sample_release_note.model_dump(mode="json")
        
        # All values should be JSON-serializable types
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        assert restored_data["header"]["product_name"] == "TestApp"

