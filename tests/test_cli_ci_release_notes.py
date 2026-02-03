from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import pytest

from gitsummary.core import CommitArtifact, CommitInfo
from gitsummary.core.enums import ChangeCategory, ImpactScope
from gitsummary.cli.commands import ci as ci_cmd


def _commit(sha: str, summary: str) -> CommitInfo:
    return CommitInfo(
        sha=sha,
        short_sha=sha[:7],
        author_name="A",
        author_email="a@example.com",
        date=datetime.now(timezone.utc),
        summary=summary,
        body="",
        parent_shas=[],
    )


def _artifact(sha: str) -> CommitArtifact:
    return CommitArtifact(
        commit_hash=sha,
        intent_summary=f"Intent for {sha[:7]}",
        category=ChangeCategory.CHORE,
        impact_scope=ImpactScope.INTERNAL,
        is_breaking=False,
        technical_highlights=[],
    )


def test_ci_release_notes_reuses_notes_and_computes_missing_in_memory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commits = [_commit("a" * 40, "first"), _commit("b" * 40, "second")]

    def fake_list_commits_in_range(_range: str):
        return commits

    notes_artifacts: Dict[str, Optional[CommitArtifact]] = {
        commits[0].sha: _artifact(commits[0].sha),
        commits[1].sha: None,
    }

    def fake_load_artifacts_for_range(shas, **_kwargs):
        return {sha: notes_artifacts.get(sha) for sha in shas}

    analyzed = []

    class FakeAnalyzer:
        def __init__(self, *args, **kwargs):
            pass

        def analyze(self, commit, diff):
            analyzed.append(commit.sha)
            return _artifact(commit.sha)

    class FakeReporter:
        def generate_llm_release_notes(self, commits, artifacts, **kwargs):
            # Minimal contract: return something renderable by markdown formatter.
            from gitsummary.reports import ReleaseNote
            from gitsummary.reports.release_notes.model import ReleaseNoteHeader, ReleaseNoteMetadata

            header = ReleaseNoteHeader(
                product_name="P",
                version="v1.0.0",
                release_date="2025-01-01",
                theme="Theme",
            )
            metadata = ReleaseNoteMetadata(
                revision_range="x..y",
                tip_commit=commits[0].sha,
                commit_count=len(commits),
                analyzed_count=sum(1 for a in artifacts.values() if a is not None),
                source_commits=[],
            )
            return ReleaseNote(
                header=header,
                metadata=metadata,
                highlights=[],
                features=[],
                improvements=[],
                fixes=[],
                deprecations=[],
                known_issues=[],
                call_to_action=None,
            )

    def fake_get_commit_diff(_sha: str):
        return object()

    monkeypatch.setattr(ci_cmd, "list_commits_in_range", fake_list_commits_in_range)
    monkeypatch.setattr(ci_cmd, "load_artifacts_for_range", fake_load_artifacts_for_range)
    monkeypatch.setattr(ci_cmd, "get_commit_diff", fake_get_commit_diff)
    monkeypatch.setattr(ci_cmd, "AnalyzerService", FakeAnalyzer)
    monkeypatch.setattr(ci_cmd, "ReporterService", FakeReporter)
    monkeypatch.setattr(ci_cmd, "repository_root", lambda: tmp_path)

    out_file = tmp_path / "out.md"
    ci_cmd.release_notes("x..y", output_file=str(out_file), use_llm=False)

    captured = capsys.readouterr()
    assert "Release notes written to" in captured.out
    assert out_file.read_text(encoding="utf-8")
    assert analyzed == [commits[1].sha]
