"""Helpers for computing commit analysis metrics."""

from __future__ import annotations

from typing import Optional

from ..core import CommitDiff, CommitInfo
from ..core.artifact import InputMetrics

TOKENS_PER_WORD_ESTIMATE = 3


def _count_words(text: str) -> int:
    return len(text.split()) if text else 0


def _estimate_tokens(text: str) -> int:
    return _count_words(text) * TOKENS_PER_WORD_ESTIMATE


def build_input_metrics(
    commit: CommitInfo,
    diff: Optional[CommitDiff],
    diff_patch: str,
) -> InputMetrics:
    message = commit.full_message or ""
    message_lines = len(message.splitlines()) if message else 0

    diff_files = len(diff.files) if diff else 0
    diff_insertions = diff.stat.insertions if diff else 0
    diff_deletions = diff.stat.deletions if diff else 0
    diff_total = diff_insertions + diff_deletions
    diff_hunks = (
        sum(len(file.hunks) for file in diff.files) if diff else 0
    )

    diff_lines = len(diff_patch.splitlines()) if diff_patch else 0
    diff_chars = len(diff_patch) if diff_patch else 0

    return InputMetrics(
        commit_message_chars=len(message),
        commit_message_lines=message_lines,
        commit_message_tokens=_estimate_tokens(message),
        diff_files=diff_files,
        diff_insertions=diff_insertions,
        diff_deletions=diff_deletions,
        diff_total=diff_total,
        diff_hunks=diff_hunks,
        diff_chars=diff_chars,
        diff_lines=diff_lines,
        diff_tokens=_estimate_tokens(diff_patch),
    )
