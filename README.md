# **gitsummary — Let Your Codebase Explain Itself**

**For Release Managers and teams who need to understand what happened.**

You have a range of 500 commits between `v1.0` and `v1.1`. The commit messages are a mix of "fix typo", "wip", and "update logic". You need to write accurate release notes and assess the risk of this deployment.

Reading raw `git log` and `git diff` is noise. You don't need to know *which lines* changed; you need to know *why* they changed and *what impact* they have on users.

**gitsummary** solves this by acting as an **Automated Historian**.

1.  **It Reads:** It scans your raw git history (offline, no GitHub/GitLab APIs needed).
2.  **It Understands:** It uses LLMs to reverse-engineer the "Intent" and "Impact" behind the code changes.
3.  **It Remembers:** It stores this semantic understanding as durable **Artifacts** directly in your repo (using Git Notes).
4.  **It Reports:** It generates clear, human-readable Release Notes and Change Summaries on demand.

---

## Installation

The project is intentionally lightweight and has no packaging metadata yet. Install the runtime dependencies and execute directly from the repository:

```bash
pip install -r requirements.txt  # optional if Typer not yet available
python -m gitsummary --help
```

## Usage

### 1. Build the History (The Historian)

```bash
gitsummary collect --tag v0.1.0 --tag v0.2.0
```
*Fetches pure-git facts, infers intent/impact, and stores a semantic artifact in `.gitsummary/` (and eventually Git Notes).*

### 2. Generate the Report (The Release Note)

```bash
gitsummary analyze <ARTIFACT_ID> --target release-notes
```
*Reads the stored artifact and outputs a structured Markdown report describing features, fixes, and breaking changes.*

## Development

- **Status:** Early Development (Step 1: Grounding & Constraints)
- **Focus:** Release Manager use case.
- **Docs:** See `docs/project_summary.md` for architectural vision.
