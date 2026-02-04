"""PostgreSQL storage for commit artifacts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .. import __version__
from ..core import (
    AnalysisMeta,
    CommitArtifact,
    InputMetrics,
    QualitativeScores,
    QualitativeSignal,
    TokenUsage,
)
from .git import GitCommandError, repository_root
from ..tracing import trace_manager

POSTGRES_DSN_ENV = "GITSUMMARY_POSTGRES_DSN"
POSTGRES_TABLE = "artifacts"
PROJECT_ID_ENV = "GITSUMMARY_PROJECT_ID"
PROJECT_SLUG_ENV = "GITSUMMARY_PROJECT_SLUG"
PROJECT_NAME_ENV = "GITSUMMARY_PROJECT_NAME"
PROJECT_PROVIDER_ENV = "GITSUMMARY_PROJECT_PROVIDER"
PROJECT_URL_ENV = "GITSUMMARY_PROJECT_URL"
CONTENT_TYPE_COMMIT_ARTIFACT = "gitsummary.commit_artifact"

ANALYSIS_COLUMNS: Tuple[Tuple[str, str], ...] = (
    ("analysis_mode", "text"),
    ("analysis_provider", "text"),
    ("analysis_model", "text"),
    ("analysis_prompt_version", "text"),
    ("analysis_timestamp", "timestamptz"),
    ("analysis_duration_ms", "integer"),
    ("analysis_fallback_reason", "text"),
    ("analysis_token_usage_input", "integer"),
    ("analysis_token_usage_output", "integer"),
    ("analysis_token_usage_cached", "integer"),
    ("analysis_input_metrics_commit_message_chars", "integer"),
    ("analysis_input_metrics_commit_message_lines", "integer"),
    ("analysis_input_metrics_commit_message_tokens", "integer"),
    ("analysis_input_metrics_diff_files", "integer"),
    ("analysis_input_metrics_diff_insertions", "integer"),
    ("analysis_input_metrics_diff_deletions", "integer"),
    ("analysis_input_metrics_diff_total", "integer"),
    ("analysis_input_metrics_diff_hunks", "integer"),
    ("analysis_input_metrics_diff_chars", "integer"),
    ("analysis_input_metrics_diff_lines", "integer"),
    ("analysis_input_metrics_diff_tokens", "integer"),
    ("analysis_qualitative_technical_difficulty_score", "integer"),
    ("analysis_qualitative_technical_difficulty_explanation", "text"),
    ("analysis_qualitative_creativity_score", "integer"),
    ("analysis_qualitative_creativity_explanation", "text"),
    ("analysis_qualitative_mental_load_score", "integer"),
    ("analysis_qualitative_mental_load_explanation", "text"),
    ("analysis_qualitative_review_effort_score", "integer"),
    ("analysis_qualitative_review_effort_explanation", "text"),
    ("analysis_qualitative_ambiguity_score", "integer"),
    ("analysis_qualitative_ambiguity_explanation", "text"),
)

ANALYSIS_COLUMN_NAMES = [name for name, _dtype in ANALYSIS_COLUMNS]
ANALYSIS_COLUMN_DEFS = ",\n            ".join(
    f"{name} {dtype}" for name, dtype in ANALYSIS_COLUMNS
)
ANALYSIS_COLUMN_ALTERS = ",\n            ".join(
    f"ADD COLUMN IF NOT EXISTS {name} {dtype}" for name, dtype in ANALYSIS_COLUMNS
)
ANALYSIS_COLUMN_SELECT = ",\n                ".join(ANALYSIS_COLUMN_NAMES)
ANALYSIS_COLUMN_INSERT = ",\n                ".join(ANALYSIS_COLUMN_NAMES)
ANALYSIS_COLUMN_PLACEHOLDERS = ", ".join(["%s"] * len(ANALYSIS_COLUMN_NAMES))
ANALYSIS_COLUMN_UPDATES = ",\n                ".join(
    f"{name} = EXCLUDED.{name}" for name in ANALYSIS_COLUMN_NAMES
)


@dataclass
class ProjectInfo:
    project_id: str
    slug: str
    name: str
    provider: str
    html_url: str


def _get_dsn() -> str:
    dsn = os.environ.get(POSTGRES_DSN_ENV)
    if not dsn:
        raise ValueError(f"{POSTGRES_DSN_ENV} is not set")
    return dsn


def _connect() -> psycopg.Connection:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "psycopg is required for Postgres storage. Install with: pip install 'psycopg[binary]'."
        ) from exc
    return psycopg.connect(_get_dsn(), row_factory=dict_row)


def _json(value: object) -> object:
    """Wrap JSON values for psycopg when available (tests may run without psycopg installed)."""
    try:
        from psycopg.types.json import Json
    except ModuleNotFoundError:
        return value
    return Json(value)

def _ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS projects (
            id text PRIMARY KEY,
            slug text UNIQUE NOT NULL,
            name text NOT NULL,
            provider text NOT NULL,
            html_url text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {POSTGRES_TABLE} (
            id text PRIMARY KEY,
            project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            content_type text NOT NULL,
            source_ref text NOT NULL,
            schema_version text NOT NULL,
            generated_at timestamptz NOT NULL,
            summary text NOT NULL,
            description text,
            why_it_matters text,
            tags text[] NOT NULL DEFAULT '{{}}'::text[],
            signals jsonb NOT NULL DEFAULT '[]'::jsonb,
            category text,
            impact_scope text,
            is_breaking boolean NOT NULL DEFAULT false,
            behavior_before text,
            behavior_after text,
            technical_highlights text[] NOT NULL DEFAULT '{{}}'::text[],
            {ANALYSIS_COLUMN_DEFS},
            tool_version text,
            commit jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (project_id, content_type, source_ref)
        )
        """
    )
    conn.execute(f"CREATE INDEX IF NOT EXISTS artifacts_project_idx ON {POSTGRES_TABLE}(project_id)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS artifacts_generated_idx ON {POSTGRES_TABLE}(generated_at DESC)")
    conn.execute(
        f"""
        ALTER TABLE {POSTGRES_TABLE}
            ADD COLUMN IF NOT EXISTS description text,
            ADD COLUMN IF NOT EXISTS category text,
            ADD COLUMN IF NOT EXISTS impact_scope text,
            ADD COLUMN IF NOT EXISTS is_breaking boolean,
            ADD COLUMN IF NOT EXISTS behavior_before text,
            ADD COLUMN IF NOT EXISTS behavior_after text,
            ADD COLUMN IF NOT EXISTS technical_highlights text[],
            {ANALYSIS_COLUMN_ALTERS},
            ADD COLUMN IF NOT EXISTS tool_version text
        """
    )


def _infer_project_from_repo_path(repo_path: Optional[Path]) -> Optional[ProjectInfo]:
    if repo_path is None:
        return None
    parts = list(repo_path.parts)
    if "repos" not in parts:
        return None
    idx = parts.index("repos")
    if idx + 2 >= len(parts):
        return None
    owner = parts[idx + 1]
    repo = parts[idx + 2]
    project_id = f"{owner}/{repo}"
    return ProjectInfo(
        project_id=project_id,
        slug=project_id,
        name=repo,
        provider="github",
        html_url=f"https://github.com/{owner}/{repo}",
    )


def _project_defaults() -> ProjectInfo:
    project_id = os.environ.get(PROJECT_ID_ENV)
    slug = os.environ.get(PROJECT_SLUG_ENV)
    name = os.environ.get(PROJECT_NAME_ENV)
    provider = os.environ.get(PROJECT_PROVIDER_ENV)
    html_url = os.environ.get(PROJECT_URL_ENV)

    repo_name = "gitsummary"
    repo_path = None
    try:
        repo_path = repository_root()
        repo_name = repo_path.name
    except GitCommandError:
        repo_path = None

    inferred = _infer_project_from_repo_path(repo_path)
    if not project_id and inferred:
        project_id = inferred.project_id
    if not slug and inferred:
        slug = inferred.slug
    if not name and inferred:
        name = inferred.name
    if not provider and inferred:
        provider = inferred.provider
    if not html_url and inferred:
        html_url = inferred.html_url

    if not slug:
        slug = repo_name
    if not project_id:
        project_id = slug
    if not name:
        name = repo_name
    if not provider:
        provider = "local"
    if not html_url:
        html_url = f"local://{repo_path}" if repo_path else "local://unknown"

    return ProjectInfo(
        project_id=project_id,
        slug=slug,
        name=name,
        provider=provider,
        html_url=html_url,
    )


def _resolve_project(conn: psycopg.Connection) -> ProjectInfo:
    info = _project_defaults()
    existing = conn.execute(
        "SELECT id FROM projects WHERE id = %s",
        (info.project_id,),
    ).fetchone()
    if existing:
        return info

    slug_row = conn.execute(
        "SELECT id FROM projects WHERE slug = %s",
        (info.slug,),
    ).fetchone()
    if slug_row:
        if os.environ.get(PROJECT_ID_ENV):
            raise ValueError(
                f"{PROJECT_ID_ENV}={info.project_id} not found, "
                f"but slug '{info.slug}' exists as project '{slug_row['id']}'."
            )
        info.project_id = slug_row["id"]
        return info

    conn.execute(
        """
        INSERT INTO projects (id, slug, name, provider, html_url)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (info.project_id, info.slug, info.name, info.provider, info.html_url),
    )
    return info


def _analysis_values(meta: Optional[AnalysisMeta]) -> Tuple[object, ...]:
    values: Dict[str, object] = {name: None for name in ANALYSIS_COLUMN_NAMES}
    if not meta:
        return tuple(values[name] for name in ANALYSIS_COLUMN_NAMES)

    values["analysis_mode"] = meta.analysis_mode
    values["analysis_provider"] = meta.provider
    values["analysis_model"] = meta.model
    values["analysis_prompt_version"] = meta.prompt_version
    values["analysis_timestamp"] = meta.analysis_timestamp
    values["analysis_duration_ms"] = meta.analysis_duration_ms
    values["analysis_fallback_reason"] = meta.fallback_reason

    if meta.token_usage:
        values["analysis_token_usage_input"] = meta.token_usage.input
        values["analysis_token_usage_output"] = meta.token_usage.output
        values["analysis_token_usage_cached"] = meta.token_usage.cached

    if meta.input_metrics:
        values["analysis_input_metrics_commit_message_chars"] = meta.input_metrics.commit_message_chars
        values["analysis_input_metrics_commit_message_lines"] = meta.input_metrics.commit_message_lines
        values["analysis_input_metrics_commit_message_tokens"] = meta.input_metrics.commit_message_tokens
        values["analysis_input_metrics_diff_files"] = meta.input_metrics.diff_files
        values["analysis_input_metrics_diff_insertions"] = meta.input_metrics.diff_insertions
        values["analysis_input_metrics_diff_deletions"] = meta.input_metrics.diff_deletions
        values["analysis_input_metrics_diff_total"] = meta.input_metrics.diff_total
        values["analysis_input_metrics_diff_hunks"] = meta.input_metrics.diff_hunks
        values["analysis_input_metrics_diff_chars"] = meta.input_metrics.diff_chars
        values["analysis_input_metrics_diff_lines"] = meta.input_metrics.diff_lines
        values["analysis_input_metrics_diff_tokens"] = meta.input_metrics.diff_tokens

    if meta.qualitative:
        def set_qual(prefix: str, signal: Optional[QualitativeSignal]) -> None:
            if not signal:
                return
            values[f"analysis_qualitative_{prefix}_score"] = signal.score
            values[f"analysis_qualitative_{prefix}_explanation"] = signal.explanation

        set_qual("technical_difficulty", meta.qualitative.technical_difficulty)
        set_qual("creativity", meta.qualitative.creativity)
        set_qual("mental_load", meta.qualitative.mental_load)
        set_qual("review_effort", meta.qualitative.review_effort)
        set_qual("ambiguity", meta.qualitative.ambiguity)

    return tuple(values[name] for name in ANALYSIS_COLUMN_NAMES)


def _qual_signal(score: object, explanation: object) -> Optional[QualitativeSignal]:
    if score is None and explanation is None:
        return None
    return QualitativeSignal(score=score, explanation=explanation)


def _analysis_meta_from_row(row: Dict[str, object]) -> Optional[AnalysisMeta]:
    if not any(row.get(name) is not None for name in ANALYSIS_COLUMN_NAMES):
        return None

    analysis_timestamp = row.get("analysis_timestamp")
    if isinstance(analysis_timestamp, datetime):
        analysis_timestamp = analysis_timestamp.isoformat()

    token_usage = None
    if (
        row.get("analysis_token_usage_input") is not None
        or row.get("analysis_token_usage_output") is not None
        or row.get("analysis_token_usage_cached") is not None
    ):
        token_usage = TokenUsage(
            input=row.get("analysis_token_usage_input"),
            output=row.get("analysis_token_usage_output"),
            cached=row.get("analysis_token_usage_cached"),
        )

    input_metrics = None
    if any(
        row.get(name) is not None
        for name in (
            "analysis_input_metrics_commit_message_chars",
            "analysis_input_metrics_commit_message_lines",
            "analysis_input_metrics_commit_message_tokens",
            "analysis_input_metrics_diff_files",
            "analysis_input_metrics_diff_insertions",
            "analysis_input_metrics_diff_deletions",
            "analysis_input_metrics_diff_total",
            "analysis_input_metrics_diff_hunks",
            "analysis_input_metrics_diff_chars",
            "analysis_input_metrics_diff_lines",
            "analysis_input_metrics_diff_tokens",
        )
    ):
        input_metrics = InputMetrics(
            commit_message_chars=row.get("analysis_input_metrics_commit_message_chars"),
            commit_message_lines=row.get("analysis_input_metrics_commit_message_lines"),
            commit_message_tokens=row.get("analysis_input_metrics_commit_message_tokens"),
            diff_files=row.get("analysis_input_metrics_diff_files"),
            diff_insertions=row.get("analysis_input_metrics_diff_insertions"),
            diff_deletions=row.get("analysis_input_metrics_diff_deletions"),
            diff_total=row.get("analysis_input_metrics_diff_total"),
            diff_hunks=row.get("analysis_input_metrics_diff_hunks"),
            diff_chars=row.get("analysis_input_metrics_diff_chars"),
            diff_lines=row.get("analysis_input_metrics_diff_lines"),
            diff_tokens=row.get("analysis_input_metrics_diff_tokens"),
        )

    qualitative = None
    if any(
        row.get(name) is not None
        for name in (
            "analysis_qualitative_technical_difficulty_score",
            "analysis_qualitative_technical_difficulty_explanation",
            "analysis_qualitative_creativity_score",
            "analysis_qualitative_creativity_explanation",
            "analysis_qualitative_mental_load_score",
            "analysis_qualitative_mental_load_explanation",
            "analysis_qualitative_review_effort_score",
            "analysis_qualitative_review_effort_explanation",
            "analysis_qualitative_ambiguity_score",
            "analysis_qualitative_ambiguity_explanation",
        )
    ):
        qualitative = QualitativeScores(
            technical_difficulty=_qual_signal(
                row.get("analysis_qualitative_technical_difficulty_score"),
                row.get("analysis_qualitative_technical_difficulty_explanation"),
            ),
            creativity=_qual_signal(
                row.get("analysis_qualitative_creativity_score"),
                row.get("analysis_qualitative_creativity_explanation"),
            ),
            mental_load=_qual_signal(
                row.get("analysis_qualitative_mental_load_score"),
                row.get("analysis_qualitative_mental_load_explanation"),
            ),
            review_effort=_qual_signal(
                row.get("analysis_qualitative_review_effort_score"),
                row.get("analysis_qualitative_review_effort_explanation"),
            ),
            ambiguity=_qual_signal(
                row.get("analysis_qualitative_ambiguity_score"),
                row.get("analysis_qualitative_ambiguity_explanation"),
            ),
        )

    return AnalysisMeta(
        analysis_mode=row.get("analysis_mode"),
        provider=row.get("analysis_provider"),
        model=row.get("analysis_model"),
        prompt_version=row.get("analysis_prompt_version"),
        analysis_timestamp=analysis_timestamp,
        analysis_duration_ms=row.get("analysis_duration_ms"),
        fallback_reason=row.get("analysis_fallback_reason"),
        token_usage=token_usage,
        input_metrics=input_metrics,
        qualitative=qualitative,
    )


def _row_to_artifact(row: Dict[str, object]) -> CommitArtifact:
    intent_summary = row.get("description") or row.get("summary") or ""
    technical_highlights = row.get("technical_highlights") or []
    is_breaking = row.get("is_breaking")
    return CommitArtifact(
        commit_hash=str(row["source_ref"]),
        schema_version=str(row.get("schema_version") or CommitArtifact.model_fields["schema_version"].default),
        intent_summary=str(intent_summary),
        category=row["category"],
        impact_scope=row["impact_scope"],
        is_breaking=bool(is_breaking) if is_breaking is not None else False,
        behavior_before=row.get("behavior_before"),
        behavior_after=row.get("behavior_after"),
        technical_highlights=list(technical_highlights),
        analysis_meta=_analysis_meta_from_row(row),
    )


def save_artifact_to_postgres(
    artifact: CommitArtifact,
    *,
    force: bool = True,
) -> str:
    sha = artifact.commit_hash
    tags: List[str] = [artifact.category.value, artifact.impact_scope.value]
    if artifact.is_breaking:
        tags.append("breaking")
    analysis_values = _analysis_values(artifact.analysis_meta)
    tool_version = __version__
    project = None
    with _connect() as conn:
        _ensure_schema(conn)
        project = _resolve_project(conn)
        if not force:
            existing = conn.execute(
                f"""
                SELECT 1 FROM {POSTGRES_TABLE}
                WHERE project_id = %s AND content_type = %s AND source_ref = %s
                """,
                (project.project_id, CONTENT_TYPE_COMMIT_ARTIFACT, sha),
            ).fetchone()
            if existing:
                raise FileExistsError(f"Artifact already exists for commit {sha[:8]}")

        artifact_id = f"{project.project_id}:{CONTENT_TYPE_COMMIT_ARTIFACT}:{sha}"
        conn.execute(
            f"""
            INSERT INTO {POSTGRES_TABLE} (
                id,
                project_id,
                content_type,
                source_ref,
                schema_version,
                generated_at,
                summary,
                description,
                why_it_matters,
                tags,
                signals,
                commit,
                category,
                impact_scope,
                is_breaking,
                behavior_before,
                behavior_after,
                technical_highlights,
                {ANALYSIS_COLUMN_INSERT},
                tool_version
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, {ANALYSIS_COLUMN_PLACEHOLDERS}, %s)
            ON CONFLICT (project_id, content_type, source_ref)
            DO UPDATE SET
                schema_version = EXCLUDED.schema_version,
                generated_at = EXCLUDED.generated_at,
                summary = EXCLUDED.summary,
                description = EXCLUDED.description,
                why_it_matters = EXCLUDED.why_it_matters,
                tags = EXCLUDED.tags,
                signals = EXCLUDED.signals,
                commit = EXCLUDED.commit,
                category = EXCLUDED.category,
                impact_scope = EXCLUDED.impact_scope,
                is_breaking = EXCLUDED.is_breaking,
                behavior_before = EXCLUDED.behavior_before,
                behavior_after = EXCLUDED.behavior_after,
                technical_highlights = EXCLUDED.technical_highlights,
                {ANALYSIS_COLUMN_UPDATES},
                tool_version = EXCLUDED.tool_version
            """,
            (
                artifact_id,
                project.project_id,
                CONTENT_TYPE_COMMIT_ARTIFACT,
                sha,
                artifact.schema_version,
                datetime.now(timezone.utc),
                artifact.intent_summary,
                artifact.intent_summary,
                None,
                tags,
                _json([]),
                _json({"sha": sha}),
                artifact.category.value,
                artifact.impact_scope.value,
                artifact.is_breaking,
                artifact.behavior_before,
                artifact.behavior_after,
                artifact.technical_highlights,
                *analysis_values,
                tool_version,
            ),
        )
    trace_manager.log_output_reference(
        kind="postgres_artifact",
        location=f"{POSTGRES_TABLE}:{project.project_id}:{sha}",
        metadata={"commit_summary": artifact.intent_summary, "project_id": project.project_id},
    )
    return sha


def load_artifact_from_postgres(commit_sha: str) -> Optional[CommitArtifact]:
    with _connect() as conn:
        _ensure_schema(conn)
        project = _resolve_project(conn)
        row = conn.execute(
            f"""
            SELECT
                source_ref,
                schema_version,
                summary,
                description,
                category,
                impact_scope,
                is_breaking,
                behavior_before,
                behavior_after,
                technical_highlights,
                {ANALYSIS_COLUMN_SELECT}
            FROM {POSTGRES_TABLE}
            WHERE project_id = %s AND content_type = %s AND source_ref = %s
            """,
            (project.project_id, CONTENT_TYPE_COMMIT_ARTIFACT, commit_sha),
        ).fetchone()
    if not row:
        return None
    return _row_to_artifact(row)


def artifact_exists_in_postgres(commit_sha: str) -> bool:
    with _connect() as conn:
        _ensure_schema(conn)
        project = _resolve_project(conn)
        row = conn.execute(
            f"""
            SELECT 1 FROM {POSTGRES_TABLE}
            WHERE project_id = %s AND content_type = %s AND source_ref = %s
            """,
            (project.project_id, CONTENT_TYPE_COMMIT_ARTIFACT, commit_sha),
        ).fetchone()
    return row is not None


def remove_artifact_from_postgres(commit_sha: str) -> bool:
    with _connect() as conn:
        _ensure_schema(conn)
        project = _resolve_project(conn)
        result = conn.execute(
            f"""
            DELETE FROM {POSTGRES_TABLE}
            WHERE project_id = %s AND content_type = %s AND source_ref = %s
            """,
            (project.project_id, CONTENT_TYPE_COMMIT_ARTIFACT, commit_sha),
        )
    return result.rowcount > 0


def load_artifacts_for_range_postgres(
    commit_shas: List[str],
) -> Dict[str, Optional[CommitArtifact]]:
    result: Dict[str, Optional[CommitArtifact]] = {sha: None for sha in commit_shas}
    if not commit_shas:
        return result
    with _connect() as conn:
        _ensure_schema(conn)
        project = _resolve_project(conn)
        rows = conn.execute(
            f"""
            SELECT
                source_ref,
                schema_version,
                summary,
                description,
                category,
                impact_scope,
                is_breaking,
                behavior_before,
                behavior_after,
                technical_highlights,
                {ANALYSIS_COLUMN_SELECT}
            FROM {POSTGRES_TABLE}
            WHERE project_id = %s AND content_type = %s AND source_ref = ANY(%s)
            """,
            (project.project_id, CONTENT_TYPE_COMMIT_ARTIFACT, commit_shas),
        ).fetchall()
    for row in rows:
        result[row["source_ref"]] = _row_to_artifact(row)
    return result
