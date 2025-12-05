"""Renderers for release notes."""

from __future__ import annotations

from ..reports import ReleaseNote
from ..reports.release_notes.model import HighlightType


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


def _render_badge(label: str, tone: HighlightType) -> str:
    palette = {
        "new": "#0f172a",
        "improved": "#0f172a",
        "fixed": "#0f172a",
        "deprecated": "#7c2d12",
        "breaking": "#7c2d12",
        "security": "#0f172a",
    }
    bg = palette.get(tone, "#0f172a")
    return (
        f'<span style="display:inline-block;padding:4px 10px;'
        f'border-radius:999px;background:{bg};color:#f8fafc;'
        f'font-size:12px;font-weight:600;">{label}</span>'
    )


def format_release_note_html(release_note: ReleaseNote) -> str:
    """Render a ReleaseNote as standalone HTML."""
    h = release_note.header
    m = release_note.metadata
    highlights = "".join(
        f"<li>{_render_badge(hl.type.title(), hl.type)} "
        f"<strong>{hl.summary}</strong></li>"
        for hl in release_note.highlights
    )

    def _list_items(title: str, items: str) -> str:
        if not items:
            return ""
        return (
            f"<section><h2>{title}</h2>"
            f"<ul class='stack'>{items}</ul></section>"
        )

    features = "".join(
        "<li>"
        f"<h3>{feat.title}</h3>"
        f"<p>{feat.description}</p>"
        f"<p class='muted'>{feat.user_benefit}</p>"
        "</li>"
        for feat in release_note.features
    )
    improvements = "".join(f"<li>{imp.summary}</li>" for imp in release_note.improvements)
    fixes = "".join(f"<li>{fix.summary}</li>" for fix in release_note.fixes)
    def _render_deadline(dep) -> str:
        return f"<p class='muted'>Deadline: {dep.deadline}</p>" if dep.deadline else ""

    deprecations = "".join(
        "<li>"
        f"<h3>{dep.what}</h3>"
        f"<p>{dep.reason}</p>"
        f"<p class='muted'>{dep.migration}</p>"
        f"{_render_deadline(dep)}"
        "</li>"
        for dep in release_note.deprecations
    )
    issues = "".join(
        f"<li><strong>{issue.status}</strong> — {issue.issue}</li>"
        for issue in release_note.known_issues
    )

    learn_more = ""
    cta = release_note.call_to_action
    if cta:
        links = []
        if cta.documentation_url:
            links.append(f'<a href="{cta.documentation_url}">Documentation</a>')
        if cta.migration_guide_url:
            links.append(f'<a href="{cta.migration_guide_url}">Migration guide</a>')
        if cta.support_url:
            links.append(f'<a href="{cta.support_url}">Support</a>')
        if links:
            learn_more = "<section><h2>Learn More</h2>" + "<br>".join(links) + "</section>"

    metadata = (
        f"<p class='muted'>{m.commit_count} commits, {m.analyzed_count} analyzed"
        + (f" • Generated with {m.llm_provider}/{m.llm_model}" if m.llm_provider else "")
        + "</p>"
    )

    body = (
        f"<section><h1>{h.product_name} {h.version}</h1>"
        f"<p class='muted'>{h.release_date}</p>"
        f"<p>{h.theme}</p>"
        f"{metadata}"
        "</section>"
        f"{_list_items('Highlights', highlights)}"
        f"{_list_items('New Features', features)}"
        f"{_list_items('Improvements', improvements)}"
        f"{_list_items('Bug Fixes', fixes)}"
        f"{_list_items('Deprecations & Breaking Changes', deprecations)}"
        f"{_list_items('Known Issues', issues)}"
        f"{learn_more}"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{h.product_name} {h.version} Release Notes</title>
  <style>
    :root {{
      --bg: #0b1224;
      --panel: #0f172a;
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #38bdf8;
    }}
    body {{
      margin: 0;
      font-family: "Space Grotesk", "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
      background: linear-gradient(120deg, #0b1224 0%, #0d1b2a 50%, #0b1224 100%);
      color: var(--text);
      padding: 32px 12px 48px;
    }}
    .page {{
      max-width: 820px;
      margin: 0 auto;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(56, 189, 248, 0.15);
      border-radius: 18px;
      padding: 28px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.35);
      backdrop-filter: blur(8px);
    }}
    h1, h2, h3 {{ margin: 0 0 12px; }}
    h1 {{ font-size: 32px; }}
    h2 {{ font-size: 20px; border-bottom: 1px solid rgba(148,163,184,0.2); padding-bottom: 8px; margin-top: 28px; }}
    h3 {{ font-size: 16px; margin-top: 12px; }}
    p {{ line-height: 1.6; }}
    .muted {{ color: var(--muted); }}
    ul.stack {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }}
    li {{ line-height: 1.6; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    @media (max-width: 640px) {{
      .page {{ padding: 20px; }}
      h1 {{ font-size: 26px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    {body}
  </div>
</body>
</html>"""
