"""GitHub CLI helpers.

These commands integrate gitsummary reports with the GitHub CLI (`gh`).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Optional

import typer

from ...infrastructure import (
    GitCommandError,
    fetch_tags,
    get_root_commit,
    list_commits_to_revision,
    list_tags_by_date,
)
from ..ui import UXState, echo_status, spinner
from . import ci as ci_cmd


def _infer_revision_range(tag: str, *, no_fetch: bool) -> str:
    if not no_fetch:
        try:
            with spinner("Fetching remote tags", final_state=UXState.SUCCESS):
                fetch_tags()
        except GitCommandError as exc:
            typer.secho(f"Failed to fetch tags: {exc}", err=True, fg=typer.colors.RED)
            raise typer.Exit(code=2) from exc

    try:
        with spinner("Reading tags", final_state=UXState.SUCCESS):
            tags = list_tags_by_date()
    except GitCommandError as exc:
        typer.secho(f"Error reading tags: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    if not tags:
        typer.secho(
            "No git tags found. Provide --range explicitly (e.g., v0.4.0..v0.5.0).",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    idx = next((i for i, t in enumerate(tags) if t.name == tag), None)
    if idx is None:
        typer.secho(
            f"Tag {tag!r} not found locally. Provide --range explicitly (e.g., v0.4.0..{tag}).",
            err=True,
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    previous = tags[idx - 1] if idx > 0 else None
    if previous is not None:
        return f"{previous.name}..{tag}"

    # First tag in history: include from root commit.
    try:
        root_sha = get_root_commit()
        # Use full SHA to avoid ambiguity.
        return f"{root_sha}..{tag}"
    except GitCommandError:
        # As a fallback, include all commits reachable from the tag.
        commits = list_commits_to_revision(tag)
        if commits:
            return f"{commits[-1].sha}..{tag}"
        return tag


def release_create(
    tag: str = typer.Argument(..., help="Tag name for the GitHub Release (e.g., v0.5.0)."),
    revision_range: Optional[str] = typer.Option(
        None,
        "--range",
        "-r",
        help="Revision range to generate notes for (e.g., v0.4.0..v0.5.0). If omitted, inferred from tags.",
    ),
    title: Optional[str] = typer.Option(
        None,
        "--title",
        help="Release title (defaults to the tag when omitted).",
    ),
    draft: bool = typer.Option(False, "--draft", help="Create a draft release."),
    prerelease: bool = typer.Option(False, "--prerelease", help="Mark as prerelease."),
    target: Optional[str] = typer.Option(
        None,
        "--target",
        help="Target branch or commit for the release.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print the inferred range and generated notes; do not call `gh`.",
    ),
    no_fetch: bool = typer.Option(
        False,
        "--no-fetch",
        help="Skip fetching remote tags when inferring ranges.",
    ),
    # Release note generation options (mirrors `gitsummary ci release-notes`)
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
    compute_missing: bool = typer.Option(
        True,
        "--compute-missing/--no-compute-missing",
        help="Compute missing commit artifacts in-memory (never stored in Git Notes).",
    ),
    reanalyze_existing: bool = typer.Option(
        False,
        "--reanalyze-existing",
        help="Recompute artifacts even if they already exist (in-memory only).",
    ),
) -> None:
    """Create a GitHub Release using gitsummary-generated notes."""
    resolved_range = revision_range or _infer_revision_range(tag, no_fetch=no_fetch)
    echo_status(f"Range: {resolved_range}", UXState.INFO)

    notes, _fmt = ci_cmd._build_release_notes_output(  # noqa: SLF001 (shared CLI helper)
        resolved_range,
        output_format="markdown",
        compute_missing=compute_missing,
        reanalyze_existing=reanalyze_existing,
        use_llm=use_llm,
        provider_name=provider_name,
        model=model,
        product_name=None,
        version=tag,
    )

    if dry_run:
        typer.echo("")
        typer.echo(notes)
        return

    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(notes)
            tmp_path = tmp.name

        cmd = ["gh", "release", "create", tag, "--notes-file", tmp_path]
        if title:
            cmd += ["--title", title]
        if draft:
            cmd.append("--draft")
        if prerelease:
            cmd.append("--prerelease")
        if target:
            cmd += ["--target", target]

        with spinner("Creating GitHub release via `gh`", final_state=UXState.SUCCESS):
            subprocess.run(cmd, check=True)
    except FileNotFoundError:
        typer.secho(
            "`gh` not found on PATH. Install GitHub CLI or run `gitsummary ci release-notes ...` and paste manually.",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=127)
    except subprocess.CalledProcessError as exc:
        typer.secho(
            f"`gh release create` failed (exit {exc.returncode}).",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=exc.returncode)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                # Best-effort cleanup.
                pass


