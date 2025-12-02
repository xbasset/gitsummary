"""HTML renderer tests for the artifact feed."""

from __future__ import annotations

from gitsummary.renderers import format_artifact_feed_html
from gitsummary.reporters.feed import ArtifactFeedBuilder


def test_feed_renderer_includes_cta_for_missing(
    simple_commit, docs_commit, feature_artifact
) -> None:
    """Missing artifacts should surface a CTA command."""
    builder = ArtifactFeedBuilder()
    report = builder.build(
        [simple_commit, docs_commit],
        {
            simple_commit.sha: feature_artifact,
            docs_commit.sha: None,
        },
    )

    html = format_artifact_feed_html("demo", "v1..v2", report)

    assert "Missing artifacts detected" in html
    assert "gitsummary analyze v1..v2" in html
    assert docs_commit.short_sha in html


def test_feed_renderer_surfaces_highlights(simple_commit, feature_artifact) -> None:
    """Technical highlights should be rendered for analyzed commits."""
    builder = ArtifactFeedBuilder()
    report = builder.build(
        [simple_commit],
        {simple_commit.sha: feature_artifact},
    )

    html = format_artifact_feed_html("demo", "main~3..main", report)

    assert "Technical notes" in html
    for highlight in feature_artifact.technical_highlights:
        assert highlight in html
