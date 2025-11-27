"""Light-weight helpers around git plumbing commands used by the CLI."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

__all__ = [
    "GitCommandError",
    "CommitInfo",
    "FileChange",
    "DiffStat",
    "DiffHunk",
    "CommitDiff",
    "run",
    "repository_root",
    "resolve_revision",
    "list_commits_in_range",
    "get_commit_info",
    "get_commit_diff",
    "diff_stat",
    "diff_patch",
    "tracked_files",
    "check_revisions",
    # Legacy aliases
    "Commit",
    "list_commits",
    "check_tags",
]


class GitCommandError(RuntimeError):
    """Raised when an underlying git command fails."""


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CommitInfo:
    """Complete information about a single commit."""

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


# Legacy alias for backwards compatibility
Commit = CommitInfo


@dataclass(frozen=True)
class FileChange:
    """Represents an entry from ``git diff --name-status``."""

    status: str
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
    """Aggregate statistics from ``git diff --numstat``."""

    insertions: int
    deletions: int

    @property
    def total_changes(self) -> int:
        return self.insertions + self.deletions


@dataclass(frozen=True)
class DiffHunk:
    """A single hunk from a unified diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    content: str


@dataclass(frozen=True)
class FileDiff:
    """Diff information for a single file."""

    path: str
    old_path: Optional[str]  # For renames
    status: str
    insertions: int
    deletions: int
    patch: str
    hunks: List[DiffHunk] = field(default_factory=list)


@dataclass(frozen=True)
class CommitDiff:
    """Complete diff information for a commit."""

    sha: str
    files: List[FileDiff]
    stat: DiffStat

    @property
    def file_paths(self) -> List[str]:
        return [f.path for f in self.files]


# ─────────────────────────────────────────────────────────────────────────────
# Core Git Operations
# ─────────────────────────────────────────────────────────────────────────────


def run(args: Sequence[str], *, cwd: Optional[Path] = None) -> str:
    """Run ``git`` with ``args`` and return stdout, raising on errors."""

    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.returncode != 0:
        raise GitCommandError(process.stderr.strip() or "git command failed")
    return process.stdout


def repository_root() -> Path:
    """Return the root directory of the current repository."""

    return Path(run(["rev-parse", "--show-toplevel"]).strip())


def resolve_revision(revision: str) -> str:
    """Resolve a revision (tag, branch, HEAD, SHA) to a full commit SHA."""
    return run(["rev-parse", "--verify", revision]).strip()


def is_valid_revision(revision: str) -> bool:
    """Check if a revision is valid without raising."""
    try:
        resolve_revision(revision)
        return True
    except GitCommandError:
        return False


def check_revisions(revisions: Iterable[str]) -> None:
    """Validate that the given revisions exist."""
    for rev in revisions:
        run(["rev-parse", "--verify", rev])


# Legacy alias
check_tags = check_revisions


# ─────────────────────────────────────────────────────────────────────────────
# Commit Information Retrieval
# ─────────────────────────────────────────────────────────────────────────────


def get_commit_info(revision: str) -> CommitInfo:
    """Get complete information about a single commit."""

    # Format: SHA%x00short_sha%x00author_name%x00author_email%x00date%x00subject%x00body%x00parents
    format_str = "%H%x00%h%x00%an%x00%ae%x00%aI%x00%s%x00%b%x00%P"
    output = run(["log", "-1", f"--format={format_str}", revision])

    parts = output.strip().split("\x00")
    if len(parts) < 8:
        raise GitCommandError(f"Unexpected git log output for {revision}")

    sha, short_sha, author_name, author_email, date_str, summary, body, parents_str = (
        parts[:8]
    )
    parent_shas = parents_str.split() if parents_str.strip() else []

    return CommitInfo(
        sha=sha,
        short_sha=short_sha,
        author_name=author_name,
        author_email=author_email,
        date=datetime.fromisoformat(date_str),
        summary=summary.strip(),
        body=body.strip(),
        parent_shas=parent_shas,
    )


def list_commits_in_range(range_spec: str) -> List[CommitInfo]:
    """Return all commits in a range, ordered from newest to oldest.

    Supports:
    - Range syntax: "v1.0..v2.0", "main~5..main"
    - Single commit: "abc123" (returns just that commit)
    - Branch/tag: "main", "v1.0" (returns just the tip commit)
    """
    # Check if this is a range (contains ..)
    if ".." in range_spec:
        # It's a range - get all commits in the range
        output = run(["rev-list", "--reverse", range_spec])
        shas = [sha for sha in output.strip().splitlines() if sha]
    else:
        # Single revision - resolve and return just that commit
        sha = resolve_revision(range_spec)
        shas = [sha]

    return [get_commit_info(sha) for sha in reversed(shas)]


# Legacy alias
def list_commits(range_spec: str) -> List[CommitInfo]:
    """Legacy alias for list_commits_in_range."""
    return list_commits_in_range(range_spec)


# ─────────────────────────────────────────────────────────────────────────────
# Diff Extraction
# ─────────────────────────────────────────────────────────────────────────────


def get_commit_diff(revision: str) -> CommitDiff:
    """Get the complete diff for a single commit.

    For merge commits, shows the combined diff against the first parent.
    """
    sha = resolve_revision(revision)

    # Get numstat for per-file statistics
    numstat_output = run(["diff", "--numstat", f"{sha}^..{sha}"])
    file_stats = {}
    for line in numstat_output.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            added, removed, path = parts[0], parts[1], parts[-1]
            file_stats[path] = {
                "insertions": int(added) if added != "-" else 0,
                "deletions": int(removed) if removed != "-" else 0,
            }

    # Get name-status for file change types
    name_status_output = run(["diff", "--name-status", f"{sha}^..{sha}"])
    file_changes = {}
    for line in name_status_output.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            # Rename or copy: status, old_path, new_path
            old_path = parts[1] if len(parts) > 1 else None
            new_path = parts[2] if len(parts) > 2 else parts[1]
            file_changes[new_path] = {"status": status, "old_path": old_path}
        else:
            path = parts[1] if len(parts) > 1 else ""
            file_changes[path] = {"status": status, "old_path": None}

    # Get the full patch
    patch_output = run(["diff", "-p", f"{sha}^..{sha}"])

    # Build FileDiff objects
    files: List[FileDiff] = []
    total_insertions = 0
    total_deletions = 0

    for path, change_info in file_changes.items():
        stats = file_stats.get(path, {"insertions": 0, "deletions": 0})
        files.append(
            FileDiff(
                path=path,
                old_path=change_info["old_path"],
                status=change_info["status"],
                insertions=stats["insertions"],
                deletions=stats["deletions"],
                patch="",  # We store full patch at commit level for simplicity
                hunks=[],
            )
        )
        total_insertions += stats["insertions"]
        total_deletions += stats["deletions"]

    return CommitDiff(
        sha=sha,
        files=files,
        stat=DiffStat(insertions=total_insertions, deletions=total_deletions),
    )


def diff_stat(range_spec: str) -> DiffStat:
    """Return aggregate diff statistics for ``range_spec``."""

    numstat_output = run(["diff", "--numstat", range_spec])
    insertions = 0
    deletions = 0
    for line in numstat_output.strip().splitlines():
        if not line:
            continue
        added, removed, *_ = line.split("\t")
        if added != "-":
            insertions += int(added)
        if removed != "-":
            deletions += int(removed)
    return DiffStat(insertions=insertions, deletions=deletions)


def diff_patch(range_spec: str) -> str:
    """Return the unified diff for ``range_spec``."""

    return run(["diff", range_spec])


def diff_patch_for_commit(revision: str) -> str:
    """Return the unified diff for a single commit against its parent."""
    sha = resolve_revision(revision)
    return run(["diff", f"{sha}^..{sha}"])


def tracked_files(range_spec: str) -> List[FileChange]:
    """Return the list of changed files for ``range_spec``."""

    output = run(["diff", "--name-status", range_spec])
    files: List[FileChange] = []
    for line in output.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            # Rename or copy
            old_path = parts[1] if len(parts) > 1 else None
            new_path = parts[2] if len(parts) > 2 else parts[1]
            files.append(FileChange(status=status, path=new_path, old_path=old_path))
        else:
            path = parts[1] if len(parts) > 1 else ""
            files.append(FileChange(status=status, path=path))
    return files


# ─────────────────────────────────────────────────────────────────────────────
# Git Notes Operations
# ─────────────────────────────────────────────────────────────────────────────

NOTES_REF = "refs/notes/intent"


def notes_exists(sha: str, notes_ref: str = NOTES_REF) -> bool:
    """Check if a note exists for the given commit."""
    try:
        run(["notes", f"--ref={notes_ref}", "show", sha])
        return True
    except GitCommandError:
        return False


def notes_read(sha: str, notes_ref: str = NOTES_REF) -> Optional[str]:
    """Read the note content for a commit, or None if not found."""
    try:
        return run(["notes", f"--ref={notes_ref}", "show", sha])
    except GitCommandError:
        return None


def notes_write(sha: str, content: str, notes_ref: str = NOTES_REF) -> None:
    """Write or overwrite a note for a commit."""
    # Use -f to force overwrite existing notes
    run(["notes", f"--ref={notes_ref}", "add", "-f", "-m", content, sha])


def notes_remove(sha: str, notes_ref: str = NOTES_REF) -> bool:
    """Remove a note for a commit. Returns True if removed, False if not found."""
    try:
        run(["notes", f"--ref={notes_ref}", "remove", sha])
        return True
    except GitCommandError:
        return False
