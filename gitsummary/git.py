"""Backwards compatibility shim for git module.

DEPRECATED: Import from gitsummary.core or gitsummary.infrastructure instead.

Example:
    # Old way (deprecated)
    from gitsummary.git import CommitInfo, list_commits_in_range, GitCommandError
    
    # New way (recommended)
    from gitsummary.core import CommitInfo
    from gitsummary.infrastructure import list_commits_in_range, GitCommandError
"""

from __future__ import annotations

# Re-export core models
from .core import (
    CommitDiff,
    CommitInfo,
    DiffHunk,
    DiffStat,
    FileChange,
    FileDiff,
)

# Re-export infrastructure operations
from .infrastructure import (
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

# Re-export notes operations
from .infrastructure.notes import (
    NOTES_REF,
    notes_exists,
    notes_read,
    notes_remove,
    notes_write,
)

# Legacy aliases
Commit = CommitInfo
list_commits = list_commits_in_range
check_tags = lambda revisions: [run(["rev-parse", "--verify", rev]) for rev in revisions]
check_revisions = check_tags

__all__ = [
    "GitCommandError",
    "CommitInfo",
    "FileChange",
    "DiffStat",
    "DiffHunk",
    "FileDiff",
    "CommitDiff",
    "run",
    "repository_root",
    "resolve_revision",
    "is_valid_revision",
    "list_commits_in_range",
    "get_commit_info",
    "get_commit_diff",
    "diff_stat",
    "diff_patch",
    "diff_patch_for_commit",
    "tracked_files",
    "NOTES_REF",
    "notes_exists",
    "notes_read",
    "notes_write",
    "notes_remove",
    # Legacy aliases
    "Commit",
    "list_commits",
    "check_tags",
    "check_revisions",
]
