"""Heuristic-based semantic extraction.

This module provides rule-based extraction from commit messages and diffs.
It serves as a reliable fallback when LLM extraction is unavailable or
for simple cases where patterns are sufficient.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..core import ChangeCategory, CommitDiff, CommitInfo, ImpactScope
from .base import ExtractionResult


class HeuristicExtractor:
    """Rule-based semantic extractor.

    Uses pattern matching and conventional commit parsing to extract
    semantic information without requiring external services.
    """

    def extract(
        self,
        commit: CommitInfo,
        diff: Optional[CommitDiff] = None,
        diff_patch: str = "",
    ) -> ExtractionResult:
        """Extract semantic information using heuristics.

        Args:
            commit: The commit information.
            diff: Optional structured diff data.
            diff_patch: Optional raw unified diff text.

        Returns:
            ExtractionResult with fields populated by heuristic analysis.
        """
        file_paths = diff.file_paths if diff else []

        return ExtractionResult(
            intent_summary=commit.summary,
            category=self._infer_category(commit.summary, commit.body, diff_patch),
            behavior_before=None,  # Heuristics can't reliably determine this
            behavior_after=None,
            impact_scope=self._infer_impact_scope(commit, file_paths, diff_patch),
            is_breaking=self._detect_breaking_change(commit, diff_patch),
            technical_highlights=self._extract_technical_highlights(diff_patch),
        )

    def _infer_category(
        self, summary: str, body: str, diff_text: str
    ) -> ChangeCategory:
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
        self, commit: CommitInfo, file_paths: List[str], diff_text: str
    ) -> ImpactScope:
        """Infer impact scope from changed files and diff content."""
        text = f"{commit.summary} {commit.body} {diff_text}".lower()
        paths_lower = [p.lower() for p in file_paths]

        # Check for documentation-only changes
        if paths_lower and all(
            any(p.endswith(ext) for ext in (".md", ".rst", ".txt", ".adoc"))
            or "doc" in p
            or "readme" in p
            for p in paths_lower
        ):
            return ImpactScope.DOCS

        # Check for test-only changes
        if paths_lower and all(
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
        if paths_lower and all(
            any(pat in p for pat in config_patterns) for p in paths_lower
        ):
            return ImpactScope.CONFIG

        # Check for public API changes
        if any(
            kw in text
            for kw in ("public api", "breaking", "endpoint", "interface", "export")
        ):
            return ImpactScope.PUBLIC_API

        # Default to internal
        return ImpactScope.INTERNAL

    def _detect_breaking_change(self, commit: CommitInfo, diff_text: str) -> bool:
        """Detect if this is a breaking change."""
        text = f"{commit.summary} {commit.body}".lower()

        # Explicit breaking change markers
        if "breaking" in text or "breaking-change" in text:
            return True
        if commit.summary.upper().startswith("BREAKING"):
            return True

        # Conventional commit: "feat!:" or "fix(scope)!:"
        if ":" in commit.summary:
            prefix = commit.summary.split(":")[0]
            if "!" in prefix:
                return True

        # Heuristic: major version bumps, removed exports
        if any(kw in text for kw in ("removed", "deprecated", "breaking")):
            if any(kw in text for kw in ("api", "export", "interface", "endpoint")):
                return True

        return False

    def _extract_technical_highlights(self, diff_text: str) -> List[str]:
        """Extract interesting technical decisions from the diff."""
        highlights: List[str] = []

        if not diff_text:
            return highlights

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
        if re.search(
            r"^\+.*\b(try|catch|except|raise|throw)\b", diff_text, re.MULTILINE
        ):
            highlights.append("Added error handling")

        # Detect added tests
        if re.search(
            r"^\+.*\b(test_|describe\(|it\(|pytest)\b", diff_text, re.MULTILINE
        ):
            highlights.append("Added tests")

        # Detect logging changes
        if re.search(
            r"^\+.*\b(logger\.|logging\.|console\.log)\b", diff_text, re.MULTILINE
        ):
            highlights.append("Added logging")

        return highlights[:5]  # Limit to 5 highlights

