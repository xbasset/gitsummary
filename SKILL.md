# gitsummary Usage (SKILL)
Exhaustive usage guide for the **gitsummary** CLI. Focus: how to run it, what each command does, options, outputs, storage, and common workflows.
## TL;DR
```bash
# One-liner release notes for latest tag
 gitsummary release-note latest
# Analyze a range and generate a changelog
 gitsummary analyze v1.0.0..v1.1.0
 gitsummary generate changelog v1.0.0..v1.1.0 -o CHANGELOG.md
```
## What gitsummary does
**Goal:** turn raw commits into **semantic artifacts** (intent, impact, behavior change), store them in **Git Notes**, and generate release notes/changelogs on demand.

**Two-phase model:**
1. **Analyze** commits -> store `CommitArtifact` in Git Notes (`refs/notes/intent`).
2. **Generate** reports from stored artifacts (release notes, changelog, impact, HTML feed).
## Installation / Run
From source (this repo):
```bash
pip install -r requirements.txt
pip install -e .
# or run without install
python -m gitsummary --help
```

Verify:
```bash
gitsummary --version
# gitsummary X.Y.Z
# Schema version: 0.1.0
```
## Revision ranges (input syntax)
gitsummary accepts any Git revision or range that `git rev-list` accepts:
- Single commit SHA: `abc1234`
- Tag: `v1.2.3`
- Branch: `main`
- Range: `v1.2.2..v1.2.3`, `main~10..main`

**Ordering:** commands operate on commits **newest -> oldest**.
## Storage model (Git Notes)
Artifacts and reports are stored as Git Notes so they travel with the repo when notes are pushed/fetched.

**Namespaces:**
- Commit artifacts: `refs/notes/intent`
- Release notes: `refs/notes/report/release-note`

**Override artifact ref:**
- `GITSUMMARY_NOTES_REF` changes the commit-artifact namespace (default `refs/notes/intent`).

**View raw notes:**
```bash
# Commit artifact
 git notes --ref=intent show <commit>
# Release note
 git notes --ref=refs/notes/report/release-note show <commit>
```

**Share notes:**
```bash
# Push/pull artifacts
 git push origin refs/notes/intent
 git fetch origin refs/notes/intent:refs/notes/intent
# Push/pull release notes
 git push origin refs/notes/report/release-note
 git fetch origin refs/notes/report/release-note:refs/notes/report/release-note
```

**Example artifact (YAML in Git Notes):**
```yaml
commit_hash: a1b2c3d4...
intent_summary: Fix null pointer in login flow
category: fix
behavior_before: Users could not log in when...
behavior_after: Login now validates...
impact_scope: internal
is_breaking: false
technical_highlights:
  - Added null check in AuthService.validate()
  - Added unit test for edge case
confidence_score: 0.95
schema_version: 0.1.0
tool_version: 0.2.0
```
## Global command entry points
```bash
# Standard CLI
 gitsummary --help
 gitsummary --version
 gitsummary version
# Python module
 python -m gitsummary --help
```
## Command reference (exhaustive)
### 1) `gitsummary analyze`
**Purpose:** analyze commits -> store artifacts in Git Notes.

**Synopsis:**
```bash
gitsummary analyze <revision-range|commit>
```

**Options:**
- `--dry-run` : print artifacts, do not store in notes
- `--json` : JSON output (implies `--dry-run`)
- `--force, -f` : overwrite existing notes
- `--reanalyze-existing` : re-run analysis even if artifact exists
- `--verbose, -v` : print detailed errors
- `--llm/--no-llm` : enable/disable LLM analysis
- `--provider, -p <name>` : LLM provider (openai, anthropic, ollama)
- `--model, -m <model>` : provider-specific model override

**Behavior notes:**
- Default: uses LLM if available; falls back to heuristic when `--no-llm`.
- Existing artifacts are skipped unless `--reanalyze-existing` or `--force` is set.
- `--force` is required to overwrite stored notes.

**Examples:**
```bash
# Analyze last 5 commits (default LLM)
 gitsummary analyze HEAD~5..HEAD
# Heuristic only
 gitsummary analyze HEAD --no-llm
# Preview without writing notes
 gitsummary analyze v1.0.0..v1.1.0 --dry-run
# JSON preview
 gitsummary analyze v1.0.0..v1.1.0 --dry-run --json
# Force overwrite
 gitsummary analyze v1.0.0..v1.1.0 --force
```
### 2) `gitsummary list`
**Purpose:** list commits and their analysis status.

**Synopsis:**
```bash
gitsummary list <revision-range>
```

**Options:**
- `--analyzed` : only commits with artifacts
- `--missing` : only commits without artifacts
- `--count` : totals only
- `--json` : JSON output
- `--date` : absolute timestamps (default = relative)

**Examples:**
```bash
# Range overview
 gitsummary list v1.0.0..v1.1.0
# Missing artifacts
 gitsummary list main..HEAD --missing
# Counts for CI
 gitsummary list HEAD~20..HEAD --count --json
```
### 3) `gitsummary show commit`
**Purpose:** show stored artifacts for commits.

**Synopsis:**
```bash
gitsummary show commit <revision-or-range>
```

**Options:**
- `--json` : JSON output
- `--yaml` : raw YAML
- `--brief` : one-line per commit
- `--field <name>` : only specific field

**Examples:**
```bash
# Single commit
 gitsummary show commit HEAD
# Range, brief
 gitsummary show commit v1.0.0..v1.1.0 --brief
# Extract one field
 gitsummary show commit abc123 --field intent_summary
```
### 4) `gitsummary show release-note`
**Purpose:** show stored release note attached to a revision/tag.

**Synopsis:**
```bash
gitsummary show release-note <revision>
```

**Options:**
- `--format, -f markdown|yaml|text`

**Examples:**
```bash
# Show stored release note for a tag
 gitsummary show release-note v1.1.0
# YAML format
 gitsummary show release-note v1.1.0 --format yaml
```
### 5) `gitsummary generate changelog`
**Purpose:** build changelog from stored artifacts.

**Synopsis:**
```bash
gitsummary generate changelog <revision-range>
```

**Options:**
- `--format, -f markdown|json|text`
- `--output, -o <file>`
- `--include-unanalyzed` : include commits without artifacts

**Examples:**
```bash
# Markdown changelog
 gitsummary generate changelog v1.0.0..v1.1.0
# JSON for CI
 gitsummary generate changelog v1.0.0..v1.1.0 --format json
# Write to file
 gitsummary generate changelog v1.0.0..v1.1.0 -o CHANGELOG.md
```
### 6) `gitsummary generate release-notes`
**Purpose:** user-facing release notes from analyzed artifacts.

**Synopsis:**
```bash
gitsummary generate release-notes <revision-range>
```

**Options:**
- `--format, -f markdown|yaml|text`
- `--output, -o <file>`
- `--llm/--no-llm`
- `--provider, -p <name>`
- `--model, -m <model>`
- `--product <name>` : header product name (default repo name)
- `--version, -v <version>` : header version (default range end)
- `--store` : store the release note in Git Notes

**Examples:**
```bash
# LLM synthesis (default)
 gitsummary generate release-notes v1.0.0..v1.1.0
# Heuristic-only
 gitsummary generate release-notes v1.0.0..v1.1.0 --no-llm
# Store in Git Notes for later retrieval
 gitsummary generate release-notes v1.0.0..v1.1.0 --store
```
### 7) `gitsummary generate impact`
**Purpose:** technical impact summary for reviewers.

**Synopsis:**
```bash
gitsummary generate impact <revision-range>
```

**Options:**
- `--format, -f markdown|json`
- `--output, -o <file>`

**Examples:**
```bash
 gitsummary generate impact HEAD~20..HEAD
 gitsummary generate impact HEAD~20..HEAD --format json
```
### 8) `gitsummary generate feed`
**Purpose:** HTML feed of artifacts for browsing.

**Synopsis:**
```bash
gitsummary generate feed <revision-range>
```

**Options:**
- `--output, -o <file>` : default is `<project>-feed.html` in repo root
- `--skip-unanalyzed` : hide missing artifacts (default shows CTAs)
- `--open` : open in browser

**Examples:**
```bash
# Build feed and open browser
 gitsummary generate feed v1.0.0..v1.1.0 --open
# Custom output path
 gitsummary generate feed v1.0.0..v1.1.0 -o /tmp/feed.html
```
### 9) `gitsummary release-note latest`
**Purpose:** end-to-end flow for latest tag (analyze missing -> generate -> store -> HTML).

**Synopsis:**
```bash
gitsummary release-note latest
```

**Options:**
- `--yes, -y` : skip prompts
- `--no-fetch` : skip `git fetch --tags`
- `--output-dir, -o <dir>` : HTML output directory (default `release-notes/`)
- `--no-open` : do not open HTML
- `--llm/--no-llm`
- `--reanalyze` : re-run analysis even if artifacts exist
- `--provider, -p <name>`
- `--model, -m <model>`

**Behavior notes:**
- Picks latest tag by date; previous tag defines range start (or repo root).
- Stores release note in Git Notes (`refs/notes/report/release-note`).
- Writes HTML to `release-notes/<tag>.html` (prompts to create folder).
- If a release note already exists and `--reanalyze` is not set, it prints the stored note instead of regenerating.

**Example:**
```bash
# Fast heuristic run
 gitsummary release-note latest --no-llm
# Force fresh analysis with LLM
 gitsummary release-note latest --reanalyze --llm
```
### 10) `gitsummary init github-release-notes`
**Purpose:** scaffold GitHub Actions workflow that generates release notes on every GitHub Release.

**Synopsis:**
```bash
gitsummary init github-release-notes
```

**Options:**
- `--yes, -y` : non-interactive, fail if required values missing
- `--force, -f` : overwrite existing workflow file
- `--openai-key-env <name>` : env var name for OpenAI key (default `OPENAI_API_KEY`)
- `--workflow-path <path>` : custom workflow file path

**What it writes:**
- `.github/workflows/gitsummary-release-notes.yml`
- Uses `gitsummary ci release-notes` and `gh release edit` to update the release body

**Example:**
```bash
 gitsummary init github-release-notes
 git add .github/workflows/gitsummary-release-notes.yml
 git commit -m "chore: enable gitsummary release notes"
```
### 11) `gitsummary ci release-notes`
**Purpose:** CI-safe release notes generation (no Git Notes writes).

**Synopsis:**
```bash
gitsummary ci release-notes <revision-range>
```

**Options:**
- `--format, -f markdown|text`
- `--output, -o <file>`
- `--compute-missing/--no-compute-missing` : in-memory artifacts
- `--reanalyze-existing` : recompute artifacts even if notes exist (in-memory)
- `--llm/--no-llm`
- `--provider, -p <name>`
- `--model, -m <model>`
- `--product <name>`
- `--version, -v <version>`

**Examples:**
```bash
# CI markdown output
 gitsummary ci release-notes v1.0.0..v1.1.0 -o /tmp/release-notes.md
# Heuristic only
 gitsummary ci release-notes v1.0.0..v1.1.0 --no-llm
```
### 12) `gitsummary version`
**Purpose:** show tool and schema versions.

**Synopsis:**
```bash
gitsummary version
 gitsummary --version
```
## LLM configuration (providers, keys)
**Provider selection:**
- CLI: `--provider` / `--model`
- Env: `GITSUMMARY_PROVIDER`, `GITSUMMARY_MODEL`

**Model selection (provider-specific):**
- Env override: `GITSUMMARY_<PROVIDER>_MODEL` (e.g., `GITSUMMARY_OPENAI_MODEL`)
- Config keys: `DEFAULT_PROVIDER`, `<PROVIDER>_MODEL` in `~/.config/gitsummary/config`

**API key resolution order:**
1. Provider-specific environment variables
2. `.env` in repo or cwd (if `python-dotenv` is installed)
3. `~/.config/gitsummary/config` (key=value format)
4. Legacy `~/.gitsummary`
5. Interactive prompt (when applicable)

**Provider env vars (supported by config):**
- OpenAI: `OPENAI_API_KEY`, `GITSUMMARY_OPENAI_KEY`
- Anthropic: `ANTHROPIC_API_KEY`, `GITSUMMARY_ANTHROPIC_KEY`
- Mistral: `MISTRAL_API_KEY`, `GITSUMMARY_MISTRAL_KEY`

**Registered providers:** `openai`, `anthropic`, `ollama`

**Examples:**
```bash
# Use OpenAI with explicit model
 GITSUMMARY_PROVIDER=openai GITSUMMARY_MODEL=gpt-5.1 \
 gitsummary analyze HEAD~3..HEAD
# Use Anthropic
 GITSUMMARY_PROVIDER=anthropic \
 gitsummary generate release-notes v1.0.0..v1.1.0
```
## Tracing & runtime files
By default, gitsummary writes JSON trace logs for each CLI run:
- Directory: `.gitsummary/` (in repo root)
- Files: `.gitsummary/*.log`

**Disable tracing:**
```bash
GITSUMMARY_TRACING_ENABLED=0 gitsummary list HEAD~5..HEAD
```

**Config file:** `.gitsummary/config.yaml`
```yaml
tracing:
  enabled: true
```
## Practical workflows
### A) Analyze a release range and generate notes
```bash
 gitsummary list v1.0.0..v1.1.0 --count
 gitsummary analyze v1.0.0..v1.1.0
 gitsummary generate release-notes v1.0.0..v1.1.0 -o RELEASE_NOTES.md
```
### B) Incremental analysis only for missing commits
```bash
 gitsummary list main..HEAD --missing
 gitsummary analyze main..HEAD
```
### C) Latest tag release notes (HTML + Git Notes)
```bash
 gitsummary release-note latest
```
### D) CI release notes without Git Notes writes
```bash
 gitsummary ci release-notes v1.0.0..v1.1.0 -o $RUNNER_TEMP/release-notes.md
```
## Troubleshooting
**No commits found**
```bash
 git log --oneline v1.0.0..v1.1.0
```

**Not a git repository**
```bash
 git status
```

**Artifacts missing**
```bash
 gitsummary list <range> --missing
 gitsummary analyze <range>
 git notes --ref=intent list
```

**Release note exists but not updating**
```bash
 gitsummary release-note latest --reanalyze
```
## Quick command index
| Command | Purpose |
|---|---|
| `gitsummary analyze <range>` | Analyze commits -> Git Notes artifacts |
| `gitsummary list <range>` | List commits + analysis status |
| `gitsummary show commit <rev>` | Show stored artifact(s) |
| `gitsummary generate changelog <range>` | Changelog from artifacts |
| `gitsummary generate release-notes <range>` | Release notes from artifacts |
| `gitsummary generate impact <range>` | Impact report |
| `gitsummary generate feed <range>` | HTML artifact feed |
| `gitsummary release-note latest` | End-to-end latest release notes |
| `gitsummary init github-release-notes` | GitHub Release automation |
| `gitsummary ci release-notes <range>` | CI-safe release notes |
| `gitsummary show release-note <rev>` | Show stored release note |
| `gitsummary version` | Version info |
