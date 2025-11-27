"""Backwards compatibility shim for artifact module.

DEPRECATED: Import from gitsummary.services or gitsummary._legacy instead.

Example:
    # Old way (deprecated)
    from gitsummary.artifact import build_commit_artifact, ArtifactBuilder
    
    # New way (recommended)
    from gitsummary.services import build_commit_artifact, AnalyzerService
"""

from __future__ import annotations

# Re-export from services
from .services import AnalyzerService, build_commit_artifact

# Re-export LLM provider interface from extractors
from .extractors import LLMProvider, get_llm_provider, set_llm_provider

# Re-export legacy types from _legacy
from ._legacy.artifact import ArtifactContext, Commit, build_artifact

# For backwards compatibility, alias AnalyzerService as ArtifactBuilder
ArtifactBuilder = AnalyzerService

__all__ = [
    "build_commit_artifact",
    "ArtifactBuilder",
    "LLMProvider",
    "get_llm_provider",
    "set_llm_provider",
    # Legacy exports
    "build_artifact",
    "ArtifactContext",
    "Commit",
]
