"""
Storage backend for artifacts.

Manages persistence of artifacts and metadata in the .gitsummary directory.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArtifactStorage:
    """
    Storage backend for gitsummary artifacts.

    Implements the POC filesystem-based storage with a layout that
    mirrors the future Git-native implementation.
    """

    SCHEMA_VERSION = "0.1.0"
    STORAGE_DIR = ".gitsummary"

    def __init__(self, repo_root: Path) -> None:
        """
        Initialize artifact storage.

        Args:
            repo_root: Root directory of the Git repository.
        """
        self.repo_root = repo_root
        self.storage_root = repo_root / self.STORAGE_DIR

        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Create the storage directory structure if it doesn't exist."""
        # Create main directories
        (self.storage_root / "artifacts").mkdir(parents=True, exist_ok=True)
        (self.storage_root / "manifests" / "by-range").mkdir(
            parents=True, exist_ok=True
        )
        (self.storage_root / "index").mkdir(parents=True, exist_ok=True)
        (self.storage_root / "schema").mkdir(parents=True, exist_ok=True)
        (self.storage_root / "notes" / "summary").mkdir(parents=True, exist_ok=True)

        # Write schema version
        version_file = self.storage_root / "schema" / "version"
        if not version_file.exists():
            version_file.write_text(self.SCHEMA_VERSION)

    def _compute_artifact_id(self, artifact: Dict[str, Any]) -> str:
        """
        Compute the artifact ID (SHA-256 hash of JSON content).

        Args:
            artifact: The artifact dictionary.

        Returns:
            Hexadecimal SHA-256 hash.
        """
        # Serialize to JSON (natural dumps, not canonical in POC)
        json_bytes = json.dumps(artifact, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()

    def save_artifact(
        self, artifact: Dict[str, Any], tag_a: str, tag_b: str
    ) -> str:
        """
        Save an artifact to storage.

        Args:
            artifact: The artifact dictionary to save.
            tag_a: Starting tag name.
            tag_b: Ending tag name.

        Returns:
            The artifact ID (OID).
        """
        # Compute artifact ID
        artifact_id = self._compute_artifact_id(artifact)

        # Save artifact file
        artifact_file = self.storage_root / "artifacts" / f"{artifact_id}.json"
        with open(artifact_file, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2, ensure_ascii=False)

        # Create range manifest
        range_key = f"{tag_a}..{tag_b}"
        manifest = {"artifact_id": artifact_id, "created_at": datetime.now().isoformat()}
        manifest_file = (
            self.storage_root / "manifests" / "by-range" / f"{range_key}.json"
        )
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # Update latest index
        latest_file = self.storage_root / "index" / "latest.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return artifact_id

    def load_artifact(self, artifact_id_prefix: str) -> Optional[Dict[str, Any]]:
        """
        Load an artifact by ID or ID prefix.

        Args:
            artifact_id_prefix: Full artifact ID or prefix (like Git).

        Returns:
            The artifact dictionary or None if not found.

        Raises:
            ValueError: If the prefix is ambiguous.
        """
        artifacts_dir = self.storage_root / "artifacts"
        if not artifacts_dir.exists():
            return None

        # Find matching artifacts
        matches = []
        for artifact_file in artifacts_dir.glob("*.json"):
            artifact_id = artifact_file.stem
            if artifact_id.startswith(artifact_id_prefix):
                matches.append(artifact_file)

        if not matches:
            return None

        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous artifact ID prefix '{artifact_id_prefix}': "
                f"matches {len(matches)} artifacts"
            )

        # Load and return the artifact
        with open(matches[0], "r", encoding="utf-8") as f:
            return json.load(f)

    def get_artifact_by_range(
        self, tag_a: str, tag_b: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load an artifact by tag range.

        Args:
            tag_a: Starting tag.
            tag_b: Ending tag.

        Returns:
            The artifact dictionary or None if not found.
        """
        range_key = f"{tag_a}..{tag_b}"
        manifest_file = (
            self.storage_root / "manifests" / "by-range" / f"{range_key}.json"
        )

        if not manifest_file.exists():
            return None

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        artifact_id = manifest.get("artifact_id")
        if not artifact_id:
            return None

        return self.load_artifact(artifact_id)

    def list_artifacts(self) -> List[Dict[str, str]]:
        """
        List all stored artifacts.

        Returns:
            List of dicts with artifact_id and creation timestamp.
        """
        artifacts_dir = self.storage_root / "artifacts"
        if not artifacts_dir.exists():
            return []

        results = []
        for artifact_file in sorted(artifacts_dir.glob("*.json")):
            artifact_id = artifact_file.stem
            stat = artifact_file.stat()
            results.append(
                {
                    "artifact_id": artifact_id,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        return results
