"""Legacy code for backwards compatibility.

This package contains deprecated code that is maintained for
backwards compatibility. New code should not use these modules.

Modules:
    artifact: Legacy build_artifact function
    analyzers: Legacy facet analyzers
"""

from __future__ import annotations

import warnings

from .artifact import ArtifactContext, build_artifact
from .analyzers import available_targets, run as run_analyzer

__all__ = [
    "build_artifact",
    "ArtifactContext",
    "available_targets",
    "run_analyzer",
]


def __getattr__(name: str):
    """Warn when accessing legacy exports."""
    if name in __all__:
        warnings.warn(
            f"gitsummary._legacy.{name} is deprecated. "
            "Use the new API in gitsummary.services instead.",
            DeprecationWarning,
            stacklevel=2,
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

