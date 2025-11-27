"""Typer-based command line interface for gitsummary.

This CLI implements the two-phase model:
- Phase 1: `analyze` - Extract semantic understanding, store in Git Notes
- Phase 2: `generate` - Produce reports from stored artifacts
"""

from __future__ import annotations

from typing import List, Optional

import typer
import yaml

from . import __version__
from .artifact import build_commit_artifact
from .git import (
    CommitInfo,
    GitCommandError,
    get_commit_diff,
    list_commits_in_range,
)
from .schema import CommitArtifact
from .storage import (
    SCHEMA_VERSION,
    artifact_exists_in_notes,
    load_artifact_from_notes,
    load_artifacts_for_range,
    save_artifact_to_notes,
)

app = typer.Typer(
    help="Summarize git changes into durable semantic artifacts.",
    no_args_is_help=True,
)

# Subapp for generate command
generate_app = typer.Typer(help="Generate reports from analyzed artifacts.")
app.add_typer(generate_app, name="generate")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _format_artifact_human(
    artifact: CommitArtifact, commit: Optional[CommitInfo] = None
) -> str:
    """Format a CommitArtifact for human-readable display."""
    short_sha = artifact.commit_hash[:7]
    lines = [
        f"╭─ {short_sha} {'─' * (50 - len(short_sha))}╮",
        f"│ {artifact.intent_summary[:50]:<50} │",
        "├" + "─" * 52 + "┤",
        f"│ Category:   {artifact.category.value:<38} │",
        f"│ Impact:     {artifact.impact_scope.value:<38} │",
        f"│ Breaking:   {'Yes' if artifact.is_breaking else 'No':<38} │",
    ]

    if artifact.behavior_before or artifact.behavior_after:
        lines.append("│" + " " * 52 + "│")
        if artifact.behavior_before:
            before_text = (
                artifact.behavior_before[:45] + "..."
                if len(artifact.behavior_before) > 45
                else artifact.behavior_before
            )
            lines.append(f"│ Before: {before_text:<43} │")
        if artifact.behavior_after:
            after_text = (
                artifact.behavior_after[:45] + "..."
                if len(artifact.behavior_after) > 45
                else artifact.behavior_after
            )
            lines.append(f"│ After:  {after_text:<43} │")

    if artifact.technical_highlights:
        lines.append("│" + " " * 52 + "│")
        lines.append("│ Technical:" + " " * 41 + "│")
        for highlight in artifact.technical_highlights[:3]:
            hl_text = highlight[:46] + "..." if len(highlight) > 46 else highlight
            lines.append(f"│   • {hl_text:<46} │")

    lines.append("╰" + "─" * 52 + "╯")
    return "\n".join(lines)


def _format_artifact_brief(artifact: CommitArtifact) -> str:
    """Format a CommitArtifact as a one-line summary."""
    short_sha = artifact.commit_hash[:7]
    category = f"[{artifact.category.value}]"
    return f"{short_sha} {category:<12} {artifact.intent_summary[:60]}"


def _format_artifact_yaml(artifact: CommitArtifact) -> str:
    """Format a CommitArtifact as YAML."""
    # Use mode='json' to get proper enum serialization
    data = artifact.model_dump(mode="json")
    return yaml.dump(
        data, default_flow_style=False, allow_unicode=True, sort_keys=False
    )


def _format_artifact_json(artifact: CommitArtifact) -> str:
    """Format a CommitArtifact as JSON."""
    return artifact.model_dump_json(indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Commands
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


@app.command()
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
            "No commits found in the specified range.", err=True, fg=typer.colors.YELLOW
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
                    typer.echo(_format_artifact_json(artifact))
                else:
                    typer.echo(_format_artifact_yaml(artifact))
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


@app.command()
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
            typer.echo(_format_artifact_json(artifact))
        elif output_yaml:
            typer.echo(_format_artifact_yaml(artifact))
        elif brief:
            typer.echo(_format_artifact_brief(artifact))
        else:
            typer.echo(_format_artifact_human(artifact, commit))

        if not brief and not output_json and len(commits) > 1:
            typer.echo("")

    if missing > 0 and found == 0:
        raise typer.Exit(code=1)


@app.command("list")
def list_cmd(
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
            import json

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
        import json

        typer.echo(json.dumps(results, indent=2))


# ─────────────────────────────────────────────────────────────────────────────
# Generate Subcommands
# ─────────────────────────────────────────────────────────────────────────────


@generate_app.command("changelog")
def generate_changelog(
    revision_range: str = typer.Argument(
        ...,
        help="Revision range to generate changelog for.",
    ),
    output_format: str = typer.Option(
        "markdown", "--format", "-f", help="Output format: markdown, json, text."
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write to file instead of stdout."
    ),
    include_unanalyzed: bool = typer.Option(
        False, "--include-unanalyzed", help="Include commits without artifacts."
    ),
) -> None:
    """Generate changelog from analyzed artifacts."""
    try:
        commits = list_commits_in_range(revision_range)
    except GitCommandError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not commits:
        typer.secho("No commits found.", err=True, fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    # Load all artifacts
    shas = [c.sha for c in commits]
    artifacts = load_artifacts_for_range(shas)

    # Group by category
    from collections import defaultdict
    from .schema import ChangeCategory

    by_category: dict = defaultdict(list)
    unanalyzed = []

    for commit in commits:
        artifact = artifacts[commit.sha]
        if artifact is None:
            if include_unanalyzed:
                unanalyzed.append(commit)
            continue
        by_category[artifact.category].append((commit, artifact))

    # Generate output
    if output_format == "json":
        import json

        result = {
            "range": revision_range,
            "features": [
                {
                    "sha": c.short_sha,
                    "summary": a.intent_summary,
                    "breaking": a.is_breaking,
                }
                for c, a in by_category.get(ChangeCategory.FEATURE, [])
            ],
            "fixes": [
                {"sha": c.short_sha, "summary": a.intent_summary}
                for c, a in by_category.get(ChangeCategory.FIX, [])
            ],
            "other": [
                {
                    "sha": c.short_sha,
                    "summary": a.intent_summary,
                    "category": a.category.value,
                }
                for cat in [
                    ChangeCategory.REFACTOR,
                    ChangeCategory.CHORE,
                    ChangeCategory.PERFORMANCE,
                    ChangeCategory.SECURITY,
                ]
                for c, a in by_category.get(cat, [])
            ],
        }
        output = json.dumps(result, indent=2)
    else:
        # Markdown format
        lines = [f"# Changelog {revision_range}", ""]

        # Features
        features = by_category.get(ChangeCategory.FEATURE, [])
        if features:
            lines.append("## Features")
            for commit, artifact in features:
                breaking = " **[BREAKING]**" if artifact.is_breaking else ""
                lines.append(
                    f"- **{artifact.intent_summary}** ({commit.short_sha}){breaking}"
                )
                if artifact.behavior_after:
                    lines.append(f"  {artifact.behavior_after}")
            lines.append("")

        # Fixes
        fixes = by_category.get(ChangeCategory.FIX, [])
        if fixes:
            lines.append("## Fixes")
            for commit, artifact in fixes:
                lines.append(f"- **{artifact.intent_summary}** ({commit.short_sha})")
            lines.append("")

        # Security
        security = by_category.get(ChangeCategory.SECURITY, [])
        if security:
            lines.append("## Security")
            for commit, artifact in security:
                lines.append(f"- **{artifact.intent_summary}** ({commit.short_sha})")
            lines.append("")

        # Breaking Changes
        breaking = [
            (c, a) for items in by_category.values() for c, a in items if a.is_breaking
        ]
        if breaking:
            lines.append("## Breaking Changes")
            for commit, artifact in breaking:
                lines.append(f"- **{artifact.intent_summary}** ({commit.short_sha})")
                if artifact.behavior_before and artifact.behavior_after:
                    lines.append(f"  - Before: {artifact.behavior_before}")
                    lines.append(f"  - After: {artifact.behavior_after}")
            lines.append("")

        # Other
        other_categories = [
            ChangeCategory.REFACTOR,
            ChangeCategory.PERFORMANCE,
            ChangeCategory.CHORE,
        ]
        other = [
            (c, a) for cat in other_categories for c, a in by_category.get(cat, [])
        ]
        if other:
            lines.append("## Other")
            for commit, artifact in other:
                lines.append(f"- {artifact.intent_summary} ({commit.short_sha})")
            lines.append("")

        # Unanalyzed
        if unanalyzed:
            lines.append("## Unanalyzed")
            for commit in unanalyzed:
                lines.append(f"- {commit.summary} ({commit.short_sha})")
            lines.append("")

        output = "\n".join(lines)

    # Output
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        typer.echo(f"Changelog written to {output_file}")
    else:
        typer.echo(output)


@generate_app.command("release-notes")
def generate_release_notes(
    revision_range: str = typer.Argument(
        ...,
        help="Revision range to generate release notes for.",
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write to file instead of stdout."
    ),
) -> None:
    """Generate user-facing release notes from analyzed artifacts."""
    try:
        commits = list_commits_in_range(revision_range)
    except GitCommandError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not commits:
        typer.secho("No commits found.", err=True, fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    # Load all artifacts
    shas = [c.sha for c in commits]
    artifacts = load_artifacts_for_range(shas)

    # Filter to user-facing changes
    from .schema import ChangeCategory, ImpactScope

    user_facing = []
    internal = []

    for commit in commits:
        artifact = artifacts[commit.sha]
        if artifact is None:
            continue

        # Determine if user-facing
        if artifact.impact_scope in (ImpactScope.PUBLIC_API, ImpactScope.CONFIG):
            user_facing.append((commit, artifact))
        elif artifact.category in (
            ChangeCategory.FEATURE,
            ChangeCategory.FIX,
            ChangeCategory.SECURITY,
        ):
            if artifact.impact_scope != ImpactScope.TEST:
                user_facing.append((commit, artifact))
        else:
            internal.append((commit, artifact))

    # Generate release notes
    lines = [f"# Release Notes: {revision_range}", ""]

    if user_facing:
        lines.append("## What's New")
        lines.append("")

        for commit, artifact in user_facing:
            category_emoji = {
                ChangeCategory.FEATURE: "✨",
                ChangeCategory.FIX: "🐛",
                ChangeCategory.SECURITY: "🔒",
                ChangeCategory.PERFORMANCE: "⚡",
            }.get(artifact.category, "📝")

            lines.append(f"### {category_emoji} {artifact.intent_summary}")
            if artifact.behavior_after:
                lines.append("")
                lines.append(artifact.behavior_after)
            if artifact.is_breaking:
                lines.append("")
                lines.append(
                    f"⚠️ **Breaking Change**: {artifact.behavior_before or 'See migration guide.'}"
                )
            lines.append("")

    # Summary stats
    analyzed_count = sum(1 for a in artifacts.values() if a is not None)
    lines.append("---")
    lines.append(f"*{len(commits)} commits, {analyzed_count} analyzed*")

    output = "\n".join(lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        typer.echo(f"Release notes written to {output_file}")
    else:
        typer.echo(output)


@generate_app.command("impact")
def generate_impact(
    revision_range: str = typer.Argument(
        ...,
        help="Revision range to generate impact report for.",
    ),
    output_format: str = typer.Option(
        "markdown", "--format", "-f", help="Output format: markdown, json."
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write to file instead of stdout."
    ),
) -> None:
    """Generate technical impact analysis for reviewers."""
    try:
        commits = list_commits_in_range(revision_range)
    except GitCommandError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not commits:
        typer.secho("No commits found.", err=True, fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    # Load all artifacts
    shas = [c.sha for c in commits]
    artifacts = load_artifacts_for_range(shas)

    from collections import Counter
    from .schema import ImpactScope

    # Aggregate statistics
    scope_counts = Counter()
    breaking_count = 0
    all_highlights = []

    for sha, artifact in artifacts.items():
        if artifact is None:
            continue
        scope_counts[artifact.impact_scope.value] += 1
        if artifact.is_breaking:
            breaking_count += 1
        all_highlights.extend(artifact.technical_highlights)

    if output_format == "json":
        import json

        result = {
            "range": revision_range,
            "total_commits": len(commits),
            "analyzed": sum(1 for a in artifacts.values() if a is not None),
            "impact_distribution": dict(scope_counts),
            "breaking_changes": breaking_count,
            "technical_highlights": all_highlights[:20],
        }
        output = json.dumps(result, indent=2)
    else:
        lines = [
            f"# Impact Analysis: {revision_range}",
            "",
            "## Summary",
            f"- **Total commits:** {len(commits)}",
            f"- **Analyzed:** {sum(1 for a in artifacts.values() if a is not None)}",
            f"- **Breaking changes:** {breaking_count}",
            "",
            "## Impact Distribution",
        ]

        for scope, count in scope_counts.most_common():
            lines.append(f"- {scope}: {count}")

        if all_highlights:
            lines.append("")
            lines.append("## Technical Highlights")
            for hl in all_highlights[:10]:
                lines.append(f"- {hl}")

        output = "\n".join(lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        typer.echo(f"Impact report written to {output_file}")
    else:
        typer.echo(output)
