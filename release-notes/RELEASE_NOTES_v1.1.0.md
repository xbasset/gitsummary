# Release Notes — v1.1.0

## Highlights
- Flattened commit artifact analysis metadata into structured Postgres columns (`analysis_*`) for queryable access.
- Postgres storage now writes/reads analysis fields from columns only (no `analysis_meta` JSON column).

## Migration
- Run `gitsummary_io/db/migrations/012_analysis_meta_columns.sql` to backfill columns from `analysis_meta`.
- Run `gitsummary_io/db/migrations/013_drop_analysis_meta.sql` to remove the JSON column.

## Notes
- Update downstream queries to use `analysis_*` columns (token usage, input metrics, qualitative scores).
