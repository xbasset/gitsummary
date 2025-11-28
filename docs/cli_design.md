# CLI Design Specification
Version: 0.1.0
Date: 2025-11-27

## Overview
This document specifies the command-line interface for **gitsummary**. The CLI enables Release Managers and developers to extract, store, and query semantic information about git commits.

## Design Philosophy: Analyze → Generate

### The Two-Phase Model
gitsummary operates in two distinct phases, reflected in its command naming:

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: ANALYZE                                               │
│  ─────────────────                                              │
│  Input:  Git commits (messages, diffs, metadata)                │
│  Action: LLM extracts semantic understanding                    │
│  Output: CommitArtifact stored in Git Notes                     │
│                                                                 │
│  Command: gitsummary analyze v1.0..v2.0                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 2: GENERATE                                              │
│  ─────────────────                                              │
│  Input:  Stored artifacts from Git Notes                        │
│  Action: Aggregate and format for specific output               │
│  Output: Changelog, release notes, or other reports             │
│                                                                 │
│  Command: gitsummary generate changelog v1.0..v2.0              │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Naming?

| Term | Meaning | Industry Precedent |
|------|---------|-------------------|
| `analyze` | Extract semantic understanding from raw data | semantic-release, static analyzers |
| `generate` | Produce formatted output from analyzed data | git-cliff, git-chglog, docgen tools |

**Rationale for choosing `analyze` over alternatives:**
- ❌ `collect` — Too vague; implies gathering without understanding
- ❌ `index` — Suggests search/retrieval, not semantic extraction
- ❌ `annotate` — Conflicts with `git annotate` (alias for blame)
- ✅ `analyze` — Clear, industry-standard, implies intelligent processing

**Rationale for choosing `generate` over alternatives:**
- ❌ `render` — Too technical, implies template processing
- ❌ `export` — Implies data format conversion, not document creation
- ❌ `report` — Noun, not verb; less action-oriented
- ✅ `generate` — Standard for changelog tools (git-cliff, conventional-changelog)

### Benefits of Two-Phase Separation

1. **Cost Efficiency**: LLM analysis is expensive; analyze once, generate many reports
2. **Cacheability**: Artifacts persist in Git Notes; regenerating reports is cheap
3. **Shareability**: Analyzed artifacts travel with the repo via `git push/fetch`
4. **Flexibility**: Same artifacts → changelog, release notes, impact report, etc.

---

## Installation
```bash
pip install gitsummary
# or
pipx install gitsummary
```

## Global Options
```
--help, -h      Show help message
--version       Show version number
--verbose, -v   Enable verbose output
--quiet, -q     Suppress non-essential output
```

---

## Commands

### `gitsummary analyze`
**Purpose:** Extract semantic understanding from commits and store as artifacts.

This is the **core command** that makes gitsummary valuable. It reads git data (commits, diffs, messages) and uses LLM to extract:
- Intent (why was this change made?)
- Behavior change (before/after)
- Impact scope (public API, internal, config, etc.)
- Breaking change detection
- Technical highlights

**Synopsis:**
```bash
gitsummary analyze <revision-range>
gitsummary analyze <commit>
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `<revision-range>` | Git revision range (e.g., `v1.0..v2.0`, `main~5..main`) |
| `<commit>` | Single commit SHA or reference |

**Options:**
| Option | Description |
|--------|-------------|
| `--dry-run` | Print artifacts in default YAML format without storing in Git Notes |
| `--force, -f` | Overwrite existing artifacts |
| `--json` | Output as JSON (implies `--dry-run`) |
| `--reanalyze-existing` | Re-analyze commits with existing artifacts (default to false) |

**Description:**
Resolves the given range to individual commits, generates a `CommitArtifact` for each using LLM analysis, and stores the result in the `refs/notes/intent` Git Notes namespace.

**Examples:**
```bash
# Analyze all commits between two tags
gitsummary analyze v1.0..v2.0

# Analyze a single commit
gitsummary analyze abc123

# Preview analysis without storing
gitsummary analyze v1.0..v2.0 --dry-run

# Force re-analysis of existing artifacts
gitsummary analyze v1.0..v2.0 --force
```

**Output:**
```
Analyzing 15 commits in v1.0..v2.0...
  ✓ abc1234 Fix null pointer in login flow
  ✓ def5678 Add user preferences API
  ⊘ 111aaaa (existing, skipped)
  ✓ 222bbbb Bump dependencies
  ...

Summary: 12 analyzed, 3 skipped, 0 errors
Artifacts stored in refs/notes/intent
```

**Exit Codes:**
| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Partial failure (some commits failed) |
| `2` | Invalid input (bad range, not in git repo) |

---

### `gitsummary generate`
**Purpose:** Create formatted reports from stored artifacts.

Takes analyzed artifacts and produces human-readable documents for different use cases.

**Synopsis:**
```bash
gitsummary generate <report-type> <revision-range>
gitsummary generate <report-type> --all
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `<report-type>` | Type of report: `changelog`, `release-notes`, `impact` |
| `<revision-range>` | Git revision range to include in report |

**Report Types:**
| Type | Description |
|------|-------------|
| `changelog` | Conventional changelog format (features, fixes, breaking) |
| `release-notes` | User-facing release notes with context |
| `impact` | Technical impact analysis for reviewers |

**Options:**
| Option | Description |
|--------|-------------|
| `--format <fmt>` | Output format: `markdown` (default), `json`, `text` |
| `--output, -o <file>` | Write to file instead of stdout |
| `--include-unanalyzed` | Include commits without artifacts (as placeholders) |

**Examples:**
```bash
# Generate changelog for a release
gitsummary generate changelog v1.0..v2.0

# Generate release notes to file
gitsummary generate release-notes v1.0..v2.0 -o RELEASE_NOTES.md

# Generate JSON for CI pipelines
gitsummary generate changelog v1.0..v2.0 --format json
```

**Output (changelog, markdown):**
```markdown
# Changelog v1.0..v2.0

## Features
- **Add user preferences API** (def5678)
  Introduces new endpoint for user settings management.

## Fixes
- **Fix null pointer in login flow** (abc1234)
  Users could not login if credentials were missing.

## Breaking Changes
None in this release.

## Other
- Bump dependencies (222bbbb)
```

**Exit Codes:**
| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Some commits missing artifacts (warning, partial output) |
| `2` | Invalid input |

---

### `gitsummary show`
**Purpose:** Display raw artifacts for inspection.

**Synopsis:**
```bash
gitsummary show <commit>
gitsummary show <revision-range>
```

**Options:**
| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--yaml` | Output as raw YAML (storage format) |
| `--brief` | One-line summary per commit |
| `--field <name>` | Show only specific field(s) |

**Examples:**
```bash
# Show artifact for single commit
gitsummary show abc123

# Brief view of range
gitsummary show v1.0..v2.0 --brief

# Extract specific field
gitsummary show abc123 --field intent_summary
```

**Output (default):**
```
╭─ abc1234 ─────────────────────────────────────────────╮
│ Fix null pointer in login flow                        │
├───────────────────────────────────────────────────────┤
│ Category:   fix                                       │
│ Impact:     internal                                  │
│ Breaking:   No                                        │
│                                                       │
│ Before: Users could not login if credentials missing  │
│ After:  Login now validates and shows clear error     │
│                                                       │
│ Technical:                                            │
│   • Added null check in AuthService.validate()        │
│   • New unit test for edge case                       │
╰───────────────────────────────────────────────────────╯
```

**Output (--brief):**
```
abc1234 [fix]     Fix null pointer in login flow
def5678 [feature] Add user preferences API
222bbbb [chore]   Bump dependencies
```

---

### `gitsummary list`
**Purpose:** List commits and their analysis status.

**Synopsis:**
```bash
gitsummary list <revision-range>
gitsummary list --all
```

**Options:**
| Option | Description |
|--------|-------------|
| `--all` | List all commits in repository |
| `--analyzed` | Only show commits with artifacts |
| `--missing` | Only show commits without artifacts |
| `--date` | Show absolute dates (YYYY-MM-DD HH:MM) instead of relative |
| `--json` | Output as JSON array |
| `--count` | Show only counts, not commit list |

**Examples:**
```bash
# List commits with analysis status (relative dates by default)
gitsummary list v1.0..v2.0

# List with absolute dates
gitsummary list v1.0..v2.0 --date

# Find commits needing analysis
gitsummary list v1.0..v2.0 --missing

# Get counts for CI
gitsummary list v1.0..v2.0 --count
```

**Output (default, relative dates):**
```
Commits in v1.0..v2.0 (15 total, 12 analyzed)

✓ abc1234   3d Fix null pointer in login flow
✓ def5678   5d Add user preferences API
○ 111aaaa  2mo WIP: experiment with caching
✓ 222bbbb   1y Bump dependencies
...
```

Relative date format: `3d` = 3 days, `2mo` = 2 months, `1y` = 1 year, `5h` = 5 hours, `now` = < 1 minute.

**Output (--date, absolute dates):**
```
Commits in v1.0..v2.0 (15 total, 12 analyzed)

✓ abc1234 2025-11-25 14:30 Fix null pointer in login flow
✓ def5678 2025-11-23 10:15 Add user preferences API
○ 111aaaa 2025-09-15 09:00 WIP: experiment with caching
...
```

**Output (--count):**
```
Total: 15
Analyzed: 12
Missing: 3
```

---

### `gitsummary version`
**Purpose:** Display version information.

**Synopsis:**
```bash
gitsummary version
gitsummary --version
```

**Output:**
```
gitsummary 0.1.0
Schema version: 0.1.0
```

---

## Command Summary

| Command | Phase | Purpose |
|---------|-------|---------|
| `analyze` | 1 | Extract semantic understanding → store artifacts |
| `generate` | 2 | Produce reports from stored artifacts |
| `show` | — | Inspect raw artifacts |
| `list` | — | Discovery and status checking |
| `version` | — | Version info |

---

## Storage

### Git Notes Namespace
Artifacts are stored in the `refs/notes/intent` namespace:
```bash
# View raw note for a commit
git notes --ref=intent show <commit>

# Push notes to remote
git push origin refs/notes/intent

# Fetch notes from remote
git fetch origin refs/notes/intent:refs/notes/intent
```

### Data Format
Notes are stored as UTF-8 encoded YAML, validated against the `CommitArtifact` schema defined in `gitsummary/schema.py`.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITSUMMARY_NOTES_REF` | Git Notes namespace | `refs/notes/intent` |
| `GITSUMMARY_NO_COLOR` | Disable colored output | unset |

---

## Exit Codes Summary

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Partial failure or not found |
| `2` | Invalid input or configuration error |
| `3` | Git repository error |

---

## See Also
- `docs/storage_layout.md` - Git Notes storage specification
- `gitsummary/schema.py` - Artifact schema definition
- `README.md` - Project overview and quickstart
