"""Command line interface for the gitsummary proof of concept."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SCHEMA_VERSION = "0.1.0"


class GitCommandError(RuntimeError):
    """Raised when an underlying git command fails."""


@dataclass
class CommitInfo:
    sha: str
    author: str
    date: datetime
    summary: str


@dataclass
class DiffStats:
    insertions: int
    deletions: int
    files: List[str]
    file_changes: List[Tuple[str, str]]


@dataclass
class FunctionChanges:
    added: List[str]
    removed: List[str]
    modified: List[str]


class StorageLayout:
    """Represents the canonical on-disk layout for gitsummary artifacts."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.artifacts = self.root / "artifacts"
        self.manifests = self.root / "manifests" / "by-range"
        self.index = self.root / "index"
        self.schema = self.root / "schema"
        self.notes = self.root / "notes" / "summary"

    def ensure(self) -> None:
        for path in [
            self.artifacts,
            self.manifests,
            self.index,
            self.schema,
            self.notes,
        ]:
            path.mkdir(parents=True, exist_ok=True)

        schema_version_file = self.schema / "version"
        if not schema_version_file.exists():
            schema_version_file.write_text(SCHEMA_VERSION + "\n", encoding="utf-8")


def run_git(args: Sequence[str]) -> str:
    """Run a git command and return the stdout, raising on failure."""

    process = subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if process.returncode != 0:
        raise GitCommandError(process.stderr.strip() or "git command failed")
    return process.stdout


def ensure_git_repository() -> Path:
    """Ensure the current working directory is inside a git repository."""

    toplevel = run_git(["rev-parse", "--show-toplevel"]).strip()
    return Path(toplevel)


def collect_commits(range_spec: str) -> List[CommitInfo]:
    output = run_git(
        [
            "log",
            "--format=%H\x1f%an\x1f%ad\x1f%s",
            "--date=iso-strict",
            range_spec,
        ]
    )
    commits: List[CommitInfo] = []
    for line in output.strip().splitlines():
        if not line:
            continue
        sha, author, date_raw, summary = line.split("\x1f", 3)
        commits.append(
            CommitInfo(
                sha=sha,
                author=author,
                date=datetime.fromisoformat(date_raw),
                summary=summary.strip(),
            )
        )
    return commits


def collect_diff_stats(range_spec: str) -> DiffStats:
    name_status_output = run_git(["diff", "--name-status", range_spec])
    files: List[str] = []
    file_changes: List[Tuple[str, str]] = []
    for line in name_status_output.strip().splitlines():
        if not line:
            continue
        status, *rest = line.split("\t")
        path = rest[-1] if rest else ""
        files.append(path)
        file_changes.append((status, path))

    numstat_output = run_git(["diff", "--numstat", range_spec])
    insertions = 0
    deletions = 0
    for line in numstat_output.strip().splitlines():
        if not line:
            continue
        added, removed, *_ = line.split("\t")
        if added != "-":
            insertions += int(added)
        if removed != "-":
            deletions += int(removed)

    return DiffStats(insertions=insertions, deletions=deletions, files=files, file_changes=file_changes)


def detect_function_changes(diff_output: str) -> FunctionChanges:
    added: List[str] = []
    removed: List[str] = []
    for line in diff_output.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            candidate = line[1:].strip()
            name = _extract_callable_name(candidate)
            if name:
                added.append(name)
        elif line.startswith("-") and not line.startswith("---"):
            candidate = line[1:].strip()
            name = _extract_callable_name(candidate)
            if name:
                removed.append(name)
    modified = sorted(set(added) & set(removed))
    added_only = sorted(set(added) - set(modified))
    removed_only = sorted(set(removed) - set(modified))
    return FunctionChanges(added=added_only, removed=removed_only, modified=modified)


def _extract_callable_name(line: str) -> Optional[str]:
    match = re.match(r"(def|class)\s+([A-Za-z0-9_]+)", line)
    if match:
        return match.group(2)
    return None


def detect_code_patterns(diff_output: str) -> List[str]:
    patterns: Dict[str, str] = {
        "TODO": "TODO markers present",
        "FIXME": "FIXME markers present",
        "logger": "Logging statements detected",
        "print(": "Print statements detected",
    }
    detected: List[str] = []
    lowered = diff_output.lower()
    for key, description in patterns.items():
        check = key.lower()
        if check in lowered:
            detected.append(description)
    return sorted(set(detected))


def detect_dependency_changes(file_changes: Iterable[Tuple[str, str]]) -> Dict[str, List[str]]:
    added: List[str] = []
    removed: List[str] = []
    dependency_files = (
        "requirements.txt",
        "pyproject.toml",
        "setup.cfg",
        "Pipfile",
        "package.json",
        "poetry.lock",
        "requirements-dev.txt",
    )
    for status, path in file_changes:
        normalized = Path(path)
        if normalized.name in dependency_files:
            if status.startswith("A"):
                added.append(path)
            elif status.startswith("D"):
                removed.append(path)
            else:
                added.append(path)
    return {"added": sorted(set(added)), "removed": sorted(set(removed))}


def infer_deployment_signals(file_changes: Iterable[Tuple[str, str]], diff_output: str) -> Dict[str, List[str]]:
    relevant_extensions = (
        ".yaml",
        ".yml",
        ".ini",
        ".tf",
        ".dockerfile",
        "Dockerfile",
    )
    categories = {
        "configuration": [],
        "infrastructure": [],
        "logging": [],
    }
    for status, path in file_changes:
        lower_path = path.lower()
        if any(lower_path.endswith(ext.lower()) for ext in relevant_extensions):
            categories["configuration"].append(path)
        if "docker" in lower_path or "deploy" in lower_path:
            categories["infrastructure"].append(path)
    if "logger" in diff_output.lower() or "logging." in diff_output.lower():
        categories["logging"].append("logging statements modified")
    return {key: sorted(set(value)) for key, value in categories.items() if value}


def infer_maintainability(diff_stats: DiffStats) -> Dict[str, object]:
    tests_modified = [path for path in diff_stats.files if "test" in path.lower()]
    return {
        "tests_modified": sorted(set(tests_modified)),
        "tech_debt_notes": (
            "Test coverage affected" if tests_modified else "No automated tests detected in changes"
        ),
    }


def build_artifact(
    start_ref: str,
    end_ref: str,
    commits: List[CommitInfo],
    diff_stats: DiffStats,
    function_changes: FunctionChanges,
    code_patterns: List[str],
    dependency_changes: Dict[str, List[str]],
    deployment_signals: Dict[str, List[str]],
) -> Dict[str, object]:
    range_spec = f"{start_ref}..{end_ref}"
    authors = sorted({commit.author for commit in commits})
    dates = sorted(commit.date for commit in commits)
    date_range: Optional[Tuple[str, str]]
    if dates:
        date_range = (dates[0].isoformat(), dates[-1].isoformat())
    else:
        date_range = None
    branch_output = run_git(["branch", "--contains", end_ref])
    branches = [line.strip().lstrip("* ") for line in branch_output.splitlines() if line.strip()]

    total_commits = len(commits)
    commit_summaries = [commit.summary for commit in commits]

    impact_summary = "; ".join(commit_summaries[:5]) or "No commit messages available"
    tests_modified = [path for path in diff_stats.files if "test" in path.lower()]

    artifact: Dict[str, object] = {
        "context": {
            "commit_range": range_spec,
            "end_reference": end_ref,
            "authors": authors,
            "date_range": date_range,
            "branches": branches,
            "commit_summaries": commit_summaries,
            "total_commits": total_commits,
        },
        "intention": {
            "summary": impact_summary,
            "rationale": "Inferred from commit messages",
            "domains": list({Path(path).parts[0] for path in diff_stats.files if Path(path).parts}),
        },
        "implementation": {
            "files_changed": diff_stats.files,
            "insertions": diff_stats.insertions,
            "deletions": diff_stats.deletions,
            "net_change": diff_stats.insertions - diff_stats.deletions,
            "function_changes": {
                "added": function_changes.added,
                "removed": function_changes.removed,
                "modified": function_changes.modified,
            },
            "code_patterns": code_patterns,
            "dependency_changes": dependency_changes,
            "complexity_delta": diff_stats.insertions - diff_stats.deletions,
        },
        "impact": {
            "user_visible": impact_summary,
            "compatibility_risks": "Potential behavior changes implied by commit summaries",
            "tests_modified": tests_modified,
        },
        "maintainability": infer_maintainability(diff_stats),
        "deployment": deployment_signals,
        "meta": {
            "artifact_version": SCHEMA_VERSION,
            "schema_version": SCHEMA_VERSION,
            "confidence": {
                "overall": 0.5 if commits else 0.2,
                "tests": 0.6 if tests_modified else 0.3,
            },
            "generated_at": datetime.now().isoformat(),
            "evidence": {
                "commits": [commit.sha for commit in commits],
            },
        },
    }
    return artifact


def write_artifact(storage: StorageLayout, range_spec: str, artifact: Dict[str, object]) -> str:
    artifact_json = json.dumps(artifact, indent=2)
    artifact_oid = hashlib.sha256(artifact_json.encode("utf-8")).hexdigest()
    storage.ensure()

    artifact_path = storage.artifacts / f"{artifact_oid}.json"
    artifact_path.write_text(artifact_json + "\n", encoding="utf-8")

    sanitized_range = range_spec.replace("/", "_")
    manifest_path = storage.manifests / f"{sanitized_range}.json"
    manifest_data = {
        "range": range_spec,
        "artifact": artifact_oid,
        "generated_at": datetime.now().isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    latest_path = storage.index / "latest.json"
    latest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    return artifact_oid


def command_collect(start_ref: str, end_ref: str) -> str:
    ensure_git_repository()
    range_spec = f"{start_ref}..{end_ref}"

    commits = collect_commits(range_spec)
    diff_stats = collect_diff_stats(range_spec)
    diff_output = run_git(["diff", range_spec])
    function_changes = detect_function_changes(diff_output)
    code_patterns = detect_code_patterns(diff_output)
    dependency_changes = detect_dependency_changes(diff_stats.file_changes)
    deployment_signals = infer_deployment_signals(diff_stats.file_changes, diff_output)

    artifact = build_artifact(
        start_ref,
        end_ref,
        commits,
        diff_stats,
        function_changes,
        code_patterns,
        dependency_changes,
        deployment_signals,
    )

    storage = StorageLayout(Path(".gitsummary"))
    artifact_oid = write_artifact(storage, range_spec, artifact)
    return artifact_oid


def command_analyze(artifact_oid: str, target: str) -> Dict[str, object]:
    storage = StorageLayout(Path(".gitsummary"))
    artifact_path = storage.artifacts / f"{artifact_oid}.json"
    if not artifact_path.exists():
        raise FileNotFoundError(f"Artifact {artifact_oid} not found at {artifact_path}")
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    facet = artifact.get(target)
    if facet is None:
        available = ", ".join(sorted(artifact.keys()))
        raise KeyError(f"Facet '{target}' not found. Available facets: {available}")
    return facet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="gitsummary proof of concept CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Collect git-derived facts between two refs")
    collect_parser.add_argument("start_ref", help="Starting git reference (older tag or commit)")
    collect_parser.add_argument("end_ref", help="Ending git reference (newer tag or commit)")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a stored artifact")
    analyze_parser.add_argument("artifact_oid", help="Identifier reported by the collect command")
    analyze_parser.add_argument(
        "--target",
        required=True,
        help="Facet to analyze (e.g. context, implementation, impact, deployment)",
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "collect":
        artifact_oid = command_collect(args.start_ref, args.end_ref)
        print(f"Artifact created: {artifact_oid}")
        return 0
    if args.command == "analyze":
        try:
            facet = command_analyze(args.artifact_oid, args.target)
        except (FileNotFoundError, KeyError, GitCommandError) as exc:
            parser.error(str(exc))
        print(json.dumps(facet, indent=2))
        return 0
    parser.error("Unknown command")
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
