"""Compatibility wrapper for LLM schemas.

Commit extraction schemas now live in `schemas_commit.py`
and release note synthesis schemas live in `schemas_release_note.py`.
"""

from __future__ import annotations

from .schemas_commit import (
    CommitBatchExtractionSchema,
    CommitExtractionSchema,
)
from .schemas_release_note import (
    BugFixSchema,
    DeprecationSchema,
    FeatureSchema,
    HighlightSchema,
    ImprovementSchema,
    ReleaseNoteSynthesisSchema,
)

__all__ = [
    "CommitExtractionSchema",
    "CommitBatchExtractionSchema",
    "HighlightSchema",
    "FeatureSchema",
    "ImprovementSchema",
    "BugFixSchema",
    "DeprecationSchema",
    "ReleaseNoteSynthesisSchema",
]
