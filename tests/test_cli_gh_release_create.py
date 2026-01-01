from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gitsummary.cli.commands import gh as gh_cmd
from gitsummary.core import TagInfo


@dataclass
class _RunCall:
    args: list[str]
    check: bool


def test_gh_release_create_generates_notes_and_calls_gh(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange: pretend tags exist so range is inferred.
    tags = [
        TagInfo(
            name="v0.4.0",
            sha="a" * 40,
            date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            is_annotated=True,
        ),
        TagInfo(
            name="v0.5.0",
            sha="b" * 40,
            date=datetime(2025, 2, 1, tzinfo=timezone.utc),
            is_annotated=True,
        ),
    ]
    monkeypatch.setattr(gh_cmd, "fetch_tags", lambda: None)
    monkeypatch.setattr(gh_cmd, "list_tags_by_date", lambda: tags)

    # Make release note generation deterministic and fast.
    monkeypatch.setattr(
        gh_cmd.ci_cmd,
        "_build_release_notes_output",
        lambda *args, **kwargs: ("# Notes\n\nHello\n", "markdown"),
    )

    calls: list[_RunCall] = []

    def fake_run(args, check=False, **_kwargs):
        calls.append(_RunCall(args=list(args), check=bool(check)))

        class _P:
            returncode = 0

        return _P()

    monkeypatch.setattr(gh_cmd.subprocess, "run", fake_run)

    # Act
    gh_cmd.release_create(
        tag="v0.5.0",
        revision_range=None,
        title="v0.5.0",
        draft=False,
        prerelease=False,
        target=None,
        dry_run=False,
        no_fetch=True,
        use_llm=False,
        provider_name=None,
        model=None,
        compute_missing=False,
        reanalyze_existing=False,
    )

    # Assert
    assert calls, "expected gh to be invoked"
    cmd = calls[0].args
    assert cmd[:4] == ["gh", "release", "create", "v0.5.0"]
    assert "--notes-file" in cmd
    notes_idx = cmd.index("--notes-file") + 1
    notes_path = Path(cmd[notes_idx])
    # Temp file should be cleaned up after the command.
    assert not notes_path.exists()

