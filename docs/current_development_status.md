# Current Development Status

## Latest Release
- **v0.0.1:** Tagged at current HEAD with release notes generated via `gitsummary generate release-notes` (heuristic mode, stored in Git Notes).

## Operational Notes
- For long ranges, run `gitsummary list <range> --missing` first, then `gitsummary analyze <range> --provider openai` without `--force` to skip already analyzed commits and avoid long reruns.
- If the LLM request times out, switch to a lighter model (e.g., `--model gpt-4.1-mini`) when generating release notes: `gitsummary generate release-notes <range> --provider openai --model gpt-4.1-mini --store`.
- Git Notes writes may require elevated permissions on some systems; rerun commands with appropriate privileges if you see `Operation not permitted` errors when creating notes or tags.

## Step 1: Ground the Problem & Constraints (Complete)
- **Status:** Done.
- **Outcome:**
  - Defined "Release Manager" as primary user.
  - Confirmed "Builder" vs "Generator" architecture.
  - Updated `README.md` with clear problem statement.
  - Moved secondary use cases to `docs/future_plans.md`.
- **Reference:** `workdir/step-1-grounding.md`.

## Step 2: Artifact Schema Design (Complete)
- **Status:** Done.
- **Outcome:**
  - Defined `CommitArtifact` Pydantic model in `gitsummary/schema.py`.
  - Decided on 1:1 Commit-to-Artifact mapping.
  - Validated schema serialization.
- **Reference:** `workdir/step-2-schema-design.md`.

## Step 3: Design Git Notes Storage Layout (Complete)
- **Status:** Done.
- **Outcome:**
  - Defined `refs/notes/intent` namespace.
  - Specified YAML storage format.
  - Created `docs/storage_layout.md`.
- **Reference:** `workdir/step-3-storage-layout.md`.

## Step 4: CLI Surface Design (Complete)
- **Status:** Done.
- **Outcome:**
  - Adopted **`analyze` → `generate`** two-phase naming scheme.
  - Defined core commands: `analyze`, `generate`, `show`, `list`, `version`.
  - Specified standard git range syntax for all commands.
  - Designed output modes: human-readable (default), `--json`, `--yaml`, `--brief`.
  - Documented exit codes and environment variables.
  - Created `docs/cli_design.md` with full specification and rationale.
- **Key Decision:** Rejected `collect` (too vague), chose `analyze` for semantic extraction phase and `generate` for report production phase, following industry patterns (semantic-release, git-cliff).
- **Reference:** `workdir/step-4-cli-design.md`.

## Step 5: Implement Core Git Range & Diff Collector (Complete)
- **Status:** Done.
- **Outcome:**
  - Enhanced `gitsummary/git.py` with `CommitInfo` dataclass.
  - Added single-commit and range resolution support.
  - Implemented `get_commit_info()`, `list_commits_in_range()`, `get_commit_diff()`.
  - Added Git Notes operations: `notes_read()`, `notes_write()`, `notes_exists()`.
- **Reference:** `workdir/step-5-6-7-core-implementation.md`.

## Step 6: Implement Artifacts Construction (Complete)
- **Status:** Done.
- **Outcome:**
  - Created `ArtifactBuilder` class with heuristic extraction.
  - Implemented LLM provider interface for future integration.
  - Added heuristic extractors for category, impact scope, breaking changes.
  - Maintained legacy `build_artifact()` for backwards compatibility.
- **Reference:** `workdir/step-5-6-7-core-implementation.md`.

## Step 7: Wire Artifacts into Git Notes (Complete)
- **Status:** Done.
- **Outcome:**
  - Implemented `save_artifact_to_notes()` and `load_artifact_from_notes()`.
  - YAML serialization with proper Pydantic enum handling.
  - Support for `GITSUMMARY_NOTES_REF` environment variable.
  - Batch loading via `load_artifacts_for_range()`.
- **Reference:** `workdir/step-5-6-7-core-implementation.md`.

## Step 8: CLI Implementation (Complete)
- **Status:** Done (merged with Steps 5-7).
- **Outcome:**
  - Implemented `analyze` command with `--dry-run`, `--force`, `--json` options.
  - Implemented `show` command with human-readable, JSON, YAML, and brief modes.
  - Implemented `list` command with `--analyzed`, `--missing`, `--count` filters.
  - Implemented `generate` subcommands: `changelog`, `release-notes`, `impact`.
  - Removed legacy `collect` command.
- **Reference:** `workdir/step-5-6-7-core-implementation.md`.

## Step 8: Codebase Reorganization (Complete)
- **Status:** Done.
- **Outcome:**
  - Restructured codebase following Clean Architecture principles.
  - Created layered package structure: `core/`, `extractors/`, `services/`, `infrastructure/`, `cli/`.
  - Separated concerns: domain models, extraction strategies, application services, infrastructure adapters, CLI presentation.
  - Moved legacy code to `_legacy/` package.
  - Created backwards-compatible shim modules for existing imports.
  - Reduced largest module from 735 lines to ~200 lines.
- **Key Files:**
  - `core/`: Domain models (CommitInfo, CommitArtifact, enums)
  - `extractors/`: Extractor protocol with heuristic and LLM implementations
  - `services/`: AnalyzerService, ReporterService
  - `infrastructure/`: Git operations, Notes, Storage
  - `cli/`: Typer commands split into modules
- **Reference:** `workdir/step-8-codebase-reorganization.md`.

## Step 9: Add Semantic Analysis Facets / LLM Integration (In Progress)
- **Status:** OpenAI provider implemented.
- **Goal:** Enrich artifacts with higher-level semantics via LLM.
- **Implemented:**
  - Pluggable LLM provider architecture (`gitsummary/llm/` package)
  - OpenAI Responses API with structured outputs
  - API key management (env vars, .env, config file, interactive prompt)
  - CLI flags: `--provider`, `--model`, `--llm/--no-llm`
  - Pydantic schemas for structured extraction
  - Prompt templates optimized for commit analysis
- **Placeholder Providers:**
  - Anthropic Claude (planned)
  - Ollama local models (planned)
- **Reference:** `workdir/step-9-llm-provider-architecture.md`

### Remaining for Step 9:
- [ ] Complete Anthropic Claude provider
- [ ] Complete Ollama provider for local models
- [ ] Add confidence scoring
- [ ] Add batch optimization for multiple commits
- [ ] Add token usage reporting

## Step 10: LLM-Assisted Release Notes Generation (Complete)
- **Status:** Done.
- **Goal:** Implement LLM-assisted synthesis for high-quality release notes.
- **Implemented:**
  - `ReleaseNote` data model in `reports/release_notes/model.py` with comprehensive schema
  - Git Notes storage at `refs/notes/report/release-note`
  - LLM synthesis prompts and schemas split into `llm/prompts_release_note.py` and `llm/schemas_release_note.py`
  - `ReporterService.generate_llm_release_notes()` with both LLM and heuristic modes
  - Enhanced CLI commands (`generate`/`report release-notes`):
    - `--llm/--no-llm` flag for LLM synthesis (default: enabled)
    - `--provider` and `--model` options for LLM selection
    - `--format` option supporting yaml, markdown, text
    - `--store` flag to save release note to Git Notes
    - `--product` and `--version` options for header customization
  - Three output formatters: YAML (raw data), Markdown, Plain text
- **Key Design Decisions:**
  - Report-level artifact (one per release range, not per commit)
  - Attached to tip commit for easy retrieval
  - Separate namespace from commit artifacts
  - Full traceability metadata (source commits, LLM used, generation time)
- **Reference:** `workdir/step-10-llm-release-notes.md`

### Future Ideas (documented in TODO.md):
- Interactive refinement mode (`--interactive`)
- Template customization (Jinja2 templates)
- Multi-language support
