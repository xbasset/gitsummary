"""The `generate` subcommands for report generation.

Produces various reports from stored artifacts:
- changelog: Grouped by category
- release-notes: User-facing changes (with optional LLM synthesis)
- impact: Technical impact analysis
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ...core import ChangeCategory, ReleaseNote
from ...infrastructure import (
    GitCommandError,
    list_commits_in_range,
    load_artifacts_for_range,
    repository_root,
    save_release_note,
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
    output_format: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Output format: markdown, yaml, text.",
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write to file instead of stdout."
    ),
    use_llm: bool = typer.Option(
        True,
        "--llm/--no-llm",
        help="Use LLM for synthesis (default: enabled).",
    ),
    provider_name: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="LLM provider to use (e.g., openai, anthropic, ollama).",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Model to use for LLM synthesis.",
    ),
    product_name: Optional[str] = typer.Option(
        None,
        "--product",
        help="Product name for the header (default: repo directory name).",
    ),
    version: Optional[str] = typer.Option(
        None,
        "--version",
        "-v",
        help="Version for the header (default: extracted from range end).",
    ),
    store: bool = typer.Option(
        False,
        "--store",
        help="Store the release note in Git Notes.",
    ),
) -> None:
    """Generate user-facing release notes from analyzed artifacts.

    Uses LLM synthesis by default to create user-focused, well-organized
    release notes. Use --no-llm for faster heuristic-based generation.
    """
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

    analyzed_count = sum(1 for a in artifacts.values() if a is not None)
    if analyzed_count == 0:
        typer.secho(
            "No analyzed commits found. Run 'gitsummary analyze' first.",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    # Determine product name
    if product_name is None:
        try:
            repo_root = Path(repository_root())
            product_name = repo_root.name
        except GitCommandError:
            product_name = "Project"

    # Determine version
    if version is None:
        # Try to extract from revision range (e.g., "v0.1.0..v0.2.0" -> "v0.2.0")
        if ".." in revision_range:
            version = revision_range.split("..")[-1]
        else:
            version = revision_range

    # Get LLM provider if requested
    provider = None
    if use_llm:
        provider = _get_llm_provider(provider_name, model)
        if provider is None:
            typer.secho(
                "LLM provider not available. Using heuristic generation.",
                err=True,
                fg=typer.colors.YELLOW,
            )

    # Generate the release note
    reporter = ReporterService()
    release_note = reporter.generate_llm_release_notes(
        commits,
        artifacts,
        product_name=product_name,
        version=version,
        revision_range=revision_range,
        provider=provider,
    )

    # Store if requested
    if store:
        tip_sha = commits[0].sha
        yaml_content = release_note.to_yaml()
        save_release_note(tip_sha, yaml_content)
        typer.secho(
            f"Release note stored for commit {commits[0].short_sha}",
            fg=typer.colors.GREEN,
        )

    # Format and output
    if output_format == "yaml":
        output = release_note.to_yaml()
    elif output_format == "text":
        output = _format_release_note_text(release_note)
    else:  # markdown
        output = _format_release_note_markdown(release_note)

    _write_output(output, output_file)


def _get_llm_provider(provider_name: Optional[str], model: Optional[str]):
    """Get an LLM provider for synthesis."""
    try:
        from ...llm import get_provider, list_available_providers
        from ...llm.base import ProviderConfig

        # If no provider specified, try to get a default
        if provider_name is None:
            available = list_available_providers()
            if not available:
                return None
            provider_name = available[0]

        # Build config
        config = ProviderConfig()
        if model:
            config.model = model

        return get_provider(provider_name, config)
    except Exception:
        return None


def _format_release_note_markdown(release_note: ReleaseNote) -> str:
    """Format a release note as Markdown."""
    lines = []

    # Header
    h = release_note.header
    lines.append(f"# {h.product_name} {h.version} — {h.release_date}")
    lines.append("")
    lines.append(f"*{h.theme}*")
    lines.append("")

    # Highlights
    if release_note.highlights:
        lines.append("## 🚀 Highlights")
        lines.append("")
        for hl in release_note.highlights:
            lines.append(f"- {hl.emoji} **{hl.type.title()}**: {hl.summary}")
        lines.append("")

    # New Features
    if release_note.features:
        lines.append("## 🆕 New Features")
        lines.append("")
        for feat in release_note.features:
            lines.append(f"### {feat.title}")
            lines.append("")
            lines.append(feat.description)
            lines.append("")
            lines.append(f"*{feat.user_benefit}*")
            lines.append("")

    # Improvements
    if release_note.improvements:
        lines.append("## ✨ Improvements")
        lines.append("")
        for imp in release_note.improvements:
            lines.append(f"- {imp.summary}")
        lines.append("")

    # Bug Fixes
    if release_note.fixes:
        lines.append("## 🛠️ Bug Fixes")
        lines.append("")
        for fix in release_note.fixes:
            lines.append(f"- {fix.summary}")
        lines.append("")

    # Deprecations / Breaking Changes
    if release_note.deprecations:
        lines.append("## ⚠️ Deprecations & Breaking Changes")
        lines.append("")
        for dep in release_note.deprecations:
            lines.append(f"### {dep.what}")
            lines.append("")
            lines.append(f"**Reason**: {dep.reason}")
            lines.append("")
            lines.append(f"**Migration**: {dep.migration}")
            if dep.deadline:
                lines.append(f"**Deadline**: {dep.deadline}")
            lines.append("")

    # Known Issues
    if release_note.known_issues:
        lines.append("## 📌 Known Issues")
        lines.append("")
        for issue in release_note.known_issues:
            lines.append(f"- {issue.issue} *({issue.status})*")
        lines.append("")

    # Call to Action
    if release_note.call_to_action:
        cta = release_note.call_to_action
        lines.append("## 📚 Learn More")
        lines.append("")
        if cta.documentation_url:
            lines.append(f"- [Documentation]({cta.documentation_url})")
        if cta.migration_guide_url:
            lines.append(f"- [Migration Guide]({cta.migration_guide_url})")
        if cta.support_url:
            lines.append(f"- [Support]({cta.support_url})")
        lines.append("")

    # Footer with metadata
    m = release_note.metadata
    lines.append("---")
    lines.append(
        f"*{m.commit_count} commits, {m.analyzed_count} analyzed"
        + (f" • Generated with {m.llm_provider}/{m.llm_model}" if m.llm_provider else "")
        + "*"
    )

    return "\n".join(lines)


def _format_release_note_text(release_note: ReleaseNote) -> str:
    """Format a release note as plain text."""
    lines = []

    # Header
    h = release_note.header
    lines.append(f"{h.product_name} {h.version} — {h.release_date}")
    lines.append("=" * len(lines[-1]))
    lines.append("")
    lines.append(h.theme)
    lines.append("")

    # Highlights
    if release_note.highlights:
        lines.append("HIGHLIGHTS")
        lines.append("-" * 10)
        for hl in release_note.highlights:
            lines.append(f"  [{hl.type.upper()}] {hl.summary}")
        lines.append("")

    # New Features
    if release_note.features:
        lines.append("NEW FEATURES")
        lines.append("-" * 12)
        for feat in release_note.features:
            lines.append(f"  * {feat.title}")
            lines.append(f"    {feat.description}")
            lines.append(f"    Why: {feat.user_benefit}")
            lines.append("")

    # Improvements
    if release_note.improvements:
        lines.append("IMPROVEMENTS")
        lines.append("-" * 12)
        for imp in release_note.improvements:
            lines.append(f"  * {imp.summary}")
        lines.append("")

    # Bug Fixes
    if release_note.fixes:
        lines.append("BUG FIXES")
        lines.append("-" * 9)
        for fix in release_note.fixes:
            lines.append(f"  * {fix.summary}")
        lines.append("")

    # Deprecations / Breaking Changes
    if release_note.deprecations:
        lines.append("DEPRECATIONS & BREAKING CHANGES")
        lines.append("-" * 31)
        for dep in release_note.deprecations:
            lines.append(f"  * {dep.what}")
            lines.append(f"    Reason: {dep.reason}")
            lines.append(f"    Migration: {dep.migration}")
            if dep.deadline:
                lines.append(f"    Deadline: {dep.deadline}")
            lines.append("")

    # Known Issues
    if release_note.known_issues:
        lines.append("KNOWN ISSUES")
        lines.append("-" * 12)
        for issue in release_note.known_issues:
            lines.append(f"  * {issue.issue} ({issue.status})")
        lines.append("")

    # Footer
    m = release_note.metadata
    lines.append("-" * 40)
    lines.append(f"{m.commit_count} commits, {m.analyzed_count} analyzed")

    return "\n".join(lines)


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

