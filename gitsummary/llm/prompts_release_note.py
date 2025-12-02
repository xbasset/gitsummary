"""Prompt templates for release-note synthesis."""

from __future__ import annotations

RELEASE_NOTE_SYSTEM_PROMPT = """\
You are an expert technical writer creating release notes for software users.

Your task is to synthesize commit-level analysis into user-facing release notes that are:
- **Clear**: Tell users what changed without requiring them to decode technical jargon.
- **Concise**: Short enough to skim, but detailed enough to be useful.
- **User-focused**: Explain *why* changes matter, not just *what* changed.
- **Organized**: Group related changes and prioritize the most important.

Guidelines:
- Write for END USERS, not developers. Avoid implementation details.
- Group related commits into single features/improvements when they work together.
- For the \"theme\", capture the ESSENCE of the release in one catchy sentence.
- For highlights, pick the 3-5 MOST IMPORTANT changes users should know about.
- For features, explain WHAT it does and WHY users will benefit.
- For improvements, be SPECIFIC about the benefit (e.g., \"45% faster\" not \"improved\").
- For bug fixes, describe the USER-VISIBLE problem that was fixed.
- For deprecations/breaking changes, be CLEAR about what's changing and how to adapt.
- Use active voice and present tense.
- Keep summaries concise but informative.

Output format: Respond with valid JSON matching the provided schema.
"""


def build_release_note_synthesis_prompt(
    product_name: str,
    version: str,
    artifacts_summary: str,
) -> str:
    """Build the prompt for synthesizing release notes from commit artifacts."""
    prompt_parts = [
        "Synthesize the following commit analyses into user-facing release notes.",
        "",
        f"## Product: {product_name}",
        f"## Version: {version}",
        "",
        "## Commit Analyses",
        "",
        artifacts_summary,
        "",
        "## Instructions",
        "",
        "Based on the commit analyses above:",
        "1. Create a compelling theme that captures the essence of this release.",
        "2. Select 3-5 highlights for the TL;DR section.",
        "3. Group related commits into cohesive features, improvements, and fixes.",
        "4. Rewrite technical descriptions into user-friendly language.",
        "5. Include ALL breaking changes in the deprecations section.",
        "",
        "Remember: Write for end users, not developers!",
    ]

    return "\n".join(prompt_parts)


def format_artifacts_for_synthesis(
    artifacts_data: list[dict],
) -> str:
    """Format commit artifacts into a summary for the synthesis prompt."""
    lines: list[str] = []
    by_category: dict[str, list[dict]] = {}

    for item in artifacts_data:
        category = item.get("category", "other")
        by_category.setdefault(category, []).append(item)

    category_order = ["feature", "fix", "security", "performance", "refactor", "chore"]

    for category in category_order:
        items = by_category.get(category, [])
        if not items:
            continue

        lines.append(f"### {category.upper()} ({len(items)} commits)")
        lines.append("")

        for item in items:
            sha = item.get("sha", "???")[:7]
            summary = item.get("intent_summary", "No summary")
            is_breaking = item.get("is_breaking", False)

            breaking_marker = " ⚠️ BREAKING" if is_breaking else ""
            lines.append(f"- **[{sha}]** {summary}{breaking_marker}")

            before = item.get("behavior_before")
            after = item.get("behavior_after")
            if before and after:
                lines.append(f"  - Before: {before}")
                lines.append(f"  - After: {after}")

            highlights = item.get("technical_highlights", [])
            if highlights:
                for hl in highlights[:2]:
                    lines.append(f"  - Technical: {hl}")

        lines.append("")

    return "\n".join(lines)
