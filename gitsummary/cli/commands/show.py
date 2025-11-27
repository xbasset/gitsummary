"""The `show` command for displaying artifacts.

Displays stored artifacts for commits in various formats.
"""

from __future__ import annotations

from typing import Optional

import typer

from ...infrastructure import (
    GitCommandError,
    list_commits_in_range,
    load_artifact_from_notes,
)
from ..formatters import (
    format_artifact_brief,
    format_artifact_human,
    format_artifact_json,
    format_artifact_yaml,
)


def show(
    revision_range: str = typer.Argument(
        ...,
        help="Commit SHA or revision range to show artifacts for.",
    ),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    output_yaml: bool = typer.Option(False, "--yaml", help="Output as raw YAML."),
    brief: bool = typer.Option(False, "--brief", help="One-line summary per commit."),
    field: Optional[str] = typer.Option(
        None, "--field", help="Show only specific field(s)."
    ),
) -> None:
    """Display artifacts for commits."""
    try:
        commits = list_commits_in_range(revision_range)
    except GitCommandError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not commits:
        typer.secho("No commits found.", err=True, fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    found = 0
    missing = 0

    for commit in commits:
        artifact = load_artifact_from_notes(commit.sha)

        if artifact is None:
            if brief:
                typer.echo(f"{commit.short_sha} [not analyzed]")
            else:
                typer.secho(
                    f"No artifact for commit {commit.short_sha}", fg=typer.colors.YELLOW
                )
            missing += 1
            continue

        found += 1

        if field:
            # Extract specific field
            data = artifact.model_dump()
            if field in data:
                typer.echo(f"{commit.short_sha}: {data[field]}")
            else:
                typer.secho(f"Unknown field: {field}", err=True, fg=typer.colors.RED)
        elif output_json:
            typer.echo(format_artifact_json(artifact))
        elif output_yaml:
            typer.echo(format_artifact_yaml(artifact))
        elif brief:
            typer.echo(format_artifact_brief(artifact))
        else:
            typer.echo(format_artifact_human(artifact, commit))

        if not brief and not output_json and len(commits) > 1:
            typer.echo("")

    if missing > 0 and found == 0:
        raise typer.Exit(code=1)

