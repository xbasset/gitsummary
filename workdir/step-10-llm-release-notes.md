# Step 10: LLM-Assisted Release Notes Generation

**Branch:** `step-10-llm-release-notes`  
**Status:** In Progress  
**Started:** 2025-12-01

---

## 1. Goal

Implement LLM-assisted synthesis for high-quality release notes that go beyond simple aggregation. The output should be user-focused, clear, concise, and structured like professional release notes.

---

## 2. Design Principles

Based on the example provided, "the best" release notes are:

| Quality      | Description |
|--------------|-------------|
| **Clear**    | Tell users what changed without technical jargon |
| **Concise**  | Short enough to skim, detailed enough to be useful |
| **User-focused** | Explain *why* changes matter, not just *what* changed |
| **Transparent** | Highlight improvements, fixes, and known issues honestly |
| **Organized** | Predictable, readable sections |

---

## 3. Data Model Design

### 3.1 ReleaseNoteArtifact Schema

The release note is a **report-level artifact** stored in Git Notes at `refs/notes/report/release-note`. It synthesizes commit-level artifacts into a coherent user-facing document.

```yaml
# Release Note Artifact (stored in Git Notes)
schema_version: "1.0.0"
artifact_type: "release-note"

# --- Metadata for traceability ---
metadata:
  generated_at: "2025-12-01T10:30:00Z"
  generator_version: "0.2.0"
  llm_provider: "openai"
  llm_model: "gpt-4o"
  revision_range: "v0.1.0..v0.2.0"
  tip_commit: "abc123def456..."
  commit_count: 15
  analyzed_count: 15
  source_commits:
    - sha: "abc123..."
      category: "feature"
    - sha: "def456..."
      category: "fix"

# --- Header ---
header:
  product_name: "gitsummary"
  version: "v0.2.0"
  release_date: "2025-12-01"
  theme: "Faster syncing and major stability improvements."

# --- Highlights (TL;DR) ---
highlights:
  - emoji: "🚀"
    type: "new"
    summary: "Smart Search with typo tolerance"
  - emoji: "✨"
    type: "improved"
    summary: "Sync speed increased by 2×"
  - emoji: "🛠️"
    type: "fixed"
    summary: "Login crash for some Android devices"
  - emoji: "⚠️"
    type: "breaking"
    summary: "Legacy API tokens deprecated"

# --- New Features ---
features:
  - title: "Smart Search (beta)"
    description: "Find files even with typos or incomplete terms."
    user_benefit: "Helps users locate content much faster, especially in large workspaces."
    commits: ["abc123"]

# --- Improvements ---
improvements:
  - summary: "Sync performance improved by 100%, especially for large projects"
    commits: ["def456", "ghi789"]
  - summary: "Reduced CPU usage during background indexing"
    commits: ["jkl012"]
  - summary: "Updated UI components for better readability"
    commits: ["mno345"]

# --- Bug Fixes ---
fixes:
  - summary: "Fixed an issue causing login crashes on Android 14"
    commits: ["pqr678"]
  - summary: "Resolved delay when switching between team workspaces"
    commits: ["stu901"]
  - summary: "Fixed inconsistent dark mode colors"
    commits: ["vwx234"]

# --- Deprecations / Breaking Changes ---
deprecations:
  - what: "Legacy API tokens"
    reason: "Migrating to OAuth-based authentication for better security"
    deadline: "2025-08-01"
    migration: "Use the new Developer Portal to create OAuth-based tokens."
    commits: ["yza567"]

# --- Known Issues ---
known_issues:
  - issue: "Some users may see duplicated items in Recent Files"
    status: "Fix coming next week"

# --- Call to Action ---
call_to_action:
  documentation_url: null
  migration_guide_url: null
  support_url: null
```

### 3.2 Key Design Decisions

1. **Report-level storage**: Unlike `CommitArtifact` (per-commit), `ReleaseNoteArtifact` is stored once per release range
2. **Attached to tip commit**: The note is attached to the tip commit of the range for easy retrieval
3. **Separate namespace**: Uses `refs/notes/report/release-note` to distinguish from per-commit artifacts
4. **Full traceability**: Includes source commit SHAs, LLM metadata, and generation timestamp
5. **YAML serialization**: Human-readable storage format

---

## 4. LLM Synthesis Approach

### 4.1 Two-Phase Generation

**Phase 1: Aggregate & Prepare Context**
- Load all `CommitArtifact` objects for the range
- Group by category (feature, fix, security, etc.)
- Extract breaking changes, technical highlights
- Build a structured context document

**Phase 2: LLM Synthesis**
- Send aggregated data to LLM with a release-notes-specific prompt
- LLM synthesizes:
  - The "theme" of the release
  - User-friendly summaries (rewriting technical descriptions)
  - Grouping related commits into single entries
  - Identifying most important highlights

### 4.2 Prompt Design

The prompt should:
1. Include the structured data from Phase 1
2. Provide the target release note structure
3. Give examples of good user-focused writing
4. Request specific output format (JSON matching our schema)

---

## 5. Output Formats

| Format | Purpose | Implementation |
|--------|---------|----------------|
| YAML   | Raw structured data (default for `--format yaml`) | Direct serialization |
| Markdown | Human-readable document | Template-based formatter |
| Plain text | Simple text for terminals/emails | Strip markdown formatting |

---

## 6. CLI Design

```bash
# Generate release notes with LLM synthesis
gitsummary generate release-notes v0.1.0..v0.2.0 --llm

# Options
--llm / --no-llm      # Enable LLM synthesis (default: --llm)
--provider <name>     # LLM provider to use (default: from config)
--model <name>        # Model to use (default: from config)
--format <fmt>        # Output format: yaml, markdown, text
--output <file>       # Write to file instead of stdout
--version <ver>       # Override version name (default: from range end)
--product <name>      # Product name for header (default: repo name)

# Store the generated release note
gitsummary generate release-notes v0.1.0..v0.2.0 --store
# Stores to refs/notes/report/release-note attached to tip commit

# Retrieve stored release note
gitsummary show release-note v0.2.0
# or by commit SHA
gitsummary show release-note abc123
```

---

## 7. Implementation Plan

### 7.1 Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `gitsummary/reports/release_notes/model.py` | ✅ Created | ReleaseNote Pydantic models |
| `gitsummary/core/__init__.py` | ✅ Modified | Export ReleaseNote models |
| `gitsummary/llm/schemas.py` | ✅ Modified | Add ReleaseNoteSynthesisSchema |
| `gitsummary/llm/prompts.py` | ✅ Modified | Add release note synthesis prompt |
| `gitsummary/services/reporter.py` | ✅ Modified | Add generate_llm_release_notes() |
| `gitsummary/infrastructure/notes.py` | ✅ Modified | Add RELEASE_NOTE_NOTES_REF constant |
| `gitsummary/infrastructure/__init__.py` | ✅ Modified | Export release note functions |
| `gitsummary/cli/commands/generate.py` | ✅ Modified | Enhanced release-notes with --llm, --store |
| `gitsummary/cli/commands/show.py` | ✅ Modified | Add show_release_note command |
| `gitsummary/cli/app.py` | ✅ Modified | Wire up show subcommands |
| `docs/TODO.md` | ✅ Modified | Add Future Ideas section |
| `docs/current_development_status.md` | ✅ Modified | Document Step 10 completion |

### 7.2 Implementation Order (All Complete)

1. ✅ Create workdir notebook (this document)
2. ✅ Define ReleaseNote data model in `reports/release_notes/model.py`
3. ✅ Add `refs/notes/report/release-note` namespace support
4. ✅ Create LLM prompts for release note synthesis
5. ✅ Implement `ReporterService.generate_llm_release_notes()`
6. ✅ Wire up CLI with `--llm` flag
7. ✅ Implement output formatters (YAML, Markdown, Text)
8. ✅ Add `show release-note` command for retrieving stored notes

---

## 8. Final CLI Usage

### Generate Release Notes

```bash
# Generate with LLM synthesis (default)
gitsummary generate release-notes v0.1.0..v0.2.0

# Generate without LLM (heuristic only, faster)
gitsummary generate release-notes v0.1.0..v0.2.0 --no-llm

# Output formats
gitsummary generate release-notes v0.1.0..v0.2.0 --format markdown
gitsummary generate release-notes v0.1.0..v0.2.0 --format yaml
gitsummary generate release-notes v0.1.0..v0.2.0 --format text

# Store to Git Notes
gitsummary generate release-notes v0.1.0..v0.2.0 --store

# Custom product/version
gitsummary generate release-notes v0.1.0..v0.2.0 --product "My App" --version "2.0.0"

# Choose LLM provider/model
gitsummary generate release-notes v0.1.0..v0.2.0 --provider openai --model gpt-4o
```

### Show Stored Release Notes

```bash
# Show by revision (commit, tag, branch)
gitsummary show release-note v0.2.0
gitsummary show release-note HEAD
gitsummary show release-note abc123

# Output formats
gitsummary show release-note v0.2.0 --format yaml
gitsummary show release-note v0.2.0 --format text
```

### Show Commit Artifacts

```bash
# Show artifact for commit(s)
gitsummary show commit HEAD
gitsummary show commit HEAD~5..HEAD --brief
```

---

## 9. Future Ideas (for TODO.md)

- **Interactive refinement**: `--interactive` mode to edit/refine sections before finalizing
- **Template customization**: Jinja2 templates for custom output formats
- **Multi-language support**: Generate release notes in different languages
- **Diff from previous**: Show what's new since last stored release note

---

## 10. Open Questions

1. **Version detection**: How to auto-detect version from revision range?
   - For tags: Extract version from tag name (v0.2.0 → 0.2.0)
   - For commits: Use short SHA or "unreleased"

2. **Known issues source**: Where do known issues come from?
   - Option A: Manual input via `--known-issue "description"`
   - Option B: Parse from commit messages (e.g., "Known issue: ...")
   - Option C: Separate storage for known issues

3. **Call to action URLs**: Should be configurable
   - Via CLI flags
   - Via config file
   - Via environment variables

---

## 11. References

- Example release note format provided by user
- Current `ReporterService` implementation: `gitsummary/services/reporter.py`
- LLM provider architecture: `workdir/step-9-llm-provider-architecture.md`
