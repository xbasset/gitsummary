# Storage Layout Specification
Version: 0.1.0
Date: 2025-11-26

## Overview
**gitsummary** stores semantic artifacts in Git Notes by default, with optional Postgres storage for shared or remote deployments. Git Notes keep the "Why" (the artifact) traveling with the "What" (the commit) when pushed/pulled, without polluting the commit message or file tree.

## 1. Storage Location
- **Namespace:** `refs/notes/intent`
- **Object Attachment:** Notes are attached directly to the **Commit Object** they analyze.

## 2. Data Format
The content of the note is a UTF-8 encoded **YAML** string.
**Validation:** The YAML content must strictly conform to the `CommitArtifact` Pydantic model defined in `gitsummary/schema.py`. This ensures type safety and schema validation despite the storage format being YAML.

The schema now includes `analysis_meta` for provenance, input metrics, token usage, and qualitative scores.
In Postgres, those fields are stored in structured `analysis_*` columns for queryable access.

### Example Note Content
```yaml
commit_hash: a1b2c3d4...
schema_version: 0.1.0
intent_summary: Fixes a null pointer exception in the user login flow...
category: fix
behavior_before: Users could not login if...
behavior_after: Users can now login with...
impact_scope: internal
is_breaking: false
risk_explanation: null
technical_highlights:
  - Used regex for validation
  - Added unit test
confidence_score: 0.95
```

## 3. Operations

### Writing (Collect)
- **Command:** `git notes --ref=intent add -f -m <YAML_STRING> <COMMIT_HASH>`
- **Behavior:** Overwrites any existing note for that commit in the `intent` namespace.
- **Idempotency:** Rerunning `collect` on the same commit will regenerate and replace the artifact.

### Reading (Analyze/Show)
- **Command:** `git notes --ref=intent show <COMMIT_HASH>`
- **Fallback:** If no note exists, the system treats the commit as "unanalyzed".

### Transport (Push/Pull)
- **Push:** `git push origin refs/notes/intent`
- **Fetch:** `git fetch origin refs/notes/intent:refs/notes/intent`

## 4. Indexing & Lookup
- **Primary Index:** The Git Object Database itself.
- **Lookup:** `Artifact(CommitHash)` is O(1) via `git notes show`.
- **Range Queries:** To find all artifacts in `A..B`, the system:
    1. Lists commits in `A..B`.
    2. Batches `git notes show` calls (or uses `git log --show-notes=gitsummary --format=%N`) to retrieve artifacts.

## 5. Constraints
- **Size:** Git Notes are blob objects. They handle large JSONs fine, but we should aim to keep artifacts under 100KB for performance.
- **Merge Conflicts:** If two users analyze the same commit differently and push, Git Notes merge strategies apply (default is usually union or manual). For v0.1, "last write wins" (force overwrite) is acceptable.

---

## 6. Postgres Backend (Optional)

When `--storage postgres` (or `GITSUMMARY_STORAGE_BACKEND=postgres`) is set, artifacts are stored in Postgres instead of Git Notes.

### Table
`artifacts`

### Columns (relevant)
- `id` (text, primary key)
- `project_id` (text, references `projects.id`)
- `content_type` (text, `gitsummary.commit_artifact`)
- `source_ref` (text, commit SHA)
- `schema_version` (text)
- `generated_at` (timestamptz)
- `summary` (text, CommitArtifact intent summary)
- `description` (text, human-friendly description; defaults to intent summary)
- `tags` (text[])
- `signals` (jsonb)
- `commit` (jsonb, optional)
- `category` (text, CommitArtifact category)
- `impact_scope` (text, CommitArtifact impact scope)
- `is_breaking` (boolean, CommitArtifact breaking change flag)
- `behavior_before` (text, CommitArtifact behavior before)
- `behavior_after` (text, CommitArtifact behavior after)
- `technical_highlights` (text[], CommitArtifact technical highlights)
- `analysis_mode` / `analysis_provider` / `analysis_model` / `analysis_prompt_version` / `analysis_timestamp` / `analysis_duration_ms` / `analysis_fallback_reason`
- `analysis_token_usage_input` / `analysis_token_usage_output` / `analysis_token_usage_cached`
- `analysis_input_metrics_commit_message_*` and `analysis_input_metrics_diff_*`
- `analysis_qualitative_*_{score,explanation}` (technical_difficulty, creativity, mental_load, review_effort, ambiguity)
- `tool_version` (text, gitsummary version that generated the artifact)

### Connection
Set `GITSUMMARY_POSTGRES_DSN` to a libpq DSN or URL (e.g., `postgresql://user:pass@host:5432/gitsummary`).

### Project Resolution
When using Postgres, gitsummary resolves the project via:
`GITSUMMARY_PROJECT_ID` / `GITSUMMARY_PROJECT_SLUG` / `GITSUMMARY_PROJECT_NAME` / `GITSUMMARY_PROJECT_PROVIDER` / `GITSUMMARY_PROJECT_URL`.
If unset, it falls back to the repo name and a `local://<repo>` URL.
