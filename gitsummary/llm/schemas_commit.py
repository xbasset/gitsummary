"""Pydantic schemas for LLM commit extraction."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class QualitativeSignalSchema(BaseModel):
    """Schema for a qualitative score with explanation."""

    score: Optional[int] = Field(
        None,
        ge=0,
        le=10,
        description="Score on a 0-10 scale.",
    )
    explanation: Optional[str] = Field(
        None,
        description="Short rationale for the score.",
    )


class QualitativeScoresSchema(BaseModel):
    """Qualitative assessment for a commit."""

    technical_difficulty: Optional[QualitativeSignalSchema] = None
    creativity: Optional[QualitativeSignalSchema] = None
    mental_load: Optional[QualitativeSignalSchema] = None
    review_effort: Optional[QualitativeSignalSchema] = None
    ambiguity: Optional[QualitativeSignalSchema] = None


class CommitExtractionSchema(BaseModel):
    """Schema for extracting semantic information from a commit."""

    intent_summary: str = Field(
        ...,
        description=(
            "A concise, one-sentence summary of what this commit *actually* does. "
            "Go beyond the commit message to describe the real change."
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
            "Focus on what was broken, missing, or suboptimal."
        ),
    )

    behavior_after: Optional[str] = Field(
        None,
        description=(
            "Description of the system's behavior AFTER this change. "
            "Contrast directly with behavior_before."
        ),
    )

    impact_scope: Literal[
        "public_api", "internal", "dependency", "config", "docs", "test", "unknown"
    ] = Field(
        ...,
        description="The scope of this change's impact.",
    )

    is_breaking: bool = Field(
        False,
        description="True if this change breaks backward compatibility.",
    )

    technical_highlights: List[str] = Field(
        default_factory=list,
        description="Key technical decisions or interesting implementation details.",
    )

    qualitative: Optional[QualitativeScoresSchema] = Field(
        None,
        description="Qualitative assessment scores with explanations.",
    )


class CommitBatchExtractionSchema(BaseModel):
    """Schema for extracting information from multiple commits at once."""

    commits: List[CommitExtractionSchema] = Field(
        ...,
        description="Analysis for each commit in the range.",
    )

    overall_summary: str = Field(
        ...,
        description="A high-level summary of all changes in this batch.",
    )

    breaking_changes: List[str] = Field(
        default_factory=list,
        description="List of breaking changes across all commits.",
    )
