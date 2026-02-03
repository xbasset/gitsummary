"""CLI tests for `gitsummary generate feed`."""

from __future__ import annotations

from pathlib import Path

from gitsummary.cli.commands import generate as generate_cmd
from gitsummary.reporters.feed import ArtifactFeedBuilder


def test_generate_feed_writes_default_file(
    tmp_path, monkeypatch, simple_commit, feature_artifact
) -> None:
    """Ensure feed command writes HTML to default location."""
    repo_root = tmp_path / "demo-project"
    repo_root.mkdir()

    monkeypatch.setattr(
        generate_cmd, "repository_root", lambda: repo_root
    )
    monkeypatch.setattr(
        generate_cmd,
        "list_commits_in_range",
        lambda range_: [simple_commit],
    )
    monkeypatch.setattr(
        generate_cmd,
        "load_artifacts_for_range",
        lambda shas, **_kwargs: {simple_commit.sha: feature_artifact},
    )

    builder = ArtifactFeedBuilder()
    feed = builder.build([simple_commit], {simple_commit.sha: feature_artifact})
    monkeypatch.setattr(
        generate_cmd.ReporterService,
        "generate_artifact_feed",
        lambda self, commits, artifacts, include_unanalyzed=True: feed,
    )

    generate_cmd.generate_feed(
        "main~1..main",
        output_file=None,
        skip_unanalyzed=False,
        open_browser=False,
    )

    output_file = repo_root / "demo-project-feed.html"
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert simple_commit.short_sha in content
