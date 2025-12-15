"""Main Typer application definition.

This module creates the main CLI application and wires up
all command modules. It's kept minimal to provide a clear
entry point.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from .. import __version__
from ..infrastructure import GitCommandError, SCHEMA_VERSION, repository_root
from ..tracing import trace_manager

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

# Create init subapp
init_app = typer.Typer(help="Bootstrap gitsummary automation in a repository.")
app.add_typer(init_app, name="init")

# Create CI subapp
ci_app = typer.Typer(help="CI-focused commands (no Git Notes writes).")
app.add_typer(ci_app, name="ci")


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
    repo_root: Path | None = None
    try:
        repo_root = Path(repository_root())
    except GitCommandError:
        repo_root = None

    trace_manager.start_session(
        argv=sys.argv[1:],
        cwd=Path.cwd(),
        repo_root=repo_root,
        tool_version=__version__,
    )
    if repo_root:
        trace_manager.attach_repo_root(repo_root)

    def _finalize() -> None:
        exit_code = getattr(ctx, "exit_code", 0) or 0
        status = "error" if exit_code else "completed"
        trace_manager.finish_session(status=status, exit_code=exit_code)

    ctx.call_on_close(_finalize)

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
from .commands import analyze, ci, generate, init, list_cmd, release_note, show  # noqa: E402, F401

# Register commands
app.command()(analyze.analyze)
app.command("release-note")(release_note.release_note)
app.command("list")(list_cmd.list_commits)

# Register show subcommands
show_app.command("commit")(show.show)  # show commit <sha>
show_app.command("release-note")(show.show_release_note)  # show release-note <revision>

# Register init subcommands
init_app.command("github-release-notes")(init.github_release_notes)

# Register generate subcommands
generate_app.command("changelog")(generate.generate_changelog)
generate_app.command("feed")(generate.generate_feed)
generate_app.command("release-notes")(generate.generate_release_notes)
generate_app.command("impact")(generate.generate_impact)

# Register CI subcommands
ci_app.command("release-notes")(ci.release_notes)
