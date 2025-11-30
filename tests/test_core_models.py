"""Tests for core domain models.

Tests the dataclasses in gitsummary.core.models including
CommitInfo, FileChange, DiffStat, DiffHunk, FileDiff, and CommitDiff.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from gitsummary.core import (
    CommitDiff,
    CommitInfo,
    DiffHunk,
    DiffStat,
    FileChange,
    FileDiff,
)


class TestCommitInfo:
    """Tests for CommitInfo dataclass."""

    def test_creation_with_all_fields(self, simple_commit: CommitInfo) -> None:
        """Test that CommitInfo can be created with all fields."""
        assert simple_commit.sha == "abc1234567890abcdef1234567890abcdef123456"
        assert simple_commit.short_sha == "abc1234"
        assert simple_commit.author_name == "Test Author"
        assert simple_commit.author_email == "test@example.com"
        assert simple_commit.summary == "feat: add user authentication"
        assert "basic user authentication" in simple_commit.body

    def test_full_message_with_body(self, simple_commit: CommitInfo) -> None:
        """Test full_message property when body is present."""
        message = simple_commit.full_message
        assert message.startswith("feat: add user authentication")
        assert "basic user authentication" in message
        assert "\n\n" in message

    def test_full_message_without_body(self) -> None:
        """Test full_message property when body is empty."""
        commit = CommitInfo(
            sha="abc123",
            short_sha="abc",
            author_name="Test",
            author_email="test@test.com",
            date=datetime.now(timezone.utc),
            summary="Simple commit",
            body="",
            parent_shas=[],
        )
        assert commit.full_message == "Simple commit"

    def test_is_merge_single_parent(self, simple_commit: CommitInfo) -> None:
        """Test is_merge is False for regular commits."""
        assert simple_commit.is_merge is False

    def test_is_merge_multiple_parents(self, merge_commit: CommitInfo) -> None:
        """Test is_merge is True for merge commits."""
        assert merge_commit.is_merge is True

    def test_is_merge_no_parents(self) -> None:
        """Test is_merge is False for root commits."""
        root_commit = CommitInfo(
            sha="root",
            short_sha="root",
            author_name="Test",
            author_email="test@test.com",
            date=datetime.now(timezone.utc),
            summary="Initial commit",
            body="",
            parent_shas=[],
        )
        assert root_commit.is_merge is False

    def test_immutability(self, simple_commit: CommitInfo) -> None:
        """Test that CommitInfo is frozen (immutable)."""
        with pytest.raises(AttributeError):
            simple_commit.sha = "new_sha"  # type: ignore[misc]


class TestFileChange:
    """Tests for FileChange dataclass."""

    def test_added_file(self) -> None:
        """Test status label for added files."""
        change = FileChange(status="A", path="new_file.py")
        assert change.status_label == "added"

    def test_deleted_file(self) -> None:
        """Test status label for deleted files."""
        change = FileChange(status="D", path="old_file.py")
        assert change.status_label == "deleted"

    def test_modified_file(self) -> None:
        """Test status label for modified files."""
        change = FileChange(status="M", path="file.py")
        assert change.status_label == "modified"

    def test_renamed_file(self) -> None:
        """Test status label for renamed files."""
        change = FileChange(status="R100", path="new_name.py", old_path="old_name.py")
        assert change.status_label == "renamed"
        assert change.old_path == "old_name.py"

    def test_copied_file(self) -> None:
        """Test status label for copied files."""
        change = FileChange(status="C100", path="copy.py", old_path="original.py")
        assert change.status_label == "copied"

    def test_type_changed_file(self) -> None:
        """Test status label for type-changed files."""
        change = FileChange(status="T", path="file")
        assert change.status_label == "type changed"

    def test_unknown_status(self) -> None:
        """Test status label for unknown status codes."""
        change = FileChange(status="X", path="file.py")
        assert change.status_label == "unknown"


class TestDiffStat:
    """Tests for DiffStat dataclass."""

    def test_total_changes(self) -> None:
        """Test total_changes calculation."""
        stat = DiffStat(insertions=100, deletions=50)
        assert stat.total_changes == 150

    def test_zero_changes(self) -> None:
        """Test total_changes when no changes."""
        stat = DiffStat(insertions=0, deletions=0)
        assert stat.total_changes == 0

    def test_insertions_only(self) -> None:
        """Test total_changes with only insertions."""
        stat = DiffStat(insertions=50, deletions=0)
        assert stat.total_changes == 50

    def test_deletions_only(self) -> None:
        """Test total_changes with only deletions."""
        stat = DiffStat(insertions=0, deletions=25)
        assert stat.total_changes == 25


class TestDiffHunk:
    """Tests for DiffHunk dataclass."""

    def test_hunk_creation(self) -> None:
        """Test that DiffHunk can be created."""
        hunk = DiffHunk(
            old_start=10,
            old_count=5,
            new_start=10,
            new_count=7,
            content="@@ -10,5 +10,7 @@\n context\n-old line\n+new line\n",
        )
        assert hunk.old_start == 10
        assert hunk.old_count == 5
        assert hunk.new_start == 10
        assert hunk.new_count == 7
        assert "old line" in hunk.content


class TestFileDiff:
    """Tests for FileDiff dataclass."""

    def test_file_diff_creation(self) -> None:
        """Test that FileDiff can be created."""
        diff = FileDiff(
            path="src/main.py",
            old_path=None,
            status="M",
            insertions=10,
            deletions=5,
            patch="diff content",
            hunks=[],
        )
        assert diff.path == "src/main.py"
        assert diff.status == "M"
        assert diff.insertions == 10
        assert diff.deletions == 5

    def test_file_diff_with_rename(self) -> None:
        """Test FileDiff for renamed files."""
        diff = FileDiff(
            path="new_name.py",
            old_path="old_name.py",
            status="R100",
            insertions=0,
            deletions=0,
            patch="",
            hunks=[],
        )
        assert diff.old_path == "old_name.py"
        assert diff.path == "new_name.py"


class TestCommitDiff:
    """Tests for CommitDiff dataclass."""

    def test_file_paths_property(self, simple_diff: CommitDiff) -> None:
        """Test file_paths property returns correct paths."""
        paths = simple_diff.file_paths
        assert "src/auth.py" in paths

    def test_file_paths_multiple_files(self, multi_file_diff: CommitDiff) -> None:
        """Test file_paths with multiple files."""
        paths = multi_file_diff.file_paths
        assert len(paths) == 3
        assert "src/auth.py" in paths
        assert "tests/test_auth.py" in paths
        assert "README.md" in paths

    def test_empty_diff(self) -> None:
        """Test CommitDiff with no file changes."""
        diff = CommitDiff(
            sha="empty",
            files=[],
            stat=DiffStat(insertions=0, deletions=0),
        )
        assert diff.file_paths == []
        assert diff.stat.total_changes == 0

