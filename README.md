# gitsummary

Release notes in one line: `gitsummary release-note latest` builds and displays release notes for your latest tag, re-analyzing commits if needed (`--reanalyze`) or staying offline (`--no-llm`).

## Why
- Understand *why* code changed and *who* it affects, not just which lines moved.
- Store semantic artifacts in Git Notes (default) or Postgres for shared storage.
- Generate release notes, changelogs, and impact summaries on demand.

## Quickstart
```bash
# Install (use a virtualenv)
pip install -r requirements.txt

# Get help
python -m gitsummary --help

# One-liner release notes for the latest tag
gitsummary release-note latest

# Force fresh analysis or stay offline
gitsummary release-note latest --reanalyze
gitsummary release-note latest --no-llm
```

## Core commands
- Analyze commits: `gitsummary analyze <range> [--dry-run] [--no-llm]`
- One-shot release notes: `gitsummary release-note latest [--reanalyze] [--no-llm]`
- Changelog: `gitsummary generate changelog <range> [--format json]`
- Show stored artifacts/notes: `gitsummary show <commit>` / `gitsummary show release-note <rev>`
- List commit analysis status: `gitsummary list <range> [--missing]`

## Docs
- Start here: `docs/index.md` (orientation, commands, architecture map)
- CLI design and usage: `docs/cli_design.md`
- Storage layout: `docs/storage_layout.md`
- Install/update: `docs/install_update.md`

## Contributing & license
- Contributions welcome — see `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.
- Security reports: `SECURITY.md`.
- License: MIT (see `LICENSE`).
