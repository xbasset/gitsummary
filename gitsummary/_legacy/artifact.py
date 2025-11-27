"""Legacy artifact construction.

DEPRECATED: Use gitsummary.services.build_commit_artifact for new code.

This module is maintained for backwards compatibility with the v0.1
artifact schema that includes facets like context, intention,
implementation, impact, maintainability, and deployment.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

# Import legacy types from core
from ..core.models import CommitInfo, DiffStat, FileChange

# Re-export for backwards compatibility
Commit = CommitInfo


@dataclass(frozen=True)
class ArtifactContext:
    """Derived context information for a commit range (LEGACY)."""

    commit_range: str
    commits: Sequence[CommitInfo]

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
    commits: Sequence[CommitInfo],
    changes: Sequence[FileChange],
    diff_stat: DiffStat,
    diff_text: str,
) -> Dict[str, object]:
    """Return an artifact dict matching the legacy v0.1 specification.

    DEPRECATED: Use build_commit_artifact for new code.

    This function produces the old multi-facet artifact format that
    includes context, intention, implementation, impact, maintainability,
    and deployment sections.
    """
    from .. import __version__

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
            "schema_version": "0.1.0",
            "tool_version": __version__,
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

