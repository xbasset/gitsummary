"""Tests for infrastructure notes module.

Tests the Git Notes operations for storing semantic artifacts.
Uses mocking to avoid requiring a real git repository.
"""

from __future__ import annotations

from unittest.mock import patch

from gitsummary.infrastructure.git import GitCommandError
from gitsummary.infrastructure.notes import (
    NOTES_REF,
    RELEASE_NOTE_NOTES_REF,
    load_release_note,
    notes_exists,
    notes_read,
    notes_remove,
    notes_write,
    release_note_exists,
    save_release_note,
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


# ─────────────────────────────────────────────────────────────────────────────
# Release Note Storage Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestReleaseNoteNotesRef:
    """Tests for RELEASE_NOTE_NOTES_REF constant."""

    def test_release_note_notes_ref(self) -> None:
        """Test the release note notes namespace."""
        assert RELEASE_NOTE_NOTES_REF == "refs/notes/report/release-note"

    def test_different_from_commit_notes(self) -> None:
        """Test that release note namespace differs from commit notes."""
        assert RELEASE_NOTE_NOTES_REF != NOTES_REF


class TestSaveReleaseNote:
    """Tests for save_release_note function."""

    def test_saves_to_correct_namespace(self) -> None:
        """Test that release notes are saved to the correct namespace."""
        yaml_content = "schema_version: 1.0.0\nartifact_type: release-note\n"
        with patch("gitsummary.infrastructure.notes.notes_write") as mock_write:
            save_release_note("abc123", yaml_content)

            mock_write.assert_called_once_with(
                "abc123", yaml_content, notes_ref=RELEASE_NOTE_NOTES_REF
            )

    def test_saves_yaml_content(self) -> None:
        """Test that YAML content is passed through correctly."""
        yaml_content = """schema_version: 1.0.0
artifact_type: release-note
header:
  product_name: TestApp
  version: v1.0.0
"""
        with patch("gitsummary.infrastructure.notes.notes_write") as mock_write:
            save_release_note("abc123def456", yaml_content)

            call_args = mock_write.call_args
            assert call_args[0][1] == yaml_content


class TestLoadReleaseNote:
    """Tests for load_release_note function."""

    def test_loads_from_correct_namespace(self) -> None:
        """Test that release notes are loaded from the correct namespace."""
        with patch("gitsummary.infrastructure.notes.notes_read") as mock_read:
            mock_read.return_value = "schema_version: 1.0.0"
            load_release_note("abc123")

            mock_read.assert_called_once_with("abc123", notes_ref=RELEASE_NOTE_NOTES_REF)

    def test_returns_content_when_exists(self) -> None:
        """Test that content is returned when release note exists."""
        expected_content = "schema_version: 1.0.0\nartifact_type: release-note\n"
        with patch("gitsummary.infrastructure.notes.notes_read") as mock_read:
            mock_read.return_value = expected_content
            result = load_release_note("abc123")

            assert result == expected_content

    def test_returns_none_when_missing(self) -> None:
        """Test that None is returned when release note doesn't exist."""
        with patch("gitsummary.infrastructure.notes.notes_read") as mock_read:
            mock_read.return_value = None
            result = load_release_note("abc123")

            assert result is None


class TestReleaseNoteExists:
    """Tests for release_note_exists function."""

    def test_checks_correct_namespace(self) -> None:
        """Test that release note existence is checked in correct namespace."""
        with patch("gitsummary.infrastructure.notes.notes_exists") as mock_exists:
            mock_exists.return_value = True
            release_note_exists("abc123")

            mock_exists.assert_called_once_with("abc123", notes_ref=RELEASE_NOTE_NOTES_REF)

    def test_returns_true_when_exists(self) -> None:
        """Test that True is returned when release note exists."""
        with patch("gitsummary.infrastructure.notes.notes_exists") as mock_exists:
            mock_exists.return_value = True
            result = release_note_exists("abc123")

            assert result is True

    def test_returns_false_when_missing(self) -> None:
        """Test that False is returned when release note doesn't exist."""
        with patch("gitsummary.infrastructure.notes.notes_exists") as mock_exists:
            mock_exists.return_value = False
            result = release_note_exists("abc123")

            assert result is False

