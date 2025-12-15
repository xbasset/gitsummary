"""CI-focused commands.

These commands are designed for automation environments (GitHub Actions, CI)
where we want to benefit from existing Git Notes artifacts without creating
new Git Notes entries or modifying the repository history.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import typer
from typer.models import OptionInfo

from ...core import CommitArtifact
from ...infrastructure import (
    GitCommandError,
    get_commit_diff,
    list_commits_in_range,
    load_artifacts_for_range,
    repository_root,
)
from ...renderers import format_release_note_markdown, format_release_note_text
from ...services import AnalyzerService, ReporterService
from ...tracing import trace_manager
from ..ui import UXState, echo_status, spinner
from .generate import _get_llm_provider


def release_notes(
    revision_range: str = typer.Argument(
        ...,
        help="Revision range to generate release notes for (e.g., v1.0..v2.0).",
    ),
    output_format: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Output format: markdown, text.",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write to file instead of stdout (recommended for CI artifacts).",
    ),
    # Analysis options
    compute_missing: bool = typer.Option(
        True,
        "--compute-missing/--no-compute-missing",
        help="Compute missing commit artifacts in-memory (never stored in Git Notes).",
    ),
    reanalyze_existing: bool = typer.Option(
        False,
        "--reanalyze-existing",
        help="Recompute artifacts even if they already exist in Git Notes (in-memory only).",
    ),
    use_llm: bool = typer.Option(
        True,
        "--llm/--no-llm",
        help="Use LLM for commit analysis and/or release note synthesis.",
    ),
    provider_name: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        envvar="GITSUMMARY_PROVIDER",
        help="LLM provider to use (e.g., openai, anthropic, ollama).",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        envvar="GITSUMMARY_MODEL",
        help="Model to use for LLM (provider-specific).",
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
) -> None:
    """Generate release notes for CI without writing Git Notes.

    This command:
    - reads existing artifacts from Git Notes if present locally (read-only)
    - optionally computes missing artifacts in-memory (no `git notes add`)
    - synthesizes release notes and writes markdown/text output
    """
    # Typer wraps defaults in OptionInfo. Normalize for tests/power users that
    # call this function directly (without going through the CLI).
    if isinstance(output_format, OptionInfo):
        output_format = "markdown"
    if isinstance(output_file, OptionInfo):
        output_file = None
    if isinstance(compute_missing, OptionInfo):
        compute_missing = True
    if isinstance(reanalyze_existing, OptionInfo):
        reanalyze_existing = False
    if isinstance(use_llm, OptionInfo):
        use_llm = True
    if isinstance(provider_name, OptionInfo):
        provider_name = None
    if isinstance(model, OptionInfo):
        model = None
    if isinstance(product_name, OptionInfo):
        product_name = None
    if isinstance(version, OptionInfo):
        version = None

    # Mirror `analyze` behavior: allow per-provider model override via env.
    if model:
        provider_key = (provider_name or "openai").upper()
        os.environ[f"GITSUMMARY_{provider_key}_MODEL"] = model

    try:
        with spinner(
            f"Resolving commits for {revision_range}", final_state=UXState.SUCCESS
        ):
            commits = list_commits_in_range(revision_range)
    except GitCommandError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not commits:
        typer.secho("No commits found.", err=True, fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    shas = [c.sha for c in commits]
    with spinner(
        "Loading artifacts from Git Notes (read-only)", final_state=UXState.SUCCESS
    ):
        artifacts: Dict[str, Optional[CommitArtifact]] = load_artifacts_for_range(shas)

    if reanalyze_existing:
        missing_commits = commits
    else:
        missing_commits = [c for c in commits if artifacts.get(c.sha) is None]

    if missing_commits and compute_missing:
        echo_status(
            f"Computing {len(missing_commits)} missing artifact(s) in-memory (no Git Notes writes)",
            UXState.INFO,
        )
        analyzer = AnalyzerService(use_llm=use_llm, provider_name=provider_name)
        errors = 0
        with typer.progressbar(missing_commits, label="Analyzing") as progress:
            for commit in progress:
                try:
                    diff = get_commit_diff(commit.sha)
                    artifacts[commit.sha] = analyzer.analyze(commit, diff)
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    typer.secho(
                        f"  ✗ {commit.short_sha} {exc}",
                        err=True,
                        fg=typer.colors.RED,
                    )
        if errors:
            typer.secho(
                f"{errors} commit(s) failed during analysis; continuing with available artifacts.",
                err=True,
                fg=typer.colors.YELLOW,
            )

    analyzed_count = sum(1 for a in artifacts.values() if a is not None)
    if analyzed_count == 0:
        typer.secho(
            "No analyzed commits available. Push/fetch refs/notes/intent or enable --compute-missing.",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    # Determine product name
    if product_name is None:
        try:
            product_name = Path(repository_root()).name
        except GitCommandError:
            product_name = "Project"

    # Determine version
    if version is None:
        version = (
            revision_range.split("..")[-1] if ".." in revision_range else revision_range
        )

    provider = _get_llm_provider(provider_name, model) if use_llm else None
    reporter = ReporterService()
    with spinner("Synthesizing release notes", final_state=UXState.SUCCESS):
        release_note = reporter.generate_llm_release_notes(
            commits,
            artifacts,
            product_name=product_name,
            version=version,
            revision_range=revision_range,
            provider=provider,
        )

    if output_format == "text":
        output = format_release_note_text(release_note)
    else:
        output = format_release_note_markdown(release_note)

    _write_output(
        output, output_file, format_hint=output_format, revision_range=revision_range
    )


def _write_output(
    output: str, output_file: Optional[str], *, format_hint: str, revision_range: str
) -> None:
    meta = {"format": format_hint, "revision_range": revision_range}
    if output_file:
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
        typer.echo(f"Release notes written to {output_file}")
        trace_manager.log_output_reference(
            kind="ci_release_notes_report",
            location=str(path.resolve()),
            metadata=meta,
        )
    else:
        typer.echo(output)
        trace_manager.log_output_reference(
            kind="ci_release_notes_report_stdout",
            location="stdout",
            metadata=meta,
        )
