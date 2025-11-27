"""The `list` command for listing commits and their analysis status.

Lists commits in a range and shows which ones have been analyzed.
"""

from __future__ import annotations

import json

import typer

from ...infrastructure import (
    GitCommandError,
    list_commits_in_range,
    load_artifacts_for_range,
)


def list_commits(
    revision_range: str = typer.Argument(
        ...,
        help="Revision range to list commits for.",
    ),
    analyzed_only: bool = typer.Option(
        False, "--analyzed", help="Only show commits with artifacts."
    ),
    missing_only: bool = typer.Option(
        False, "--missing", help="Only show commits without artifacts."
    ),
    count_only: bool = typer.Option(False, "--count", help="Show only counts."),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """List commits and their analysis status."""
    try:
        commits = list_commits_in_range(revision_range)
    except GitCommandError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not commits:
        typer.secho("No commits found.", err=True, fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    # Check analysis status for all commits
    shas = [c.sha for c in commits]
    artifacts = load_artifacts_for_range(shas)

    analyzed_count = sum(1 for a in artifacts.values() if a is not None)
    missing_count = len(commits) - analyzed_count

    if count_only:
        if output_json:
            typer.echo(
                json.dumps(
                    {
                        "total": len(commits),
                        "analyzed": analyzed_count,
                        "missing": missing_count,
                    }
                )
            )
        else:
            typer.echo(f"Total: {len(commits)}")
            typer.echo(f"Analyzed: {analyzed_count}")
            typer.echo(f"Missing: {missing_count}")
        return

    if not output_json:
        typer.echo(
            f"Commits in {revision_range} ({len(commits)} total, {analyzed_count} analyzed)"
        )
        typer.echo("")

    results = []
    for commit in commits:
        is_analyzed = artifacts[commit.sha] is not None

        if analyzed_only and not is_analyzed:
            continue
        if missing_only and is_analyzed:
            continue

        if output_json:
            results.append(
                {
                    "sha": commit.sha,
                    "short_sha": commit.short_sha,
                    "summary": commit.summary,
                    "analyzed": is_analyzed,
                }
            )
        else:
            status = "✓" if is_analyzed else "○"
            typer.echo(f"{status} {commit.short_sha} {commit.summary[:60]}")

    if output_json:
        typer.echo(json.dumps(results, indent=2))

