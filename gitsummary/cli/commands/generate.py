"""The `generate` subcommands for report generation.

Produces various reports from stored artifacts:
- changelog: Grouped by category
- release-notes: User-facing changes (with optional LLM synthesis)
- impact: Technical impact analysis
"""

from __future__ import annotations

import json
import re
import webbrowser
from pathlib import Path
from typing import Optional

import typer

from ...core import ChangeCategory
from ...infrastructure import (
    GitCommandError,
    list_commits_in_range,
    load_artifacts_for_range,
    repository_root,
    save_release_note,
)
from ...renderers import (
    format_artifact_feed_html,
    format_changelog_markdown,
    format_impact_markdown,
    format_release_note_markdown,
    format_release_note_text,
)
from ...reports import ReleaseNote
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
        output = format_changelog_markdown(revision_range, report)

    _write_output(output, output_file)


def generate_feed(
    revision_range: str = typer.Argument(
        ...,
        help="Revision range to generate an HTML artifact feed for.",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write to file instead of the default <project>-feed.html.",
    ),
    skip_unanalyzed: bool = typer.Option(
        False,
        "--skip-unanalyzed",
        help="Hide commits without artifacts (by default they are included as friendly CTAs).",
    ),
    open_browser: bool = typer.Option(
        False,
        "--open",
        help="Open the generated feed in your default browser.",
    ),
) -> None:
    """Generate a scroll-friendly HTML feed of commits and artifacts."""
    try:
        commits = list_commits_in_range(revision_range)
    except GitCommandError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not commits:
        typer.secho("No commits found.", err=True, fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    shas = [c.sha for c in commits]
    artifacts = load_artifacts_for_range(shas)

    try:
        project_name = Path(repository_root()).name
    except GitCommandError:
        project_name = "Project"

    reporter = ReporterService()
    feed = reporter.generate_artifact_feed(
        commits,
        artifacts,
        include_unanalyzed=not skip_unanalyzed,
    )

    html_output = format_artifact_feed_html(project_name, revision_range, feed)

    default_name = f"{_safe_project_name(project_name)}-feed.html"
    output_path = Path(output_file) if output_file else Path(repository_root()) / default_name
    output_path.write_text(html_output, encoding="utf-8")
    typer.echo(f"Feed written to {output_path}")

    if open_browser:
        try:
            webbrowser.open(output_path.resolve().as_uri())
        except Exception:
            typer.secho("Unable to open browser automatically.", err=True, fg=typer.colors.YELLOW)


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
        output = format_release_note_text(release_note)
    else:  # markdown
        output = format_release_note_markdown(release_note)

    _write_output(output, output_file)


def _get_llm_provider(provider_name: Optional[str], model: Optional[str]):
    """Get an LLM provider for synthesis."""
    try:
        from ...llm import (
            get_config_manager,
            get_provider,
            list_available_providers,
        )
        from ...llm.base import ProviderConfig

        # If no provider specified, try to get a default
        if provider_name is None:
            available = list_available_providers()
            if not available:
                return None
            provider_name = available[0]

        # Build config. If no model override is provided, delegate to the
        # registry/config manager so it can inject API keys from env/config.
        config: Optional[ProviderConfig] = None
        if model:
            config = ProviderConfig(model=model)
            # Ensure API key is set when we supply an explicit config
            cm = get_config_manager()
            api_key = cm.get_api_key(provider_name, prompt_if_missing=False)
            if api_key:
                config.api_key = api_key

        return get_provider(provider_name, config)
    except Exception:
        return None




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
        output = format_impact_markdown(revision_range, report)

    _write_output(output, output_file)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _write_output(output: str, output_file: Optional[str]) -> None:
    """Write output to file or stdout."""
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        typer.echo(f"Report written to {output_file}")
    else:
        typer.echo(output)


def _safe_project_name(name: str) -> str:
    """Convert project name to a filesystem-friendly slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip())
    cleaned = cleaned.strip("-").lower()
    return cleaned or "project"
