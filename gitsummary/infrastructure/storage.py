"""Artifact storage for CommitArtifacts.

This module provides high-level storage operations for CommitArtifacts,
using Git Notes (default) or Postgres based on configuration. Artifacts
are serialized to YAML for Git Notes; Postgres stores structured columns.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import yaml

from .. import __version__
from ..core import CommitArtifact
from .notes import NOTES_REF, notes_exists, notes_read, notes_write, notes_remove
from ..tracing import trace_manager

SCHEMA_VERSION = "0.2.0"
STORAGE_BACKEND_ENV = "GITSUMMARY_STORAGE_BACKEND"
DEFAULT_STORAGE_BACKEND = "notes"
STORAGE_BACKENDS = {"notes", "postgres"}


def _get_notes_ref() -> str:
    """Get the notes ref from environment or default."""
    return os.environ.get("GITSUMMARY_NOTES_REF", NOTES_REF)


def normalize_storage_backend(backend: Optional[str]) -> str:
    """Normalize storage backend selection."""
    value = backend or os.environ.get(STORAGE_BACKEND_ENV, DEFAULT_STORAGE_BACKEND)
    value = value.lower()
    if value not in STORAGE_BACKENDS:
        raise ValueError(
            f"Unsupported storage backend '{value}'. Use one of: {', '.join(sorted(STORAGE_BACKENDS))}."
        )
    return value


# ─────────────────────────────────────────────────────────────────────────────
# Serialization
# ─────────────────────────────────────────────────────────────────────────────


def artifact_to_yaml(artifact: CommitArtifact) -> str:
    """Serialize a CommitArtifact to YAML for storage in Git Notes.

    Args:
        artifact: The artifact to serialize.

    Returns:
        YAML string with artifact data and metadata.
    """
    # Use mode='json' to get proper enum serialization
    data = artifact.model_dump(mode="json")
    # Add metadata
    data["schema_version"] = SCHEMA_VERSION
    data["tool_version"] = __version__
    return yaml.dump(
        data, default_flow_style=False, allow_unicode=True, sort_keys=False
    )


def yaml_to_artifact(yaml_content: str) -> CommitArtifact:
    """Deserialize a CommitArtifact from YAML stored in Git Notes.

    Args:
        yaml_content: The YAML string to parse.

    Returns:
        The deserialized CommitArtifact.

    Raises:
        ValueError: If the YAML is invalid or missing required fields.
    """
    data = yaml.safe_load(yaml_content)
    # Remove metadata fields before creating artifact
    data.pop("schema_version", None)
    data.pop("tool_version", None)
    return CommitArtifact(**data)


# ─────────────────────────────────────────────────────────────────────────────
# Storage Operations
# ─────────────────────────────────────────────────────────────────────────────


def save_artifact_to_notes(
    artifact: CommitArtifact,
    *,
    notes_ref: Optional[str] = None,
    force: bool = True,
) -> str:
    """Save a CommitArtifact to Git Notes.

    Args:
        artifact: The artifact to save.
        notes_ref: Git Notes namespace (default: refs/notes/intent).
        force: Whether to overwrite existing notes (default: True).

    Returns:
        The commit SHA the note was attached to.

    Raises:
        FileExistsError: If note exists and force=False.
    """
    ref = notes_ref or _get_notes_ref()
    sha = artifact.commit_hash

    if not force and notes_exists(sha, ref):
        raise FileExistsError(f"Artifact already exists for commit {sha[:8]}")

    yaml_content = artifact_to_yaml(artifact)
    notes_write(sha, yaml_content, ref)
    trace_manager.log_output_reference(
        kind="git_note",
        location=f"{ref}:{sha}",
        metadata={"commit_summary": artifact.intent_summary},
    )
    return sha


def save_artifact(
    artifact: CommitArtifact,
    *,
    backend: Optional[str] = None,
    notes_ref: Optional[str] = None,
    force: bool = True,
) -> str:
    """Save a CommitArtifact to the selected backend."""
    selected = normalize_storage_backend(backend)
    if selected == "notes":
        return save_artifact_to_notes(artifact, notes_ref=notes_ref, force=force)
    from .postgres import save_artifact_to_postgres

    return save_artifact_to_postgres(artifact, force=force)


def load_artifact_from_notes(
    commit_sha: str,
    *,
    notes_ref: Optional[str] = None,
) -> Optional[CommitArtifact]:
    """Load a CommitArtifact from Git Notes.

    Args:
        commit_sha: The commit SHA to load artifact for.
        notes_ref: Git Notes namespace (default: refs/notes/intent).

    Returns:
        The CommitArtifact if found, None otherwise.
    """
    ref = notes_ref or _get_notes_ref()
    yaml_content = notes_read(commit_sha, ref)

    if yaml_content is None:
        return None

    return yaml_to_artifact(yaml_content)


def load_artifact(
    commit_sha: str,
    *,
    backend: Optional[str] = None,
    notes_ref: Optional[str] = None,
) -> Optional[CommitArtifact]:
    """Load a CommitArtifact from the selected backend."""
    selected = normalize_storage_backend(backend)
    if selected == "notes":
        return load_artifact_from_notes(commit_sha, notes_ref=notes_ref)
    from .postgres import load_artifact_from_postgres

    return load_artifact_from_postgres(commit_sha)


def artifact_exists_in_notes(
    commit_sha: str,
    *,
    notes_ref: Optional[str] = None,
) -> bool:
    """Check if an artifact exists in Git Notes for the given commit.

    Args:
        commit_sha: The commit SHA to check.
        notes_ref: Git Notes namespace (default: refs/notes/intent).

    Returns:
        True if an artifact exists, False otherwise.
    """
    ref = notes_ref or _get_notes_ref()
    return notes_exists(commit_sha, ref)


def artifact_exists(
    commit_sha: str,
    *,
    backend: Optional[str] = None,
    notes_ref: Optional[str] = None,
) -> bool:
    """Check if an artifact exists in the selected backend."""
    selected = normalize_storage_backend(backend)
    if selected == "notes":
        return artifact_exists_in_notes(commit_sha, notes_ref=notes_ref)
    from .postgres import artifact_exists_in_postgres

    return artifact_exists_in_postgres(commit_sha)


def remove_artifact_from_notes(
    commit_sha: str,
    *,
    notes_ref: Optional[str] = None,
) -> bool:
    """Remove an artifact from Git Notes.

    Args:
        commit_sha: The commit SHA to remove artifact from.
        notes_ref: Git Notes namespace (default: refs/notes/intent).

    Returns:
        True if removed, False if not found.
    """
    ref = notes_ref or _get_notes_ref()
    return notes_remove(commit_sha, ref)


def remove_artifact(
    commit_sha: str,
    *,
    backend: Optional[str] = None,
    notes_ref: Optional[str] = None,
) -> bool:
    """Remove a CommitArtifact from the selected backend."""
    selected = normalize_storage_backend(backend)
    if selected == "notes":
        return remove_artifact_from_notes(commit_sha, notes_ref=notes_ref)
    from .postgres import remove_artifact_from_postgres

    return remove_artifact_from_postgres(commit_sha)


def list_analyzed_commits(
    commit_shas: List[str],
    *,
    notes_ref: Optional[str] = None,
) -> Dict[str, bool]:
    """Check which commits have artifacts in Git Notes.

    Args:
        commit_shas: List of commit SHAs to check.
        notes_ref: Git Notes namespace (default: refs/notes/intent).

    Returns:
        Dict mapping SHA -> bool (True if analyzed).
    """
    ref = notes_ref or _get_notes_ref()
    return {sha: notes_exists(sha, ref) for sha in commit_shas}


def load_artifacts_for_range(
    commit_shas: List[str],
    *,
    backend: Optional[str] = None,
    notes_ref: Optional[str] = None,
) -> Dict[str, Optional[CommitArtifact]]:
    """Load all artifacts for a list of commits.

    Args:
        commit_shas: List of commit SHAs to load.
        backend: Storage backend to use.
        notes_ref: Git Notes namespace (default: refs/notes/intent).

    Returns:
        Dict mapping SHA -> CommitArtifact (or None if not analyzed).
    """
    selected = normalize_storage_backend(backend)
    if selected == "notes":
        ref = notes_ref or _get_notes_ref()
        result: Dict[str, Optional[CommitArtifact]] = {}
        for sha in commit_shas:
            result[sha] = load_artifact_from_notes(sha, notes_ref=ref)
        return result
    from .postgres import load_artifacts_for_range_postgres

    return load_artifacts_for_range_postgres(commit_shas)
