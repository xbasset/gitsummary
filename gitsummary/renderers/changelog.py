"""Renderers for changelog reports."""

from __future__ import annotations

from ..reporters import ChangelogReport


def format_changelog_markdown(revision_range: str, report: ChangelogReport) -> str:
    lines = [f"# Changelog {revision_range}", ""]

    if report.features:
        lines.append("## Features")
        for commit, artifact in report.features:
            breaking = " **[BREAKING]**" if artifact.is_breaking else ""
            lines.append(
                f"- **{artifact.intent_summary}** ({commit.short_sha}){breaking}"
            )
            if artifact.behavior_after:
                lines.append(f"  {artifact.behavior_after}")
        lines.append("")

    if report.fixes:
        lines.append("## Fixes")
        for commit, artifact in report.fixes:
            lines.append(f"- **{artifact.intent_summary}** ({commit.short_sha})")
        lines.append("")

    if report.security:
        lines.append("## Security")
        for commit, artifact in report.security:
            lines.append(f"- **{artifact.intent_summary}** ({commit.short_sha})")
        lines.append("")

    if report.breaking_changes:
        lines.append("## Breaking Changes")
        for commit, artifact in report.breaking_changes:
            lines.append(f"- **{artifact.intent_summary}** ({commit.short_sha})")
            if artifact.behavior_before and artifact.behavior_after:
                lines.append(f"  - Before: {artifact.behavior_before}")
                lines.append(f"  - After: {artifact.behavior_after}")
        lines.append("")

    other = report.refactors + report.performance + report.chores
    if other:
        lines.append("## Other")
        for commit, artifact in other:
            lines.append(f"- {artifact.intent_summary} ({commit.short_sha})")
        lines.append("")

    if report.unanalyzed:
        lines.append("## Unanalyzed")
        for commit in report.unanalyzed:
            lines.append(f"- {commit.summary} ({commit.short_sha})")
        lines.append("")

    return "\n".join(lines)
