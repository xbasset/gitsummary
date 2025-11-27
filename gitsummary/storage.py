"""Artifact storage utilities for gitsummary.

This module provides two storage backends:
1. Git Notes storage (primary) - stores artifacts in refs/notes/intent
2. File-based storage (legacy) - stores artifacts in .gitsummary/ directory

The Git Notes backend is the preferred storage mechanism as it:
- Travels with the repository via git push/fetch
- Is garbage-collection safe
- Doesn't pollute the working tree
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

import yaml

from . import __version__
from .git import NOTES_REF, notes_exists, notes_read, notes_remove, notes_write
from .schema import CommitArtifact

SCHEMA_VERSION = "0.1.0"

__all__ = [
    "SCHEMA_VERSION",
    "NOTES_REF",
    # Git Notes storage
    "save_artifact_to_notes",
    "load_artifact_from_notes",
    "artifact_exists_in_notes",
    "remove_artifact_from_notes",
    "list_analyzed_commits",
    # File-based storage (legacy)
    "StorageLayout",
    "save_artifact",
    "load_artifact",
]


# ─────────────────────────────────────────────────────────────────────────────
# Git Notes Storage (Primary)
# ─────────────────────────────────────────────────────────────────────────────


def _get_notes_ref() -> str:
    """Get the notes ref from environment or default."""
    return os.environ.get("GITSUMMARY_NOTES_REF", NOTES_REF)


def artifact_to_yaml(artifact: CommitArtifact) -> str:
    """Serialize a CommitArtifact to YAML for storage in Git Notes."""
    # Use mode='json' to get proper enum serialization
    data = artifact.model_dump(mode="json")
    # Add metadata
    data["schema_version"] = SCHEMA_VERSION
    data["tool_version"] = __version__
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


def yaml_to_artifact(yaml_content: str) -> CommitArtifact:
    """Deserialize a CommitArtifact from YAML stored in Git Notes."""
    data = yaml.safe_load(yaml_content)
    # Remove metadata fields before creating artifact
    data.pop("schema_version", None)
    data.pop("tool_version", None)
    return CommitArtifact(**data)


def save_artifact_to_notes(
    artifact: CommitArtifact,
    *,
    notes_ref: Optional[str] = None,
    force: bool = True,
) -> str:
    """Save a CommitArtifact to Git Notes.

    Args:
        artifact: The artifact to save
        notes_ref: Git Notes namespace (default: refs/notes/intent)
        force: Whether to overwrite existing notes (default: True)

    Returns:
        The commit SHA the note was attached to

    Raises:
        FileExistsError: If note exists and force=False
    """
    ref = notes_ref or _get_notes_ref()
    sha = artifact.commit_hash

    if not force and notes_exists(sha, ref):
        raise FileExistsError(f"Artifact already exists for commit {sha[:8]}")

    yaml_content = artifact_to_yaml(artifact)
    notes_write(sha, yaml_content, ref)
    return sha


def load_artifact_from_notes(
    commit_sha: str,
    *,
    notes_ref: Optional[str] = None,
) -> Optional[CommitArtifact]:
    """Load a CommitArtifact from Git Notes.

    Args:
        commit_sha: The commit SHA to load artifact for
        notes_ref: Git Notes namespace (default: refs/notes/intent)

    Returns:
        The CommitArtifact if found, None otherwise
    """
    ref = notes_ref or _get_notes_ref()
    yaml_content = notes_read(commit_sha, ref)

    if yaml_content is None:
        return None

    return yaml_to_artifact(yaml_content)


def artifact_exists_in_notes(
    commit_sha: str,
    *,
    notes_ref: Optional[str] = None,
) -> bool:
    """Check if an artifact exists in Git Notes for the given commit."""
    ref = notes_ref or _get_notes_ref()
    return notes_exists(commit_sha, ref)


def remove_artifact_from_notes(
    commit_sha: str,
    *,
    notes_ref: Optional[str] = None,
) -> bool:
    """Remove an artifact from Git Notes.

    Returns:
        True if removed, False if not found
    """
    ref = notes_ref or _get_notes_ref()
    return notes_remove(commit_sha, ref)


def list_analyzed_commits(
    commit_shas: List[str],
    *,
    notes_ref: Optional[str] = None,
) -> Dict[str, bool]:
    """Check which commits have artifacts in Git Notes.

    Args:
        commit_shas: List of commit SHAs to check
        notes_ref: Git Notes namespace (default: refs/notes/intent)

    Returns:
        Dict mapping SHA -> bool (True if analyzed)
    """
    ref = notes_ref or _get_notes_ref()
    return {sha: notes_exists(sha, ref) for sha in commit_shas}


def load_artifacts_for_range(
    commit_shas: List[str],
    *,
    notes_ref: Optional[str] = None,
) -> Dict[str, Optional[CommitArtifact]]:
    """Load all artifacts for a list of commits.

    Args:
        commit_shas: List of commit SHAs to load
        notes_ref: Git Notes namespace (default: refs/notes/intent)

    Returns:
        Dict mapping SHA -> CommitArtifact (or None if not analyzed)
    """
    ref = notes_ref or _get_notes_ref()
    result: Dict[str, Optional[CommitArtifact]] = {}
    for sha in commit_shas:
        result[sha] = load_artifact_from_notes(sha, notes_ref=ref)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# File-based Storage (Legacy)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StorageLayout:
    """Filesystem layout used for persisting artifacts (LEGACY).

    This class supports the original file-based storage mechanism.
    New code should prefer Git Notes storage via save_artifact_to_notes().
    """

    root: Path

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def manifests(self) -> Path:
        return self.root / "manifests" / "by-range"

    @property
    def schema_dir(self) -> Path:
        return self.root / "schema"

    def ensure(self) -> None:
        """Create the directory layout if necessary."""

        for path in (self.artifacts, self.manifests, self.schema_dir):
            path.mkdir(parents=True, exist_ok=True)
        version_file = self.schema_dir / "version"
        if not version_file.exists():
            version_file.write_text(SCHEMA_VERSION + "\n", encoding="utf-8")

    def artifact_path(self, artifact_id: str) -> Path:
        return self.artifacts / f"{artifact_id}.json"


def _artifact_digest(data: Mapping[str, object]) -> str:
    packed = json.dumps(data, sort_keys=True, indent=2).encode("utf-8")
    return hashlib.sha256(packed).hexdigest()


def save_artifact(
    layout: StorageLayout, artifact: Mapping[str, object]
) -> Tuple[str, Path]:
    """Persist ``artifact`` and return its identifier and file path (LEGACY).

    DEPRECATED: Use save_artifact_to_notes() for new code.
    """

    enriched: Dict[str, object] = dict(artifact)
    enriched.setdefault("meta", {})
    meta = dict(enriched["meta"])  # type: ignore[arg-type]
    meta.setdefault("schema_version", SCHEMA_VERSION)
    meta.setdefault("tool_version", __version__)
    enriched["meta"] = meta

    artifact_id = _artifact_digest(enriched)
    layout.ensure()
    artifact_path = layout.artifact_path(artifact_id)
    artifact_path.write_text(
        json.dumps(enriched, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return artifact_id, artifact_path


def load_artifact(
    layout: StorageLayout, prefix: str
) -> Tuple[str, Mapping[str, object]]:
    """Load an artifact by ``prefix`` (similar to git abbreviated SHAs) (LEGACY).

    DEPRECATED: Use load_artifact_from_notes() for new code.
    """

    layout.ensure()
    matches: Dict[str, Path] = {}
    for path in layout.artifacts.glob("*.json"):
        artifact_id = path.stem
        if artifact_id.startswith(prefix):
            matches[artifact_id] = path
    if not matches:
        raise FileNotFoundError(f"No artifact matching prefix '{prefix}'")
    if len(matches) > 1:
        raise FileExistsError(
            "Multiple artifacts match prefix '{prefix}'. Please provide a longer identifier.".format(
                prefix=prefix
            )
        )
    artifact_id, artifact_path = matches.popitem()
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    return artifact_id, data
