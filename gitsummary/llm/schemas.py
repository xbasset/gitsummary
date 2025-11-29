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

