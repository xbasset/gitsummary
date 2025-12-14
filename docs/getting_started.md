# Getting Started with gitsummary

A step-by-step guide to install gitsummary from source and test it on any Git repository.

---

## Automate release notes on every GitHub Release

Release notes often fail for boring reasons: they’re manual, easy to forget, and hard to keep consistent.
If you ship via GitHub Releases, gitsummary can automate release notes in a way that’s easy to review:

- **Setup**: run `gitsummary init github-release-notes`, then add the `OPENAI_API_KEY` GitHub Actions secret.
- **On every Release publish**:
  - Generates `release-notes/<tag>.md`
  - Updates the **GitHub Release body**
  - Opens a **PR** that commits the markdown file

### Quick setup

From the repo you want to onboard:

```bash
gitsummary init github-release-notes
git add .github/workflows/gitsummary-release-notes.yml release-notes/README.md
git commit -m "chore: enable automated release notes"
git push
```

Then add the required secret:
- GitHub UI: Settings → Secrets and variables → Actions → New repository secret
  - Name: `OPENAI_API_KEY`
  - Value: your OpenAI API key

Optional CLI (if you use `gh`):

```bash
gh secret set OPENAI_API_KEY --body "<your-key>"
```

After that, publish a GitHub Release (UI or `gh release create ...`). The workflow triggers on **Release published** and does the rest.

---

## Prerequisites

- **Python 3.10+** — Check with `python3 --version`
- **Git** — Any recent version
- A Git repository with some commit history to analyze

---

## Step 1: Clone and Install

```bash
# Clone the repository (or use your local copy)
git clone https://github.com/yourusername/gitsummary.git
cd gitsummary

# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode (makes `gitsummary` command available)
pip install -e .
```

**Verify installation:**

```bash
gitsummary --version
# Expected output:
# gitsummary 0.2.0
# Schema version: 0.2.0
```

Or run without installing:

```bash
python -m gitsummary --version
```

---

## Step 2: Navigate to Your Target Repository

```bash
# Go to the repository you want to analyze
cd /path/to/your/repository

# Verify you're in a git repository
git status
```

---

## Step 3: Explore Available Commands

```bash
# Show all commands
gitsummary --help
```

**Expected output:**

```
 Usage: gitsummary [OPTIONS] COMMAND [ARGS]...

 Summarize git changes into durable semantic artifacts.

╭─ Options ─────────────────────────────────────────────────────────────────────╮
│ --version  -V        Show version and exit.                                   │
│ --help               Show this message and exit.                              │
╰───────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ────────────────────────────────────────────────────────────────────╮
│ analyze   Extract semantic understanding from commits and store as artifacts. │
│ generate  Generate reports from analyzed artifacts.                           │
│ init      Bootstrap gitsummary automation in a repository.                    │
│ list      List commits and their analysis status.                             │
│ show      Display artifacts or stored reports.                          │
│ version   Print version information.                                          │
╰───────────────────────────────────────────────────────────────────────────────╯
```

---

## Step 4: List Commits in a Range

Before analyzing, explore what commits are in your target range.

```bash
# List commits between two tags
gitsummary list v1.0.0..v1.1.0

# List commits on current branch not in main
gitsummary list main..HEAD

# List last 10 commits
gitsummary list HEAD~10..HEAD

# Show only the count
gitsummary list HEAD~5..HEAD --count

# Show absolute dates instead of relative
gitsummary list HEAD~5..HEAD --date
```

**Example output (default, with relative dates):**

```
Commits in HEAD~5..HEAD (5 total, 0 analyzed)

○ a1b2c3d   3d Add new feature
○ d4e5f6g   5d Fix bug in parser
○ h7i8j9k  2mo Update documentation
○ l0m1n2o  3mo Refactor utils
○ p3q4r5s   1y Initial commit
```

**With `--date` flag (absolute dates):**

```
Commits in HEAD~5..HEAD (5 total, 0 analyzed)

○ a1b2c3d 2025-11-25 14:30 Add new feature
○ d4e5f6g 2025-11-23 10:15 Fix bug in parser
○ h7i8j9k 2025-09-15 09:00 Update documentation
```

- `○` means "not analyzed yet"
- `✓` means artifact exists
- Date format: `3d` = 3 days ago, `2mo` = 2 months ago, `1y` = 1 year ago

---

## Step 5: Analyze Commits (Dry Run First)

**Always preview with `--dry-run` before storing artifacts:**

```bash
# Preview analysis without storing (outputs YAML)
gitsummary analyze HEAD~3..HEAD --dry-run

# Preview as JSON
gitsummary analyze HEAD~3..HEAD --dry-run --json
```

**Example dry-run output:**

```yaml
commit_sha: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
summary: Add new feature for user authentication
intent: ENHANCEMENT
impact: MODERATE
behavior_change: true
facets:
  affected_components:
    - auth/login.py
    - auth/session.py
  keywords:
    - authentication
    - security
    - login
meta:
  gitsummary_version: 0.2.0
  schema_version: 0.2.0
  analyzed_at: 2025-01-15T10:30:00Z
  extractor: heuristic
---
```

---

## Step 6: Analyze and Store Artifacts

Once satisfied with the dry-run, analyze and store:

```bash
# Analyze and store in Git Notes
gitsummary analyze HEAD~3..HEAD
```

**Expected output:**

```
Analyzing 3 commit(s) in HEAD~3..HEAD...
  ✓ a1b2c3d Add new feature for user authentication
  ✓ d4e5f6g Fix bug in parser validation
  ✓ h7i8j9k Update documentation for API

Summary: 3 analyzed, 0 skipped, 0 errors
Artifacts stored in refs/notes/intent
```

---

## Step 7: Verify Artifacts Were Stored

```bash
# List commits again — should show ✓ now
gitsummary list HEAD~3..HEAD

# Show artifact for a specific commit
gitsummary show HEAD

# Show a stored release note attached to a tip commit/tag
gitsummary show release-note v1.1.0

# Show as JSON
gitsummary show HEAD --json

# Show as YAML
gitsummary show HEAD --yaml

# Show brief one-liner
gitsummary show HEAD~3..HEAD --brief
```

**Example `show` output:**

```
Commit: a1b2c3d (Add new feature for user authentication)

Intent:    ENHANCEMENT
Impact:    MODERATE
Behavior:  Breaking change

Components:
  • auth/login.py
  • auth/session.py

Keywords: authentication, security, login

─────────────────────────────────────────────────────
Analyzed: 2025-01-15T10:30:00Z (heuristic)
Schema: 0.2.0
```

---

## Step 8: Generate Reports

```bash
# Generate a changelog
gitsummary generate changelog HEAD~5..HEAD

# Generate release notes (LLM by default; use --no-llm to disable)
gitsummary generate release-notes v1.0.0..v1.1.0

# Generate impact summary
gitsummary generate impact HEAD~10..HEAD

# Output to file
gitsummary generate changelog HEAD~5..HEAD -o CHANGELOG.md

# Output as JSON (for CI pipelines)
gitsummary generate changelog HEAD~5..HEAD --format json
```

Release notes are stored in Git Notes under `refs/notes/report/release-note` when you pass `--store`.

---

## Common Workflows

### Workflow A: Analyze a Release Range

```bash
# 1. See what's in the release
gitsummary list v1.0.0..v1.1.0 --count

# 2. Preview analysis
gitsummary analyze v1.0.0..v1.1.0 --dry-run

# 3. Run analysis
gitsummary analyze v1.0.0..v1.1.0

# 4. Generate release notes
gitsummary generate release-notes v1.0.0..v1.1.0 -o RELEASE_NOTES.md
```

### Workflow B: Incremental Analysis

```bash
# Find commits that haven't been analyzed
gitsummary list main..HEAD --missing

# Analyze only the missing ones (already the default behavior)
gitsummary analyze main..HEAD
```

### Workflow C: Force Re-analysis

```bash
# Re-analyze even if artifacts exist
gitsummary analyze HEAD~3..HEAD --force
```

---

## Where Are Artifacts Stored?

Artifacts are stored in **Git Notes** under `refs/notes/intent`. This means:

- They're part of your Git repository
- They travel with the repo when pushed (if you push notes)
- They're tied to specific commit SHAs

**View raw notes:**

```bash
# See the note for a commit
git notes --ref=intent show HEAD

# List all notes
git notes --ref=intent list
```

**Push notes to remote:**

```bash
git push origin refs/notes/intent
```

---

## Troubleshooting

### "No commits found in the specified range"

- Verify your revision range is valid: `git log --oneline v1.0..v1.1`
- Check tag names: `git tag -l`

### "Error: Not a git repository"

- Make sure you're inside a git repository
- Run `git status` to verify

### Artifacts not showing up

- Check if notes exist: `git notes --ref=intent list`
- Run with `--verbose` for more details: `gitsummary analyze ... --verbose`

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `gitsummary list <range>` | List commits with relative dates (default) |
| `gitsummary list <range> --date` | List commits with absolute dates |
| `gitsummary list <range> --missing` | Show only un-analyzed commits |
| `gitsummary analyze <range> --dry-run` | Preview without storing |
| `gitsummary analyze <range>` | Analyze and store artifacts |
| `gitsummary analyze <range> --force` | Re-analyze existing artifacts |
| `gitsummary show <commit>` | Display artifact for a commit |
| `gitsummary show <range> --brief` | One-line summary per commit |
| `gitsummary generate changelog <range>` | Generate changelog |
| `gitsummary generate impact <range>` | Generate impact report |
| `gitsummary generate release-notes <range>` | Generate release notes |
| `gitsummary show release-note <rev>` | Show stored release note for a commit/tag |

---

## Next Steps

- Read `docs/cli_design.md` for full command reference
- Check `docs/storage_layout.md` for artifact schema details
- See `docs/project_summary.md` for architectural overview
