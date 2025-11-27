"""Backwards compatibility shim for schema module.

DEPRECATED: Import from gitsummary.core instead.

Example:
    # Old way (deprecated)
    from gitsummary.schema import CommitArtifact, ChangeCategory, ImpactScope
    
    # New way (recommended)  
    from gitsummary.core import CommitArtifact, ChangeCategory, ImpactScope
"""

from __future__ import annotations

# Re-export from new location for backwards compatibility
from .core import ChangeCategory, CommitArtifact, ImpactScope

__all__ = ["CommitArtifact", "ChangeCategory", "ImpactScope"]
