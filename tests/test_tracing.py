import json

from gitsummary.tracing import TraceManager, load_trace_config


def test_load_trace_config_creates_default(tmp_path):
    cfg = load_trace_config(tmp_path)
    assert cfg.enabled is True
    config_path = tmp_path / ".gitsummary" / "config.yaml"
    assert config_path.exists()
    content = config_path.read_text(encoding="utf-8")
    assert "tracing" in content


def test_trace_manager_writes_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manager = TraceManager()
    manager.start_session(["gitsummary", "analyze"], cwd=tmp_path, repo_root=tmp_path)
    manager.log_git_command(
        ["status"],
        cwd=tmp_path,
        returncode=0,
        stdout="clean\n",
        stderr="",
        duration_seconds=0.01,
        success=True,
    )
    manager.finish_session(status="completed", exit_code=0)

    log_files = list((tmp_path / ".gitsummary").glob("*.log"))
    assert log_files, "trace log file should be created"
    payload = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert payload["exit_code"] == 0
    events = payload["events"]
    assert any(event["event"] == "git_command" for event in events)
