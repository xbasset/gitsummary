"""Infrastructure layer for gitsummary.

This package contains adapters for external systems:
- Git operations (commands, diff extraction)
- Git Notes (reading/writing semantic artifacts)
- Storage backends (notes-based and file-based)

These modules encapsulate all subprocess calls and file I/O,
keeping the rest of the application pure and testable.
"""

from __future__ import annotations

from .git import (
    GitCommandError,
    diff_patch,
    diff_patch_for_commit,
    diff_stat,
    get_commit_diff,
    get_commit_info,
    is_valid_revision,
    list_commits_in_range,
    repository_root,
    resolve_revision,
    run,
    tracked_files,
)
from .notes import (
    NOTES_REF,
    RELEASE_NOTE_NOTES_REF,
    load_release_note,
    notes_exists,
    notes_read,
    notes_remove,
    notes_write,
    release_note_exists,
    save_release_note,
)
from .storage import (
    SCHEMA_VERSION,
    artifact_exists_in_notes,
    artifact_to_yaml,
    load_artifact_from_notes,
    load_artifacts_for_range,
    remove_artifact_from_notes,
    save_artifact_to_notes,
    yaml_to_artifact,
)

__all__ = [
    # Exceptions
    "GitCommandError",
    # Git operations
    "run",
    "repository_root",
    "resolve_revision",
    "is_valid_revision",
    "get_commit_info",
    "list_commits_in_range",
    "get_commit_diff",
    "diff_stat",
    "diff_patch",
    "diff_patch_for_commit",
    "tracked_files",
    # Notes operations
    "NOTES_REF",
    "RELEASE_NOTE_NOTES_REF",
    "notes_exists",
    "notes_read",
    "notes_write",
    "notes_remove",
    # Release note storage
    "save_release_note",
    "load_release_note",
    "release_note_exists",
    # Storage operations
    "SCHEMA_VERSION",
    "artifact_to_yaml",
    "yaml_to_artifact",
    "save_artifact_to_notes",
    "load_artifact_from_notes",
    "artifact_exists_in_notes",
    "remove_artifact_from_notes",
    "load_artifacts_for_range",
]

