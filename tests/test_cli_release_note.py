"""CLI tests for `gitsummary release-note latest`."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import pytest

from gitsummary.cli.commands import release_note as release_note_cmd
from gitsummary.core import TagInfo
from gitsummary.reports import (
    ReleaseNote,
    ReleaseNoteHeader,
    ReleaseNoteMetadata,
)


@pytest.fixture
def simple_release_note(simple_commit) -> ReleaseNote:
    """A minimal release note fixture."""
    return ReleaseNote(
        header=ReleaseNoteHeader(
            product_name="demo",
            version="v1.0.0",
            release_date="2024-03-01",
            theme="Test release",
        ),
        highlights=[],
        features=[],
        improvements=[],
        fixes=[],
        deprecations=[],
        known_issues=[],
        call_to_action=None,
        metadata=ReleaseNoteMetadata(
            revision_range="v0.9.0..v1.0.0",
            tip_commit=simple_commit.sha,
            commit_count=1,
            analyzed_count=1,
            source_commits=[],
        ),
    )


def test_release_note_latest_writes_html(
    tmp_path, monkeypatch, simple_commit, feature_artifact, simple_release_note
) -> None:
    """End-to-end happy path without prompts."""
    repo_root = tmp_path / "demo"
    repo_root.mkdir()
    output_dir = repo_root / "release-notes"

    tags = [
        TagInfo(
            name="v0.9.0",
            sha="prevsha",
            date=datetime(2024, 2, 1, tzinfo=timezone.utc),
            is_annotated=True,
        ),
        TagInfo(
            name="v1.0.0",
            sha="latestsha",
            date=datetime(2024, 3, 1, tzinfo=timezone.utc),
            is_annotated=True,
        ),
    ]

    monkeypatch.setattr(release_note_cmd, "fetch_tags", lambda: None)
    monkeypatch.setattr(release_note_cmd, "list_tags_by_date", lambda: tags)
    monkeypatch.setattr(release_note_cmd, "repository_root", lambda: repo_root)
    monkeypatch.setattr(
        release_note_cmd, "list_commits_in_range", lambda _: [simple_commit]
    )
    monkeypatch.setattr(
        release_note_cmd,
        "load_artifacts_for_range",
        lambda shas, **_kwargs: {simple_commit.sha: feature_artifact},
    )
    monkeypatch.setattr(
        release_note_cmd.ReporterService,
        "generate_llm_release_notes",
        lambda self, commits, artifacts, **kwargs: simple_release_note,
    )
    monkeypatch.setattr(release_note_cmd, "save_release_note", lambda sha, content: None)
    monkeypatch.setattr(release_note_cmd.webbrowser, "open", lambda url: True)

    release_note_cmd.release_note(
        target="latest",
        yes=True,
        no_fetch=True,
        output_dir=str(output_dir),
        no_open=True,
        use_llm=False,
        reanalyze=False,
        provider=None,
        model=None,
    )

    html_path = output_dir / "v1.0.0.html"
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "demo v1.0.0" in html
    assert simple_release_note.header.theme in html


def test_release_note_existing_uses_stored(
    tmp_path, monkeypatch, simple_commit, simple_release_note
) -> None:
    """When a release note exists, load and render without re-generation."""
    repo_root = tmp_path / "demo"
    repo_root.mkdir()
    output_dir = repo_root / "release-notes"

    tags = [
        TagInfo(
            name="v1.0.0",
            sha="latestsha",
            date=datetime(2024, 3, 1, tzinfo=timezone.utc),
            is_annotated=True,
        ),
    ]

    monkeypatch.setattr(release_note_cmd, "fetch_tags", lambda: None)
    monkeypatch.setattr(release_note_cmd, "list_tags_by_date", lambda: tags)
    monkeypatch.setattr(release_note_cmd, "repository_root", lambda: repo_root)
    monkeypatch.setattr(
        release_note_cmd,
        "list_commits_to_revision",
        lambda _: [simple_commit],
    )
    monkeypatch.setattr(
        release_note_cmd, "get_root_commit", lambda: simple_commit.sha
    )
    monkeypatch.setattr(
        release_note_cmd,
        "release_note_exists",
        lambda sha: True,
    )
    monkeypatch.setattr(
        release_note_cmd,
        "load_release_note",
        lambda sha: simple_release_note.to_yaml(),
    )
    # Ensure generation path is not used when note exists
    monkeypatch.setattr(
        release_note_cmd.ReporterService,
        "generate_llm_release_notes",
        lambda self, *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not regenerate")),
    )

    release_note_cmd.release_note(
        target="latest",
        yes=True,
        no_fetch=True,
        output_dir=str(output_dir),
        no_open=True,
        use_llm=False,
        reanalyze=False,
        provider=None,
        model=None,
    )

    html_path = output_dir / "v1.0.0.html"
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert simple_release_note.header.theme in html
