"""Core domain models for git data.

These dataclasses represent the structured information extracted from git,
before any semantic analysis or artifact construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class TagInfo:
    """Information about a git tag ordered by creation/annotation date."""

    name: str
    sha: str
    date: datetime
    is_annotated: bool = False


@dataclass(frozen=True)
class CommitInfo:
    """Complete information about a single commit.

    This is the primary representation of a commit used throughout
    the application. It's immutable to ensure consistent data flow.
    """

    sha: str
    short_sha: str
    author_name: str
    author_email: str
    date: datetime
    summary: str
    body: str
    parent_shas: List[str] = field(default_factory=list)

    @property
    def full_message(self) -> str:
        """Return the complete commit message (summary + body)."""
        if self.body:
            return f"{self.summary}\n\n{self.body}"
        return self.summary

    @property
    def is_merge(self) -> bool:
        """Return True if this is a merge commit."""
        return len(self.parent_shas) > 1


@dataclass(frozen=True)
class FileChange:
    """Represents a file change from ``git diff --name-status``.

    Used to track what files were affected and how.
    """

    status: str  # A=added, D=deleted, M=modified, R=renamed, C=copied
    path: str
    old_path: Optional[str] = None  # For renames (R status)

    @property
    def status_label(self) -> str:
        """Human-readable status label."""
        labels = {
            "A": "added",
            "D": "deleted",
            "M": "modified",
            "R": "renamed",
            "C": "copied",
            "T": "type changed",
        }
        return labels.get(self.status[0], "unknown")


@dataclass(frozen=True)
class DiffStat:
    """Aggregate statistics from ``git diff --numstat``.

    Provides a quick overview of change magnitude.
    """

    insertions: int
    deletions: int

    @property
    def total_changes(self) -> int:
        """Total lines changed (insertions + deletions)."""
        return self.insertions + self.deletions


@dataclass(frozen=True)
class DiffHunk:
    """A single hunk from a unified diff.

    Represents one contiguous region of changes in a file.
    """

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    content: str


@dataclass(frozen=True)
class FileDiff:
    """Diff information for a single file.

    Combines status, statistics, and patch content.
    """

    path: str
    old_path: Optional[str]  # For renames
    status: str
    insertions: int
    deletions: int
    patch: str
    hunks: List[DiffHunk] = field(default_factory=list)


@dataclass(frozen=True)
class CommitDiff:
    """Complete diff information for a commit.

    Aggregates file-level diffs with overall statistics.
    """

    sha: str
    files: List[FileDiff]
    stat: DiffStat

    @property
    def file_paths(self) -> List[str]:
        """List of all affected file paths."""
        return [f.path for f in self.files]
