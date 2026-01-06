"""Core domain layer for gitsummary.

This package contains the pure domain models and business logic,
free from infrastructure concerns (git operations, storage, CLI).

Modules:
    models: Data classes representing git commit data
    enums: Change categories and impact scopes
    artifact: The CommitArtifact schema (Pydantic model)
"""

from __future__ import annotations

from .artifact import (
    AnalysisMeta,
    CommitArtifact,
    InputMetrics,
    QualitativeScores,
    QualitativeSignal,
    TokenUsage,
)
from .enums import ChangeCategory, ImpactScope
from .models import (
    CommitDiff,
    CommitInfo,
    DiffHunk,
    DiffStat,
    FileChange,
    FileDiff,
    TagInfo,
)
__all__ = [
    # Models
    "CommitInfo",
    "TagInfo",
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
    "AnalysisMeta",
    "InputMetrics",
    "TokenUsage",
    "QualitativeSignal",
    "QualitativeScores",
]
