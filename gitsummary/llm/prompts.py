"""Prompt templates for LLM-based commit analysis.

This module contains the system and user prompts used to guide
LLM extraction of semantic information from commits.

Prompts are designed to:
- Be clear and specific about expected output
- Provide context about the extraction task
- Handle edge cases (merge commits, reverts, etc.)
- Work across different LLM providers
"""

from __future__ import annotations

from typing import Optional

from ..core import CommitInfo


# System prompt for commit analysis
COMMIT_ANALYSIS_SYSTEM_PROMPT = """\
You are an expert software engineer analyzing git commits to extract semantic understanding.

Your task is to analyze the commit message and code diff to determine:
1. What the change ACTUALLY does (which may differ from the commit message)
2. The category of change (feature, fix, security, performance, refactor, chore)
3. The behavior before and after (for fixes and features)
4. The scope of impact (public API, internal, config, docs, tests)
5. Whether this is a breaking change
6. Key technical decisions made in the implementation

Guidelines:
- Be specific and actionable in your descriptions
- For behavior_before/after, focus on observable differences
- Only mark as breaking if external consumers are affected
- Look at actual code changes, not just the commit message
- For refactors, behavior_before and behavior_after should be null
- For new features without prior behavior, behavior_before should be null
- Technical highlights should focus on HOW, not WHAT

Output format: Respond with valid JSON matching the provided schema.
"""


def build_commit_analysis_prompt(
    commit: CommitInfo,
    diff_patch: str,
    max_diff_lines: int = 500,
) -> str:
    """Build the user prompt for analyzing a single commit.

    Args:
        commit: The commit information.
        diff_patch: The unified diff patch text.
        max_diff_lines: Maximum diff lines to include (truncate if longer).

    Returns:
        The formatted user prompt.
    """
    # Truncate diff if too long
    diff_lines = diff_patch.split("\n")
    if len(diff_lines) > max_diff_lines:
        truncated_diff = "\n".join(diff_lines[:max_diff_lines])
        truncated_diff += f"\n\n... (diff truncated, {len(diff_lines) - max_diff_lines} more lines)"
    else:
        truncated_diff = diff_patch

    # Build the prompt
    prompt_parts = [
        "Analyze the following git commit and extract semantic information.",
        "",
        "## Commit Information",
        f"- **SHA**: {commit.short_sha}",
        f"- **Author**: {commit.author_name} <{commit.author_email}>",
        f"- **Date**: {commit.date.isoformat()}",
        "",
        "## Commit Message",
        "```",
        commit.full_message,
        "```",
        "",
    ]

    if truncated_diff:
        prompt_parts.extend([
            "## Code Diff",
            "```diff",
            truncated_diff,
            "```",
            "",
        ])
    else:
        prompt_parts.extend([
            "## Code Diff",
            "(No diff available - this may be a merge commit or initial commit)",
            "",
        ])

    prompt_parts.extend([
        "## Instructions",
        "Based on the commit message and diff above, extract the semantic information.",
        "Focus on understanding the REAL intent and impact of this change.",
    ])

    return "\n".join(prompt_parts)


def build_batch_analysis_prompt(
    commits: list[CommitInfo],
    diffs: dict[str, str],
    max_commits: int = 20,
) -> str:
    """Build a prompt for analyzing multiple commits at once.

    Args:
        commits: List of commits to analyze.
        diffs: Mapping of commit SHA to diff patch.
        max_commits: Maximum commits to include.

    Returns:
        The formatted batch analysis prompt.
    """
    prompt_parts = [
        "Analyze the following git commits and extract semantic information for each.",
        "Also provide an overall summary of the changes.",
        "",
    ]

    for i, commit in enumerate(commits[:max_commits]):
        diff = diffs.get(commit.sha, "")
        # Shorter diffs for batch mode
        diff_preview = "\n".join(diff.split("\n")[:50]) if diff else "(no diff)"

        prompt_parts.extend([
            f"## Commit {i + 1}: {commit.short_sha}",
            f"**Message**: {commit.summary}",
            "",
            "```diff",
            diff_preview,
            "```",
            "",
        ])

    if len(commits) > max_commits:
        prompt_parts.append(f"(... and {len(commits) - max_commits} more commits)")

    return "\n".join(prompt_parts)


# ─────────────────────────────────────────────────────────────────────────────
# Release Note Synthesis Prompts
# ─────────────────────────────────────────────────────────────────────────────


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
- For the "theme", capture the ESSENCE of the release in one catchy sentence.
- For highlights, pick the 3-5 MOST IMPORTANT changes users should know about.
- For features, explain WHAT it does and WHY users will benefit.
- For improvements, be SPECIFIC about the benefit (e.g., "45% faster" not "improved").
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
    """Build the prompt for synthesizing release notes from commit artifacts.

    Args:
        product_name: Name of the product/project.
        version: Version being released.
        artifacts_summary: Pre-formatted summary of commit artifacts.

    Returns:
        The formatted user prompt.
    """
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
    """Format commit artifacts into a summary for the synthesis prompt.

    Args:
        artifacts_data: List of dicts with commit and artifact info.
            Each dict should have: sha, category, intent_summary,
            behavior_before, behavior_after, is_breaking, technical_highlights

    Returns:
        Formatted string for the prompt.
    """
    lines = []

    # Group by category for easier processing
    by_category: dict[str, list[dict]] = {}
    for item in artifacts_data:
        category = item.get("category", "other")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(item)

    # Format each category
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

            # Add behavior change if present
            before = item.get("behavior_before")
            after = item.get("behavior_after")
            if before and after:
                lines.append(f"  - Before: {before}")
                lines.append(f"  - After: {after}")

            # Add technical highlights if present
            highlights = item.get("technical_highlights", [])
            if highlights:
                for hl in highlights[:2]:  # Limit to top 2
                    lines.append(f"  - Technical: {hl}")

        lines.append("")

    return "\n".join(lines)



