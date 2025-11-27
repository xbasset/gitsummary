"""Utilities for constructing gitsummary artifacts.

This module provides the bridge between raw git data and semantic artifacts.
It includes both heuristic-based extraction and hooks for LLM-powered analysis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

from .git import CommitDiff, CommitInfo, diff_patch_for_commit
from .schema import ChangeCategory, CommitArtifact, ImpactScope

__all__ = [
    "build_commit_artifact",
    "ArtifactBuilder",
    "LLMProvider",
    # Legacy exports
    "build_artifact",
]


# ─────────────────────────────────────────────────────────────────────────────
# LLM Provider Interface
# ─────────────────────────────────────────────────────────────────────────────

# Type alias for LLM provider function
# Takes: commit_info, diff_patch -> Returns: CommitArtifact or dict with extracted fields
LLMProvider = Callable[[CommitInfo, str], Optional[Dict[str, object]]]


def _default_llm_provider(commit: CommitInfo, diff_patch: str) -> Optional[Dict[str, object]]:
    """Default provider returns None, triggering heuristic fallback."""
    return None


# Global LLM provider (can be set by CLI or tests)
_llm_provider: LLMProvider = _default_llm_provider


def set_llm_provider(provider: LLMProvider) -> None:
    """Set the global LLM provider for artifact extraction."""
    global _llm_provider
    _llm_provider = provider


def get_llm_provider() -> LLMProvider:
    """Get the current LLM provider."""
    return _llm_provider


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic Extractors (Fallback when LLM unavailable)
# ─────────────────────────────────────────────────────────────────────────────


def _infer_category(summary: str, body: str, diff_text: str) -> ChangeCategory:
    """Infer change category from commit message and diff."""
    text = f"{summary} {body}".lower()

    # Check for explicit conventional commit prefixes
    if summary.lower().startswith("fix"):
        return ChangeCategory.FIX
    if summary.lower().startswith("feat"):
        return ChangeCategory.FEATURE
    if summary.lower().startswith("perf"):
        return ChangeCategory.PERFORMANCE
    if summary.lower().startswith("refactor"):
        return ChangeCategory.REFACTOR
    if any(summary.lower().startswith(p) for p in ("chore", "build", "ci", "docs")):
        return ChangeCategory.CHORE

    # Fallback to keyword detection
    if any(kw in text for kw in ("security", "vulnerability", "cve", "exploit")):
        return ChangeCategory.SECURITY
    if any(kw in text for kw in ("performance", "optimize", "speed", "faster")):
        return ChangeCategory.PERFORMANCE
    if any(kw in text for kw in ("fix", "bug", "issue", "error", "crash")):
        return ChangeCategory.FIX
    if any(kw in text for kw in ("refactor", "cleanup", "restructure")):
        return ChangeCategory.REFACTOR
    if any(kw in text for kw in ("add", "feature", "implement", "new")):
        return ChangeCategory.FEATURE

    return ChangeCategory.CHORE


def _infer_impact_scope(
    commit: CommitInfo, file_paths: List[str], diff_text: str
) -> ImpactScope:
    """Infer impact scope from changed files and diff content."""
    text = f"{commit.summary} {commit.body} {diff_text}".lower()
    paths_lower = [p.lower() for p in file_paths]

    # Check for documentation-only changes
    if all(
        any(p.endswith(ext) for ext in (".md", ".rst", ".txt", ".adoc"))
        or "doc" in p
        or "readme" in p
        for p in paths_lower
    ):
        return ImpactScope.DOCS

    # Check for test-only changes
    if all(
        "test" in p or p.endswith("_test.py") or p.endswith(".test.ts")
        for p in paths_lower
    ):
        return ImpactScope.TEST

    # Check for dependency changes
    dep_files = (
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "go.mod",
        "cargo.toml",
        "gemfile",
        "pom.xml",
    )
    if any(any(p.endswith(d) for d in dep_files) for p in paths_lower):
        return ImpactScope.DEPENDENCY

    # Check for config changes
    config_patterns = (
        ".env",
        "config",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        "dockerfile",
        "docker-compose",
    )
    if all(any(pat in p for pat in config_patterns) for p in paths_lower):
        return ImpactScope.CONFIG

    # Check for public API changes
    if any(
        kw in text for kw in ("public api", "breaking", "endpoint", "interface", "export")
    ):
        return ImpactScope.PUBLIC_API

    # Default to internal
    return ImpactScope.INTERNAL


def _detect_breaking_change(commit: CommitInfo, diff_text: str) -> bool:
    """Detect if this is a breaking change."""
    text = f"{commit.summary} {commit.body}".lower()

    # Explicit breaking change markers
    if "breaking" in text or "breaking-change" in text:
        return True
    if commit.summary.upper().startswith("BREAKING"):
        return True
    if "!" in commit.summary.split(":")[0] if ":" in commit.summary else False:
        # Conventional commit: "feat!:" or "fix(scope)!:"
        return True

    # Heuristic: major version bumps, removed exports
    if any(kw in text for kw in ("removed", "deprecated", "breaking")):
        if any(kw in text for kw in ("api", "export", "interface", "endpoint")):
            return True

    return False


def _extract_technical_highlights(diff_text: str) -> List[str]:
    """Extract interesting technical decisions from the diff."""
    highlights: List[str] = []

    # Detect added functions/classes
    added_symbols = re.findall(
        r"^\+\s*(def|class|function|async function)\s+([\w_]+)",
        diff_text,
        re.MULTILINE,
    )
    if added_symbols:
        symbols = [f"Added {kind} `{name}`" for kind, name in added_symbols[:3]]
        highlights.extend(symbols)

    # Detect removed functions/classes
    removed_symbols = re.findall(
        r"^-\s*(def|class|function)\s+([\w_]+)", diff_text, re.MULTILINE
    )
    if removed_symbols:
        symbols = [f"Removed {kind} `{name}`" for kind, name in removed_symbols[:2]]
        highlights.extend(symbols)

    # Detect added error handling
    if re.search(r"^\+.*\b(try|catch|except|raise|throw)\b", diff_text, re.MULTILINE):
        highlights.append("Added error handling")

    # Detect added tests
    if re.search(r"^\+.*\b(test_|describe\(|it\(|pytest)\b", diff_text, re.MULTILINE):
        highlights.append("Added tests")

    # Detect logging changes
    if re.search(r"^\+.*\b(logger\.|logging\.|console\.log)\b", diff_text, re.MULTILINE):
        highlights.append("Added logging")

    return highlights[:5]  # Limit to 5 highlights


# ─────────────────────────────────────────────────────────────────────────────
# Artifact Builder
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ArtifactBuilder:
    """Builds CommitArtifact from raw git data with optional LLM enhancement."""

    use_llm: bool = True
    llm_provider: Optional[LLMProvider] = None

    def build(self, commit: CommitInfo, diff: Optional[CommitDiff] = None) -> CommitArtifact:
        """Build a CommitArtifact from commit info and diff data."""
        # Get the diff patch
        try:
            diff_text = diff_patch_for_commit(commit.sha)
        except Exception:
            diff_text = ""

        file_paths = diff.file_paths if diff else []

        # Try LLM extraction first if enabled
        llm_result = None
        if self.use_llm:
            provider = self.llm_provider or get_llm_provider()
            llm_result = provider(commit, diff_text)

        # Build artifact using LLM results or fallback to heuristics
        if llm_result:
            # LLM provided extraction - use its results
            return CommitArtifact(
                commit_hash=commit.sha,
                intent_summary=llm_result.get("intent_summary", commit.summary),
                category=ChangeCategory(llm_result.get("category", "chore")),
                behavior_before=llm_result.get("behavior_before"),
                behavior_after=llm_result.get("behavior_after"),
                impact_scope=ImpactScope(llm_result.get("impact_scope", "internal")),
                is_breaking=llm_result.get("is_breaking", False),
                technical_highlights=llm_result.get("technical_highlights", []),
            )

        # Fallback to heuristic extraction
        return CommitArtifact(
            commit_hash=commit.sha,
            intent_summary=commit.summary,
            category=_infer_category(commit.summary, commit.body, diff_text),
            behavior_before=None,  # Heuristics can't determine this
            behavior_after=None,
            impact_scope=_infer_impact_scope(commit, file_paths, diff_text),
            is_breaking=_detect_breaking_change(commit, diff_text),
            technical_highlights=_extract_technical_highlights(diff_text),
        )


def build_commit_artifact(
    commit: CommitInfo,
    diff: Optional[CommitDiff] = None,
    *,
    use_llm: bool = True,
) -> CommitArtifact:
    """Build a CommitArtifact from commit info and optional diff data.

    Args:
        commit: The commit information
        diff: Optional pre-fetched diff data
        use_llm: Whether to attempt LLM extraction (default True)

    Returns:
        A fully populated CommitArtifact
    """
    builder = ArtifactBuilder(use_llm=use_llm)
    return builder.build(commit, diff)


# ─────────────────────────────────────────────────────────────────────────────
# Legacy Support
# ─────────────────────────────────────────────────────────────────────────────

# These types are imported from git.py for legacy compatibility
from .git import Commit, DiffStat, FileChange


@dataclass(frozen=True)
class ArtifactContext:
    """Derived context information for a commit range (LEGACY)."""

    commit_range: str
    commits: Sequence[Commit]

    @property
    def authors(self) -> List[str]:
        return sorted({commit.author_name for commit in self.commits})

    @property
    def summary(self) -> str:
        messages = [commit.summary for commit in self.commits]
        return "; ".join(messages[:10])

    @property
    def date_range(self) -> Dict[str, object]:
        if not self.commits:
            return {"start": None, "end": None}
        dates = sorted(commit.date for commit in self.commits)
        return {"start": dates[0].isoformat(), "end": dates[-1].isoformat()}


def _changed_paths(changes: Sequence[FileChange]) -> List[str]:
    return [change.path for change in changes]


def build_artifact(
    *,
    commit_range: str,
    commits: Sequence[Commit],
    changes: Sequence[FileChange],
    diff_stat: DiffStat,
    diff_text: str,
) -> Dict[str, object]:
    """Return an artifact dict matching the legacy v0.1 specification.

    DEPRECATED: Use build_commit_artifact for new code.
    """
    from collections import Counter
    from pathlib import Path

    context = ArtifactContext(commit_range=commit_range, commits=commits)
    files = _changed_paths(changes)
    extensions = Counter(Path(path).suffix for path in files if path)
    top_extensions = [ext or "<none>" for ext, _ in extensions.most_common(3)]

    # Detect symbols from diff
    pattern = re.compile(
        r"^[+-]\s*(def|class|function|module|interface)\s+([\w\.]+)", re.MULTILINE
    )
    added: List[str] = []
    removed: List[str] = []
    for match in pattern.finditer(diff_text):
        token = match.group(0)
        symbol = match.group(2)
        if token.startswith("+"):
            added.append(symbol)
        elif token.startswith("-"):
            removed.append(symbol)
    modified = sorted(set(added) & set(removed))

    # Infer intention
    if not commits:
        intention = {"goal": "No commits in range", "rationale": None, "domain": None}
    else:
        headline = commits[0].summary.lower()
        domain = None
        if any(keyword in headline for keyword in ("doc", "readme", "spec")):
            domain = "documentation"
        elif any(keyword in headline for keyword in ("build", "ci", "pipeline")):
            domain = "infrastructure"
        elif any(keyword in headline for keyword in ("refactor", "cleanup")):
            domain = "maintainability"
        else:
            domain = "feature"
        intention = {
            "goal": commits[0].summary,
            "rationale": "Derived from the latest commit message.",
            "domain": domain,
        }

    # Assess risk
    risk = "low"
    if re.search(r"(schema|migration|database)", diff_text, re.IGNORECASE):
        risk = "medium"
    if re.search(r"(public api|breaking|deprecation)", diff_text, re.IGNORECASE):
        risk = "high"

    # Maintainability signals
    tests_added = len(re.findall(r"^\+.*test", diff_text, flags=re.MULTILINE))
    debt_references = len(re.findall(r"TODO|FIXME", diff_text))
    score = max(0, 5 + tests_added - debt_references)

    # Deployment signals
    configuration_files = [
        line
        for line in diff_text.splitlines()
        if line.startswith("+++ b/")
        and any(
            line.endswith(candidate)
            for candidate in (
                "Dockerfile",
                "docker-compose.yml",
                "helm.yaml",
                "values.yaml",
                "requirements.txt",
            )
        )
    ]
    logging_changes = len(
        re.findall(
            r"logger|logging|console\.log|print\(", diff_text, flags=re.IGNORECASE
        )
    )

    artifact: Dict[str, object] = {
        "context": {
            "commit_range": commit_range,
            "authors": context.authors,
            "date_range": context.date_range,
            "summaries": [commit.summary for commit in commits],
        },
        "intention": intention,
        "implementation": {
            "files_changed": files,
            "loc": {"added": diff_stat.insertions, "removed": diff_stat.deletions},
            "top_file_types": top_extensions,
            "functions": {"added": added, "removed": removed, "modified": modified},
        },
        "impact": {
            "summary": "Heuristic impact assessment based on diff keywords.",
            "risk": risk,
        },
        "maintainability": {
            "tests_added": tests_added,
            "debt_references": debt_references,
            "score": score,
        },
        "deployment": {
            "configuration_touches": configuration_files,
            "logging_changes": logging_changes,
        },
        "meta": {
            "commit_count": len(commits),
            "confidence": {
                "context": 0.9 if commits else 0.5,
                "intention": 0.6,
                "implementation": 0.7,
                "impact": 0.5,
                "maintainability": 0.4,
                "deployment": 0.5,
            },
        },
    }
    return artifact
