"""Git command wrapper and data extraction.

This module encapsulates all git subprocess calls, providing
a clean interface for the rest of the application. It handles
error translation and data parsing.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from ..core import CommitDiff, CommitInfo, DiffStat, FileChange, FileDiff, TagInfo


class GitCommandError(RuntimeError):
    """Raised when an underlying git command fails."""


# ─────────────────────────────────────────────────────────────────────────────
# Low-Level Command Execution
# ─────────────────────────────────────────────────────────────────────────────


def run(args: Sequence[str], *, cwd: Optional[Path] = None) -> str:
    """Run ``git`` with ``args`` and return stdout, raising on errors.

    Args:
        args: Arguments to pass to git (without the 'git' prefix).
        cwd: Optional working directory for the command.

    Returns:
        The stdout output from the command.

    Raises:
        GitCommandError: If the command exits with non-zero status.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# Repository Information
# ─────────────────────────────────────────────────────────────────────────────


def repository_root() -> Path:
    """Return the root directory of the current repository."""
    return Path(run(["rev-parse", "--show-toplevel"]).strip())


def is_worktree_clean() -> bool:
    """Return True if the working tree has no staged or unstaged changes."""
    status = run(["status", "--porcelain"])
    return status.strip() == ""


def ensure_clean_worktree() -> None:
    """Raise GitCommandError if the worktree has uncommitted changes."""
    if not is_worktree_clean():
        raise GitCommandError("Working tree is dirty. Commit or stash changes first.")


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


def check_revisions(revisions: Sequence[str]) -> None:
    """Validate that the given revisions exist.

    Raises:
        GitCommandError: If any revision is invalid.
    """
    for rev in revisions:
        run(["rev-parse", "--verify", rev])


# ─────────────────────────────────────────────────────────────────────────────
# Tag Information
# ─────────────────────────────────────────────────────────────────────────────


def fetch_tags(*, prune: bool = False) -> None:
    """Fetch remote tags.

    Args:
        prune: Whether to prune deleted tags.
    """
    args = ["fetch", "--tags"]
    if prune:
        args.append("--prune")
    run(args)


def list_tags_by_date() -> List[TagInfo]:
    """Return all tags ordered by annotated/creation date (oldest→newest)."""
    # Avoid git sort specifiers (taggerdate) for compatibility; sort in Python instead.
    output = run(
        [
            "for-each-ref",
            "--format=%(refname:strip=2)\t%(taggerdate:iso8601)\t%(creatordate:iso8601)\t%(objectname)",
            "refs/tags",
        ]
    )
    
    tags: List[TagInfo] = []
    for line in output.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        name, taggerdate, creatordate, _ = parts[:4]
        date_str = taggerdate or creatordate
        if not date_str:
            continue
        tags.append(
            TagInfo(
                name=name,
                sha=resolve_revision(name),
                date=_parse_git_date(date_str),
                is_annotated=bool(taggerdate),
            )
        )

    tags.sort(key=lambda t: t.date)
    return tags


def get_root_commit() -> str:
    """Return the SHA of the repository's root commit."""
    output = run(["rev-list", "--max-parents=0", "HEAD"])
    roots = [line for line in output.strip().splitlines() if line]
    if not roots:
        raise GitCommandError("Unable to determine root commit")
    return roots[0]


# ─────────────────────────────────────────────────────────────────────────────
# Commit Information Retrieval
# ─────────────────────────────────────────────────────────────────────────────


def _parse_git_date(date_str: str) -> datetime:
    """Parse a git ISO-8601 date string, handling the 'Z' suffix.

    Git uses 'Z' for UTC, but Python's fromisoformat() only supports
    this in Python 3.11+. This helper normalizes the format.
    """
    # Replace 'Z' suffix with '+00:00' for compatibility with Python < 3.11
    if date_str.endswith("Z"):
        date_str = date_str[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        # Fallback for git formats like "2025-12-02 14:32:07 +0100"
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        except ValueError as exc:  # pragma: no cover - defensive
            raise


def get_commit_info(revision: str) -> CommitInfo:
    """Get complete information about a single commit.

    Args:
        revision: Any valid git revision (SHA, tag, branch, HEAD, etc.).

    Returns:
        CommitInfo with all commit metadata.

    Raises:
        GitCommandError: If the revision is invalid.
    """
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
        date=_parse_git_date(date_str),
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

    Args:
        range_spec: Git revision range or single revision.

    Returns:
        List of CommitInfo, newest first.

    Raises:
        GitCommandError: If the range is invalid.
    """
    if ".." in range_spec:
        # It's a range - get all commits in the range
        output = run(["rev-list", "--reverse", range_spec])
        shas = [sha for sha in output.strip().splitlines() if sha]
    else:
        # Single revision - resolve and return just that commit
        sha = resolve_revision(range_spec)
        shas = [sha]

    return [get_commit_info(sha) for sha in reversed(shas)]


def list_commits_to_revision(revision: str) -> List[CommitInfo]:
    """Return all commits reachable from a revision (newest → oldest)."""
    output = run(["rev-list", revision])
    shas = [sha for sha in output.strip().splitlines() if sha]
    return [get_commit_info(sha) for sha in shas]


# ─────────────────────────────────────────────────────────────────────────────
# Diff Extraction
# ─────────────────────────────────────────────────────────────────────────────


def get_commit_diff(revision: str) -> CommitDiff:
    """Get the complete diff for a single commit.

    For merge commits, shows the combined diff against the first parent.

    Args:
        revision: Any valid git revision.

    Returns:
        CommitDiff with all file changes and statistics.
    """
    sha = resolve_revision(revision)

    # Get numstat for per-file statistics
    numstat_output = run(["diff", "--numstat", f"{sha}^!"])
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
    name_status_output = run(["diff", "--name-status", f"{sha}^!"])
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
                patch="",  # Full patch stored at commit level for simplicity
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
    """Return aggregate diff statistics for a revision range.

    Args:
        range_spec: Git revision range (e.g., "v1.0..v2.0").

    Returns:
        DiffStat with total insertions and deletions.
    """
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
    """Return the unified diff for a revision range.

    Args:
        range_spec: Git revision range (e.g., "v1.0..v2.0").

    Returns:
        The unified diff as a string.
    """
    return run(["diff", range_spec])


def diff_patch_for_commit(revision: str) -> str:
    """Return the unified diff for a single commit against its parent.

    Args:
        revision: Any valid git revision.

    Returns:
        The unified diff as a string.
    """
    sha = resolve_revision(revision)
    return run(["diff", f"{sha}^..{sha}"])


def tracked_files(range_spec: str) -> List[FileChange]:
    """Return the list of changed files for a revision range.

    Args:
        range_spec: Git revision range (e.g., "v1.0..v2.0").

    Returns:
        List of FileChange objects.
    """
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
