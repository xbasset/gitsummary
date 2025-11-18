# Repository Guidelines

## Project Structure & Module Organization
- `gitsummary/` is the CLI package; `cli.py` wires Typer commands, `git.py` wraps git plumbing, `artifact.py` builds facet payloads, `storage.py` persists artifacts, and `analyzers/` exposes renderable targets.
- Docs and design notes live in `docs/spec.md` and `workdir/*.md`; update these when changing artifact semantics or CLI behavior.
- Runtime artifacts are written under `.gitsummary/` (created on demand); keep the directory out of version control unless you need to inspect generated JSON.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` (or reuse the existing venv) to isolate dependencies.
- `pip install -r requirements.txt` installs Typer and other runtime dependencies.
- `python -m gitsummary --help` validates the CLI entry point after edits.
- `python -m gitsummary collect --tag v0.1.0 --tag v0.2.0` captures artifacts for a tag range; swap in real tags while developing.
- `python -m gitsummary analyze <ARTIFACT_ID> --target implementation` renders stored data; prefixes are accepted for convenience.

## Coding Style & Naming Conventions
- Target Python 3.10+ with complete type hints and dataclasses for structured payloads.
- Keep four-space indentation, `snake_case` functions, `CapWords` classes, and UPPER_SNAKE_CASE constants to match the current modules.
- Prefer small, pure helpers; raise `GitCommandError` for git failures and let Typer handle user-facing messaging.
- Maintain concise docstrings describing intent and keep CLI output stable for downstream tooling.

## Testing Guidelines
- There is no dedicated test harness yet; add one alongside new functionality.
- Favor deterministic tests around `artifact.build_artifact`, `storage.save_artifact`, and git wrappers (mock subprocess as needed).
- Place tests under `tests/` mirroring module names (e.g., `tests/test_storage.py`); integrate `pytest` or `unittest` and document any new dependencies.
- Run `pytest` (or the chosen runner) locally before submitting and include CLI smoke checks for critical paths.

## Commit & Pull Request Guidelines
- Follow the existing history: single-line, imperative summaries (`Refine CLI architecture and documentation`) with optional wrapped bodies at 72 columns.
- Reference related issues in commit bodies; separate mechanical refactors from behavioral changes.
- Pull requests should include a problem statement, testing notes, and sample CLI output or artifact excerpts when relevant.
- Keep branches scoped and rebase onto the latest main branch before requesting review.

## Artifact Storage Notes
- Use `StorageLayout` helpers instead of manual paths; `save_artifact` stamps schema and tool versions automatically.
- When altering artifact shape, bump `SCHEMA_VERSION`, regenerate supporting docs, and describe migration steps in `docs/spec.md`.

## Development Plan
- Use the `docs/TODO.md` file to guide the development process.
- Create / update the status in docs/current_development_status.md