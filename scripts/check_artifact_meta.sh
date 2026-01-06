#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/check_artifact_meta.sh --project <project_id> --sha <commit_sha> [--dsn "<dsn>"]

Env:
  GITSUMMARY_POSTGRES_DSN can be used instead of --dsn.

Example:
  GITSUMMARY_POSTGRES_DSN="user=gitsummary password=gitsummary dbname=gitsummary host=localhost port=5432" \
  scripts/check_artifact_meta.sh --project openai/codex --sha 66b7c673e96d61c4d767086c0ed438a4b163d357
EOF
}

PROJECT_ID=""
COMMIT_SHA=""
DSN="${GITSUMMARY_POSTGRES_DSN:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT_ID="${2:-}"; shift 2 ;;
    --sha)
      COMMIT_SHA="${2:-}"; shift 2 ;;
    --dsn)
      DSN="${2:-}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage; exit 1 ;;
  esac
done

if [[ -z "$PROJECT_ID" || -z "$COMMIT_SHA" ]]; then
  echo "Missing --project or --sha" >&2
  usage
  exit 1
fi

if [[ -z "$DSN" ]]; then
  echo "Missing DSN. Set GITSUMMARY_POSTGRES_DSN or use --dsn." >&2
  exit 1
fi

psql "$DSN" -v ON_ERROR_STOP=1 -X -c "
SELECT
  project_id,
  source_ref,
  raw_artifact ? 'analysis_meta' AS has_analysis_meta,
  raw_artifact->'analysis_meta'->>'analysis_mode' AS analysis_mode,
  raw_artifact->'analysis_meta'->>'provider' AS provider,
  raw_artifact->'analysis_meta'->>'model' AS model,
  raw_artifact->'analysis_meta'->'token_usage' AS token_usage,
  raw_artifact->'analysis_meta'->'input_metrics' AS input_metrics,
  raw_artifact->'analysis_meta'->'qualitative' AS qualitative
FROM artifacts
WHERE project_id = '${PROJECT_ID}'
  AND content_type = 'gitsummary.commit_artifact'
  AND source_ref = '${COMMIT_SHA}';

SELECT jsonb_pretty(raw_artifact->'analysis_meta') AS analysis_meta_pretty
FROM artifacts
WHERE project_id = '${PROJECT_ID}'
  AND content_type = 'gitsummary.commit_artifact'
  AND source_ref = '${COMMIT_SHA}';
"
