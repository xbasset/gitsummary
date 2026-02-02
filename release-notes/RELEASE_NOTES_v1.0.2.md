# Release Notes — v1.0.2

## Highlights
- Postgres artifacts now persist commit artifact fields in dedicated columns (description, category, impact scope, behavior before/after, technical highlights, analysis meta, tool version) in addition to `raw_artifact`.
- Postgres schema initialization auto-adds the new columns for existing databases.

## Notes
- Run the DB migration in `gitsummary_io/db/migrations/010_artifact_columns.sql` to backfill existing rows.
