"""Command-line interface for gitsummary.

This package contains the Typer-based CLI implementation,
organized into separate modules for each command group.

The CLI implements a two-phase model:
- Phase 1: `analyze` - Extract semantic understanding, store in Git Notes
- Phase 2: `generate` - Produce reports from stored artifacts

Modules:
    app: Main Typer application definition
    formatters: Output formatting functions
    commands/: Individual command implementations
"""

from __future__ import annotations

from .app import app

__all__ = ["app"]

