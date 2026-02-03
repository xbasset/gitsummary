"""Tests for Postgres artifact storage.

These tests validate the structured-column Postgres schema integration
(no artifacts.raw_artifact).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pytest

from gitsummary.core import AnalysisMeta, CommitArtifact
from gitsummary.infrastructure import postgres as pg


class FakeCursor:
    def __init__(
        self,
        *,
        one: Optional[Dict[str, Any]] = None,
        all_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self._one = one
        self._all = all_rows or []
        self.rowcount = 0

    def fetchone(self) -> Optional[Dict[str, Any]]:
        return self._one

    def fetchall(self) -> List[Dict[str, Any]]:
        return self._all


class FakeConn:
    def __init__(self, responses: Optional[List[FakeCursor]] = None) -> None:
        self.calls: List[Tuple[str, object]] = []
        self._responses = responses or []

    def execute(self, sql: str, params: object = None) -> FakeCursor:
        self.calls.append((sql, params))
        if self._responses:
            return self._responses.pop(0)
        return FakeCursor()

    def __enter__(self) -> "FakeConn":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


def _project() -> pg.ProjectInfo:
    return pg.ProjectInfo(
        project_id="acme/repo",
        slug="acme/repo",
        name="repo",
        provider="github",
        html_url="https://github.com/acme/repo",
    )


class TestSaveArtifactToPostgres:
    def test_inserts_structured_columns_no_raw(
        self, monkeypatch: pytest.MonkeyPatch, feature_artifact: CommitArtifact
    ) -> None:
        conn = FakeConn()
        monkeypatch.setattr(pg, "_connect", lambda: conn)
        monkeypatch.setattr(pg, "_ensure_schema", lambda _conn: None)
        monkeypatch.setattr(pg, "_resolve_project", lambda _conn: _project())
        monkeypatch.setattr(pg, "_json", lambda value: value)

        sha = pg.save_artifact_to_postgres(feature_artifact)
        assert sha == feature_artifact.commit_hash
        assert len(conn.calls) == 1

        sql, params = conn.calls[0]
        assert "INSERT INTO" in sql
        assert "raw_artifact" not in sql
        assert "analysis_meta" in sql
        assert "tool_version" in sql

        assert isinstance(params, tuple)
        assert len(params) == 20

        project = _project()
        assert params[0] == f"{project.project_id}:{pg.CONTENT_TYPE_COMMIT_ARTIFACT}:{feature_artifact.commit_hash}"
        assert params[1] == project.project_id
        assert params[2] == pg.CONTENT_TYPE_COMMIT_ARTIFACT
        assert params[3] == feature_artifact.commit_hash
        assert params[6] == feature_artifact.intent_summary
        assert params[7] == feature_artifact.intent_summary
        assert params[12] == feature_artifact.category.value
        assert params[13] == feature_artifact.impact_scope.value
        assert params[14] == feature_artifact.is_breaking
        assert params[17] == feature_artifact.technical_highlights
        assert params[18] is None
        assert params[19] == pg.__version__

    def test_force_false_raises_if_existing(
        self, monkeypatch: pytest.MonkeyPatch, feature_artifact: CommitArtifact
    ) -> None:
        conn = FakeConn(responses=[FakeCursor(one={"exists": 1})])
        monkeypatch.setattr(pg, "_connect", lambda: conn)
        monkeypatch.setattr(pg, "_ensure_schema", lambda _conn: None)
        monkeypatch.setattr(pg, "_resolve_project", lambda _conn: _project())

        with pytest.raises(FileExistsError):
            pg.save_artifact_to_postgres(feature_artifact, force=False)

        assert len(conn.calls) == 1
        sql, _params = conn.calls[0]
        assert "SELECT 1" in sql

    def test_saves_analysis_meta_when_present(
        self, monkeypatch: pytest.MonkeyPatch, feature_artifact: CommitArtifact
    ) -> None:
        conn = FakeConn()
        monkeypatch.setattr(pg, "_connect", lambda: conn)
        monkeypatch.setattr(pg, "_ensure_schema", lambda _conn: None)
        monkeypatch.setattr(pg, "_resolve_project", lambda _conn: _project())
        monkeypatch.setattr(pg, "_json", lambda value: value)

        artifact = feature_artifact.model_copy(
            update={
                "analysis_meta": AnalysisMeta(
                    analysis_mode="llm",
                    provider="openai",
                    model="gpt-4.1",
                )
            }
        )

        pg.save_artifact_to_postgres(artifact)
        _sql, params = conn.calls[0]
        assert isinstance(params, tuple)
        meta = params[18]
        assert isinstance(meta, dict)
        assert meta["analysis_mode"] == "llm"
        assert meta["provider"] == "openai"
        assert meta["model"] == "gpt-4.1"


class TestLoadArtifactFromPostgres:
    def test_load_reconstructs_artifact_from_columns(
        self, monkeypatch: pytest.MonkeyPatch, feature_artifact: CommitArtifact
    ) -> None:
        row = {
            "source_ref": feature_artifact.commit_hash,
            "schema_version": feature_artifact.schema_version,
            "summary": "short summary",
            "description": feature_artifact.intent_summary,
            "category": feature_artifact.category.value,
            "impact_scope": feature_artifact.impact_scope.value,
            "is_breaking": feature_artifact.is_breaking,
            "behavior_before": feature_artifact.behavior_before,
            "behavior_after": feature_artifact.behavior_after,
            "technical_highlights": feature_artifact.technical_highlights,
            "analysis_meta": {"analysis_mode": "llm"},
        }
        conn = FakeConn(responses=[FakeCursor(one=row)])
        monkeypatch.setattr(pg, "_connect", lambda: conn)
        monkeypatch.setattr(pg, "_ensure_schema", lambda _conn: None)
        monkeypatch.setattr(pg, "_resolve_project", lambda _conn: _project())

        artifact = pg.load_artifact_from_postgres(feature_artifact.commit_hash)
        assert artifact is not None
        assert artifact.commit_hash == feature_artifact.commit_hash
        assert artifact.intent_summary == feature_artifact.intent_summary
        assert artifact.category == feature_artifact.category
        assert artifact.impact_scope == feature_artifact.impact_scope
        assert artifact.is_breaking == feature_artifact.is_breaking
        assert artifact.analysis_meta is not None
        assert artifact.analysis_meta.analysis_mode == "llm"

        sql, _params = conn.calls[0]
        assert "raw_artifact" not in sql

    def test_load_returns_none_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        conn = FakeConn(responses=[FakeCursor(one=None)])
        monkeypatch.setattr(pg, "_connect", lambda: conn)
        monkeypatch.setattr(pg, "_ensure_schema", lambda _conn: None)
        monkeypatch.setattr(pg, "_resolve_project", lambda _conn: _project())

        assert pg.load_artifact_from_postgres("missing") is None


class TestLoadArtifactsForRangePostgres:
    def test_range_populates_none_for_missing(
        self, monkeypatch: pytest.MonkeyPatch, feature_artifact: CommitArtifact
    ) -> None:
        wanted = [feature_artifact.commit_hash, "missing-sha"]
        rows = [
            {
                "source_ref": feature_artifact.commit_hash,
                "schema_version": feature_artifact.schema_version,
                "summary": feature_artifact.intent_summary,
                "description": feature_artifact.intent_summary,
                "category": feature_artifact.category.value,
                "impact_scope": feature_artifact.impact_scope.value,
                "is_breaking": feature_artifact.is_breaking,
                "behavior_before": feature_artifact.behavior_before,
                "behavior_after": feature_artifact.behavior_after,
                "technical_highlights": feature_artifact.technical_highlights,
                "analysis_meta": None,
            }
        ]
        conn = FakeConn(responses=[FakeCursor(all_rows=rows)])
        monkeypatch.setattr(pg, "_connect", lambda: conn)
        monkeypatch.setattr(pg, "_ensure_schema", lambda _conn: None)
        monkeypatch.setattr(pg, "_resolve_project", lambda _conn: _project())

        result = pg.load_artifacts_for_range_postgres(wanted)
        assert result[wanted[0]] is not None
        assert result[wanted[1]] is None

