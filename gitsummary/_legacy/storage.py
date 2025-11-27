"""Legacy file-based storage for artifacts.

DEPRECATED: Use Git Notes storage via gitsummary.infrastructure.storage.

This module provides the original file-based storage mechanism that
stores artifacts in the .gitsummary/ directory.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Tuple

from .. import __version__

SCHEMA_VERSION = "0.1.0"


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
            f"Multiple artifacts match prefix '{prefix}'. "
            "Please provide a longer identifier."
        )
    artifact_id, artifact_path = matches.popitem()
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    return artifact_id, data

