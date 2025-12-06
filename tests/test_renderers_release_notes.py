"""Tests for release note renderers."""

from __future__ import annotations

from gitsummary.renderers import format_release_note_html
from gitsummary.reports import (
    ReleaseNote,
    ReleaseNoteHeader,
    ReleaseNoteMetadata,
)


def _sample_release_note() -> ReleaseNote:
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
            tip_commit="latestsha",
            commit_count=3,
            analyzed_count=3,
            source_commits=[],
        ),
    )


def test_format_release_note_html_contains_header() -> None:
    """Ensure HTML renderer includes key header content."""
    note = _sample_release_note()
    html = format_release_note_html(note)

    assert "demo v1.0.0" in html
    assert note.header.theme in html
    assert "Release Notes" in html
