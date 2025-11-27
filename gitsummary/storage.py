"""Backwards compatibility shim for storage module.

DEPRECATED: Import from gitsummary.infrastructure instead.

Example:
    # Old way (deprecated)
    from gitsummary.storage import save_artifact_to_notes, load_artifact_from_notes
    
    # New way (recommended)
    from gitsummary.infrastructure import save_artifact_to_notes, load_artifact_from_notes
"""

from __future__ import annotations

# Re-export from infrastructure
from .infrastructure import (
    SCHEMA_VERSION,
    artifact_exists_in_notes,
    artifact_to_yaml,
    load_artifact_from_notes,
    load_artifacts_for_range,
    remove_artifact_from_notes,
    save_artifact_to_notes,
    yaml_to_artifact,
)

# Re-export notes ref
from .infrastructure.notes import NOTES_REF

# Re-export legacy storage
from ._legacy.storage import StorageLayout, load_artifact, save_artifact

__all__ = [
    "SCHEMA_VERSION",
    "NOTES_REF",
    # Git Notes storage
    "save_artifact_to_notes",
    "load_artifact_from_notes",
    "artifact_exists_in_notes",
    "remove_artifact_from_notes",
    "load_artifacts_for_range",
    "artifact_to_yaml",
    "yaml_to_artifact",
    # Legacy file storage
    "StorageLayout",
    "save_artifact",
    "load_artifact",
]
