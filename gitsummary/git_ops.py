"""
Git operations module.

Provides clean abstractions for interacting with Git repositories
using GitPython, focusing on pure Git data extraction.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional

import git


@dataclass
class CommitInfo:
    """Represents a single commit's metadata."""

    sha: str
    author_name: str
    author_email: str
    date: datetime
    message: str


@dataclass
class FileChange:
    """Represents a single file change in a diff."""

    path: str
    change_type: str  # A=added, D=deleted, M=modified, R=renamed
    old_path: Optional[str]  # For renames
    additions: int
    deletions: int
    diff: str  # The actual diff content


@dataclass
class BlameInfo:
    """Represents blame information for a file."""

    file_path: str
    authors: List[str]  # Unique authors who touched this file
    last_modified: datetime


class GitRepository:
    """
    Clean wrapper around GitPython for pure Git operations.

    This class provides high-level methods for extracting Git data
    without any platform-specific dependencies.
    """

    def __init__(self, repo_path: Optional[Path] = None) -> None:
        """
        Initialize a Git repository wrapper.

        Args:
            repo_path: Path to the Git repository. If None, uses current directory.

        Raises:
            git.exc.InvalidGitRepositoryError: If the path is not a valid Git repository.
        """
        self.repo_path = repo_path or Path.cwd()
        self.repo = git.Repo(self.repo_path, search_parent_directories=True)

    def get_tag_commit(self, tag_name: str) -> git.Commit:
        """
        Resolve a tag name to its commit.

        Args:
            tag_name: Name of the tag to resolve.

        Returns:
            The commit object the tag points to.

        Raises:
            ValueError: If the tag doesn't exist.
        """
        try:
            tag_ref = self.repo.tags[tag_name]
            # Tags can be annotated (tag object) or lightweight (direct commit)
            commit = tag_ref.commit
            return commit
        except (IndexError, AttributeError) as e:
            raise ValueError(f"Tag '{tag_name}' not found") from e

    def get_commits_between(
        self, tag_a: str, tag_b: str
    ) -> Iterator[CommitInfo]:
        """
        Get all commits between two tags (A..B).

        This uses Git's range semantics: commits reachable from B
        but not from A.

        Args:
            tag_a: Starting tag (exclusive).
            tag_b: Ending tag (inclusive).

        Yields:
            CommitInfo objects for each commit in the range.

        Raises:
            ValueError: If either tag doesn't exist.
        """
        commit_a = self.get_tag_commit(tag_a)
        commit_b = self.get_tag_commit(tag_b)

        # Use git log A..B semantics
        commits = self.repo.iter_commits(f"{commit_a.hexsha}..{commit_b.hexsha}")

        for commit in commits:
            yield CommitInfo(
                sha=commit.hexsha,
                author_name=commit.author.name,
                author_email=commit.author.email,
                date=datetime.fromtimestamp(commit.committed_date),
                message=commit.message.strip(),
            )

    def get_diff_between(
        self, tag_a: str, tag_b: str
    ) -> Iterator[FileChange]:
        """
        Get file-level diff between two tags.

        Args:
            tag_a: Starting tag.
            tag_b: Ending tag.

        Yields:
            FileChange objects for each changed file.

        Raises:
            ValueError: If either tag doesn't exist.
        """
        commit_a = self.get_tag_commit(tag_a)
        commit_b = self.get_tag_commit(tag_b)

        # Get the diff between the two commits
        diff_index = commit_a.diff(commit_b)

        for diff_item in diff_index:
            # Determine change type
            if diff_item.new_file:
                change_type = "A"
                path = diff_item.b_path
                old_path = None
            elif diff_item.deleted_file:
                change_type = "D"
                path = diff_item.a_path
                old_path = None
            elif diff_item.renamed_file:
                change_type = "R"
                path = diff_item.b_path
                old_path = diff_item.a_path
            else:
                change_type = "M"
                path = diff_item.a_path or diff_item.b_path
                old_path = None

            # Get diff content
            try:
                diff_text = diff_item.diff.decode("utf-8", errors="replace")
            except AttributeError:
                diff_text = ""

            # Count additions and deletions from the diff text
            additions = diff_text.count("\n+") - diff_text.count("\n+++")
            deletions = diff_text.count("\n-") - diff_text.count("\n---")

            yield FileChange(
                path=path,
                change_type=change_type,
                old_path=old_path,
                additions=max(0, additions),
                deletions=max(0, deletions),
                diff=diff_text,
            )

    def get_blame_for_file(
        self, file_path: str, ref: str = "HEAD"
    ) -> Optional[BlameInfo]:
        """
        Get blame information for a file at a specific ref.

        Args:
            file_path: Path to the file relative to repo root.
            ref: Git reference (commit, tag, branch) to blame at.

        Returns:
            BlameInfo object or None if file doesn't exist.
        """
        try:
            commit = self.repo.commit(ref)
            blame_entries = self.repo.blame(commit, file_path)

            # Extract unique authors and find last modification
            authors = set()
            last_date = None

            for commit_obj, _ in blame_entries:
                authors.add(f"{commit_obj.author.name} <{commit_obj.author.email}>")
                commit_date = datetime.fromtimestamp(commit_obj.committed_date)
                if last_date is None or commit_date > last_date:
                    last_date = commit_date

            return BlameInfo(
                file_path=file_path,
                authors=sorted(authors),
                last_modified=last_date or datetime.now(),
            )
        except (git.exc.GitCommandError, KeyError):
            return None

    def get_commit_summary(self, commits: List[CommitInfo]) -> str:
        """
        Generate a human-readable summary of commit messages.

        Args:
            commits: List of CommitInfo objects.

        Returns:
            Formatted summary string.
        """
        if not commits:
            return "No commits in range"

        lines = []
        for commit in commits:
            # Take first line of commit message
            first_line = commit.message.split("\n")[0]
            lines.append(f"- {commit.sha[:7]}: {first_line}")

        return "\n".join(lines)
