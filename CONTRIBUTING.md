# Contributing to gitsummary

Thanks for helping improve gitsummary! This project aims to stay lightweight and easy to understand.

## How to contribute
- File issues for bugs or small enhancements with repro steps or sample commands.
- For code changes, prefer small PRs with a short description and before/after behavior.
- Follow existing style: Python 3.10+, type hints, four-space indents.
- Keep CLI output stable; add a note if output changes.

## Development setup
- Use a virtualenv: `python -m venv .venv && source .venv/bin/activate`.
- Install deps: `pip install -r requirements.txt` (and `requirements-dev.txt` if you need extra tooling).
- Run tests: `pytest` (add targeted tests for new behavior).
- Smoke test: `python -m gitsummary --help` and try `gitsummary analyze HEAD~1..HEAD --dry-run`.

## Commit/PR guidelines
- Commit messages: short, imperative summaries.
- Add tests when possible, especially for storage, tracing, and CLI argument parsing.
- Note any breaking behavior or CLI output changes in the PR description.

## Code of Conduct
Be kind and constructive. See `CODE_OF_CONDUCT.md` for details.
