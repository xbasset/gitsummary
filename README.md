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

### 1. Analyze Commits (Build Understanding)

```bash
gitsummary analyze v1.0..v2.0
```
*Reads commits in the range, uses LLM to extract semantic understanding (intent, impact, behavior changes), and stores artifacts in Git Notes.*

```bash
# Preview without storing
gitsummary analyze v1.0..v2.0 --dry-run

# Force re-analysis of existing artifacts
gitsummary analyze v1.0..v2.0 --force
```

### 2. Generate Reports (Create Documents)

```bash
gitsummary generate changelog v1.0..v2.0
```
*Reads stored artifacts and produces a formatted changelog.*

```bash
# Release notes (LLM by default; use --no-llm to skip)
gitsummary generate release-notes v1.0..v2.0 -o RELEASE_NOTES.md --store

# Impact summary
gitsummary generate impact v1.0..v2.0

# Generate JSON for CI pipelines
gitsummary generate changelog v1.0..v2.0 --format json
```

### 3. Inspect and Discover

```bash
# Show artifact for a single commit
gitsummary show abc123

# List commits with their analysis status (relative dates by default)
gitsummary list v1.0..v2.0

# List with absolute dates
gitsummary list v1.0..v2.0 --date

# Find commits that need analysis
gitsummary list v1.0..v2.0 --missing

# Show stored release notes for a revision (tip commit/tag)
gitsummary show release-note v2.0
```

## The Two-Phase Model

```
Raw Git Data  ──[analyze]──▶  Semantic Artifacts  ──[generate]──▶  Reports
   (noise)                      (understanding)                  (documents)
```

- **`analyze`**: Expensive (LLM), runs once per commit, stores durable artifacts
- **`generate`**: Cheap, runs from cached artifacts, produces multiple formats

## Development

- **Status:** Active development (LLM-assisted release notes shipped).
- **Focus:** Release Manager use case.
- **Docs:** See `docs/project_summary.md` and `docs/cli_design.md` for architecture and CLI reference.

## Development Commands

```bash
# Validate CLI entry point
python -m gitsummary --help

# Run analysis (once implemented)
python -m gitsummary analyze v0.1.0..v0.2.0

# Generate changelog
python -m gitsummary generate changelog v0.1.0..v0.2.0

# Generate release notes and store to Git Notes (refs/notes/report/release-note)
python -m gitsummary generate release-notes v0.1.0..v0.2.0 --store
```
