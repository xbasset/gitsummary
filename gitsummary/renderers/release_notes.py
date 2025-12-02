"""Renderers for release notes."""

from __future__ import annotations

from ..reports import ReleaseNote


def format_release_note_markdown(release_note: ReleaseNote) -> str:
    lines = []

    h = release_note.header
    lines.append(f"# {h.product_name} {h.version} — {h.release_date}")
    lines.append("")
    lines.append(f"*{h.theme}*")
    lines.append("")

    if release_note.highlights:
        lines.append("## 🚀 Highlights")
        lines.append("")
        for hl in release_note.highlights:
            lines.append(f"- {hl.emoji} **{hl.type.title()}**: {hl.summary}")
        lines.append("")

    if release_note.features:
        lines.append("## 🆕 New Features")
        lines.append("")
        for feat in release_note.features:
            lines.append(f"### {feat.title}")
            lines.append("")
            lines.append(feat.description)
            lines.append("")
            lines.append(f"*{feat.user_benefit}*")
            lines.append("")

    if release_note.improvements:
        lines.append("## ✨ Improvements")
        lines.append("")
        for imp in release_note.improvements:
            lines.append(f"- {imp.summary}")
        lines.append("")

    if release_note.fixes:
        lines.append("## 🛠️ Bug Fixes")
        lines.append("")
        for fix in release_note.fixes:
            lines.append(f"- {fix.summary}")
        lines.append("")

    if release_note.deprecations:
        lines.append("## ⚠️ Deprecations & Breaking Changes")
        lines.append("")
        for dep in release_note.deprecations:
            lines.append(f"### {dep.what}")
            lines.append("")
            lines.append(f"**Reason**: {dep.reason}")
            lines.append("")
            lines.append(f"**Migration**: {dep.migration}")
            if dep.deadline:
                lines.append(f"**Deadline**: {dep.deadline}")
            lines.append("")

    if release_note.known_issues:
        lines.append("## 📌 Known Issues")
        lines.append("")
        for issue in release_note.known_issues:
            lines.append(f"- {issue.issue} *({issue.status})*")
        lines.append("")

    if release_note.call_to_action:
        cta = release_note.call_to_action
        lines.append("## 📚 Learn More")
        lines.append("")
        if cta.documentation_url:
            lines.append(f"- [Documentation]({cta.documentation_url})")
        if cta.migration_guide_url:
            lines.append(f"- [Migration Guide]({cta.migration_guide_url})")
        if cta.support_url:
            lines.append(f"- [Support]({cta.support_url})")
        lines.append("")

    m = release_note.metadata
    lines.append("---")
    lines.append(
        f"*{m.commit_count} commits, {m.analyzed_count} analyzed"
        + (f" • Generated with {m.llm_provider}/{m.llm_model}" if m.llm_provider else "")
        + "*"
    )

    return "\n".join(lines)


def format_release_note_text(release_note: ReleaseNote) -> str:
    lines = []

    h = release_note.header
    lines.append(f"{h.product_name} {h.version} — {h.release_date}")
    lines.append("=" * len(lines[-1]))
    lines.append("")
    lines.append(h.theme)
    lines.append("")

    if release_note.highlights:
        lines.append("HIGHLIGHTS")
        lines.append("-" * 10)
        for hl in release_note.highlights:
            lines.append(f"  [{hl.type.upper()}] {hl.summary}")
        lines.append("")

    if release_note.features:
        lines.append("NEW FEATURES")
        lines.append("-" * 12)
        for feat in release_note.features:
            lines.append(f"  * {feat.title}")
            lines.append(f"    {feat.description}")
            lines.append(f"    Why: {feat.user_benefit}")
            lines.append("")

    if release_note.improvements:
        lines.append("IMPROVEMENTS")
        lines.append("-" * 12)
        for imp in release_note.improvements:
            lines.append(f"  * {imp.summary}")
        lines.append("")

    if release_note.fixes:
        lines.append("BUG FIXES")
        lines.append("-" * 9)
        for fix in release_note.fixes:
            lines.append(f"  * {fix.summary}")
        lines.append("")

    if release_note.deprecations:
        lines.append("DEPRECATIONS & BREAKING CHANGES")
        lines.append("-" * 31)
        for dep in release_note.deprecations:
            lines.append(f"  * {dep.what}")
            lines.append(f"    Reason: {dep.reason}")
            lines.append(f"    Migration: {dep.migration}")
            if dep.deadline:
                lines.append(f"    Deadline: {dep.deadline}")
            lines.append("")

    if release_note.known_issues:
        lines.append("KNOWN ISSUES")
        lines.append("-" * 12)
        for issue in release_note.known_issues:
            lines.append(f"  * {issue.issue} ({issue.status})")
        lines.append("")

    m = release_note.metadata
    lines.append("-" * 40)
    lines.append(f"{m.commit_count} commits, {m.analyzed_count} analyzed")

    return "\n".join(lines)
