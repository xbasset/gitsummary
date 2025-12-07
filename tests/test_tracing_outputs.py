from gitsummary.cli.commands import generate
from gitsummary.infrastructure import notes


class DummyTraceManager:
    def __init__(self) -> None:
        self.calls = []

    def log_output_reference(self, *, kind: str, location: str, metadata=None) -> None:
        self.calls.append(
            {"kind": kind, "location": location, "metadata": metadata or {}}
        )


def test_write_output_logs_file_destination(monkeypatch, tmp_path):
    dummy_trace = DummyTraceManager()
    monkeypatch.setattr(generate, "trace_manager", dummy_trace)
    output_path = tmp_path / "report.md"

    generate._write_output(
        "hello",
        str(output_path),
        kind="changelog_report",
        format_hint="markdown",
        metadata={"revision_range": "v1..v2"},
    )

    assert output_path.read_text(encoding="utf-8") == "hello"
    assert dummy_trace.calls == [
        {
            "kind": "changelog_report",
            "location": str(output_path.resolve()),
            "metadata": {"revision_range": "v1..v2", "format": "markdown"},
        }
    ]


def test_write_output_logs_stdout(monkeypatch, capsys):
    dummy_trace = DummyTraceManager()
    monkeypatch.setattr(generate, "trace_manager", dummy_trace)

    generate._write_output(
        "hi there",
        None,
        kind="impact_report",
        format_hint="json",
    )

    captured = capsys.readouterr()
    assert "hi there" in captured.out
    assert dummy_trace.calls == [
        {
            "kind": "impact_report_stdout",
            "location": "stdout",
            "metadata": {"format": "json"},
        }
    ]


def test_save_release_note_traces_output(monkeypatch):
    dummy_trace = DummyTraceManager()
    monkeypatch.setattr(notes, "trace_manager", dummy_trace)
    writes = []
    monkeypatch.setattr(
        notes,
        "notes_write",
        lambda sha, content, notes_ref: writes.append((sha, content, notes_ref)),
    )

    notes.save_release_note("abc123", "content")

    assert writes == [("abc123", "content", notes.RELEASE_NOTE_NOTES_REF)]
    assert dummy_trace.calls == [
        {
            "kind": "git_note_release_note",
            "location": f"{notes.RELEASE_NOTE_NOTES_REF}:abc123",
            "metadata": {},
        }
    ]
