"""Tests for infrastructure notes module.

Tests the Git Notes operations for storing semantic artifacts.
Uses mocking to avoid requiring a real git repository.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from gitsummary.infrastructure.git import GitCommandError
from gitsummary.infrastructure.notes import (
    NOTES_REF,
    notes_exists,
    notes_read,
    notes_write,
    notes_remove,
)


class TestNotesRef:
    """Tests for NOTES_REF constant."""

    def test_default_notes_ref(self) -> None:
        """Test the default notes namespace."""
        assert NOTES_REF == "refs/notes/intent"


class TestNotesExists:
    """Tests for notes_exists function."""

    def test_returns_true_when_note_exists(self) -> None:
        """Test that True is returned when note exists."""
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.return_value = "note content\n"
            result = notes_exists("abc123")

            assert result is True
            mock_run.assert_called_once_with(
                ["notes", f"--ref={NOTES_REF}", "show", "abc123"]
            )

    def test_returns_false_when_note_missing(self) -> None:
        """Test that False is returned when note doesn't exist."""
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.side_effect = GitCommandError("no note found")
            result = notes_exists("abc123")

            assert result is False

    def test_uses_custom_notes_ref(self) -> None:
        """Test that custom notes ref is used."""
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.return_value = "content"
            notes_exists("abc123", notes_ref="refs/notes/custom")

            mock_run.assert_called_once_with(
                ["notes", "--ref=refs/notes/custom", "show", "abc123"]
            )


class TestNotesRead:
    """Tests for notes_read function."""

    def test_returns_content_when_exists(self) -> None:
        """Test that content is returned when note exists."""
        expected_content = "commit_hash: abc123\nintent_summary: test\n"
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.return_value = expected_content
            result = notes_read("abc123")

            assert result == expected_content

    def test_returns_none_when_missing(self) -> None:
        """Test that None is returned when note doesn't exist."""
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.side_effect = GitCommandError("no note found")
            result = notes_read("abc123")

            assert result is None

    def test_uses_custom_notes_ref(self) -> None:
        """Test that custom notes ref is used for reading."""
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.return_value = "content"
            notes_read("abc123", notes_ref="refs/notes/custom")

            mock_run.assert_called_once_with(
                ["notes", "--ref=refs/notes/custom", "show", "abc123"]
            )


class TestNotesWrite:
    """Tests for notes_write function."""

    def test_writes_note_with_force(self) -> None:
        """Test that notes are written with force flag."""
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.return_value = ""
            notes_write("abc123", "note content")

            mock_run.assert_called_once_with(
                ["notes", f"--ref={NOTES_REF}", "add", "-f", "-m", "note content", "abc123"]
            )

    def test_uses_custom_notes_ref(self) -> None:
        """Test that custom notes ref is used for writing."""
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.return_value = ""
            notes_write("abc123", "content", notes_ref="refs/notes/custom")

            mock_run.assert_called_once_with(
                ["notes", "--ref=refs/notes/custom", "add", "-f", "-m", "content", "abc123"]
            )


class TestNotesRemove:
    """Tests for notes_remove function."""

    def test_returns_true_when_removed(self) -> None:
        """Test that True is returned when note is removed."""
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.return_value = ""
            result = notes_remove("abc123")

            assert result is True
            mock_run.assert_called_once_with(
                ["notes", f"--ref={NOTES_REF}", "remove", "abc123"]
            )

    def test_returns_false_when_not_found(self) -> None:
        """Test that False is returned when note doesn't exist."""
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.side_effect = GitCommandError("no note found")
            result = notes_remove("abc123")

            assert result is False

    def test_uses_custom_notes_ref(self) -> None:
        """Test that custom notes ref is used for removal."""
        with patch("gitsummary.infrastructure.notes.run") as mock_run:
            mock_run.return_value = ""
            notes_remove("abc123", notes_ref="refs/notes/custom")

            mock_run.assert_called_once_with(
                ["notes", "--ref=refs/notes/custom", "remove", "abc123"]
            )



