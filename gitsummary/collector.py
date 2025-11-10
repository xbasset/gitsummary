"""
Artifact collection logic.

Coordinates Git operations to collect and structure artifact data.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from gitsummary import __version__
from gitsummary.git_ops import CommitInfo, FileChange, GitRepository
from gitsummary.ignore import IgnoreFilter


class ArtifactCollector:
    """
    Collects Git data and produces structured artifacts.

    Orchestrates Git operations, filtering, and artifact structure generation
    according to the spec.
    """

    def __init__(self, repo_path: Optional[Path] = None) -> None:
        """
        Initialize the collector.

        Args:
            repo_path: Path to Git repository. If None, uses current directory.
        """
        self.git_repo = GitRepository(repo_path)
        self.ignore_filter = IgnoreFilter(self.git_repo.repo_path)

    def collect(self, tag_a: str, tag_b: str) -> Dict[str, Any]:
        """
        Collect an artifact for the range between two tags.

        Args:
            tag_a: Starting tag (exclusive).
            tag_b: Ending tag (inclusive).

        Returns:
            Complete artifact dictionary.

        Raises:
            ValueError: If tags are invalid.
        """
        # Collect commits
        commits = list(self.git_repo.get_commits_between(tag_a, tag_b))

        # Collect file changes
        file_changes = list(self.git_repo.get_diff_between(tag_a, tag_b))

        # Filter file changes based on ignore rules
        filtered_changes = [
            change
            for change in file_changes
            if self.ignore_filter.should_include(change.path)
        ]

        # Build artifact structure
        artifact = {
            "context": self._build_context(tag_a, tag_b, commits, filtered_changes),
            "intention": self._build_intention(commits, filtered_changes),
            "implementation": self._build_implementation(filtered_changes),
            "impact": self._build_impact(commits, filtered_changes),
            "maintainability": self._build_maintainability(filtered_changes),
            "deployment": self._build_deployment(filtered_changes),
            "meta": self._build_meta(commits, filtered_changes),
            "alias": None,  # Reserved for future use
        }

        return artifact

    def _build_context(
        self,
        tag_a: str,
        tag_b: str,
        commits: List[CommitInfo],
        changes: List[FileChange],
    ) -> Dict[str, Any]:
        """Build the context section of the artifact."""
        # Extract unique authors
        authors = list(set(f"{c.author_name} <{c.author_email}>" for c in commits))

        # Get date range
        if commits:
            dates = [c.date for c in commits]
            date_range = {
                "start": min(dates).isoformat(),
                "end": max(dates).isoformat(),
            }
        else:
            date_range = {"start": None, "end": None}

        return {
            "commit_range": f"{tag_a}..{tag_b}",
            "tags": {"start": tag_a, "end": tag_b},
            "authors": sorted(authors),
            "date_range": date_range,
            "commit_count": len(commits),
            "file_count": len(changes),
            "commits_summary": self.git_repo.get_commit_summary(commits),
        }

    def _build_intention(
        self, commits: List[CommitInfo], changes: List[FileChange]
    ) -> Dict[str, Any]:
        """
        Build the intention section (inferred semantics).

        In POC, this provides structured placeholders for LLM reasoning.
        Future versions will integrate actual inference.
        """
        # Extract commit message patterns
        commit_messages = [c.message for c in commits]
        all_text = " ".join(commit_messages).lower()

        # Simple keyword-based inference (placeholder for future LLM)
        keywords = {
            "feature": ["add", "implement", "create", "new"],
            "bugfix": ["fix", "bug", "issue", "resolve"],
            "refactor": ["refactor", "cleanup", "improve", "reorganize"],
            "documentation": ["docs", "documentation", "readme"],
            "testing": ["test", "testing", "coverage"],
        }

        detected_types = []
        for type_name, terms in keywords.items():
            if any(term in all_text for term in terms):
                detected_types.append(type_name)

        # Detect affected subsystems from file paths
        subsystems = set()
        for change in changes:
            parts = Path(change.path).parts
            if len(parts) > 1:
                subsystems.add(parts[0])

        return {
            "inferred_goal": f"Changes spanning {len(changes)} files",
            "inferred_types": detected_types if detected_types else ["unknown"],
            "affected_subsystems": sorted(subsystems),
            "confidence": "low",  # POC: simple heuristics only
            "rationale": "Inferred from commit messages and file paths",
        }

    def _build_implementation(
        self, changes: List[FileChange]
    ) -> Dict[str, Any]:
        """Build the implementation section."""
        total_additions = sum(c.additions for c in changes)
        total_deletions = sum(c.deletions for c in changes)

        # Categorize changes by type
        changes_by_type = {
            "added": [c for c in changes if c.change_type == "A"],
            "modified": [c for c in changes if c.change_type == "M"],
            "deleted": [c for c in changes if c.change_type == "D"],
            "renamed": [c for c in changes if c.change_type == "R"],
        }

        # Detect dependency changes
        dependency_files = [
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "Gemfile",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
        ]
        dependency_changes = [
            c.path
            for c in changes
            if any(Path(c.path).name == df for df in dependency_files)
        ]

        # Detect patterns in code
        patterns = self._detect_code_patterns(changes)

        return {
            "files_changed": len(changes),
            "lines_added": total_additions,
            "lines_deleted": total_deletions,
            "net_change": total_additions - total_deletions,
            "changes_by_type": {
                k: [{"path": c.path, "additions": c.additions, "deletions": c.deletions}]
                for k, v in changes_by_type.items()
                for c in v
            },
            "dependency_changes": dependency_changes,
            "detected_patterns": patterns,
            "complexity_delta": self._estimate_complexity_delta(changes),
        }

    def _detect_code_patterns(self, changes: List[FileChange]) -> List[str]:
        """Detect common code patterns in changes."""
        patterns = []
        all_diffs = " ".join(c.diff for c in changes if c.diff)

        # Simple pattern detection
        pattern_keywords = {
            "async_await": ["async def", "await "],
            "error_handling": ["try:", "except ", "raise ", "throw "],
            "logging": ["logger.", "log.", "print("],
            "database": ["SELECT ", "INSERT ", "UPDATE ", "DELETE "],
            "api_endpoints": ["@app.", "@router.", "app.get", "app.post"],
            "testing": ["def test_", "class Test", "assert "],
        }

        for pattern_name, keywords in pattern_keywords.items():
            if any(keyword in all_diffs for keyword in keywords):
                patterns.append(pattern_name)

        return patterns

    def _estimate_complexity_delta(self, changes: List[FileChange]) -> str:
        """Estimate the complexity change (simple heuristic)."""
        total_lines = sum(c.additions + c.deletions for c in changes)

        if total_lines < 50:
            return "low"
        elif total_lines < 200:
            return "medium"
        else:
            return "high"

    def _build_impact(
        self, commits: List[CommitInfo], changes: List[FileChange]
    ) -> Dict[str, Any]:
        """Build the impact section."""
        # Detect potentially user-visible changes
        ui_patterns = [".html", ".css", ".jsx", ".tsx", ".vue", ".svelte"]
        ui_changes = [c for c in changes if any(c.path.endswith(p) for p in ui_patterns)]

        # Detect breaking changes from commit messages
        breaking_indicators = ["BREAKING", "breaking change", "breaking:"]
        breaking_commits = [
            c
            for c in commits
            if any(indicator in c.message for indicator in breaking_indicators)
        ]

        return {
            "user_visible_changes": len(ui_changes) > 0,
            "ui_files_changed": len(ui_changes),
            "breaking_changes_detected": len(breaking_commits) > 0,
            "compatibility_risks": self._assess_compatibility_risks(changes),
            "behavioral_changes": f"{len(changes)} files modified",
        }

    def _assess_compatibility_risks(self, changes: List[FileChange]) -> List[str]:
        """Assess potential compatibility risks."""
        risks = []

        # Check for API/schema changes
        api_files = [".proto", "schema", "api", "openapi"]
        if any(any(pattern in c.path for pattern in api_files) for c in changes):
            risks.append("API or schema changes detected")

        # Check for configuration changes
        config_files = [".env", ".yaml", ".yml", ".toml", ".ini", "config"]
        if any(any(pattern in c.path for pattern in config_files) for c in changes):
            risks.append("Configuration changes may require updates")

        # Check for database migrations
        if any("migration" in c.path.lower() for c in changes):
            risks.append("Database migrations present")

        return risks

    def _build_maintainability(self, changes: List[FileChange]) -> Dict[str, Any]:
        """Build the maintainability section."""
        # Detect test changes
        test_patterns = ["test_", "_test.", "spec.", ".test.", "__tests__"]
        test_changes = [
            c for c in changes if any(pattern in c.path for pattern in test_patterns)
        ]

        # Detect documentation changes
        doc_patterns = [".md", "README", "CHANGELOG", "docs/"]
        doc_changes = [
            c for c in changes if any(pattern in c.path for pattern in doc_patterns)
        ]

        # Simple tech debt indicators
        tech_debt_indicators = []
        all_diffs = " ".join(c.diff for c in changes if c.diff)
        if "TODO" in all_diffs or "FIXME" in all_diffs:
            tech_debt_indicators.append("New TODOs or FIXMEs added")
        if any(c.additions > 200 for c in changes):
            tech_debt_indicators.append("Large files added/modified")

        return {
            "test_changes": {
                "count": len(test_changes),
                "files": [c.path for c in test_changes],
            },
            "documentation_changes": {
                "count": len(doc_changes),
                "files": [c.path for c in doc_changes],
            },
            "tech_debt_indicators": tech_debt_indicators,
            "refactor_signals": self._detect_refactor_signals(changes),
        }

    def _detect_refactor_signals(self, changes: List[FileChange]) -> List[str]:
        """Detect signals indicating refactoring work."""
        signals = []

        # Detect file renames (common in refactors)
        renamed = [c for c in changes if c.change_type == "R"]
        if renamed:
            signals.append(f"{len(renamed)} file(s) renamed")

        # Detect balanced add/delete (refactoring pattern)
        for change in changes:
            if (
                change.additions > 0
                and change.deletions > 0
                and abs(change.additions - change.deletions) < 10
            ):
                signals.append(f"Balanced changes in {change.path}")
                break  # Just report once

        return signals

    def _build_deployment(self, changes: List[FileChange]) -> Dict[str, Any]:
        """Build the deployment section."""
        # Detect new logging
        log_patterns = [
            "logger.",
            "log.",
            "console.log",
            "print(",
            "System.out.",
            "fmt.Print",
        ]
        log_changes = []
        for change in changes:
            if change.diff and any(pattern in change.diff for pattern in log_patterns):
                log_changes.append(change.path)

        # Detect error handling changes
        error_patterns = ["try:", "catch", "except ", "raise ", "throw "]
        error_changes = []
        for change in changes:
            if change.diff and any(pattern in change.diff for pattern in error_patterns):
                error_changes.append(change.path)

        # Detect configuration changes
        config_files = [
            ".env",
            ".yaml",
            ".yml",
            ".ini",
            "Dockerfile",
            "docker-compose",
            ".sh",
        ]
        config_changes = [
            c.path for c in changes if any(cf in c.path for cf in config_files)
        ]

        # Detect infrastructure changes
        infra_patterns = [
            "k8s/",
            "kubernetes/",
            "helm/",
            "terraform/",
            ".tf",
            ".github/workflows",
            ".gitlab-ci",
            "Jenkinsfile",
        ]
        infra_changes = [
            c.path for c in changes if any(pattern in c.path for pattern in infra_patterns)
        ]

        # Monitoring recommendations
        monitoring_notes = []
        if log_changes:
            monitoring_notes.append("New logging added - consider log aggregation setup")
        if error_changes:
            monitoring_notes.append("Error handling modified - review alerting rules")
        if infra_changes:
            monitoring_notes.append("Infrastructure changes - verify monitoring coverage")

        return {
            "new_logs_detected": {
                "count": len(log_changes),
                "files": log_changes[:10],  # Limit to first 10
            },
            "error_handling_changes": {
                "count": len(error_changes),
                "files": error_changes[:10],
            },
            "configuration_changes": config_changes,
            "infrastructure_changes": infra_changes,
            "monitoring_notes": monitoring_notes,
        }

    def _build_meta(
        self, commits: List[CommitInfo], changes: List[FileChange]
    ) -> Dict[str, Any]:
        """Build the meta section with confidence and evidence."""
        # Collect evidence references
        evidence = []
        for commit in commits[:5]:  # First 5 commits as evidence
            evidence.append({"commit": commit.sha, "message": commit.message.split("\n")[0]})

        for change in changes[:5]:  # First 5 file changes
            evidence.append(
                {
                    "commit": "range",  # In a range, don't track per-file commits in POC
                    "file": change.path,
                    "change_type": change.change_type,
                }
            )

        return {
            "schema_version": "0.1.0",
            "tool_version": __version__,
            "collected_at": datetime.now().isoformat(),
            "confidence": {
                "context": "high",  # Direct from Git
                "intention": "low",  # Simple heuristics only
                "implementation": "high",  # Direct from Git
                "impact": "medium",  # Pattern-based
                "maintainability": "medium",  # Pattern-based
                "deployment": "medium",  # Pattern-based
            },
            "evidence": evidence,
        }
