"""Tests for infrastructure git module.

Tests the git command wrapper and data extraction functions.
Uses mocking to avoid requiring a real git repository.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gitsummary.infrastructure.git import (
    GitCommandError,
    run,
    repository_root,
    resolve_revision,
    is_valid_revision,
    check_revisions,
    get_commit_info,
    list_commits_in_range,
    get_commit_diff,
    diff_stat,
    diff_patch,
    diff_patch_for_commit,
    tracked_files,
    _parse_git_date,
)
from gitsummary.core import CommitDiff, CommitInfo, DiffStat, FileChange, FileDiff


class TestRun:
    """Tests for the run function."""

    def test_run_success(self) -> None:
        """Test that run returns stdout on success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output text\n",
                stderr="",
            )
            result = run(["status"])
            assert result == "output text\n"
            mock_run.assert_called_once()

    def test_run_failure_raises(self) -> None:
        """Test that run raises GitCommandError on failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="fatal: error message",
            )
            with pytest.raises(GitCommandError) as exc_info:
                run(["invalid-command"])
            assert "fatal: error message" in str(exc_info.value)

    def test_run_failure_empty_stderr(self) -> None:
        """Test run with empty stderr uses fallback message."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="",
            )
            with pytest.raises(GitCommandError) as exc_info:
                run(["bad-command"])
            assert "git command failed" in str(exc_info.value)

    def test_run_with_cwd(self) -> None:
        """Test that run passes cwd to subprocess."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            run(["status"], cwd=Path("/some/path"))
            call_args = mock_run.call_args
            assert call_args.kwargs["cwd"] == Path("/some/path")


class TestRepositoryRoot:
    """Tests for repository_root function."""

    def test_returns_path(self) -> None:
        """Test that repository_root returns a Path object."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "/path/to/repo\n"
            result = repository_root()
            assert result == Path("/path/to/repo")
            mock_run.assert_called_once_with(["rev-parse", "--show-toplevel"])


class TestResolveRevision:
    """Tests for resolve_revision function."""

    def test_resolves_sha(self) -> None:
        """Test resolving a full SHA."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "abc1234567890\n"
            result = resolve_revision("abc123")
            assert result == "abc1234567890"

    def test_resolves_tag(self) -> None:
        """Test resolving a tag name."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "def9876543210\n"
            result = resolve_revision("v1.0.0")
            assert result == "def9876543210"


class TestIsValidRevision:
    """Tests for is_valid_revision function."""

    def test_valid_revision_returns_true(self) -> None:
        """Test that valid revision returns True."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "abc123\n"
            assert is_valid_revision("HEAD") is True

    def test_invalid_revision_returns_false(self) -> None:
        """Test that invalid revision returns False."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.side_effect = GitCommandError("not a valid object")
            assert is_valid_revision("nonexistent") is False


class TestCheckRevisions:
    """Tests for check_revisions function."""

    def test_all_valid_passes(self) -> None:
        """Test that valid revisions don't raise."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "abc123\n"
            # Should not raise
            check_revisions(["HEAD", "main", "v1.0"])

    def test_invalid_revision_raises(self) -> None:
        """Test that invalid revision raises GitCommandError."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.side_effect = GitCommandError("bad revision")
            with pytest.raises(GitCommandError):
                check_revisions(["bad-ref"])


class TestParseGitDate:
    """Tests for _parse_git_date function."""

    def test_parse_iso_format(self) -> None:
        """Test parsing standard ISO format."""
        result = _parse_git_date("2024-01-15T10:30:00+00:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_z_suffix(self) -> None:
        """Test parsing date with Z suffix (UTC)."""
        result = _parse_git_date("2024-01-15T10:30:00Z")
        assert result.year == 2024
        assert result.tzinfo is not None


class TestGetCommitInfo:
    """Tests for get_commit_info function."""

    def test_returns_commit_info(self) -> None:
        """Test that get_commit_info returns a CommitInfo object."""
        # Format: SHA\x00short_sha\x00author_name\x00author_email\x00date\x00subject\x00body\x00parents
        mock_output = (
            "abc1234567890\x00abc1234\x00Test Author\x00test@example.com\x00"
            "2024-01-15T10:30:00+00:00\x00feat: add feature\x00Body text\x00parent123\n"
        )
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = mock_output
            result = get_commit_info("abc123")

            assert isinstance(result, CommitInfo)
            assert result.sha == "abc1234567890"
            assert result.short_sha == "abc1234"
            assert result.author_name == "Test Author"
            assert result.author_email == "test@example.com"
            assert result.summary == "feat: add feature"
            assert result.body == "Body text"
            assert result.parent_shas == ["parent123"]

    def test_handles_no_parents(self) -> None:
        """Test handling of root commit (no parents)."""
        mock_output = (
            "abc123\x00abc\x00Author\x00a@b.com\x00"
            "2024-01-15T10:30:00Z\x00Initial commit\x00\x00\n"
        )
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = mock_output
            result = get_commit_info("abc123")
            assert result.parent_shas == []

    def test_handles_multiple_parents(self) -> None:
        """Test handling of merge commit (multiple parents)."""
        mock_output = (
            "abc123\x00abc\x00Author\x00a@b.com\x00"
            "2024-01-15T10:30:00Z\x00Merge\x00\x00parent1 parent2\n"
        )
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = mock_output
            result = get_commit_info("abc123")
            assert result.parent_shas == ["parent1", "parent2"]
            assert result.is_merge is True

    def test_invalid_output_raises(self) -> None:
        """Test that invalid output raises GitCommandError."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "invalid\x00output\n"
            with pytest.raises(GitCommandError):
                get_commit_info("abc123")


class TestListCommitsInRange:
    """Tests for list_commits_in_range function."""

    def test_range_with_two_dots(self) -> None:
        """Test listing commits in a range."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            # First call: rev-list for the range
            # Second+ calls: log for each commit info
            mock_run.side_effect = [
                "sha1\nsha2\nsha3\n",  # rev-list output
                "sha3\x00sha3\x00A\x00a@b.com\x002024-01-15T10:30:00Z\x00Msg3\x00\x00sha2\n",
                "sha2\x00sha2\x00A\x00a@b.com\x002024-01-14T10:30:00Z\x00Msg2\x00\x00sha1\n",
                "sha1\x00sha1\x00A\x00a@b.com\x002024-01-13T10:30:00Z\x00Msg1\x00\x00\n",
            ]
            result = list_commits_in_range("v1.0..v2.0")

            assert len(result) == 3
            # Ordered newest first
            assert result[0].sha == "sha3"
            assert result[1].sha == "sha2"
            assert result[2].sha == "sha1"

    def test_single_revision(self) -> None:
        """Test listing a single commit."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.side_effect = [
                "abc123fullsha\n",  # resolve_revision
                "abc123fullsha\x00abc\x00A\x00a@b.com\x002024-01-15T10:30:00Z\x00Msg\x00\x00\n",
            ]
            result = list_commits_in_range("abc123")

            assert len(result) == 1
            assert result[0].sha == "abc123fullsha"


class TestGetCommitDiff:
    """Tests for get_commit_diff function."""

    def test_returns_commit_diff(self) -> None:
        """Test that get_commit_diff returns a CommitDiff object."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.side_effect = [
                "abc123fullsha\n",  # resolve_revision
                "10\t5\tsrc/main.py\n",  # numstat
                "M\tsrc/main.py\n",  # name-status
            ]
            result = get_commit_diff("abc123")

            assert isinstance(result, CommitDiff)
            assert result.sha == "abc123fullsha"
            assert len(result.files) == 1
            assert result.files[0].path == "src/main.py"
            assert result.files[0].status == "M"
            assert result.stat.insertions == 10
            assert result.stat.deletions == 5

    def test_handles_renamed_file(self) -> None:
        """Test handling of renamed files."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.side_effect = [
                "abc123\n",  # resolve_revision
                "0\t0\tnew.py\n",  # numstat
                "R100\told.py\tnew.py\n",  # name-status with rename
            ]
            result = get_commit_diff("abc123")

            assert len(result.files) == 1
            assert result.files[0].path == "new.py"
            assert result.files[0].old_path == "old.py"
            assert result.files[0].status == "R100"

    def test_handles_binary_files(self) -> None:
        """Test handling of binary files (- for stats)."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.side_effect = [
                "abc123\n",  # resolve_revision
                "-\t-\timage.png\n",  # numstat with binary
                "A\timage.png\n",  # name-status
            ]
            result = get_commit_diff("abc123")

            assert len(result.files) == 1
            assert result.files[0].insertions == 0
            assert result.files[0].deletions == 0


class TestDiffStat:
    """Tests for diff_stat function."""

    def test_returns_diff_stat(self) -> None:
        """Test that diff_stat returns a DiffStat object."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "10\t5\tfile1.py\n20\t10\tfile2.py\n"
            result = diff_stat("v1.0..v2.0")

            assert isinstance(result, DiffStat)
            assert result.insertions == 30
            assert result.deletions == 15

    def test_handles_empty_diff(self) -> None:
        """Test handling of empty diff."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "\n"
            result = diff_stat("same..same")

            assert result.insertions == 0
            assert result.deletions == 0

    def test_handles_binary_files(self) -> None:
        """Test handling of binary files in stats."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "-\t-\tbinary.png\n5\t2\ttext.py\n"
            result = diff_stat("v1.0..v2.0")

            # Binary files don't add to counts
            assert result.insertions == 5
            assert result.deletions == 2


class TestDiffPatch:
    """Tests for diff_patch function."""

    def test_returns_patch_string(self) -> None:
        """Test that diff_patch returns the raw patch."""
        patch_content = "diff --git a/file.py b/file.py\n+line\n"
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = patch_content
            result = diff_patch("v1.0..v2.0")

            assert result == patch_content


class TestDiffPatchForCommit:
    """Tests for diff_patch_for_commit function."""

    def test_returns_commit_patch(self) -> None:
        """Test getting patch for a single commit."""
        patch_content = "diff --git a/file.py b/file.py\n+added line\n"
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.side_effect = [
                "abc123fullsha\n",  # resolve_revision
                patch_content,  # diff output
            ]
            result = diff_patch_for_commit("abc123")

            assert result == patch_content


class TestTrackedFiles:
    """Tests for tracked_files function."""

    def test_returns_file_changes(self) -> None:
        """Test that tracked_files returns FileChange objects."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "M\tsrc/main.py\nA\tsrc/new.py\nD\told.py\n"
            result = tracked_files("v1.0..v2.0")

            assert len(result) == 3
            assert all(isinstance(f, FileChange) for f in result)
            assert result[0].status == "M"
            assert result[0].path == "src/main.py"
            assert result[1].status == "A"
            assert result[2].status == "D"

    def test_handles_rename(self) -> None:
        """Test handling of renamed files."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "R100\told.py\tnew.py\n"
            result = tracked_files("v1.0..v2.0")

            assert len(result) == 1
            assert result[0].status == "R100"
            assert result[0].path == "new.py"
            assert result[0].old_path == "old.py"

    def test_handles_copy(self) -> None:
        """Test handling of copied files."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "C100\toriginal.py\tcopy.py\n"
            result = tracked_files("v1.0..v2.0")

            assert len(result) == 1
            assert result[0].status == "C100"
            assert result[0].path == "copy.py"
            assert result[0].old_path == "original.py"

    def test_handles_empty_result(self) -> None:
        """Test handling of no changed files."""
        with patch("gitsummary.infrastructure.git.run") as mock_run:
            mock_run.return_value = "\n"
            result = tracked_files("same..same")

            assert result == []

