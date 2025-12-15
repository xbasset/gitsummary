# Step 15: CI release notes without Git Notes writes

Date: 2025-12-15

## Problem

The GitHub Actions workflow that generates release notes should not mutate the repository by:
- committing files back into the git tree, or
- creating new Git Notes entries during CI.

At the same time, CI should benefit from artifacts computed by developers locally and persisted in Git Notes.

## Key assumption (validated)

Artifacts are stored in Git Notes under `refs/notes/intent` (and release notes under `refs/notes/report/release-note`).

However, a standard CI checkout does not reliably include notes refs. To reuse artifacts in CI, the workflow must explicitly fetch them:

```bash
git fetch origin refs/notes/intent:refs/notes/intent
```

This is read-only with respect to the remote: it enables consumption of existing notes without pushing new ones.

## Design decision

Introduce a CI-focused command that:
- reads existing artifacts from Git Notes (read-only),
- computes missing artifacts in-memory (no `git notes add`),
- synthesizes release notes to a markdown/text document,
- writes the output outside the repo tree (e.g., `$RUNNER_TEMP`) and uploads it as a workflow artifact.

This keeps Git Notes as the canonical store, while ensuring CI does not create or modify notes.

## CLI surface

New command:

```bash
gitsummary ci release-notes <range> --output <file>
```

Key flags:
- `--compute-missing/--no-compute-missing`
- `--reanalyze-existing`
- `--llm/--no-llm`, `--provider`, `--model`

## Workflow responsibilities

- Fetch notes refs read-only to maximize reuse.
- Run `gitsummary ci release-notes ...` to produce a markdown file.
- Upload the markdown as a workflow artifact.
- Update the GitHub Release body from the generated markdown.

## Non-goals

- No filesystem caching fallback for CI beyond Git Notes reuse.
- No committing release notes back into the repository.

