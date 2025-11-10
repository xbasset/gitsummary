"""Typer-based command line interface for gitsummary."""

from __future__ import annotations

from typing import List

import typer

from . import __version__
from .artifact import build_artifact
from .analyzers import available_targets, run as run_analyzer
from .git import (
    GitCommandError,
    check_tags,
    diff_patch,
    diff_stat,
    list_commits,
    repository_root,
    tracked_files,
)
from .storage import StorageLayout, load_artifact, save_artifact

app = typer.Typer(help="Summarise git changes into durable artifacts.")


def _artifact_layout() -> StorageLayout:
    repo_root = repository_root()
    return StorageLayout(repo_root / ".gitsummary")


@app.callback()
def main() -> None:
    """Display version information when ``--version`` is supplied."""


@app.command()
def version() -> None:
    """Print the CLI version."""

    typer.echo(__version__)


@app.command()
def collect(
    tag: List[str] = typer.Option(..., "--tag", min=2, max=2, help="Two git tags describing the range."),
) -> None:
    """Collect git metadata for a tag range and persist an artifact."""

    if len(tag) != 2:
        typer.secho("Please provide exactly two tags via --tag <A> <B>.", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        check_tags(tag)
    except GitCommandError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    start_tag, end_tag = tag
    range_spec = f"{start_tag}..{end_tag}"

    commits = list_commits(range_spec)
    changes = tracked_files(range_spec)
    stats = diff_stat(range_spec)
    diff_text = diff_patch(range_spec)

    artifact = build_artifact(
        commit_range=range_spec,
        commits=commits,
        changes=changes,
        diff_stat=stats,
        diff_text=diff_text,
    )

    layout = _artifact_layout()
    artifact_id, artifact_path = save_artifact(layout, artifact)
    typer.echo(f"Artifact created: {artifact_id}")
    typer.echo(f"Location: {artifact_path}")


@app.command()
def analyze(
    artifact_id: str = typer.Argument(..., help="Artifact identifier or prefix."),
    target: str = typer.Option(..., "--target", help="Facet to analyse."),
) -> None:
    """Render the requested facet for an artifact."""

    layout = _artifact_layout()
    try:
        resolved_id, artifact = load_artifact(layout, artifact_id)
    except (FileNotFoundError, FileExistsError) as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    targets = available_targets()
    if target not in targets:
        valid = ", ".join(sorted(targets))
        typer.secho(f"Unknown target '{target}'. Available: {valid}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)

    output = run_analyzer(target, artifact)
    typer.echo(f"Artifact: {resolved_id}")
    typer.echo(f"Target: {target}")
    typer.echo("")
    typer.echo(output)
