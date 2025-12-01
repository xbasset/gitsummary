"""ReleaseNote schema definition.

The ReleaseNote is a report-level artifact that synthesizes
commit-level artifacts into a coherent, user-facing release document.

Unlike CommitArtifact (per-commit), ReleaseNote is stored once per
release range, attached to the tip commit of the range.

Storage: refs/notes/report/release-note
Format: YAML (human-readable)
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Metadata for traceability
# ─────────────────────────────────────────────────────────────────────────────


class SourceCommit(BaseModel):
    """Reference to a source commit used in the release note."""

    sha: str = Field(..., description="Short SHA of the commit.")
    category: str = Field(..., description="Category of the commit (feature, fix, etc.).")


class ReleaseNoteMetadata(BaseModel):
    """Metadata for tracing release note generation."""

    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when this release note was generated.",
    )
    generator_version: str = Field(
        "0.2.0",
        description="Version of gitsummary that generated this release note.",
    )
    llm_provider: Optional[str] = Field(
        None,
        description="LLM provider used for synthesis (e.g., 'openai', 'anthropic').",
    )
    llm_model: Optional[str] = Field(
        None,
        description="Model used for synthesis (e.g., 'gpt-4o').",
    )
    revision_range: str = Field(
        ...,
        description="The git revision range covered (e.g., 'v0.1.0..v0.2.0').",
    )
    tip_commit: str = Field(
        ...,
        description="Full SHA of the tip commit this note is attached to.",
    )
    commit_count: int = Field(
        ...,
        description="Total number of commits in the range.",
    )
    analyzed_count: int = Field(
        ...,
        description="Number of commits with artifacts.",
    )
    source_commits: List[SourceCommit] = Field(
        default_factory=list,
        description="List of source commits included in this release note.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────


class ReleaseNoteHeader(BaseModel):
    """The header section of the release note."""

    product_name: str = Field(
        ...,
        description="Name of the product/project.",
    )
    version: str = Field(
        ...,
        description="Version number or identifier.",
    )
    release_date: str = Field(
        ...,
        description="Release date (YYYY-MM-DD format).",
    )
    theme: str = Field(
        ...,
        description=(
            "One-sentence summary of the release's theme. "
            "Example: 'This release introduces faster syncing and major stability improvements.'"
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Highlights (TL;DR section)
# ─────────────────────────────────────────────────────────────────────────────

HighlightType = Literal["new", "improved", "fixed", "deprecated", "breaking", "security"]


class Highlight(BaseModel):
    """A single highlight in the TL;DR section."""

    emoji: str = Field(
        ...,
        description="Emoji for this highlight (e.g., '🚀', '✨', '🛠️', '⚠️').",
    )
    type: HighlightType = Field(
        ...,
        description="Type of highlight.",
    )
    summary: str = Field(
        ...,
        description="Brief summary of the highlight.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# New Features
# ─────────────────────────────────────────────────────────────────────────────


class Feature(BaseModel):
    """A new feature in the release."""

    title: str = Field(
        ...,
        description="Feature title (e.g., 'Smart Search (beta)').",
    )
    description: str = Field(
        ...,
        description="What the feature is.",
    )
    user_benefit: str = Field(
        ...,
        description="Why this feature matters to users.",
    )
    commits: List[str] = Field(
        default_factory=list,
        description="Short SHAs of commits implementing this feature.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Improvements
# ─────────────────────────────────────────────────────────────────────────────


class Improvement(BaseModel):
    """An improvement in the release."""

    summary: str = Field(
        ...,
        description="User-friendly summary of the improvement.",
    )
    commits: List[str] = Field(
        default_factory=list,
        description="Short SHAs of related commits.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Bug Fixes
# ─────────────────────────────────────────────────────────────────────────────


class BugFix(BaseModel):
    """A bug fix in the release."""

    summary: str = Field(
        ...,
        description="User-friendly description of what was fixed.",
    )
    commits: List[str] = Field(
        default_factory=list,
        description="Short SHAs of related commits.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Deprecations / Breaking Changes
# ─────────────────────────────────────────────────────────────────────────────


class Deprecation(BaseModel):
    """A deprecation or breaking change."""

    what: str = Field(
        ...,
        description="What is being deprecated or changed.",
    )
    reason: str = Field(
        ...,
        description="Why this change is being made.",
    )
    deadline: Optional[str] = Field(
        None,
        description="When the deprecated feature will be removed (YYYY-MM-DD).",
    )
    migration: str = Field(
        ...,
        description="What users should do to migrate.",
    )
    commits: List[str] = Field(
        default_factory=list,
        description="Short SHAs of related commits.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Known Issues
# ─────────────────────────────────────────────────────────────────────────────


class KnownIssue(BaseModel):
    """A known issue in this release."""

    issue: str = Field(
        ...,
        description="Description of the known issue.",
    )
    status: str = Field(
        ...,
        description="Current status or expected fix timeline.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Call to Action
# ─────────────────────────────────────────────────────────────────────────────


class CallToAction(BaseModel):
    """Links and resources for users."""

    documentation_url: Optional[str] = Field(
        None,
        description="Link to documentation.",
    )
    migration_guide_url: Optional[str] = Field(
        None,
        description="Link to migration guide.",
    )
    support_url: Optional[str] = Field(
        None,
        description="Link to support/help.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main ReleaseNote Model
# ─────────────────────────────────────────────────────────────────────────────


class ReleaseNote(BaseModel):
    """A complete release note artifact.

    This is the top-level model for a release note, containing all
    sections needed for a user-facing release document.

    Storage: refs/notes/report/release-note (attached to tip commit)
    """

    schema_version: str = Field(
        "1.0.0",
        description="Version of the release note schema.",
    )
    artifact_type: Literal["release-note"] = Field(
        "release-note",
        description="Type identifier for this artifact.",
    )

    # Metadata for traceability
    metadata: ReleaseNoteMetadata = Field(
        ...,
        description="Metadata for tracing this release note's generation.",
    )

    # Header
    header: ReleaseNoteHeader = Field(
        ...,
        description="The header section with version and theme.",
    )

    # TL;DR highlights
    highlights: List[Highlight] = Field(
        default_factory=list,
        description="Quick summary highlights for skimmers.",
    )

    # Content sections
    features: List[Feature] = Field(
        default_factory=list,
        description="New features in this release.",
    )
    improvements: List[Improvement] = Field(
        default_factory=list,
        description="Improvements and enhancements.",
    )
    fixes: List[BugFix] = Field(
        default_factory=list,
        description="Bug fixes.",
    )
    deprecations: List[Deprecation] = Field(
        default_factory=list,
        description="Deprecations and breaking changes.",
    )

    # Additional info
    known_issues: List[KnownIssue] = Field(
        default_factory=list,
        description="Known issues in this release.",
    )
    call_to_action: Optional[CallToAction] = Field(
        None,
        description="Links and resources for users.",
    )

    def to_yaml(self) -> str:
        """Serialize to YAML format for storage."""
        import yaml

        # Convert to dict, handling datetime serialization
        data = self.model_dump(mode="json")
        return yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ReleaseNote":
        """Deserialize from YAML format."""
        import yaml

        data = yaml.safe_load(yaml_content)
        return cls.model_validate(data)

