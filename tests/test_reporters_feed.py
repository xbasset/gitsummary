"""Tests for the artifact feed builder and report."""

from __future__ import annotations

from gitsummary.reporters.feed import ArtifactFeedBuilder


def test_feed_counts_include_missing(
    simple_commit, docs_commit, feature_artifact
) -> None:
    """Feed should include missing artifacts by default."""
    builder = ArtifactFeedBuilder()
    report = builder.build(
        [simple_commit, docs_commit],
        {
            simple_commit.sha: feature_artifact,
            docs_commit.sha: None,
        },
    )

    assert report.total_commits == 2
    assert report.analyzed_count == 1
    assert report.missing_count == 1
    assert report.items[0].technical_highlights  # carries through highlights


def test_feed_can_skip_unanalyzed(simple_commit, docs_commit, feature_artifact) -> None:
    """Missing artifacts can be omitted when requested."""
    builder = ArtifactFeedBuilder()
    report = builder.build(
        [simple_commit, docs_commit],
        {
            simple_commit.sha: feature_artifact,
            docs_commit.sha: None,
        },
        include_unanalyzed=False,
    )

    assert report.total_commits == 1
    assert report.missing_count == 0
    assert all(item.analyzed for item in report.items)
