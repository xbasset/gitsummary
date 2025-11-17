"""Light-weight helpers around git plumbing commands used by the CLI."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

__all__ = [
    "GitCommandError",
    "Commit",
    "FileChange",
    "DiffStat",
    "run",
    "repository_root",
    "list_commits",
    "diff_stat",
    "diff_patch",
    "tracked_files",
    "check_tags",
]


class GitCommandError(RuntimeError):
    """Raised when an underlying git command fails."""


@dataclass(frozen=True)
class Commit:
    """Information about a single commit returned by ``git log``."""

    sha: str
    author: str
    date: datetime
    summary: str


@dataclass(frozen=True)
class FileChange:
    """Represents an entry from ``git diff --name-status``."""

    status: str
    path: str


@dataclass(frozen=True)
class DiffStat:
    """Aggregate statistics from ``git diff --numstat``."""

    insertions: int
    deletions: int


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


def list_commits(range_spec: str) -> List[Commit]:
    """Return commits for ``range_spec`` ordered from newest to oldest."""

    output = run(
        ["log", "--format=%H\x1f%an\x1f%ad\x1f%s", "--date=iso-strict", range_spec]
    )
    commits: List[Commit] = []
    for line in output.strip().splitlines():
        if not line:
            continue
        sha, author, date_raw, summary = line.split("\x1f", 3)
        commits.append(
            Commit(
                sha=sha,
                author=author,
                date=datetime.fromisoformat(date_raw),
                summary=summary.strip(),
            )
        )
    return commits


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


def tracked_files(range_spec: str) -> List[FileChange]:
    """Return the list of changed files for ``range_spec``."""

    output = run(["diff", "--name-status", range_spec])
    files: List[FileChange] = []
    for line in output.strip().splitlines():
        if not line:
            continue
        status, *rest = line.split("\t")
        path = rest[-1] if rest else ""
        files.append(FileChange(status=status, path=path))
    return files


def check_tags(tags: Iterable[str]) -> None:
    """Validate that the given tags exist."""

    for tag in tags:
        run(["rev-parse", "--verify", tag])
