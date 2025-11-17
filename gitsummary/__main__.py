"""Console entry point for ``python -m gitsummary``."""

from __future__ import annotations

from .cli import app


def main() -> None:
    """Invoke the Typer application."""

    app()


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
