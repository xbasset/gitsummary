"""Repository bootstrap commands.

Goal: provide a single command that sets up automatic release note generation
for GitHub Releases with minimal friction.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer
from typer.models import OptionInfo

from ...infrastructure import GitCommandError, repository_root
from ...llm.config import get_config_manager
from ..ui import UXState, echo_status


WORKFLOW_RELATIVE_PATH = Path(".github/workflows/gitsummary-release-notes.yml")
RELEASE_NOTES_DIRNAME = "release-notes"


def github_release_notes(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Run without interactive prompts (fails if required values are missing).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing files.",
    ),
    openai_key_env: str = typer.Option(
        "OPENAI_API_KEY",
        "--openai-key-env",
        help="Environment variable name to check for the OpenAI API key.",
    ),
    workflow_path: Optional[str] = typer.Option(
        None,
        "--workflow-path",
        help="Where to write the GitHub Actions workflow (default: .github/workflows/gitsummary-release-notes.yml).",
    ),
) -> None:
    """Initialize GitHub Release Note automation for the current repository.

    This scaffolds a GitHub Actions workflow that:
    - generates release notes on GitHub Release publish
    - updates the GitHub Release body
    - uploads the markdown as a workflow artifact (no repo commits)

    It also ensures an OpenAI API key exists locally (env/config). If not found,
    it prompts for one and offers to save it to the user config file.
    """
    # Typer wraps defaults in OptionInfo. This command is primarily invoked via
    # CLI, but tests (and power users) call it directly; normalize for that case.
    if isinstance(yes, OptionInfo):
        yes = False
    if isinstance(force, OptionInfo):
        force = False
    if isinstance(openai_key_env, OptionInfo):
        openai_key_env = "OPENAI_API_KEY"
    if isinstance(workflow_path, OptionInfo):
        workflow_path = None

    try:
        repo_root = Path(repository_root())
    except GitCommandError as exc:
        typer.secho(
            f"Error: not a git repository ({exc})", err=True, fg=typer.colors.RED
        )
        raise typer.Exit(code=2) from exc

    cm = get_config_manager()

    api_key = os.environ.get(openai_key_env) or cm.get_api_key(
        "openai", prompt_if_missing=False
    )
    if not api_key:
        if yes:
            typer.secho(
                f"Missing OpenAI API key. Set {openai_key_env} or configure OPENAI_API_KEY in ~/.config/gitsummary/config.",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=2)

        api_key = _prompt_required_secret(
            prompt=f"Enter your OpenAI API key (will not echo)",
        )
        save = typer.confirm(
            "Save this key to ~/.config/gitsummary/config?",
            default=True,
        )
        if save:
            if cm.save_api_key("openai", api_key):
                echo_status("Saved OpenAI API key to user config.", UXState.SUCCESS)
            else:
                typer.secho(
                    "Warning: could not save key to config file.",
                    err=True,
                    fg=typer.colors.YELLOW,
                )

    workflow_rel = Path(workflow_path) if workflow_path else WORKFLOW_RELATIVE_PATH
    workflow_abs = repo_root / workflow_rel
    workflow_yaml = render_github_release_notes_workflow_yaml()

    _write_text_file(
        workflow_abs,
        workflow_yaml,
        yes=yes,
        force=force,
    )

    echo_status("GitHub Actions workflow installed.", UXState.SUCCESS)
    typer.echo("")
    typer.echo("Next step (required for CI):")
    typer.echo(
        f"- Add a GitHub Actions secret named {openai_key_env} with your OpenAI API key."
    )
    typer.echo(
        "  UI: Settings → Secrets and variables → Actions → New repository secret"
    )
    typer.echo("")
    typer.echo("Optional (CLI):")
    typer.echo(f'- gh secret set {openai_key_env} --body "<your-key>"')
    typer.echo("")
    typer.echo(
        "That’s it. On the next GitHub Release publish, release notes will be generated."
    )


def render_github_release_notes_workflow_yaml() -> str:
    """Render the GitHub Actions workflow for automatic release notes."""
    # Important: CI is non-interactive. We fail fast if OPENAI_API_KEY is missing.
    return """name: gitsummary release notes

on:
  release:
    types: [published]

permissions:
  contents: write

jobs:
  release-notes:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Fetch Git Notes (read-only artifacts cache)
        run: |
          set -euo pipefail
          git fetch origin refs/notes/intent:refs/notes/intent || true
          git fetch origin refs/notes/report/release-note:refs/notes/report/release-note || true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install gitsummary
        run: |
          python -m pip install --upgrade pip
          pip install gitsummary

      - name: Ensure OpenAI key is configured
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          if [ -z "${OPENAI_API_KEY}" ]; then
            echo "::error::Missing OPENAI_API_KEY. Add it as a GitHub Actions secret (Settings → Secrets and variables → Actions)."
            exit 1
          fi

      - name: Compute revision range
        id: range
        env:
          GH_TOKEN: ${{ github.token }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          TAG: ${{ github.event.release.tag_name }}
        run: |
          set -euo pipefail
          echo "tag=${TAG}" >> "$GITHUB_OUTPUT"

          # Find previous published release (excluding drafts). If none, fall back to repo root.
          PREV_TAG="$(gh api "repos/${GITHUB_REPOSITORY}/releases?per_page=20" --jq ".[] | select(.draft==false) | .tag_name" | awk -v tag="${TAG}" '$0!=tag {print; exit}' || true)"
          if [ -n "${PREV_TAG}" ]; then
            echo "prev_tag=${PREV_TAG}" >> "$GITHUB_OUTPUT"
            echo "range=${PREV_TAG}..${TAG}" >> "$GITHUB_OUTPUT"
          else
            ROOT_SHA="$(git rev-list --max-parents=0 HEAD | tail -n 1)"
            echo "prev_tag=" >> "$GITHUB_OUTPUT"
            echo "range=${ROOT_SHA}..${TAG}" >> "$GITHUB_OUTPUT"
          fi

      - name: Generate release notes (CI mode; no Git Notes writes)
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITSUMMARY_PROVIDER: openai
        run: |
          OUT="$RUNNER_TEMP/release-notes-${{ steps.range.outputs.tag }}.md"
          gitsummary ci release-notes "${{ steps.range.outputs.range }}" --format markdown --output "$OUT"
          echo "out=${OUT}" >> "$GITHUB_OUTPUT"
        id: ci_notes

      - name: Upload release notes artifact
        uses: actions/upload-artifact@v4
        with:
          name: release-notes-${{ steps.range.outputs.tag }}
          path: ${{ steps.ci_notes.outputs.out }}

      - name: Update GitHub Release body
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ steps.range.outputs.tag }}
        run: |
          gh release edit "${TAG}" --notes-file "${{ steps.ci_notes.outputs.out }}"
"""


def _prompt_required_secret(*, prompt: str) -> str:
    """Prompt until a non-empty secret value is provided (or user aborts)."""
    while True:
        try:
            value = typer.prompt(prompt, hide_input=True)
        except (typer.Abort, EOFError, KeyboardInterrupt):
            raise typer.Exit(code=1)
        value = value.strip()
        if value:
            return value


def _write_text_file(path: Path, content: str, *, yes: bool, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        if yes:
            typer.secho(
                f"Refusing to overwrite existing file without --force: {path}",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=2)
        decision = typer.confirm(f"File exists: {path}. Overwrite?", default=False)
        if not decision:
            typer.secho("Aborted.", err=True, fg=typer.colors.YELLOW)
            raise typer.Exit(code=1)
    path.write_text(content, encoding="utf-8")
    echo_status(f"Wrote {path}", UXState.SUCCESS)
