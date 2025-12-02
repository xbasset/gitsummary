"""Renderers for impact reports."""

from __future__ import annotations

from ..reporters import ImpactReport


def format_impact_markdown(revision_range: str, report: ImpactReport) -> str:
    lines = [
        f"# Impact Analysis: {revision_range}",
        "",
        "## Summary",
        f"- **Total commits:** {report.total_commits}",
        f"- **Analyzed:** {report.analyzed_count}",
        f"- **Breaking changes:** {report.breaking_count}",
        "",
        "## Impact Distribution",
    ]

    for scope, count in sorted(
        report.scope_distribution.items(), key=lambda x: -x[1]
    ):
        lines.append(f"- {scope}: {count}")

    if report.technical_highlights:
        lines.append("")
        lines.append("## Technical Highlights")
        for hl in report.technical_highlights[:10]:
            lines.append(f"- {hl}")

    return "\n".join(lines)
