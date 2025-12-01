"""Pydantic schemas for LLM structured output extraction.

These schemas define the structure expected from LLM responses
when analyzing commits. They are designed to be compatible with
OpenAI's structured outputs feature and other LLM providers.

The schemas mirror the CommitArtifact fields but are specifically
designed for LLM extraction, with detailed field descriptions that
serve as prompts for the model.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CommitExtractionSchema(BaseModel):
    """Schema for extracting semantic information from a commit.

    This schema is passed to the LLM to structure its response.
    Field descriptions act as instructions for the model.
    """

    intent_summary: str = Field(
        ...,
        description=(
            "A concise, one-sentence summary of what this commit *actually* does. "
            "Go beyond the commit message to describe the real change. "
            "Be specific about the problem solved or feature added. "
            "Example: 'Fixes race condition in user session handling by adding mutex lock.' "
            "Example: 'Adds OAuth2 login flow with Google as identity provider.'"
        ),
    )

    category: Literal["feature", "fix", "security", "performance", "refactor", "chore"] = Field(
        ...,
        description=(
            "The primary category of this change. Choose the MOST appropriate: "
            "- 'feature': New functionality or capability "
            "- 'fix': Bug fix or error correction "
            "- 'security': Security improvement or vulnerability fix "
            "- 'performance': Performance optimization "
            "- 'refactor': Code restructuring without behavior change "
            "- 'chore': Maintenance, docs, tests, dependencies"
        ),
    )

    behavior_before: Optional[str] = Field(
        None,
        description=(
            "Description of the system's behavior BEFORE this change. "
            "Focus on what was broken, missing, or suboptimal. "
            "Leave null if this is a new feature with no prior behavior. "
            "Example: 'API returned 500 error when user email contained special characters.' "
            "Example: 'Search results took 5+ seconds to load with large datasets.'"
        ),
    )

    behavior_after: Optional[str] = Field(
        None,
        description=(
            "Description of the system's behavior AFTER this change. "
            "Contrast directly with behavior_before. "
            "Leave null if this is a refactor with no behavior change. "
            "Example: 'API properly handles all valid email formats and returns 400 for invalid ones.' "
            "Example: 'Search results load in under 500ms using new indexing strategy.'"
        ),
    )

    impact_scope: Literal[
        "public_api", "internal", "dependency", "config", "docs", "test", "unknown"
    ] = Field(
        ...,
        description=(
            "The scope of this change's impact: "
            "- 'public_api': Changes external interfaces, endpoints, or public methods "
            "- 'internal': Internal logic, private methods, implementation details "
            "- 'dependency': Package updates, new libraries, version bumps "
            "- 'config': Configuration, environment variables, feature flags "
            "- 'docs': Documentation, comments, README changes "
            "- 'test': Test files, fixtures, test utilities only "
            "- 'unknown': Cannot determine from the diff"
        ),
    )

    is_breaking: bool = Field(
        False,
        description=(
            "True if this change breaks backward compatibility. "
            "Consider: API changes, removed features, changed defaults, "
            "renamed public methods, different return types. "
            "Internal refactors are NOT breaking. Documentation changes are NOT breaking."
        ),
    )

    technical_highlights: List[str] = Field(
        default_factory=list,
        description=(
            "Key technical decisions or interesting implementation details. "
            "Focus on HOW the problem was solved, not WHAT was done. "
            "Limit to 3-5 most important points. "
            "Examples: "
            "['Introduced connection pooling for database queries', "
            "'Used bloom filter to reduce memory usage by 60%', "
            "'Added circuit breaker pattern for external API calls']"
        ),
    )


class CommitBatchExtractionSchema(BaseModel):
    """Schema for extracting information from multiple commits at once.

    Useful for summarizing a release or change range.
    """

    commits: List[CommitExtractionSchema] = Field(
        ...,
        description="Analysis for each commit in the range.",
    )

    overall_summary: str = Field(
        ...,
        description=(
            "A high-level summary of all changes in this batch. "
            "Focus on the overall theme or goal of these changes."
        ),
    )

    breaking_changes: List[str] = Field(
        default_factory=list,
        description="List of breaking changes across all commits.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Release Note Synthesis Schemas
# ─────────────────────────────────────────────────────────────────────────────


class HighlightSchema(BaseModel):
    """A single highlight in the TL;DR section."""

    emoji: str = Field(
        ...,
        description="Emoji for this highlight: 🚀 (new), ✨ (improved), 🛠️ (fixed), ⚠️ (breaking/deprecated), 🔒 (security).",
    )
    type: Literal["new", "improved", "fixed", "deprecated", "breaking", "security"] = Field(
        ...,
        description="Type of highlight.",
    )
    summary: str = Field(
        ...,
        description="Brief, user-friendly summary (max 10 words).",
    )


class FeatureSchema(BaseModel):
    """A new feature for release notes."""

    title: str = Field(
        ...,
        description="Short feature title (e.g., 'Smart Search (beta)').",
    )
    description: str = Field(
        ...,
        description="What the feature does (1-2 sentences).",
    )
    user_benefit: str = Field(
        ...,
        description="Why this matters to users (1-2 sentences).",
    )
    commit_refs: List[str] = Field(
        default_factory=list,
        description="Short SHAs of commits implementing this feature.",
    )


class ImprovementSchema(BaseModel):
    """An improvement for release notes."""

    summary: str = Field(
        ...,
        description="User-friendly summary of the improvement.",
    )
    commit_refs: List[str] = Field(
        default_factory=list,
        description="Short SHAs of related commits.",
    )


class BugFixSchema(BaseModel):
    """A bug fix for release notes."""

    summary: str = Field(
        ...,
        description="User-friendly description of what was fixed. Avoid technical jargon.",
    )
    commit_refs: List[str] = Field(
        default_factory=list,
        description="Short SHAs of related commits.",
    )


class DeprecationSchema(BaseModel):
    """A deprecation or breaking change for release notes."""

    what: str = Field(
        ...,
        description="What is being deprecated or changed.",
    )
    reason: str = Field(
        ...,
        description="Why this change is being made.",
    )
    migration: str = Field(
        ...,
        description="What users should do to migrate or adapt.",
    )
    commit_refs: List[str] = Field(
        default_factory=list,
        description="Short SHAs of related commits.",
    )


class ReleaseNoteSynthesisSchema(BaseModel):
    """Schema for synthesizing release notes from commit artifacts.

    This schema is used by the LLM to generate user-facing release notes
    from aggregated commit-level data.
    """

    theme: str = Field(
        ...,
        description=(
            "One-sentence theme that captures the essence of this release. "
            "Example: 'Faster syncing and major stability improvements.' "
            "Should be catchy and user-focused."
        ),
    )

    highlights: List[HighlightSchema] = Field(
        ...,
        description=(
            "3-5 most important changes for the TL;DR section. "
            "Include the most significant new feature, improvement, fix, and any breaking changes."
        ),
    )

    features: List[FeatureSchema] = Field(
        default_factory=list,
        description=(
            "New features in this release. Group related commits into single features. "
            "Write for end users, not developers."
        ),
    )

    improvements: List[ImprovementSchema] = Field(
        default_factory=list,
        description=(
            "Improvements and enhancements. Include performance gains, UX improvements, etc. "
            "Be specific about the benefit (e.g., '45% faster' not 'improved performance')."
        ),
    )

    fixes: List[BugFixSchema] = Field(
        default_factory=list,
        description=(
            "Bug fixes. Describe what was broken from the user's perspective, not technical details. "
            "Example: 'Fixed an issue where notifications wouldn't appear after login.'"
        ),
    )

    deprecations: List[DeprecationSchema] = Field(
        default_factory=list,
        description=(
            "Deprecations and breaking changes. Include what's changing, why, and how to migrate. "
            "Be clear and actionable."
        ),
    )



