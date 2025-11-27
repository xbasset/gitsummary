"""Backwards compatibility shim for analyzers module.

DEPRECATED: Use gitsummary._legacy.analyzers instead.

These analyzers work with the old v0.1 artifact format.
New code should use CommitArtifact directly.
"""

from __future__ import annotations

# Re-export from legacy
from .._legacy.analyzers import available_targets, run

__all__ = ["available_targets", "run"]
