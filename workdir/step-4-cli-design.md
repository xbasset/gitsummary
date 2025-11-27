# Step 4: CLI Surface Design
Version: 1.1
Date: 2025-11-27

## Objective
Define the user-facing CLI commands that Release Managers and developers will use to interact with gitsummary.

## Context & Inputs
- **Storage Layout:** `refs/notes/intent` namespace, YAML format, 1:1 commit-to-note mapping.
- **Schema:** `CommitArtifact` Pydantic model with intent, behavior, impact, and technical highlights.
- **Primary User:** Release Manager preparing release documentation.

---

## Key Design Decision: `analyze` → `generate` Naming Scheme

### The Problem with "collect"
The original design used `collect` as the primary command. This was problematic:
- **Too vague**: "Collect" implies gathering without processing
- **Doesn't convey value**: The real value is semantic *understanding*, not collection
- **Misleading**: Users might think it's just fetching git data

### Alternatives Considered

| Command | Pros | Cons | Verdict |
|---------|------|------|---------|
| `collect` | Simple | Vague, doesn't convey semantic extraction | ❌ Rejected |
| `index` | Familiar (search engines) | Implies retrieval, not understanding | ❌ Rejected |
| `annotate` | Aligns with Git Notes concept | Conflicts with `git annotate` (blame) | ❌ Rejected |
| `understand` | Captures intent perfectly | Unusual CLI verb, might feel awkward | ❌ Rejected |
| `note` | Aligns with Git Notes storage | Conflicts with `git notes` command | ❌ Rejected |
| `distill` | Evocative, unique | Less intuitive for newcomers | ❌ Rejected |
| **`analyze`** | Industry standard, clear meaning | Generic (but acceptably so) | ✅ **Selected** |

### Why `analyze` → `generate`?

**Industry Precedent:**
- `semantic-release` uses `analyze` for commit inspection
- `git-cliff`, `git-chglog` use `generate` for changelog creation
- Static analysis tools universally use `analyze`

**Mental Model Alignment:**
```
Raw Git Data  ──[analyze]──▶  Semantic Artifacts  ──[generate]──▶  Reports
   (noise)                      (understanding)                  (documents)
```

**User Clarity:**
- "I analyze commits" = I extract meaning from them
- "I generate changelog" = I produce a document from analyzed data

### The Two-Phase Model

This naming scheme explicitly communicates gitsummary's architecture:

```
Phase 1: ANALYZE
├── Input: Git commits, diffs, messages
├── Process: LLM semantic extraction
├── Output: CommitArtifact stored in Git Notes
└── Command: gitsummary analyze v1.0..v2.0

Phase 2: GENERATE
├── Input: Stored artifacts from Git Notes
├── Process: Aggregate, format, render
├── Output: Changelog, release notes, impact report
└── Command: gitsummary generate changelog v1.0..v2.0
```

**Benefits:**
1. **Cost efficiency**: Analyze once (expensive LLM), generate many (cheap)
2. **Cacheability**: Artifacts persist; reports regenerate instantly
3. **Shareability**: Artifacts travel with repo via Git Notes
4. **Flexibility**: Same artifacts → multiple report formats

---

## Final Command Structure

### Core Commands (Two-Phase)
```bash
# Phase 1: Analyze commits → store artifacts
gitsummary analyze v1.0..v2.0
gitsummary analyze abc123 --dry-run
gitsummary analyze v1.0..v2.0 --force

# Phase 2: Generate reports from artifacts
gitsummary generate changelog v1.0..v2.0
gitsummary generate release-notes v1.0..v2.0 -o RELEASE.md
gitsummary generate impact v1.0..v2.0 --format json
```

### Utility Commands
```bash
# Inspect raw artifacts
gitsummary show abc123
gitsummary show v1.0..v2.0 --brief

# Discovery and status
gitsummary list v1.0..v2.0
gitsummary list v1.0..v2.0 --missing

# Version info
gitsummary version
```

---

## Design Philosophy

### 1. Commit-Centric, Range-Aware
The storage model is **commit-centric** (one artifact per commit), but Release Managers think in **ranges** (e.g., "what changed between v1.0 and v2.0"). The CLI bridges this:
- **Storage:** Individual commit artifacts in Git Notes
- **UX:** Commands accept ranges and operate across multiple commits

### 2. Builder, Not Generator (for Phase 1)
The `analyze` command is a "builder" that uses LLM to *extract* semantic information:
- Never generates content from nothing
- Always traces back to source (commit, diff, message)
- Stores durable artifacts for later use

### 3. Generator (for Phase 2)
The `generate` command is a "generator" that *produces* documents:
- Reads from stored artifacts
- Aggregates across ranges
- Formats for specific output types

### 4. Offline-First, Git-Native
- All data derived from local `.git` directory
- Storage via Git Notes enables `push`/`fetch` workflows
- No external APIs required for core operations

---

## Output Modes
All commands support multiple output formats:
- **Human-readable** (default): Formatted text for terminals
- **JSON** (`--json`): Machine-readable for pipelines
- **YAML** (`--yaml`): Matches storage format for debugging
- **Brief** (`--brief`): One-line summaries for quick scanning

---

## Non-Goals for v0.1
- **Interactive mode:** No TUI or prompts
- **Watch mode:** No continuous monitoring
- **Remote fetching:** No automatic fetch of notes from remotes
- **Custom generators:** Generator extension comes later
- **Streaming output:** Full output after completion

---

## Migration from Legacy Implementation
The current codebase uses legacy command names:

| Legacy | New | Notes |
|--------|-----|-------|
| `collect` | `analyze` | Semantic extraction phase |
| `analyze --target <x>` | `generate <x>` | Report generation phase |

This will be updated in Step 9 (CLI Implementation).

---

## Artifacts Created
- `docs/cli_design.md`: Formal CLI specification with rationale

## Next Steps
- **Step 5:** Implement core Git range & diff collector
- **Step 9:** Implement CLI commands (rename `collect` → `analyze`, `analyze` → `generate`)
