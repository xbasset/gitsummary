"""Git Notes operations for storing semantic artifacts.

Git Notes provide a way to attach additional data to commits
without modifying them. This module handles all notes operations
for the gitsummary artifact storage.
"""

from __future__ import annotations

from typing import Optional

from .git import GitCommandError, run

# Default notes namespace for gitsummary artifacts
NOTES_REF = "refs/notes/intent"


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

