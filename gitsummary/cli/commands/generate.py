"""The `generate` subcommands for report generation.

Produces various reports from stored artifacts:
- changelog: Grouped by category
- release-notes: User-facing changes
- impact: Technical impact analysis
"""

from __future__ import annotations

import json
from typing import Optional

import typer

from ...core import ChangeCategory
from ...infrastructure import (
    GitCommandError,
    list_commits_in_range,
    load_artifacts_for_range,
)
from ...services import ReporterService


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

    # Generate report
    reporter = ReporterService()
    report = reporter.generate_changelog(
        commits, artifacts, include_unanalyzed=include_unanalyzed
    )

    # Format output
    if output_format == "json":
        result = {
            "range": revision_range,
            "features": [
                {
                    "sha": c.short_sha,
                    "summary": a.intent_summary,
                    "breaking": a.is_breaking,
                }
                for c, a in report.features
            ],
            "fixes": [
                {"sha": c.short_sha, "summary": a.intent_summary}
                for c, a in report.fixes
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
                for c, a in report.by_category.get(cat, [])
            ],
        }
        output = json.dumps(result, indent=2)
    else:
        output = _format_changelog_markdown(revision_range, report)

    _write_output(output, output_file)


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

    # Generate report
    reporter = ReporterService()
    report = reporter.generate_release_notes(commits, artifacts)

    # Format output
    lines = [f"# Release Notes: {revision_range}", ""]

    if report.user_facing:
        lines.append("## What's New")
        lines.append("")

        for commit, artifact in report.user_facing:
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
    lines.append("---")
    lines.append(f"*{report.total_commits} commits, {report.analyzed_count} analyzed*")

    output = "\n".join(lines)
    _write_output(output, output_file)


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

    # Generate report
    reporter = ReporterService()
    report = reporter.generate_impact_report(commits, artifacts)

    if output_format == "json":
        result = {
            "range": revision_range,
            "total_commits": report.total_commits,
            "analyzed": report.analyzed_count,
            "impact_distribution": report.scope_distribution,
            "breaking_changes": report.breaking_count,
            "technical_highlights": report.technical_highlights[:20],
        }
        output = json.dumps(result, indent=2)
    else:
        lines = [
            f"# Impact Analysis: {revision_range}",
            "",
            "## Summary",
            f"- **Total commits:** {report.total_commits}",
            f"- **Analyzed:** {report.analyzed_count}",
            f"- **Breaking changes:** {report.breaking_count}",
            "",
            "## Impact Distribution",
        ]

        for scope, count in sorted(
            report.scope_distribution.items(), key=lambda x: -x[1]
        ):
            lines.append(f"- {scope}: {count}")

        if report.technical_highlights:
            lines.append("")
            lines.append("## Technical Highlights")
            for hl in report.technical_highlights[:10]:
                lines.append(f"- {hl}")

        output = "\n".join(lines)

    _write_output(output, output_file)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _format_changelog_markdown(revision_range: str, report) -> str:
    """Format a changelog report as Markdown."""
    lines = [f"# Changelog {revision_range}", ""]

    # Features
    if report.features:
        lines.append("## Features")
        for commit, artifact in report.features:
            breaking = " **[BREAKING]**" if artifact.is_breaking else ""
            lines.append(
                f"- **{artifact.intent_summary}** ({commit.short_sha}){breaking}"
            )
            if artifact.behavior_after:
                lines.append(f"  {artifact.behavior_after}")
        lines.append("")

    # Fixes
    if report.fixes:
        lines.append("## Fixes")
        for commit, artifact in report.fixes:
            lines.append(f"- **{artifact.intent_summary}** ({commit.short_sha})")
        lines.append("")

    # Security
    if report.security:
        lines.append("## Security")
        for commit, artifact in report.security:
            lines.append(f"- **{artifact.intent_summary}** ({commit.short_sha})")
        lines.append("")

    # Breaking Changes
    if report.breaking_changes:
        lines.append("## Breaking Changes")
        for commit, artifact in report.breaking_changes:
            lines.append(f"- **{artifact.intent_summary}** ({commit.short_sha})")
            if artifact.behavior_before and artifact.behavior_after:
                lines.append(f"  - Before: {artifact.behavior_before}")
                lines.append(f"  - After: {artifact.behavior_after}")
        lines.append("")

    # Other
    other = report.refactors + report.performance + report.chores
    if other:
        lines.append("## Other")
        for commit, artifact in other:
            lines.append(f"- {artifact.intent_summary} ({commit.short_sha})")
        lines.append("")

    # Unanalyzed
    if report.unanalyzed:
        lines.append("## Unanalyzed")
        for commit in report.unanalyzed:
            lines.append(f"- {commit.summary} ({commit.short_sha})")
        lines.append("")

    return "\n".join(lines)


def _write_output(output: str, output_file: Optional[str]) -> None:
    """Write output to file or stdout."""
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        typer.echo(f"Report written to {output_file}")
    else:
        typer.echo(output)

