"""Compatibility wrapper for LLM prompt helpers.

This module re-exports prompt builders that now live in
more focused modules (prompts_commit, prompts_release_note).
"""

from __future__ import annotations

from .prompts_commit import (
    COMMIT_ANALYSIS_SYSTEM_PROMPT,
    build_batch_analysis_prompt,
    build_commit_analysis_prompt,
)
from .prompts_release_note import (
    RELEASE_NOTE_SYSTEM_PROMPT,
    build_release_note_synthesis_prompt,
    format_artifacts_for_synthesis,
)

__all__ = [
    "COMMIT_ANALYSIS_SYSTEM_PROMPT",
    "build_commit_analysis_prompt",
    "build_batch_analysis_prompt",
    "RELEASE_NOTE_SYSTEM_PROMPT",
    "build_release_note_synthesis_prompt",
    "format_artifacts_for_synthesis",
]


