"""The `analyze` command for extracting semantic artifacts.

This is the core command that analyzes commits using heuristics
(and optionally LLM) to extract semantic information about each change.
Results are stored in Git Notes (refs/notes/intent).
"""

from __future__ import annotations

from typing import List

import typer

from ...core import CommitArtifact
from ...infrastructure import (
    GitCommandError,
    artifact_exists_in_notes,
    get_commit_diff,
    list_commits_in_range,
    save_artifact_to_notes,
)
from ...services import build_commit_artifact
from ..formatters import format_artifact_json, format_artifact_yaml


def analyze(
    revision_range: str = typer.Argument(
        ...,
        help="Git revision range (e.g., v1.0..v2.0) or single commit.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print artifacts without storing in Git Notes."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing artifacts."
    ),
    reanalyze: bool = typer.Option(
        False,
        "--reanalyze-existing",
        help="Re-analyze commits with existing artifacts.",
    ),
    output_json: bool = typer.Option(
        False, "--json", help="Output as JSON (implies --dry-run)."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed progress."
    ),
) -> None:
    """Extract semantic understanding from commits and store as artifacts.

    This is the core command that analyzes commits using heuristics (and
    optionally LLM) to extract semantic information about each change.
    Results are stored in Git Notes (refs/notes/intent).
    """
    # --json implies --dry-run
    if output_json:
        dry_run = True

    try:
        commits = list_commits_in_range(revision_range)
    except GitCommandError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not commits:
        typer.secho(
            "No commits found in the specified range.",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    if not dry_run:
        typer.echo(f"Analyzing {len(commits)} commit(s) in {revision_range}...")

    analyzed = 0
    skipped = 0
    errors = 0
    artifacts: List[CommitArtifact] = []

    for commit in commits:
        # Check if already analyzed
        if not reanalyze and not force and artifact_exists_in_notes(commit.sha):
            if not dry_run:
                typer.echo(f"  ⊘ {commit.short_sha} (existing, skipped)")
            skipped += 1
            continue

        try:
            # Get diff data
            diff = get_commit_diff(commit.sha)

            # Build artifact
            artifact = build_commit_artifact(commit, diff, use_llm=True)
            artifacts.append(artifact)

            if dry_run:
                if output_json:
                    typer.echo(format_artifact_json(artifact))
                else:
                    typer.echo(format_artifact_yaml(artifact))
                    typer.echo("---")
            else:
                # Store in Git Notes
                save_artifact_to_notes(artifact, force=force)
                typer.echo(f"  ✓ {commit.short_sha} {commit.summary[:50]}")

            analyzed += 1

        except Exception as exc:
            if verbose:
                typer.secho(
                    f"  ✗ {commit.short_sha} Error: {exc}",
                    err=True,
                    fg=typer.colors.RED,
                )
            else:
                typer.secho(
                    f"  ✗ {commit.short_sha} (error)", err=True, fg=typer.colors.RED
                )
            errors += 1

    if not dry_run:
        typer.echo("")
        typer.echo(f"Summary: {analyzed} analyzed, {skipped} skipped, {errors} errors")
        if analyzed > 0:
            typer.echo("Artifacts stored in refs/notes/intent")

    # Exit codes per CLI spec
    if errors > 0 and analyzed == 0:
        raise typer.Exit(code=1)

