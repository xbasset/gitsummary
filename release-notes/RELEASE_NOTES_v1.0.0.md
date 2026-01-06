# gitsummary v1.0.0

Major release focused on richer commit analysis metadata and Postgres output support.

## Highlights
- Commit artifacts now include `analysis_meta` with LLM token usage, prompt/model info, input metrics, and qualitative scores (difficulty/creativity/mental load).
- LLM prompts moved to versioned files under `gitsummary/llm/prompt_assets/` for easier iteration.
- New Postgres backend with `--storage postgres` and `GITSUMMARY_POSTGRES_DSN`, mapping artifacts into `public.artifacts` and `projects`.
- CLI human output surfaces the new analysis metadata summary.

## Breaking changes
- Artifact schema version bumped to `0.2.0` (new `analysis_meta`).
- Project version bumped to `1.0.0`.

## Upgrade notes
- Ensure your storage can accept the new `analysis_meta` JSON field in artifacts (Git Notes and Postgres are compatible).
- For Postgres: set `GITSUMMARY_STORAGE_BACKEND=postgres` and `GITSUMMARY_POSTGRES_DSN` (or use `--storage postgres --postgres-dsn`).

## Docs
- New install/update guide and updated CLI/storage documentation.
