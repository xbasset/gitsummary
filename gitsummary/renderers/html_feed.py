"""HTML renderer for the artifact feed."""

from __future__ import annotations

import html
from datetime import datetime
from typing import List

from ..reporters import ArtifactFeedReport, FeedItem


def _format_date(dt: datetime) -> str:
    """Format commit date for display."""
    return dt.strftime("%Y-%m-%d")


def _escape(text: str) -> str:
    """Escape text for HTML."""
    return html.escape(text, quote=True)


def _render_highlights(highlights: List[str]) -> str:
    if not highlights:
        return ""
    items = "".join(f"<li>{_escape(h)}</li>" for h in highlights[:4])
    return f"""
    <div class="section">
      <div class="section-title">Technical notes</div>
      <ul class="highlights">
        {items}
      </ul>
    </div>
    """


def format_artifact_feed_html(
    project_name: str,
    revision_range: str,
    report: ArtifactFeedReport,
) -> str:
    """Render the feed as a self-contained HTML document."""
    header_cta = ""
    if report.missing_count:
        analyze_range_cmd = f"gitsummary analyze {revision_range}"
        header_cta = f"""
        <div class="cta-card">
          <div class="cta-content">
            <div class="cta-title">Missing artifacts detected</div>
            <div class="cta-subtitle">Run the analyzer to fill in {report.missing_count} gaps.</div>
          </div>
          <button class="copy-btn" onclick="copyCommand('{_escape(analyze_range_cmd)}', this)">Copy range command</button>
          <code class="cta-code">{_escape(analyze_range_cmd)}</code>
        </div>
        """

    cards = []
    for item in report.items:
        commit = item.commit
        commit_title = _escape(item.intent_summary or commit.summary)
        commit_meta = f"{_escape(commit.author_name)} • {_format_date(commit.date)}"
        category_badge = (
            f"<span class='badge category'>{_escape(item.category.value)}</span>"
            if item.category
            else "<span class='badge missing'>missing</span>"
        )
        impact_badge = (
            f"<span class='badge impact'>{_escape(item.impact_scope.value)}</span>"
            if item.impact_scope
            else ""
        )
        breaking_badge = (
            "<span class='badge breaking'>breaking</span>" if item.is_breaking else ""
        )

        behavior = ""
        if item.behavior_before or item.behavior_after:
            before = (
                f"<div><span class='label'>Before</span> {_escape(item.behavior_before)}</div>"
                if item.behavior_before
                else ""
            )
            after = (
                f"<div><span class='label'>After</span> {_escape(item.behavior_after)}</div>"
                if item.behavior_after
                else ""
            )
            behavior = f"""
            <div class="section">
              <div class="section-title">Behavior change</div>
              <div class="behavior">{before}{after}</div>
            </div>
            """

        if item.analyzed:
            card = f"""
            <article class="card analyzed">
              <div class="card-header">
                <div>
                  <div class="commit-sha">{_escape(commit.short_sha)}</div>
                  <div class="commit-meta">{commit_meta}</div>
                </div>
                <div class="badges">{category_badge}{impact_badge}{breaking_badge}</div>
              </div>
              <h3 class="card-title">{commit_title}</h3>
              {behavior}
              {_render_highlights(item.technical_highlights)}
            </article>
            """
        else:
            cmd = f"gitsummary analyze {commit.sha}"
            card = f"""
            <article class="card missing">
              <div class="card-header">
                <div>
                  <div class="commit-sha">{_escape(commit.short_sha)}</div>
                  <div class="commit-meta">{commit_meta}</div>
                </div>
                <div class="badges">{category_badge}</div>
              </div>
              <h3 class="card-title">{_escape(commit.summary)}</h3>
              <p class="missing-copy">This commit is waiting for its story. Run the analyzer to bring it to life.</p>
              <div class="cta-inline">
                <code>{_escape(cmd)}</code>
                <button class="copy-btn ghost" onclick="copyCommand('{_escape(cmd)}', this)">Copy</button>
              </div>
            </article>
            """

        cards.append(card)

    cards_html = "\n".join(cards)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{_escape(project_name)} – Artifact Feed</title>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #0b1020;
      --card: rgba(255, 255, 255, 0.04);
      --border: rgba(255, 255, 255, 0.08);
      --accent: #7c3aed;
      --accent-2: #14b8a6;
      --text: #e5e7eb;
      --muted: #94a3b8;
      --warning: #f59e0b;
      --danger: #f43f5e;
      --shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
      font-family: "Segoe UI", "Helvetica Neue", "Source Sans Pro", "Work Sans", system-ui, sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 20% 20%, rgba(124, 58, 237, 0.14), transparent 35%),
                  radial-gradient(circle at 80% 0%, rgba(20, 184, 166, 0.15), transparent 40%),
                  var(--bg);
      color: var(--text);
      -webkit-font-smoothing: antialiased;
    }}
    .page {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 28px 18px 48px;
    }}
    .hero {{
      position: sticky;
      top: 0;
      backdrop-filter: blur(10px);
      background: linear-gradient(120deg, rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.75));
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 18px 20px;
      margin-bottom: 18px;
      box-shadow: var(--shadow);
      z-index: 10;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    h1 {{
      margin: 0 0 6px 0;
      font-size: 28px;
      letter-spacing: -0.03em;
    }}
    .subtitle {{
      margin: 0 0 14px 0;
      color: var(--muted);
    }}
    .stats {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }}
    .stat-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      font-weight: 600;
      color: var(--text);
    }}
    .stat-chip .label {{
      color: var(--muted);
      font-weight: 500;
      font-size: 13px;
    }}
    .cta-card {{
      margin-top: 6px;
      display: grid;
      gap: 6px;
      grid-template-columns: 1fr auto;
      align-items: center;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px dashed rgba(244, 63, 94, 0.5);
      background: rgba(244, 63, 94, 0.1);
    }}
    .cta-content {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .cta-title {{ font-weight: 700; }}
    .cta-subtitle {{ color: var(--muted); font-size: 14px; }}
    .cta-code {{
      grid-column: 1 / -1;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 10px;
      padding: 6px 10px;
      font-family: "JetBrains Mono", "SFMono-Regular", Menlo, monospace;
      color: var(--text);
    }}
    .copy-btn {{
      padding: 8px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--accent);
      color: white;
      font-weight: 700;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease, background 120ms ease;
      box-shadow: 0 10px 30px rgba(124, 58, 237, 0.3);
    }}
    .copy-btn:hover {{ transform: translateY(-1px); }}
    .copy-btn.ghost {{
      background: transparent;
      box-shadow: none;
      border-color: var(--border);
    }}
    .feed {{
      display: grid;
      gap: 16px;
    }}
    .card {{
      border-radius: 16px;
      padding: 18px;
      border: 1px solid var(--border);
      background: var(--card);
      box-shadow: var(--shadow);
      backdrop-filter: blur(6px);
    }}
    .card.analyzed {{
      border: 1px solid rgba(124, 58, 237, 0.3);
    }}
    .card.missing {{
      background: rgba(255, 255, 255, 0.02);
      border: 1px dashed rgba(255, 255, 255, 0.25);
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: baseline;
      margin-bottom: 8px;
    }}
    .commit-sha {{
      font-weight: 800;
      letter-spacing: 0.03em;
    }}
    .commit-meta {{
      color: var(--muted);
      font-size: 13px;
    }}
    .badges {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .badge {{
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: white;
      background: rgba(255, 255, 255, 0.08);
    }}
    .badge.category {{ background: linear-gradient(120deg, #7c3aed, #6366f1); }}
    .badge.impact {{ background: linear-gradient(120deg, #0ea5e9, #22d3ee); }}
    .badge.breaking {{ background: linear-gradient(120deg, #f43f5e, #fb7185); }}
    .badge.missing {{ background: linear-gradient(120deg, #f59e0b, #fb923c); }}
    .card-title {{
      margin: 4px 0 12px 0;
      font-size: 20px;
      letter-spacing: -0.01em;
    }}
    .section {{ margin-bottom: 10px; }}
    .section-title {{
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: 0.06em;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .behavior {{
      display: grid;
      gap: 6px;
      background: rgba(255, 255, 255, 0.03);
      padding: 10px;
      border-radius: 12px;
      border: 1px solid var(--border);
    }}
    .behavior .label {{
      display: inline-block;
      padding: 4px 8px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      margin-right: 6px;
      font-size: 12px;
      color: var(--muted);
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}
    .highlights {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 6px;
    }}
    .highlights li {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border);
      padding: 10px 12px;
      border-radius: 10px;
    }}
    .missing-copy {{
      color: var(--muted);
      margin: 8px 0 12px 0;
    }}
    .cta-inline {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
      background: rgba(255, 255, 255, 0.04);
      border-radius: 12px;
      padding: 10px 12px;
      border: 1px dashed var(--border);
    }}
    .cta-inline code {{
      font-family: "JetBrains Mono", "SFMono-Regular", Menlo, monospace;
      color: var(--text);
      overflow-wrap: anywhere;
    }}
    @media (max-width: 720px) {{
      .hero {{
        position: static;
      }}
      .card {{
        padding: 16px;
      }}
      .card-header {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .cta-card {{
        grid-template-columns: 1fr;
        gap: 8px;
      }}
      .cta-inline {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="hero">
      <div class="eyebrow">{_escape(project_name)} / {_escape(revision_range)}</div>
      <h1>Artifact Feed</h1>
      <p class="subtitle">Scroll through commits like a storybook. Analyzed artifacts lead the way; missing ones invite you to run the analyzer.</p>
      <div class="stats">
        <div class="stat-chip"><span class="label">Total</span> {report.total_commits}</div>
        <div class="stat-chip"><span class="label">Analyzed</span> {report.analyzed_count}</div>
        <div class="stat-chip"><span class="label">Missing</span> {report.missing_count}</div>
        <div class="stat-chip"><span class="label">Breaking</span> {report.breaking_count}</div>
      </div>
      {header_cta}
    </header>
    <main class="feed">
      {cards_html}
    </main>
  </div>
  <script>
    function copyCommand(cmd, button) {{
      if (!navigator.clipboard) {{
        alert("Clipboard is unavailable in this browser.");
        return;
      }}
      navigator.clipboard.writeText(cmd).then(() => {{
        const original = button.textContent;
        button.textContent = "Copied!";
        setTimeout(() => (button.textContent = original), 1200);
      }});
    }}
  </script>
</body>
</html>
"""
