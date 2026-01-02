"""PostgreSQL storage for commit artifacts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from .. import __version__
from ..core import CommitArtifact
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
    return psycopg.connect(_get_dsn(), row_factory=dict_row)


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
            why_it_matters text,
            tags text[] NOT NULL DEFAULT '{{}}'::text[],
            signals jsonb NOT NULL DEFAULT '[]'::jsonb,
            commit jsonb,
            raw_artifact jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (project_id, content_type, source_ref)
        )
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


def _artifact_to_record(artifact: CommitArtifact) -> Dict[str, object]:
    data = artifact.model_dump(mode="json")
    data["tool_version"] = __version__
    return data


def _record_to_artifact(data: Dict[str, object]) -> CommitArtifact:
    data.pop("schema_version", None)
    data.pop("tool_version", None)
    return CommitArtifact(**data)


def save_artifact_to_postgres(
    artifact: CommitArtifact,
    *,
    force: bool = True,
) -> str:
    sha = artifact.commit_hash
    payload = _artifact_to_record(artifact)
    tags: List[str] = [artifact.category.value, artifact.impact_scope.value]
    if artifact.is_breaking:
        tags.append("breaking")
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
                why_it_matters,
                tags,
                signals,
                commit,
                raw_artifact
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (project_id, content_type, source_ref)
            DO UPDATE SET
                schema_version = EXCLUDED.schema_version,
                generated_at = EXCLUDED.generated_at,
                summary = EXCLUDED.summary,
                why_it_matters = EXCLUDED.why_it_matters,
                tags = EXCLUDED.tags,
                signals = EXCLUDED.signals,
                commit = EXCLUDED.commit,
                raw_artifact = EXCLUDED.raw_artifact
            """,
            (
                artifact_id,
                project.project_id,
                CONTENT_TYPE_COMMIT_ARTIFACT,
                sha,
                artifact.schema_version,
                datetime.now(timezone.utc),
                artifact.intent_summary,
                None,
                tags,
                Json([]),
                Json({"sha": sha}),
                Json(payload),
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
            SELECT raw_artifact FROM {POSTGRES_TABLE}
            WHERE project_id = %s AND content_type = %s AND source_ref = %s
            """,
            (project.project_id, CONTENT_TYPE_COMMIT_ARTIFACT, commit_sha),
        ).fetchone()
    if not row:
        return None
    data = row["raw_artifact"]
    return _record_to_artifact(data)


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
            SELECT source_ref, raw_artifact FROM {POSTGRES_TABLE}
            WHERE project_id = %s AND content_type = %s AND source_ref = ANY(%s)
            """,
            (project.project_id, CONTENT_TYPE_COMMIT_ARTIFACT, commit_shas),
        ).fetchall()
    for row in rows:
        result[row["source_ref"]] = _record_to_artifact(row["raw_artifact"])
    return result
