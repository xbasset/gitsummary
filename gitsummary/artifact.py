"""Utilities for constructing gitsummary artifacts."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

from .git import Commit, DiffStat, FileChange

__all__ = ["build_artifact"]


@dataclass(frozen=True)
class ArtifactContext:
    """Derived context information for a commit range."""

    commit_range: str
    commits: Sequence[Commit]

    @property
    def authors(self) -> List[str]:
        return sorted({commit.author for commit in self.commits})

    @property
    def summary(self) -> str:
        messages = [commit.summary for commit in self.commits]
        return "; ".join(messages[:10])

    @property
    def date_range(self) -> Dict[str, str]:
        if not self.commits:
            return {"start": None, "end": None}
        dates = sorted(commit.date for commit in self.commits)
        return {"start": dates[0].isoformat(), "end": dates[-1].isoformat()}


def _changed_paths(changes: Sequence[FileChange]) -> List[str]:
    return [change.path for change in changes]


def _section_intention(context: ArtifactContext) -> Dict[str, object]:
    if not context.commits:
        return {"goal": "No commits in range", "rationale": None, "domain": None}
    headline = context.commits[0].summary.lower()
    domain = None
    if any(keyword in headline for keyword in ("doc", "readme", "spec")):
        domain = "documentation"
    elif any(keyword in headline for keyword in ("build", "ci", "pipeline")):
        domain = "infrastructure"
    elif any(keyword in headline for keyword in ("refactor", "cleanup")):
        domain = "maintainability"
    else:
        domain = "feature"
    return {
        "goal": context.commits[0].summary,
        "rationale": "Derived from the latest commit message.",
        "domain": domain,
    }


def _section_implementation(changes: Sequence[FileChange], diff_stat: DiffStat, diff_text: str) -> Dict[str, object]:
    files = _changed_paths(changes)
    extensions = Counter(Path(path).suffix for path in files if path)
    top_extensions = [ext or "<none>" for ext, _ in extensions.most_common(3)]
    return {
        "files_changed": files,
        "loc": {"added": diff_stat.insertions, "removed": diff_stat.deletions},
        "top_file_types": top_extensions,
        "functions": _detect_symbols(diff_text),
    }


def _section_impact(diff_text: str) -> Dict[str, object]:
    risk = "low"
    if re.search(r"(schema|migration|database)", diff_text, re.IGNORECASE):
        risk = "medium"
    if re.search(r"(public api|breaking|deprecation)", diff_text, re.IGNORECASE):
        risk = "high"
    return {
        "summary": "Heuristic impact assessment based on diff keywords.",
        "risk": risk,
    }


def _section_maintainability(diff_text: str) -> Dict[str, object]:
    tests_added = len(re.findall(r"^\+.*test", diff_text, flags=re.MULTILINE))
    debt_references = len(re.findall(r"TODO|FIXME", diff_text))
    score = max(0, 5 + tests_added - debt_references)
    return {
        "tests_added": tests_added,
        "debt_references": debt_references,
        "score": score,
    }


def _section_deployment(diff_text: str) -> Dict[str, object]:
    configuration_files = [
        line for line in diff_text.splitlines() if line.startswith("+++ b/") and any(
            line.endswith(candidate)
            for candidate in ("Dockerfile", "docker-compose.yml", "helm.yaml", "values.yaml", "requirements.txt")
        )
    ]
    logging_changes = len(re.findall(r"logger|logging|console\.log|print\(", diff_text, flags=re.IGNORECASE))
    return {
        "configuration_touches": configuration_files,
        "logging_changes": logging_changes,
    }


def _detect_symbols(diff_text: str) -> Dict[str, List[str]]:
    pattern = re.compile(r"^[+-]\s*(def|class|function|module|interface)\s+([\w\.]+)", re.MULTILINE)
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
    return {"added": added, "removed": removed, "modified": modified}


def build_artifact(
    *,
    commit_range: str,
    commits: Sequence[Commit],
    changes: Sequence[FileChange],
    diff_stat: DiffStat,
    diff_text: str,
) -> Dict[str, object]:
    """Return an artifact dict matching the v0.1 specification."""

    context = ArtifactContext(commit_range=commit_range, commits=commits)
    artifact: Dict[str, object] = {
        "context": {
            "commit_range": commit_range,
            "authors": context.authors,
            "date_range": context.date_range,
            "summaries": [commit.summary for commit in commits],
        },
        "intention": _section_intention(context),
        "implementation": _section_implementation(changes, diff_stat, diff_text),
        "impact": _section_impact(diff_text),
        "maintainability": _section_maintainability(diff_text),
        "deployment": _section_deployment(diff_text),
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
