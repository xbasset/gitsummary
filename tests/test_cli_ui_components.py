"""Tests for CLI UX components."""

from __future__ import annotations

from gitsummary.cli.ui.components import UXState, render_status, spinner_enabled


def test_render_status_prefixes_icon() -> None:
    """Ensure status lines include icon."""
    assert render_status("Working", UXState.RUNNING).startswith("[..]")
    assert render_status("Done", UXState.SUCCESS).startswith("[OK]")
    assert render_status("Warn", UXState.WARNING).startswith("[!]")
    assert render_status("Err", UXState.ERROR).startswith("[X]")


def test_spinner_enabled_defaults_to_stdout(monkeypatch) -> None:
    """Spinner enablement respects stdout isatty."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    assert spinner_enabled() is True
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    assert spinner_enabled() is False
