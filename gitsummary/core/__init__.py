"""Core domain layer for gitsummary.

This package contains the pure domain models and business logic,
free from infrastructure concerns (git operations, storage, CLI).

Modules:
    models: Data classes representing git commit data
    enums: Change categories and impact scopes
    artifact: The CommitArtifact schema (Pydantic model)
    release_note: The ReleaseNote schema (Pydantic model)
"""

from __future__ import annotations

from .artifact import CommitArtifact
from .enums import ChangeCategory, ImpactScope
from .models import CommitDiff, CommitInfo, DiffHunk, DiffStat, FileChange, FileDiff
from .release_note import (
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

__all__ = [
    # Models
    "CommitInfo",
    "FileChange",
    "DiffStat",
    "DiffHunk",
    "FileDiff",
    "CommitDiff",
    # Enums
    "ChangeCategory",
    "ImpactScope",
    # Commit Artifact
    "CommitArtifact",
    # Release Note
    "ReleaseNote",
    "ReleaseNoteMetadata",
    "ReleaseNoteHeader",
    "SourceCommit",
    "Highlight",
    "Feature",
    "Improvement",
    "BugFix",
    "Deprecation",
    "KnownIssue",
    "CallToAction",
]

