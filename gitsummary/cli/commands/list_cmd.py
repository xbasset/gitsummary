"""The `list` command for listing commits and their analysis status.

Lists commits in a range and shows which ones have been analyzed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import typer

from ...infrastructure import (
    GitCommandError,
    list_commits_in_range,
    load_artifacts_for_range,
)


def _format_date_absolute(dt: datetime) -> str:
    """Format datetime as YYYY-MM-DD HH:MM."""
    return dt.strftime("%Y-%m-%d %H:%M")


def _format_date_relative(dt: datetime) -> str:
    """Format datetime as short relative time (e.g., '2d', '3mo', '1y')."""
    now = datetime.now(timezone.utc)
    # Make dt timezone-aware if it isn't
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    delta = now - dt
    seconds = delta.total_seconds()
    
    if seconds < 60:
        return "now"
    if seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins}m"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h"
    if seconds < 86400 * 30:
        days = int(seconds / 86400)
        return f"{days}d"
    if seconds < 86400 * 365:
        months = int(seconds / (86400 * 30))
        return f"{months}mo"
    
    years = int(seconds / (86400 * 365))
    return f"{years}y"


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
    absolute_date: bool = typer.Option(
        False, "--date", help="Show absolute dates (YYYY-MM-DD HH:MM) instead of relative."
    ),
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

        # Format date based on --date flag (default is relative)
        if absolute_date:
            date_str = _format_date_absolute(commit.date)
            date_display = date_str  # "YYYY-MM-DD HH:MM" = 16 chars
        else:
            date_str = _format_date_relative(commit.date)
            date_display = f"{date_str:>4}"  # Right-align, max 4 chars

        if output_json:
            results.append(
                {
                    "sha": commit.sha,
                    "short_sha": commit.short_sha,
                    "date": commit.date.isoformat(),
                    "summary": commit.summary,
                    "analyzed": is_analyzed,
                }
            )
        else:
            status = "✓" if is_analyzed else "○"
            # Adjust summary truncation based on date format
            max_summary = 44 if absolute_date else 55
            typer.echo(f"{status} {commit.short_sha} {date_display} {commit.summary[:max_summary]}")

    if output_json:
        typer.echo(json.dumps(results, indent=2))

