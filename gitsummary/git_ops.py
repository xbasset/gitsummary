"""Git operations for collecting repository data."""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from git import Repo, Tag, Commit, Diff
from git.exc import GitCommandError


@dataclass
class CommitInfo:
    """Information about a single commit."""

    hexsha: str
    author: str
    author_email: str
    authored_date: datetime
    message: str
    summary: str


@dataclass
class FileChange:
    """Information about a file change."""

    path: str
    change_type: str  # 'A', 'D', 'M', 'R'
    additions: int
    deletions: int
    diff: str
    hunks: List[str]  # List of hunk headers like "@@ -21,7 +22,11 @@"


@dataclass
class BlameInfo:
    """Blame information for a file."""

    path: str
    lines: Dict[int, Tuple[str, str]]  # line_number -> (commit_hexsha, author)


class GitOperations:
    """Handles Git repository operations."""

    def __init__(self, repo_path: str = "."):
        """Initialize Git operations.

        Args:
            repo_path: Path to the Git repository root
        """
        self.repo = Repo(repo_path)
        if self.repo.bare:
            raise ValueError("Repository is bare, cannot work with working tree")
        self.repo_root = Path(self.repo.working_tree_dir) if self.repo.working_tree_dir else Path(repo_path)

    def get_tag(self, tag_name: str) -> Optional[Tag]:
        """Get a tag object by name.

        Args:
            tag_name: Name of the tag

        Returns:
            Tag object or None if not found
        """
        try:
            return self.repo.tags[tag_name]
        except (IndexError, KeyError):
            return None

    def get_commits_between(self, tag_a: str, tag_b: str) -> List[Commit]:
        """Get commits between two tags (A..B).

        Args:
            tag_a: Starting tag (exclusive)
            tag_b: Ending tag (inclusive)

        Returns:
            List of commits in the range
        """
        tag_a_obj = self.get_tag(tag_a)
        tag_b_obj = self.get_tag(tag_b)

        if tag_a_obj is None:
            raise ValueError(f"Tag '{tag_a}' not found")
        if tag_b_obj is None:
            raise ValueError(f"Tag '{tag_b}' not found")

        # Get commits reachable from tag_b but not from tag_a
        commits = list(self.repo.iter_commits(f"{tag_a}..{tag_b}"))
        return commits

    def get_commit_info(self, commit: Commit) -> CommitInfo:
        """Extract structured information from a commit.

        Args:
            commit: Git commit object

        Returns:
            CommitInfo with structured data
        """
        return CommitInfo(
            hexsha=commit.hexsha,
            author=commit.author.name,
            author_email=commit.author.email,
            authored_date=commit.authored_datetime,
            message=commit.message,
            summary=commit.summary,
        )

    def get_diff_between_tags(self, tag_a: str, tag_b: str) -> Diff:
        """Get the diff between two tags.

        Args:
            tag_a: Starting tag
            tag_b: Ending tag

        Returns:
            Diff object
        """
        tag_a_obj = self.get_tag(tag_a)
        tag_b_obj = self.get_tag(tag_b)

        if tag_a_obj is None:
            raise ValueError(f"Tag '{tag_a}' not found")
        if tag_b_obj is None:
            raise ValueError(f"Tag '{tag_b}' not found")

        return tag_a_obj.commit.diff(tag_b_obj.commit, create_patch=True)

    def extract_file_changes(self, diff: Diff) -> List[FileChange]:
        """Extract file change information from a diff.

        Args:
            diff: Git diff object

        Returns:
            List of FileChange objects
        """
        changes = []
        hunk_pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

        for item in diff:
            if item.b_blob is None and item.a_blob is None:
                continue

            # Determine change type
            if item.new_file:
                change_type = "A"
            elif item.deleted_file:
                change_type = "D"
            elif item.renamed_file:
                change_type = "R"
            else:
                change_type = "M"

            # Extract hunks
            hunks = []
            if item.diff:
                for line in item.diff.decode("utf-8", errors="replace").split("\n"):
                    match = hunk_pattern.match(line)
                    if match:
                        hunks.append(line)

            # Count additions and deletions
            additions = sum(
                1
                for line in item.diff.decode("utf-8", errors="replace").split("\n")
                if line.startswith("+") and not line.startswith("+++")
            )
            deletions = sum(
                1
                for line in item.diff.decode("utf-8", errors="replace").split("\n")
                if line.startswith("-") and not line.startswith("---")
            )

            changes.append(
                FileChange(
                    path=item.b_path or item.a_path,
                    change_type=change_type,
                    additions=additions,
                    deletions=deletions,
                    diff=item.diff.decode("utf-8", errors="replace") if item.diff else "",
                    hunks=hunks,
                )
            )

        return changes

    def get_blame_for_file(self, commit: Commit, file_path: str) -> Optional[BlameInfo]:
        """Get blame information for a file at a specific commit.

        Args:
            commit: Commit to check blame at
            file_path: Path to the file relative to repo root

        Returns:
            BlameInfo or None if file doesn't exist at that commit
        """
        try:
            # Get the blob at this commit
            try:
                blob = commit.tree / file_path
            except KeyError:
                return None

            # Get blame for the file
            blame_result = self.repo.blame(commit, file_path)
            lines: Dict[int, Tuple[str, str]] = {}

            for i, (commit_obj, line_content) in enumerate(blame_result, start=1):
                lines[i] = (commit_obj.hexsha, commit_obj.author.name)

            return BlameInfo(path=file_path, lines=lines)
        except (GitCommandError, KeyError):
            return None

    def get_authors(self, commits: List[Commit]) -> Set[str]:
        """Get unique authors from a list of commits.

        Args:
            commits: List of commit objects

        Returns:
            Set of author names
        """
        return {commit.author.name for commit in commits}

    def get_date_range(self, commits: List[Commit]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get the date range from a list of commits.

        Args:
            commits: List of commit objects

        Returns:
            Tuple of (earliest_date, latest_date)
        """
        if not commits:
            return (None, None)

        dates = [commit.authored_datetime for commit in commits]
        return (min(dates), max(dates))

    def get_branches_in_range(self, tag_a: str, tag_b: str) -> List[str]:
        """Get branches that contain commits in the range.

        Args:
            tag_a: Starting tag
            tag_b: Ending tag

        Returns:
            List of branch names
        """
        tag_b_obj = self.get_tag(tag_b)
        if tag_b_obj is None:
            return []

        branches = []
        commits = self.get_commits_between(tag_a, tag_b)

        for branch in self.repo.branches:
            try:
                branch_commits = list(self.repo.iter_commits(branch))
                branch_commit_shas = {c.hexsha for c in branch_commits}
                if any(c.hexsha in branch_commit_shas for c in commits):
                    branches.append(branch.name)
            except Exception:
                continue

        return branches
