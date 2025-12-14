# gitsummary Documentation

Quick orientation for new users and contributors.

## Start Here
- **GitHub Releases automation:** `gitsummary init github-release-notes` — one-command setup for CI-generated release notes that (1) writes `release-notes/<tag>.md`, (2) updates the GitHub Release body, and (3) opens a PR committing the file.
- **One-liner:** `gitsummary release-note latest` — generate release notes for your latest tag; add `--reanalyze` to force fresh analysis or `--no-llm` to stay offline.
- **Install:** `pip install -r requirements.txt && python -m gitsummary --help` (use a virtualenv).
- **Why:** Summarize *intent* and *impact* of changes, store them in Git Notes, and turn them into release notes/changelogs on demand.

## Key Commands
- `gitsummary analyze <range>` — build semantic artifacts (LLM + heuristic) and store in Git Notes.
- `gitsummary init github-release-notes` — install GitHub Release automation workflow (requires `OPENAI_API_KEY` secret for CI).
- `gitsummary release-note latest [--reanalyze] [--no-llm]` — analyze/generate release notes for the latest tag in one go.
- `gitsummary generate changelog <range>` — produce changelog from stored artifacts.
- `gitsummary show <commit>` / `show release-note <rev>` — inspect stored outputs.

## Architecture at a Glance
- CLI (`gitsummary/cli`): Typer app wiring commands.
- Services (`gitsummary/services`): Analyzer and Reporter orchestrations.
- LLM (`gitsummary/llm`): Provider registry, prompts, schemas.
- Infrastructure (`gitsummary/infrastructure`): Git plumbing, Git Notes storage.
- Tracing (`gitsummary/tracing.py`): Optional JSON traces in `.gitsummary/*.log`.

## Storage Layout
- Artifacts and release notes live in Git Notes (`refs/notes/intent`, `refs/notes/report/release-note`).
- Runtime config/traces live under `.gitsummary/` (ignored in git; config.yaml is kept).
- See `docs/storage_layout.md` for details.

## More Detail
- CLI design and rationale: `docs/cli_design.md`
- Project overview: `docs/project_summary.md`
- Future/roadmap: `docs/future_plans.md`
- Examples: `examples/release-note-latest.md`
