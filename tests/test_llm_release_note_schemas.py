"""Tests for LLM release note schemas and prompts.

Tests the Pydantic schemas and prompt builders for release note synthesis.
"""

from __future__ import annotations

import json

import pytest

from gitsummary.llm.prompts import (
    RELEASE_NOTE_SYSTEM_PROMPT,
    build_release_note_synthesis_prompt,
    format_artifacts_for_synthesis,
)
from gitsummary.llm.schemas import (
    BugFixSchema,
    DeprecationSchema,
    FeatureSchema,
    HighlightSchema,
    ImprovementSchema,
    ReleaseNoteSynthesisSchema,
)


# ─────────────────────────────────────────────────────────────────────────────
# Schema Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHighlightSchema:
    """Tests for HighlightSchema."""

    def test_creation(self) -> None:
        """Test creating a highlight schema."""
        hl = HighlightSchema(
            emoji="🚀",
            type="new",
            summary="New feature added",
        )
        assert hl.emoji == "🚀"
        assert hl.type == "new"
        assert hl.summary == "New feature added"

    def test_all_valid_types(self) -> None:
        """Test all valid highlight types."""
        valid_types = ["new", "improved", "fixed", "deprecated", "breaking", "security"]
        for hl_type in valid_types:
            hl = HighlightSchema(emoji="📝", type=hl_type, summary="Test")  # type: ignore[arg-type]
            assert hl.type == hl_type

    def test_invalid_type_rejected(self) -> None:
        """Test that invalid types are rejected."""
        with pytest.raises(Exception):  # Pydantic validation error
            HighlightSchema(emoji="📝", type="invalid", summary="Test")  # type: ignore[arg-type]

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        hl = HighlightSchema(emoji="✨", type="improved", summary="Better performance")
        data = hl.model_dump(mode="json")
        assert data["emoji"] == "✨"
        assert data["type"] == "improved"


class TestFeatureSchema:
    """Tests for FeatureSchema."""

    def test_creation(self) -> None:
        """Test creating a feature schema."""
        feat = FeatureSchema(
            title="Smart Search",
            description="Find files with typos.",
            user_benefit="Faster discovery.",
            commit_refs=["abc1234"],
        )
        assert feat.title == "Smart Search"
        assert feat.user_benefit == "Faster discovery."
        assert feat.commit_refs == ["abc1234"]

    def test_default_commit_refs(self) -> None:
        """Test that commit_refs defaults to empty list."""
        feat = FeatureSchema(
            title="Test",
            description="Test desc",
            user_benefit="Test benefit",
        )
        assert feat.commit_refs == []


class TestImprovementSchema:
    """Tests for ImprovementSchema."""

    def test_creation(self) -> None:
        """Test creating an improvement schema."""
        imp = ImprovementSchema(
            summary="50% faster startup",
            commit_refs=["abc1234"],
        )
        assert imp.summary == "50% faster startup"
        assert imp.commit_refs == ["abc1234"]


class TestBugFixSchema:
    """Tests for BugFixSchema."""

    def test_creation(self) -> None:
        """Test creating a bug fix schema."""
        fix = BugFixSchema(
            summary="Fixed login crash",
            commit_refs=["abc1234"],
        )
        assert fix.summary == "Fixed login crash"


class TestDeprecationSchema:
    """Tests for DeprecationSchema."""

    def test_creation(self) -> None:
        """Test creating a deprecation schema."""
        dep = DeprecationSchema(
            what="API v1",
            reason="Migrating to v2",
            migration="Use API v2",
            commit_refs=["abc1234"],
        )
        assert dep.what == "API v1"
        assert dep.reason == "Migrating to v2"
        assert dep.migration == "Use API v2"


class TestReleaseNoteSynthesisSchema:
    """Tests for ReleaseNoteSynthesisSchema."""

    def test_creation(self) -> None:
        """Test creating a full synthesis schema."""
        schema = ReleaseNoteSynthesisSchema(
            theme="Faster and more stable",
            highlights=[
                HighlightSchema(emoji="🚀", type="new", summary="New feature"),
            ],
            features=[
                FeatureSchema(
                    title="Feature",
                    description="Desc",
                    user_benefit="Benefit",
                ),
            ],
            improvements=[
                ImprovementSchema(summary="Faster"),
            ],
            fixes=[
                BugFixSchema(summary="Fixed bug"),
            ],
            deprecations=[
                DeprecationSchema(
                    what="Old API",
                    reason="Outdated",
                    migration="Use new API",
                ),
            ],
        )
        
        assert schema.theme == "Faster and more stable"
        assert len(schema.highlights) == 1
        assert len(schema.features) == 1
        assert len(schema.improvements) == 1
        assert len(schema.fixes) == 1
        assert len(schema.deprecations) == 1

    def test_default_empty_lists(self) -> None:
        """Test that lists default to empty."""
        schema = ReleaseNoteSynthesisSchema(
            theme="Test theme",
            highlights=[],
        )
        assert schema.features == []
        assert schema.improvements == []
        assert schema.fixes == []
        assert schema.deprecations == []

    def test_json_serialization(self) -> None:
        """Test JSON serialization for LLM output."""
        schema = ReleaseNoteSynthesisSchema(
            theme="Test",
            highlights=[
                HighlightSchema(emoji="🚀", type="new", summary="Test"),
            ],
        )
        
        json_str = schema.model_dump_json()
        data = json.loads(json_str)
        
        assert data["theme"] == "Test"
        assert len(data["highlights"]) == 1
        assert data["highlights"][0]["type"] == "new"

    def test_from_dict(self) -> None:
        """Test creating from dict (as LLM would return)."""
        data = {
            "theme": "Test theme",
            "highlights": [
                {"emoji": "🚀", "type": "new", "summary": "Feature"},
            ],
            "features": [],
            "improvements": [],
            "fixes": [],
            "deprecations": [],
        }
        
        schema = ReleaseNoteSynthesisSchema.model_validate(data)
        assert schema.theme == "Test theme"
        assert len(schema.highlights) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestReleaseNoteSystemPrompt:
    """Tests for the release note system prompt."""

    def test_prompt_exists(self) -> None:
        """Test that system prompt is defined."""
        assert RELEASE_NOTE_SYSTEM_PROMPT is not None
        assert len(RELEASE_NOTE_SYSTEM_PROMPT) > 0

    def test_prompt_contains_guidelines(self) -> None:
        """Test that prompt contains key guidelines."""
        prompt = RELEASE_NOTE_SYSTEM_PROMPT.lower()
        
        # Should mention user-focused writing
        assert "user" in prompt or "end user" in prompt
        
        # Should mention clear/concise
        assert "clear" in prompt or "concise" in prompt

    def test_prompt_mentions_json_output(self) -> None:
        """Test that prompt mentions JSON output format."""
        assert "json" in RELEASE_NOTE_SYSTEM_PROMPT.lower()


class TestBuildReleaseNoteSynthesisPrompt:
    """Tests for build_release_note_synthesis_prompt function."""

    def test_includes_product_name(self) -> None:
        """Test that prompt includes product name."""
        prompt = build_release_note_synthesis_prompt(
            product_name="TestApp",
            version="v1.0.0",
            artifacts_summary="Test summary",
        )
        
        assert "TestApp" in prompt

    def test_includes_version(self) -> None:
        """Test that prompt includes version."""
        prompt = build_release_note_synthesis_prompt(
            product_name="TestApp",
            version="v2.0.0",
            artifacts_summary="Test summary",
        )
        
        assert "v2.0.0" in prompt

    def test_includes_artifacts_summary(self) -> None:
        """Test that prompt includes artifacts summary."""
        summary = "### FEATURE (3 commits)\n- Smart Search\n- Dark Mode"
        prompt = build_release_note_synthesis_prompt(
            product_name="TestApp",
            version="v1.0.0",
            artifacts_summary=summary,
        )
        
        assert "Smart Search" in prompt
        assert "Dark Mode" in prompt

    def test_includes_instructions(self) -> None:
        """Test that prompt includes synthesis instructions."""
        prompt = build_release_note_synthesis_prompt(
            product_name="TestApp",
            version="v1.0.0",
            artifacts_summary="Test",
        )
        
        # Should have instructions section
        assert "instructions" in prompt.lower()


class TestFormatArtifactsForSynthesis:
    """Tests for format_artifacts_for_synthesis function."""

    def test_formats_empty_list(self) -> None:
        """Test formatting empty artifacts list."""
        result = format_artifacts_for_synthesis([])
        assert result == ""

    def test_groups_by_category(self) -> None:
        """Test that artifacts are grouped by category."""
        artifacts = [
            {
                "sha": "abc1234",
                "category": "feature",
                "intent_summary": "Add search",
                "is_breaking": False,
            },
            {
                "sha": "def5678",
                "category": "fix",
                "intent_summary": "Fix crash",
                "is_breaking": False,
            },
        ]
        
        result = format_artifacts_for_synthesis(artifacts)
        
        assert "FEATURE" in result
        assert "FIX" in result
        assert "Add search" in result
        assert "Fix crash" in result

    def test_marks_breaking_changes(self) -> None:
        """Test that breaking changes are marked."""
        artifacts = [
            {
                "sha": "abc1234",
                "category": "feature",
                "intent_summary": "Breaking change",
                "is_breaking": True,
            },
        ]
        
        result = format_artifacts_for_synthesis(artifacts)
        
        assert "BREAKING" in result

    def test_includes_behavior_changes(self) -> None:
        """Test that behavior before/after are included."""
        artifacts = [
            {
                "sha": "abc1234",
                "category": "fix",
                "intent_summary": "Fix login",
                "behavior_before": "Login crashed",
                "behavior_after": "Login works",
                "is_breaking": False,
            },
        ]
        
        result = format_artifacts_for_synthesis(artifacts)
        
        assert "Before:" in result
        assert "After:" in result
        assert "Login crashed" in result
        assert "Login works" in result

    def test_includes_technical_highlights(self) -> None:
        """Test that technical highlights are included."""
        artifacts = [
            {
                "sha": "abc1234",
                "category": "feature",
                "intent_summary": "Add caching",
                "is_breaking": False,
                "technical_highlights": ["Added Redis cache", "Improved latency"],
            },
        ]
        
        result = format_artifacts_for_synthesis(artifacts)
        
        assert "Technical:" in result
        assert "Redis cache" in result

    def test_limits_technical_highlights(self) -> None:
        """Test that technical highlights are limited."""
        artifacts = [
            {
                "sha": "abc1234",
                "category": "feature",
                "intent_summary": "Complex change",
                "is_breaking": False,
                "technical_highlights": [
                    "Highlight 1",
                    "Highlight 2",
                    "Highlight 3",
                    "Highlight 4",
                    "Highlight 5",
                ],
            },
        ]
        
        result = format_artifacts_for_synthesis(artifacts)
        
        # Should only include first 2
        assert "Highlight 1" in result
        assert "Highlight 2" in result
        # Should not include all 5
        count = result.count("Technical:")
        assert count <= 2

    def test_orders_categories(self) -> None:
        """Test that categories are ordered logically."""
        artifacts = [
            {"sha": "1", "category": "chore", "intent_summary": "Chore", "is_breaking": False},
            {"sha": "2", "category": "feature", "intent_summary": "Feature", "is_breaking": False},
            {"sha": "3", "category": "fix", "intent_summary": "Fix", "is_breaking": False},
        ]
        
        result = format_artifacts_for_synthesis(artifacts)
        
        # Feature should come before Fix, Fix before Chore
        feature_pos = result.find("FEATURE")
        fix_pos = result.find("FIX")
        chore_pos = result.find("CHORE")
        
        assert feature_pos < fix_pos < chore_pos

