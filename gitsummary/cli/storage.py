"""Shared CLI options for storage backends."""

from __future__ import annotations

import os
import typer

from ..infrastructure import (
    DEFAULT_STORAGE_BACKEND,
    STORAGE_BACKEND_ENV,
    STORAGE_BACKENDS,
    normalize_storage_backend,
)

POSTGRES_DSN_ENV = "GITSUMMARY_POSTGRES_DSN"


def _validate_storage_backend(value: str) -> str:
    try:
        normalized = normalize_storage_backend(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if normalized == "postgres" and not os.environ.get(POSTGRES_DSN_ENV):
        raise typer.BadParameter(
            f"{POSTGRES_DSN_ENV} must be set when using --storage postgres."
        )
    return normalized


def storage_option() -> typer.Option:
    choices = ", ".join(sorted(STORAGE_BACKENDS))
    return typer.Option(
        DEFAULT_STORAGE_BACKEND,
        "--storage",
        "-s",
        envvar=STORAGE_BACKEND_ENV,
        callback=_validate_storage_backend,
        help=f"Artifact storage backend: {choices}.",
        show_default=True,
    )
