"""Report-level schemas and registry helpers.

This package hosts report-specific models (e.g., release notes)
and any shared registration helpers for report types.
"""

from __future__ import annotations

from .release_notes import (
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
