"""Release note helper for the latest tagged release."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import List, Optional

import typer

from ...core import CommitInfo, TagInfo
from ...infrastructure import (
    GitCommandError,
    fetch_tags,
    get_commit_diff,
    get_commit_info,
    get_root_commit,
    list_commits_in_range,
    list_commits_to_revision,
    list_tags_by_date,
    load_artifacts_for_range,
    load_release_note,
    RELEASE_NOTE_NOTES_REF,
    repository_root,
    release_note_exists,
    save_artifact,
    save_release_note,
)
from ...tracing import trace_manager
from ...renderers import format_release_note_html, format_release_note_markdown
from ...reports import ReleaseNote
from ...services import AnalyzerService, ReporterService
from ..storage import storage_option
from ..ui import UXState, echo_status, spinner
from ..commands.generate import _get_llm_provider


def release_note(
    target: str = typer.Argument(
        "latest",
        help="Release target to analyze (only 'latest' is supported).",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Run without interactive prompts.",
    ),
    no_fetch: bool = typer.Option(
        False,
        "--no-fetch",
        help="Skip fetching remote tags.",
    ),
    output_dir: Optional[str] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory to write the HTML release note (default: <repo>/release-notes).",
    ),
    no_open: bool = typer.Option(
        False,
        "--no-open",
        help="Do not attempt to open the HTML release note.",
    ),
    use_llm: bool = typer.Option(
        True,
        "--llm/--no-llm",
        help="Use LLM for synthesis (default: enabled).",
    ),
    reanalyze: bool = typer.Option(
        False,
        "--reanalyze",
        help="Re-analyze commits even if artifacts already exist.",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="LLM provider to use for synthesis.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model to use for synthesis.",
    ),
    storage: str = storage_option(),
) -> None:
    """Analyze commits for the latest tag and generate release notes."""
    if target != "latest":
        typer.secho(
            "Only the 'latest' target is supported for release-note.",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    try:
        with spinner("Detecting repository root"):
            repo_root = Path(repository_root())
    except GitCommandError as exc:
        typer.secho(
            f"Error determining repository root: {exc}", err=True, fg=typer.colors.RED
        )
        raise typer.Exit(code=2) from exc

    if not no_fetch:
        try:
            with spinner("Fetching remote tags"):
                fetch_tags()
        except GitCommandError as exc:
            typer.secho(f"Failed to fetch tags: {exc}", err=True, fg=typer.colors.RED)
            raise typer.Exit(code=2) from exc

    try:
        with spinner("Reading tags"):
            tags = list_tags_by_date()
    except GitCommandError as exc:
        typer.secho(f"Error reading tags: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not tags:
        typer.secho(
            "No git tags found. Create a version tag (e.g., git tag v0.1.0) and rerun.",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    latest_tag = tags[-1]
    previous_tag = tags[-2] if len(tags) > 1 else None

    try:
        with spinner("Computing commit range"):
            commits, revision_range = _compute_commits(latest_tag, previous_tag)
    except GitCommandError as exc:
        typer.secho(f"Error loading commits: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not commits:
        typer.secho(
            "No commits found for the selected range.", err=True, fg=typer.colors.YELLOW
        )
        raise typer.Exit(code=1)

    tip_sha = commits[0].sha
    if release_note_exists(tip_sha) and not reanalyze:
        typer.secho(
            f"Release note already exists for {latest_tag.name}; showing stored copy.",
            fg=typer.colors.GREEN,
        )
        yaml_content = load_release_note(tip_sha)
        if not yaml_content:
            typer.secho(
                "Failed to load stored release note content.",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=2)

        try:
            release_note = ReleaseNote.from_yaml(yaml_content)
        except Exception as exc:  # noqa: BLE001
            typer.secho(
                f"Failed to parse stored release note: {exc}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=2) from exc

        markdown = format_release_note_markdown(release_note)
        typer.echo("")
        typer.echo(markdown)

        html_path = _write_html_release_note(release_note, repo_root, output_dir, yes)
        if html_path and not no_open:
            try:
                webbrowser.open(html_path.resolve().as_uri())
            except Exception:
                typer.secho(
                    "Unable to open browser automatically.",
                    err=True,
                    fg=typer.colors.YELLOW,
                )
        return

    commit_shas = [c.sha for c in commits]
    artifacts = load_artifacts_for_range(commit_shas, backend=storage)

    if reanalyze:
        analyzed_count = 0
        missing_commits = commits
    else:
        analyzed_count = sum(1 for a in artifacts.values() if a is not None)
        missing_commits = [c for c in commits if artifacts.get(c.sha) is None]

    echo_status(f"Repository: {repo_root}", UXState.INFO)
    echo_status(f"Latest tag: {latest_tag.name} ({latest_tag.date.date()})", UXState.INFO)
    echo_status(
        f"Previous tag: {previous_tag.name if previous_tag else 'none (using repo root)'}",
        UXState.INFO,
    )
    echo_status(f"Range: {revision_range}", UXState.INFO)
    echo_status(
        f"Commits: {len(commits)} • analyzed: {analyzed_count} • missing: {len(missing_commits)}",
        UXState.INFO,
    )
    to_analyze = {c.sha for c in missing_commits}
    _print_commit_status(commits, artifacts, to_analyze)

    if missing_commits:
        prompt_text = (
            f"Re-analyze {len(missing_commits)} commit(s)?"
            if reanalyze
            else f"Analyze {len(missing_commits)} missing commit(s)?"
        )
        decision = True if reanalyze else (yes or typer.confirm(prompt_text, default=True))
        trace_manager.log_user_interaction(
            action="confirm_analyze_missing_commits",
            prompt=prompt_text,
            response=decision,
        )
        if decision:
            _analyze_missing(missing_commits, artifacts, use_llm, provider, storage)
        else:
            typer.secho("Aborted before analysis.", err=True, fg=typer.colors.YELLOW)
            raise typer.Exit(code=1)

    analyzed_count = sum(1 for a in artifacts.values() if a is not None)
    if analyzed_count == 0:
        typer.secho(
            "No analyzed commits available. Run 'gitsummary analyze' for the range and retry.",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    llm_provider = _get_llm_provider(provider, model) if use_llm else None
    reporter = ReporterService()
    release_note = reporter.generate_llm_release_notes(
        commits,
        artifacts,
        product_name=repo_root.name,
        version=latest_tag.name,
        revision_range=revision_range,
        provider=llm_provider,
    )

    try:
        save_release_note(commits[0].sha, release_note.to_yaml())
        typer.secho(
            f"Release note stored in Git Notes for {commits[0].short_sha}",
            fg=typer.colors.GREEN,
        )
    except GitCommandError as exc:
        trace_manager.log_error(
            message="Failed to store release note",
            detail=str(exc),
        )
        typer.secho(
            f"Warning: could not store release note in Git Notes ({exc}).",
            err=True,
            fg=typer.colors.YELLOW,
        )

    markdown = format_release_note_markdown(release_note)
    typer.echo("")
    typer.echo(markdown)

    html_path = _write_html_release_note(release_note, repo_root, output_dir, yes)
    if html_path:
        typer.echo(f"HTML release note written to {html_path}")
        if not no_open:
            try:
                webbrowser.open(html_path.resolve().as_uri())
            except Exception:
                typer.secho(
                    "Unable to open browser automatically.",
                    err=True,
                    fg=typer.colors.YELLOW,
                )


def _compute_commits(
    latest: TagInfo, previous: Optional[TagInfo]
) -> tuple[List["CommitInfo"], str]:
    if previous:
        revision_range = f"{previous.name}..{latest.name}"
        commits = list_commits_in_range(revision_range)
        return commits, revision_range

    root_sha = get_root_commit()
    commits = list_commits_to_revision(latest.name)
    revision_range = (
        f"{commits[-1].short_sha}..{latest.name}"
        if commits
        else f"{root_sha[:7]}..{latest.name}"
    )
    # Ensure the root commit is included if it was excluded by two-dot semantics
    if commits and commits[-1].sha != root_sha:
        commits.append(get_commit_info(root_sha))
    return commits, revision_range


def _print_commit_status(commits, artifacts, to_analyze) -> None:
    typer.echo("")
    echo_status("Commit analysis status (latest → earliest):", UXState.INFO)
    preview = commits[:12]
    for commit in preview:
        analyzed = artifacts.get(commit.sha) is not None
        pending = commit.sha in to_analyze
        marker = "[..]" if pending or not analyzed else "[OK]"
        typer.echo(f"  {marker} {commit.short_sha} {commit.summary}")
    if len(commits) > len(preview):
        typer.echo(f"  … {len(commits) - len(preview)} more")
    typer.echo("")


def _analyze_missing(
    commits: List["CommitInfo"],
    artifacts,
    use_llm: bool,
    provider: Optional[str],
    storage: str,
) -> None:
    typer.echo(f"Analyzing {len(commits)} missing commit(s)...")
    analyzer = AnalyzerService(use_llm=use_llm, provider_name=provider)
    errors = 0
    with typer.progressbar(commits, label="Analyzing") as progress:
        for commit in progress:
            try:
                diff = get_commit_diff(commit.sha)
                artifact = analyzer.analyze(commit, diff)
                artifacts[commit.sha] = artifact
                save_artifact(artifact, backend=storage)
            except Exception as exc:  # noqa: BLE001
                errors += 1
                typer.secho(
                    f"  ✗ {commit.short_sha} {exc}",
                    err=True,
                    fg=typer.colors.RED,
                )

    if errors:
        typer.secho(
            f"{errors} commit(s) failed during analysis.",
            err=True,
            fg=typer.colors.YELLOW,
        )


def _write_html_release_note(
    release_note: ReleaseNote,
    repo_root: Path,
    output_dir: Optional[str],
    yes: bool,
) -> Optional[Path]:
    html_content = format_release_note_html(release_note)
    directory = Path(output_dir) if output_dir else repo_root / "release-notes"
    if not directory.exists():
        prompt_text = f"Create output directory {directory}?"
        decision = yes or typer.confirm(prompt_text, default=True)
        trace_manager.log_user_interaction(
            action="confirm_create_release_note_directory",
            prompt=prompt_text,
            response=decision,
        )
        if decision:
            directory.mkdir(parents=True, exist_ok=True)
        else:
            typer.secho(
                "Skipped HTML output (directory not created).",
                err=True,
                fg=typer.colors.YELLOW,
            )
            return None

    html_path = directory / f"{release_note.header.version}.html"
    html_path.write_text(html_content, encoding="utf-8")
    trace_manager.log_output_reference(
        kind="release_note_html",
        location=str(html_path),
    )
    return html_path
