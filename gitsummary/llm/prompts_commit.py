"""Prompt templates for commit-level LLM analysis."""

from __future__ import annotations

import re
from importlib import resources

from ..core import CommitInfo
from .base import SkippableLLMError

COMMIT_ANALYSIS_PROMPT_VERSION = "commit_artifact_v2.1"
MAX_DIFF_LINES = 500
MAX_DIFF_BYTES = 180_000
MAX_FILE_DIFF_BYTES = 48_000
MAX_LINE_CHARS = 2_000
OVERSIZED_LINE_CHARS = 12_000
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

SKIP_DIFF_EXTENSIONS = {
    ".ipynb": "notebook_diff",
    ".png": "binary_diff",
    ".jpg": "binary_diff",
    ".jpeg": "binary_diff",
    ".gif": "binary_diff",
    ".webp": "binary_diff",
    ".pdf": "binary_diff",
    ".zip": "binary_diff",
    ".gz": "binary_diff",
    ".jar": "binary_diff",
    ".woff": "binary_diff",
    ".woff2": "binary_diff",
    ".ttf": "binary_diff",
    ".ico": "binary_diff",
    ".snap": "generated_fixture_diff",
    ".snapshot": "generated_fixture_diff",
    ".golden": "generated_fixture_diff",
}


def _load_prompt_asset(path: str, fallback: str) -> str:
    try:
        asset = (
            resources.files(__package__)
            / "prompt_assets"
            / "commit_artifact_v2"
            / path
        )
        return asset.read_text(encoding="utf-8")
    except Exception:
        return fallback


COMMIT_ANALYSIS_SYSTEM_PROMPT = _load_prompt_asset(
    "system.md",
    """\
You are an expert software engineer analyzing git commits to extract semantic understanding.

Your task is to analyze the commit message and code diff to determine:
1. What the change ACTUALLY does (which may differ from the commit message)
2. The category of change (feature, fix, security, performance, refactor, chore)
3. The behavior before and after (for fixes and features)
4. The scope of impact (public API, internal, config, docs, tests)
5. Whether this is a breaking change
6. Key technical decisions made in the implementation
7. Qualitative scores with short explanations (difficulty, creativity, mental load, review effort, ambiguity)

Guidelines:
- Be specific and actionable in your descriptions
- For behavior_before/after, focus on observable differences
- Only mark as breaking if external consumers are affected
- Look at actual code changes, not just the commit message
- For refactors, behavior_before and behavior_after should be null
- For new features without prior behavior, behavior_before should be null
- Technical highlights should focus on HOW, not WHAT
- For qualitative scores, use the provided rubric and keep explanations short

Output format: Respond with valid JSON matching the provided schema.
""",
)

COMMIT_ANALYSIS_INSTRUCTIONS = _load_prompt_asset(
    "instructions.md",
    """\
## Qualitative scoring rubric (0-10)
- technical_difficulty: 0 trivial rename -> 10 architecture/complex algorithm
- creativity: 0 boilerplate -> 10 novel pattern/solution
- mental_load: 0 routine -> 10 high context/multi-system
- review_effort: 0 quick -> 10 multi-file, subtle, high risk
- ambiguity: 0 clear intent -> 10 unclear intent

Provide a short explanation (1-2 sentences) for each score.

Return all qualitative fields, even if you estimate low scores.
""",
)


def build_commit_analysis_prompt(
    commit: CommitInfo,
    diff_patch: str,
    max_diff_lines: int = MAX_DIFF_LINES,
) -> str:
    """Build the user prompt for analyzing a single commit."""
    truncated_diff = _prepare_diff_for_prompt(diff_patch, max_diff_lines=max_diff_lines)

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
        prompt_parts.extend(
            [
                "## Code Diff",
                "```diff",
                truncated_diff,
                "```",
                "",
            ]
        )
    else:
        prompt_parts.extend(
            [
                "## Code Diff",
                "(No diff available - this may be a merge commit or initial commit)",
                "",
            ]
        )

    prompt_parts.extend(
        [
            "## Instructions",
            "Based on the commit message and diff above, extract the semantic information.",
            "Focus on understanding the REAL intent and impact of this change.",
            "",
            COMMIT_ANALYSIS_INSTRUCTIONS.strip(),
        ]
    )

    prompt = "\n".join(prompt_parts)
    prompt_bytes = len(prompt.encode("utf-8"))
    if prompt_bytes > MAX_DIFF_BYTES * 2:
        raise SkippableLLMError(
            "diff_too_large",
            f"Prompt remained oversized after trimming ({prompt_bytes} bytes).",
        )
    return prompt


def _prepare_diff_for_prompt(diff_patch: str, *, max_diff_lines: int) -> str:
    if not diff_patch:
        return ""

    sections = _split_diff_sections(diff_patch)
    if not sections:
        sections = [{"path": None, "content": diff_patch}]

    included_sections: list[str] = []
    retained_sections = 0
    omitted: list[str] = []
    lines_used = 0
    bytes_used = 0

    for section in sections:
        path = section["path"]
        content = section["content"]
        skip_reason = _classify_skipped_diff(path, content)
        if skip_reason is not None:
            label = path or "diff"
            omitted.append(f"{label} ({skip_reason})")
            continue

        normalized = _normalize_diff_lines(content)
        if not normalized:
            continue
        section_bytes = len(normalized.encode("utf-8"))
        if section_bytes > MAX_FILE_DIFF_BYTES:
            omitted.append(f"{path or 'diff'} (diff_too_large)")
            continue

        remaining_lines = max(max_diff_lines - lines_used, 0)
        remaining_bytes = max(MAX_DIFF_BYTES - bytes_used, 0)
        if remaining_lines == 0 or remaining_bytes <= 0:
            omitted.append(f"{path or 'diff'} (diff_budget_exhausted)")
            continue

        trimmed = _trim_to_budget(
            normalized,
            max_lines=remaining_lines,
            max_bytes=min(MAX_FILE_DIFF_BYTES, remaining_bytes),
        )
        if not trimmed:
            omitted.append(f"{path or 'diff'} (diff_budget_exhausted)")
            continue

        included_sections.append(trimmed)
        retained_sections += 1
        lines_used += trimmed.count("\n") + (0 if trimmed.endswith("\n") else 1)
        bytes_used += len(trimmed.encode("utf-8"))

    if omitted:
        included_sections.insert(
            0,
            "## Diff sections omitted before analysis:\n"
            + "\n".join(f"- {entry}" for entry in omitted[:12]),
        )

    prompt_diff = "\n\n".join(section for section in included_sections if section)
    if retained_sections == 0 and omitted:
        reason = omitted[0].split("(")[-1].rstrip(")")
        raise SkippableLLMError(
            reason,
            f"All diff content was filtered before prompt build ({', '.join(omitted[:3])}).",
        )

    prompt_bytes = len(prompt_diff.encode("utf-8"))
    if prompt_bytes > MAX_DIFF_BYTES:
        raise SkippableLLMError(
            "diff_too_large",
            f"Diff remained oversized after trimming ({prompt_bytes} bytes).",
        )
    return prompt_diff


def _split_diff_sections(diff_patch: str) -> list[dict[str, str | None]]:
    lines = diff_patch.splitlines()
    sections: list[dict[str, str | None]] = []
    current: list[str] = []
    current_path: str | None = None

    for line in lines:
        if line.startswith("diff --git ") and current:
            sections.append({"path": current_path, "content": "\n".join(current)})
            current = []
            current_path = None
        current.append(line)
        if line.startswith("+++ b/"):
            current_path = line[6:].strip()

    if current:
        sections.append({"path": current_path, "content": "\n".join(current)})
    return sections


def _classify_skipped_diff(path: str | None, content: str) -> str | None:
    lowered_path = (path or "").lower()
    for suffix, reason in SKIP_DIFF_EXTENSIONS.items():
        if lowered_path.endswith(suffix):
            return reason
    if "binary files " in content.lower():
        return "binary_diff"
    if ANSI_ESCAPE_RE.search(content) and (
        lowered_path.endswith(".golden")
        or lowered_path.endswith(".txt")
        or "/testdata/" in lowered_path
        or "/fixtures/" in lowered_path
    ):
        return "ansi_fixture_diff"
    if _looks_binaryish(content):
        return "binary_diff"
    if lowered_path.endswith((".min.js", ".min.css")):
        return "generated_diff"
    return None


def _looks_binaryish(content: str) -> bool:
    if "\x00" in content:
        return True
    control_chars = sum(
        1 for ch in content if ord(ch) < 32 and ch not in "\n\r\t"
    )
    if control_chars > 64:
        return True
    very_long_lines = sum(1 for line in content.splitlines() if len(line) > OVERSIZED_LINE_CHARS)
    return very_long_lines > 3


def _normalize_diff_lines(content: str) -> str:
    normalized_lines: list[str] = []
    truncated_long_line = False
    for line in content.splitlines():
        if len(line) > MAX_LINE_CHARS:
            normalized_lines.append(
                f"{line[:MAX_LINE_CHARS]} … (line truncated, {len(line) - MAX_LINE_CHARS} chars removed)"
            )
            truncated_long_line = True
            continue
        normalized_lines.append(line)

    if truncated_long_line:
        normalized_lines.append("")
        normalized_lines.append("... (diff lines truncated to stay within prompt budget)")
    return "\n".join(normalized_lines).strip()


def _trim_to_budget(content: str, *, max_lines: int, max_bytes: int) -> str:
    output_lines: list[str] = []
    bytes_used = 0
    lines = content.splitlines()
    truncated = False

    for index, line in enumerate(lines):
        if index >= max_lines:
            truncated = True
            break
        encoded = f"{line}\n".encode("utf-8")
        if bytes_used + len(encoded) > max_bytes:
            truncated = True
            break
        output_lines.append(line)
        bytes_used += len(encoded)

    if truncated:
        output_lines.append("")
        output_lines.append("... (diff truncated to stay within prompt budget)")
    return "\n".join(output_lines).strip()


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

        prompt_parts.extend(
            [
                f"## Commit {i + 1}: {commit.short_sha}",
                f"**Message**: {commit.summary}",
                "",
                "```diff",
                diff_preview,
                "```",
                "",
            ]
        )

    if len(commits) > max_commits:
        prompt_parts.append(f"(... and {len(commits) - max_commits} more commits)")

    return "\n".join(prompt_parts)
