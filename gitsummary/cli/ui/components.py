"""CLI UX components for consistent status and feedback."""

from __future__ import annotations

import itertools
import sys
import threading
import time
from contextlib import contextmanager
from enum import Enum
from typing import Iterator, Optional

import typer


class UXState(str, Enum):
    """Canonical CLI UX states for consistent rendering."""

    STARTING = "starting"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


_STATE_ICONS = {
    UXState.STARTING: "[..]",
    UXState.RUNNING: "[..]",
    UXState.SUCCESS: "[OK]",
    UXState.WARNING: "[!]",
    UXState.ERROR: "[X]",
    UXState.INFO: "[i]",
}

_STATE_COLORS = {
    UXState.STARTING: typer.colors.CYAN,
    UXState.RUNNING: typer.colors.CYAN,
    UXState.SUCCESS: typer.colors.GREEN,
    UXState.WARNING: typer.colors.YELLOW,
    UXState.ERROR: typer.colors.RED,
    UXState.INFO: typer.colors.BLUE,
}


def render_status(message: str, state: UXState = UXState.INFO) -> str:
    """Return a single-line status with icon."""
    icon = _STATE_ICONS.get(state, "[ ]")
    return f"{icon} {message}"


def echo_status(message: str, state: UXState = UXState.INFO) -> None:
    """Print a status line with standard coloring."""
    text = render_status(message, state)
    color = _STATE_COLORS.get(state)
    typer.secho(text, fg=color)


def spinner_enabled(enabled: Optional[bool] = None) -> bool:
    """Determine if spinners should be shown."""
    if enabled is not None:
        return enabled
    return sys.stdout.isatty()


def _spinner_frames() -> Iterator[str]:
    frames = "|/-\\"
    yield from itertools.cycle(frames)


@contextmanager
def spinner(
    message: str,
    *,
    final_state: UXState = UXState.SUCCESS,
    enabled: Optional[bool] = None,
) -> Iterator[None]:
    """Display a lightweight spinner while a block runs.

    Falls back to a single status line when spinners are disabled.
    """
    if not spinner_enabled(enabled):
        echo_status(message, UXState.RUNNING)
        try:
            yield
            echo_status(message, final_state)
        except Exception:
            echo_status(message, UXState.ERROR)
            raise
        return

    stop = threading.Event()
    frames = _spinner_frames()

    def _run() -> None:
        while not stop.is_set():
            frame = next(frames)
            sys.stdout.write(f"\r[{frame}] {message}")
            sys.stdout.flush()
            time.sleep(0.12)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    try:
        yield
        stop.set()
        thread.join()
        sys.stdout.write(f"\r{render_status(message, final_state)}\n")
        sys.stdout.flush()
    except Exception:
        stop.set()
        thread.join()
        sys.stdout.write(f"\r{render_status(message, UXState.ERROR)}\n")
        sys.stdout.flush()
        raise
