"""High-level package for gitsummary.

gitsummary summarizes git changes into durable semantic artifacts,
stored in Git Notes by default (or Postgres when configured).

Package Structure:
    core/           Domain models and schemas
    extractors/     Semantic extraction strategies  
    services/       Application services (analyzer, reporter)
    infrastructure/ External system adapters (git, storage)
    cli/            Command-line interface
    _legacy/        Deprecated code for backwards compatibility

Quick Start:
    from gitsummary import build_commit_artifact
    from gitsummary.infrastructure import list_commits_in_range, get_commit_diff
    
    commits = list_commits_in_range("v1.0..v2.0")
    for commit in commits:
        diff = get_commit_diff(commit.sha)
        artifact = build_commit_artifact(commit, diff)
        print(artifact.intent_summary)
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "app",
    # Core models (commonly used)
    "CommitArtifact",
    "CommitInfo",
    "ChangeCategory",
    "ImpactScope",
    # Services (primary API)
    "build_commit_artifact",
    "AnalyzerService",
    "ReporterService",
]

__version__ = "0.6.1"

# CLI app
from .cli import app

# Core domain models
from .core import (
    ChangeCategory,
    CommitArtifact,
    CommitInfo,
    ImpactScope,
)

# Primary API
from .services import AnalyzerService, ReporterService, build_commit_artifact
