"""Backwards compatibility shim for cli module.

DEPRECATED: Import from gitsummary.cli instead.

Example:
    # Old way (deprecated)
    from gitsummary.cli import app
    
    # New way (recommended)
    from gitsummary.cli import app
    # or
    from gitsummary import app
"""

from __future__ import annotations

# Re-export from new CLI package
from .cli import app

__all__ = ["app"]
