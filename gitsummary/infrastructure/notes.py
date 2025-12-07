"""Git Notes operations for storing semantic artifacts.

Git Notes provide a way to attach additional data to commits
without modifying them. This module handles all notes operations
for the gitsummary artifact storage.

Namespaces:
    refs/notes/intent         - Per-commit semantic artifacts (CommitArtifact)
    refs/notes/report/release-note - Release note reports (ReleaseNote)
"""

from __future__ import annotations

from typing import Optional

from .git import GitCommandError, run
from ..tracing import trace_manager

# Default notes namespace for gitsummary artifacts
NOTES_REF = "refs/notes/intent"

# Notes namespace for release note reports
RELEASE_NOTE_NOTES_REF = "refs/notes/report/release-note"


def notes_exists(sha: str, notes_ref: str = NOTES_REF) -> bool:
    """Check if a note exists for the given commit.

    Args:
        sha: The commit SHA to check.
        notes_ref: The notes namespace (default: refs/notes/intent).

    Returns:
        True if a note exists, False otherwise.
    """
    try:
        run(["notes", f"--ref={notes_ref}", "show", sha])
        return True
    except GitCommandError:
        return False


def notes_read(sha: str, notes_ref: str = NOTES_REF) -> Optional[str]:
    """Read the note content for a commit.

    Args:
        sha: The commit SHA to read notes for.
        notes_ref: The notes namespace (default: refs/notes/intent).

    Returns:
        The note content as a string, or None if no note exists.
    """
    try:
        return run(["notes", f"--ref={notes_ref}", "show", sha])
    except GitCommandError:
        return None


def notes_write(sha: str, content: str, notes_ref: str = NOTES_REF) -> None:
    """Write or overwrite a note for a commit.

    Args:
        sha: The commit SHA to attach the note to.
        content: The note content to write.
        notes_ref: The notes namespace (default: refs/notes/intent).
    """
    # Use -f to force overwrite existing notes
    run(["notes", f"--ref={notes_ref}", "add", "-f", "-m", content, sha])


def notes_remove(sha: str, notes_ref: str = NOTES_REF) -> bool:
    """Remove a note for a commit.

    Args:
        sha: The commit SHA to remove the note from.
        notes_ref: The notes namespace (default: refs/notes/intent).

    Returns:
        True if a note was removed, False if no note existed.
    """
    try:
        run(["notes", f"--ref={notes_ref}", "remove", sha])
        return True
    except GitCommandError:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Release Note Storage
# ─────────────────────────────────────────────────────────────────────────────


def save_release_note(sha: str, content: str) -> None:
    """Save a release note to Git Notes.

    The release note is attached to the tip commit of the release range.

    Args:
        sha: The tip commit SHA to attach the release note to.
        content: The release note content (YAML format).
    """
    notes_write(sha, content, notes_ref=RELEASE_NOTE_NOTES_REF)
    trace_manager.log_output_reference(
        kind="git_note_release_note",
        location=f"{RELEASE_NOTE_NOTES_REF}:{sha}",
    )


def load_release_note(sha: str) -> Optional[str]:
    """Load a release note from Git Notes.

    Args:
        sha: The commit SHA to load the release note from.

    Returns:
        The release note content (YAML), or None if not found.
    """
    return notes_read(sha, notes_ref=RELEASE_NOTE_NOTES_REF)


def release_note_exists(sha: str) -> bool:
    """Check if a release note exists for a commit.

    Args:
        sha: The commit SHA to check.

    Returns:
        True if a release note exists.
    """
    return notes_exists(sha, notes_ref=RELEASE_NOTE_NOTES_REF)
