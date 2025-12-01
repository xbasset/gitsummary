"""Main Typer application definition.

This module creates the main CLI application and wires up
all command modules. It's kept minimal to provide a clear
entry point.
"""

from __future__ import annotations

import typer

from .. import __version__
from ..infrastructure import SCHEMA_VERSION

# Create main app
app = typer.Typer(
    help="Summarize git changes into durable semantic artifacts.",
    no_args_is_help=True,
)

# Create generate subapp
generate_app = typer.Typer(help="Generate reports from analyzed artifacts.")
app.add_typer(generate_app, name="generate")

# Create show subapp
show_app = typer.Typer(help="Display stored artifacts and reports.")
app.add_typer(show_app, name="show")


# ─────────────────────────────────────────────────────────────────────────────
# Root Commands
# ─────────────────────────────────────────────────────────────────────────────


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit."
    ),
) -> None:
    """Summarize git changes into durable semantic artifacts."""
    if version:
        typer.echo(f"gitsummary {__version__}")
        typer.echo(f"Schema version: {SCHEMA_VERSION}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def version() -> None:
    """Print version information."""
    typer.echo(f"gitsummary {__version__}")
    typer.echo(f"Schema version: {SCHEMA_VERSION}")


# ─────────────────────────────────────────────────────────────────────────────
# Import and register commands
# ─────────────────────────────────────────────────────────────────────────────

# Import commands after app is created to avoid circular imports
from .commands import analyze, generate, list_cmd, show  # noqa: E402, F401

# Register commands
app.command()(analyze.analyze)
app.command("list")(list_cmd.list_commits)

# Register show subcommands
show_app.command("commit")(show.show)  # show commit <sha>
show_app.command("release-note")(show.show_release_note)  # show release-note <revision>

# Register generate subcommands
generate_app.command("changelog")(generate.generate_changelog)
generate_app.command("release-notes")(generate.generate_release_notes)
generate_app.command("impact")(generate.generate_impact)

