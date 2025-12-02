"""Pydantic schemas for release note synthesis outputs."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


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
    """Schema for synthesizing release notes from commit artifacts."""

    theme: str = Field(
        ...,
        description="One-sentence theme that captures the essence of this release.",
    )

    highlights: List[HighlightSchema] = Field(
        ...,
        description="3-5 most important changes for the TL;DR section.",
    )

    features: List[FeatureSchema] = Field(
        default_factory=list,
        description="New features in this release.",
    )

    improvements: List[ImprovementSchema] = Field(
        default_factory=list,
        description="Improvements and enhancements.",
    )

    fixes: List[BugFixSchema] = Field(
        default_factory=list,
        description="Bug fixes.",
    )

    deprecations: List[DeprecationSchema] = Field(
        default_factory=list,
        description="Deprecations and breaking changes.",
    )
