"""High-level package metadata for :mod:`gitsummary`."""

from __future__ import annotations

__all__ = ["__version__", "app"]

__version__ = "0.1.0"

from .cli import app  # noqa: E402  (import after __version__ definition)
