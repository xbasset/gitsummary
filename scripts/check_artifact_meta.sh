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
  (
    analysis_mode IS NOT NULL
    OR analysis_provider IS NOT NULL
    OR analysis_model IS NOT NULL
    OR analysis_prompt_version IS NOT NULL
    OR analysis_timestamp IS NOT NULL
    OR analysis_token_usage_input IS NOT NULL
    OR analysis_input_metrics_diff_files IS NOT NULL
    OR analysis_qualitative_technical_difficulty_score IS NOT NULL
  ) AS has_analysis_fields,
  analysis_mode,
  analysis_provider,
  analysis_model,
  analysis_prompt_version,
  analysis_timestamp,
  analysis_duration_ms,
  analysis_fallback_reason,
  analysis_token_usage_input,
  analysis_token_usage_output,
  analysis_token_usage_cached,
  analysis_input_metrics_commit_message_chars,
  analysis_input_metrics_commit_message_lines,
  analysis_input_metrics_commit_message_tokens,
  analysis_input_metrics_diff_files,
  analysis_input_metrics_diff_insertions,
  analysis_input_metrics_diff_deletions,
  analysis_input_metrics_diff_total,
  analysis_input_metrics_diff_hunks,
  analysis_input_metrics_diff_chars,
  analysis_input_metrics_diff_lines,
  analysis_input_metrics_diff_tokens,
  analysis_qualitative_technical_difficulty_score,
  analysis_qualitative_technical_difficulty_explanation,
  analysis_qualitative_creativity_score,
  analysis_qualitative_creativity_explanation,
  analysis_qualitative_mental_load_score,
  analysis_qualitative_mental_load_explanation,
  analysis_qualitative_review_effort_score,
  analysis_qualitative_review_effort_explanation,
  analysis_qualitative_ambiguity_score,
  analysis_qualitative_ambiguity_explanation
FROM artifacts
WHERE project_id = '${PROJECT_ID}'
  AND content_type = 'gitsummary.commit_artifact'
  AND source_ref = '${COMMIT_SHA}';
"
