"""Prompt templates for commit-level LLM analysis."""

from __future__ import annotations

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
    """Build the user prompt for analyzing a single commit."""
    diff_lines = diff_patch.split("\n")
    if len(diff_lines) > max_diff_lines:
        truncated_diff = "\n".join(diff_lines[:max_diff_lines])
        truncated_diff += f"\n\n... (diff truncated, {len(diff_lines) - max_diff_lines} more lines)"
    else:
        truncated_diff = diff_patch

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
    """Build a prompt for analyzing multiple commits at once."""
    prompt_parts = [
        "Analyze the following git commits and extract semantic information for each.",
        "Also provide an overall summary of the changes.",
        "",
    ]

    for i, commit in enumerate(commits[:max_commits]):
        diff = diffs.get(commit.sha, "")
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
