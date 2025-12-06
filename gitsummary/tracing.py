"""Tracing utilities for CLI operations.

This module records structured trace events for each CLI invocation so we can
inspect what happened: commands executed, git calls, LLM interactions, user
prompts, and produced artifacts. Traces are written as JSON documents into
``.gitsummary/*.log`` under the repository root (or current working directory
when the repo root cannot be determined).
"""

from __future__ import annotations

import atexit
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

TRACE_SCHEMA_VERSION = "0.1.0"


def _utcnow() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _isoformat(ts: datetime) -> str:
    """Return ISO-8601 timestamp with Z suffix."""
    return ts.isoformat().replace("+00:00", "Z")


def _bool_env(var: str) -> Optional[bool]:
    """Parse a boolean environment variable if present."""
    value = os.environ.get(var)
    if value is None:
        return None
    value = value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


def _truncate(text: Optional[str], limit: int = 2000) -> Optional[str]:
    """Truncate long text for trace safety."""
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [truncated {len(text) - limit} chars]"


def _make_json_safe(value: Any) -> Any:
    """Convert common structured objects into JSON-safe data."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()  # type: ignore[attr-defined]
        except Exception:
            pass
    if isinstance(value, dict):
        return {k: _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]
    return value


@dataclass
class TraceConfig:
    """Configuration for tracing."""

    enabled: bool = True
    log_dir: Path = Path(".gitsummary")


def load_trace_config(base_dir: Path) -> TraceConfig:
    """Load tracing config from .gitsummary/config.yaml, creating defaults.

    The file structure is kept minimal to stay forward compatible:

    tracing:
      enabled: true
    """
    cfg_dir = base_dir / ".gitsummary"
    cfg_path = cfg_dir / "config.yaml"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    data: Dict[str, Any] = {}
    if cfg_path.exists():
        try:
            with cfg_path.open("r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
                if isinstance(loaded, dict):
                    data = loaded
        except Exception:
            data = {}

    tracing_data = data.get("tracing", {}) if isinstance(data, dict) else {}
    enabled = tracing_data.get("enabled", True)

    # Environment variable override
    env_override = _bool_env("GITSUMMARY_TRACING_ENABLED")
    if env_override is not None:
        enabled = env_override

    config = TraceConfig(enabled=bool(enabled), log_dir=cfg_dir)

    # Write defaults if file was missing
    if not cfg_path.exists():
        cfg_path.write_text(
            yaml.dump({"tracing": {"enabled": config.enabled}}, sort_keys=False),
            encoding="utf-8",
        )

    return config


@dataclass
class TraceEvent:
    """Single trace event."""

    event: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dict."""
        return {
            "event": self.event,
            "timestamp": _isoformat(self.timestamp),
            "data": self.data,
        }


@dataclass
class TraceSession:
    """In-memory trace session."""

    session_id: str
    command: List[str]
    cwd: Path
    repo_root: Optional[Path]
    started_at: datetime
    schema_version: str = TRACE_SCHEMA_VERSION
    events: List[TraceEvent] = field(default_factory=list)
    ended_at: Optional[datetime] = None
    status: Optional[str] = None
    exit_code: Optional[int] = None
    log_path: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the session to a dict."""
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "command": self.command,
            "cwd": str(self.cwd),
            "repo_root": str(self.repo_root) if self.repo_root else None,
            "started_at": _isoformat(self.started_at),
            "ended_at": _isoformat(self.ended_at) if self.ended_at else None,
            "status": self.status,
            "exit_code": self.exit_code,
            "events": [event.to_dict() for event in self.events],
        }

    def append(self, event: TraceEvent) -> None:
        """Append an event to the session."""
        self.events.append(event)


class TraceManager:
    """Coordinator for trace sessions."""

    def __init__(self) -> None:
        self._session: Optional[TraceSession] = None
        self._config: Optional[TraceConfig] = None
        self._exit_hook_registered = False

    @property
    def session(self) -> Optional[TraceSession]:
        return self._session

    @property
    def enabled(self) -> bool:
        return bool(self._config and self._config.enabled)

    def start_session(
        self,
        argv: List[str],
        *,
        cwd: Optional[Path] = None,
        repo_root: Optional[Path] = None,
        tool_version: Optional[str] = None,
    ) -> None:
        """Start a new trace session if enabled."""
        if self._session is not None:
            return

        cwd = cwd or Path.cwd()
        base_dir = repo_root or cwd
        self._config = load_trace_config(base_dir)

        if not self._config.enabled:
            return

        started_at = _utcnow()
        session_id = uuid.uuid4().hex
        log_dir = self._config.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_name = f"{started_at.strftime('%Y%m%dT%H%M%SZ')}-{session_id[:8]}.log"
        log_path = log_dir / log_name

        session = TraceSession(
            session_id=session_id,
            command=list(argv),
            cwd=cwd,
            repo_root=repo_root,
            started_at=started_at,
            log_path=log_path,
        )
        session.append(
            TraceEvent(
                event="command_invocation",
                timestamp=started_at,
                data={
                    "argv": argv,
                    "tool_version": tool_version,
                    "python_version": sys.version,
                },
            )
        )
        self._session = session

        if not self._exit_hook_registered:
            atexit.register(self.finish_session)
            self._exit_hook_registered = True

    def finish_session(self, *, status: str = "completed", exit_code: int = 0) -> None:
        """Finalize and flush the current session."""
        if self._session is None:
            return
        if self._session.ended_at is not None:
            return

        self._session.ended_at = _utcnow()
        self._session.status = status
        self._session.exit_code = exit_code

        log_path = self._session.log_path
        if log_path is not None:
            try:
                with log_path.open("w", encoding="utf-8") as f:
                    for event in [
                        TraceEvent(
                            event="session_summary",
                            timestamp=self._session.ended_at,
                            data={"status": status, "exit_code": exit_code},
                        )
                    ]:
                        self._session.append(event)
                    json.dump(self._session.to_dict(), f, ensure_ascii=True)
            except Exception:
                # Avoid interfering with CLI operation if logging fails
                pass

    def _append_event(self, event: str, data: Dict[str, Any]) -> None:
        if not self._session:
            return
        self._session.append(TraceEvent(event=event, timestamp=_utcnow(), data=data))

    def log_git_command(
        self,
        args: List[str],
        *,
        cwd: Optional[Path],
        returncode: int,
        stdout: Optional[str],
        stderr: Optional[str],
        duration_seconds: float,
        success: bool,
    ) -> None:
        """Record a git command execution."""
        if not self.enabled:
            return
        self._append_event(
            "git_command",
            {
                "args": args,
                "cwd": str(cwd) if cwd else None,
                "returncode": returncode,
                "stdout": _truncate(stdout),
                "stderr": _truncate(stderr),
                "duration_seconds": duration_seconds,
                "success": success,
            },
        )

    def log_llm_call(
        self,
        *,
        provider: Optional[str],
        model: Optional[str],
        system_prompt: Optional[str],
        prompt: Optional[str],
        input_context: Optional[Dict[str, Any]],
        response: Optional[Dict[str, Any]],
        raw_text: Optional[str],
        refusal: Optional[str],
        token_usage: Optional[Dict[str, Any]],
        success: bool,
        duration_seconds: float,
    ) -> None:
        """Record an LLM call."""
        if not self.enabled:
            return
        self._append_event(
            "llm_call",
            {
                "provider": provider,
                "model": model,
                "system_prompt": system_prompt,
                "prompt": prompt,
                "input_context": _make_json_safe(input_context),
                "response": _make_json_safe(response),
                "raw_text": _truncate(raw_text),
                "refusal": refusal,
                "token_usage": _make_json_safe(token_usage),
                "success": success,
                "duration_seconds": duration_seconds,
            },
        )

    def log_user_interaction(
        self,
        *,
        action: str,
        prompt: Optional[str],
        response: Any,
    ) -> None:
        """Record user interaction such as confirmations."""
        if not self.enabled:
            return
        self._append_event(
            "user_interaction",
            {
                "action": action,
                "prompt": prompt,
                "response": response,
            },
        )

    def log_output_reference(
        self,
        *,
        kind: str,
        location: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a reference to produced output (file path, git notes, etc.)."""
        if not self.enabled:
            return
        self._append_event(
            "output_reference",
            {"kind": kind, "location": location, "metadata": metadata or {}},
        )

    def log_error(self, *, message: str, detail: Optional[str] = None) -> None:
        """Record an error without raising."""
        if not self.enabled:
            return
        self._append_event("error", {"message": message, "detail": detail})

    def attach_repo_root(self, repo_root: Path) -> None:
        """Update repo root after session start (best-effort)."""
        if self._session is None:
            return
        self._session.repo_root = repo_root


trace_manager = TraceManager()
