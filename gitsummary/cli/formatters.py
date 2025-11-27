"""Output formatting functions for CLI display.

This module contains all formatting logic for displaying artifacts
and reports in various formats (human-readable, JSON, YAML, brief).
"""

from __future__ import annotations

from typing import Optional

import yaml

from ..core import CommitArtifact, CommitInfo


# ─────────────────────────────────────────────────────────────────────────────
# Artifact Formatters
# ─────────────────────────────────────────────────────────────────────────────


def format_artifact_human(
    artifact: CommitArtifact, commit: Optional[CommitInfo] = None
) -> str:
    """Format a CommitArtifact for human-readable display.

    Creates a visually appealing box-style output with key information.
    """
    short_sha = artifact.commit_hash[:7]
    lines = [
        f"╭─ {short_sha} {'─' * (50 - len(short_sha))}╮",
        f"│ {artifact.intent_summary[:50]:<50} │",
        "├" + "─" * 52 + "┤",
        f"│ Category:   {artifact.category.value:<38} │",
        f"│ Impact:     {artifact.impact_scope.value:<38} │",
        f"│ Breaking:   {'Yes' if artifact.is_breaking else 'No':<38} │",
    ]

    if artifact.behavior_before or artifact.behavior_after:
        lines.append("│" + " " * 52 + "│")
        if artifact.behavior_before:
            before_text = (
                artifact.behavior_before[:45] + "..."
                if len(artifact.behavior_before) > 45
                else artifact.behavior_before
            )
            lines.append(f"│ Before: {before_text:<43} │")
        if artifact.behavior_after:
            after_text = (
                artifact.behavior_after[:45] + "..."
                if len(artifact.behavior_after) > 45
                else artifact.behavior_after
            )
            lines.append(f"│ After:  {after_text:<43} │")

    if artifact.technical_highlights:
        lines.append("│" + " " * 52 + "│")
        lines.append("│ Technical:" + " " * 41 + "│")
        for highlight in artifact.technical_highlights[:3]:
            hl_text = highlight[:46] + "..." if len(highlight) > 46 else highlight
            lines.append(f"│   • {hl_text:<46} │")

    lines.append("╰" + "─" * 52 + "╯")
    return "\n".join(lines)


def format_artifact_brief(artifact: CommitArtifact) -> str:
    """Format a CommitArtifact as a one-line summary."""
    short_sha = artifact.commit_hash[:7]
    category = f"[{artifact.category.value}]"
    return f"{short_sha} {category:<12} {artifact.intent_summary[:60]}"


def format_artifact_yaml(artifact: CommitArtifact) -> str:
    """Format a CommitArtifact as YAML."""
    # Use mode='json' to get proper enum serialization
    data = artifact.model_dump(mode="json")
    return yaml.dump(
        data, default_flow_style=False, allow_unicode=True, sort_keys=False
    )


def format_artifact_json(artifact: CommitArtifact) -> str:
    """Format a CommitArtifact as JSON."""
    return artifact.model_dump_json(indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Report Formatters
# ─────────────────────────────────────────────────────────────────────────────


def format_commit_status(commit: CommitInfo, analyzed: bool) -> str:
    """Format a commit with its analysis status."""
    status = "✓" if analyzed else "○"
    return f"{status} {commit.short_sha} {commit.summary[:60]}"

