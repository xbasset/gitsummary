"""Reporter service for generating reports from artifacts.

This service provides high-level report generation capabilities,
transforming stored artifacts into various output formats.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type

from ..core import ChangeCategory, CommitArtifact, CommitInfo, ImpactScope
from ..core.release_note import (
    BugFix,
    CallToAction,
    Deprecation,
    Feature,
    Highlight,
    Improvement,
    ReleaseNote,
    ReleaseNoteHeader,
    ReleaseNoteMetadata,
    SourceCommit,
)


class ReporterService:
    """Service for generating reports from commit artifacts.

    Provides methods for generating changelogs, release notes,
    and impact analyses from stored artifacts.
    """

    def generate_changelog(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
        *,
        include_unanalyzed: bool = False,
    ) -> "ChangelogReport":
        """Generate a changelog report from commits and their artifacts.

        Args:
            commits: List of commits in the range.
            artifacts: Dict mapping SHA to artifact (or None if not analyzed).
            include_unanalyzed: Whether to include commits without artifacts.

        Returns:
            A ChangelogReport ready for formatting.
        """
        by_category: Dict[ChangeCategory, List[Tuple[CommitInfo, CommitArtifact]]] = (
            defaultdict(list)
        )
        unanalyzed: List[CommitInfo] = []

        for commit in commits:
            artifact = artifacts.get(commit.sha)
            if artifact is None:
                if include_unanalyzed:
                    unanalyzed.append(commit)
                continue
            by_category[artifact.category].append((commit, artifact))

        return ChangelogReport(
            by_category=dict(by_category),
            unanalyzed=unanalyzed,
        )

    def generate_release_notes(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
    ) -> "ReleaseNotesReport":
        """Generate release notes focusing on user-facing changes.

        Args:
            commits: List of commits in the range.
            artifacts: Dict mapping SHA to artifact (or None if not analyzed).

        Returns:
            A ReleaseNotesReport ready for formatting.
        """
        user_facing: List[Tuple[CommitInfo, CommitArtifact]] = []
        internal: List[Tuple[CommitInfo, CommitArtifact]] = []

        for commit in commits:
            artifact = artifacts.get(commit.sha)
            if artifact is None:
                continue

            # Determine if user-facing
            if artifact.impact_scope in (ImpactScope.PUBLIC_API, ImpactScope.CONFIG):
                user_facing.append((commit, artifact))
            elif artifact.category in (
                ChangeCategory.FEATURE,
                ChangeCategory.FIX,
                ChangeCategory.SECURITY,
            ):
                if artifact.impact_scope != ImpactScope.TEST:
                    user_facing.append((commit, artifact))
            else:
                internal.append((commit, artifact))

        return ReleaseNotesReport(
            user_facing=user_facing,
            internal=internal,
            total_commits=len(commits),
            analyzed_count=sum(1 for a in artifacts.values() if a is not None),
        )

    def generate_impact_report(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
    ) -> "ImpactReport":
        """Generate an impact analysis report.

        Args:
            commits: List of commits in the range.
            artifacts: Dict mapping SHA to artifact (or None if not analyzed).

        Returns:
            An ImpactReport ready for formatting.
        """
        from collections import Counter

        scope_counts: Counter[str] = Counter()
        breaking_changes: List[Tuple[CommitInfo, CommitArtifact]] = []
        all_highlights: List[str] = []

        for commit in commits:
            artifact = artifacts.get(commit.sha)
            if artifact is None:
                continue

            scope_counts[artifact.impact_scope.value] += 1
            if artifact.is_breaking:
                breaking_changes.append((commit, artifact))
            all_highlights.extend(artifact.technical_highlights)

        return ImpactReport(
            total_commits=len(commits),
            analyzed_count=sum(1 for a in artifacts.values() if a is not None),
            scope_distribution=dict(scope_counts),
            breaking_changes=breaking_changes,
            technical_highlights=all_highlights,
        )

    def generate_llm_release_notes(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
        *,
        product_name: str,
        version: str,
        revision_range: str,
        provider: Optional["BaseLLMProvider"] = None,
    ) -> ReleaseNote:
        """Generate user-facing release notes using LLM synthesis.

        This method synthesizes commit-level artifacts into a cohesive,
        user-focused release note document.

        Args:
            commits: List of commits in the range.
            artifacts: Dict mapping SHA to artifact (or None if not analyzed).
            product_name: Name of the product for the header.
            version: Version string for the header.
            revision_range: Git revision range (e.g., 'v0.1.0..v0.2.0').
            provider: LLM provider to use for synthesis. If None, uses heuristics.

        Returns:
            A complete ReleaseNote ready for formatting or storage.
        """
        # Get tip commit SHA
        tip_commit = commits[0].sha if commits else ""

        # Prepare artifacts data for synthesis
        artifacts_data = self._prepare_artifacts_for_synthesis(commits, artifacts)

        # Generate the synthesized content
        if provider is not None:
            synthesized = self._synthesize_with_llm(
                product_name, version, artifacts_data, provider
            )
        else:
            synthesized = self._synthesize_heuristic(commits, artifacts)

        # Build the release note
        source_commits = [
            SourceCommit(sha=c.short_sha, category=artifacts[c.sha].category.value)
            for c in commits
            if c.sha in artifacts and artifacts[c.sha] is not None
        ]

        analyzed_count = sum(1 for a in artifacts.values() if a is not None)

        metadata = ReleaseNoteMetadata(
            generated_at=datetime.utcnow(),
            generator_version="0.2.0",
            llm_provider=provider.name if provider else None,
            llm_model=provider.get_model() if provider else None,
            revision_range=revision_range,
            tip_commit=tip_commit,
            commit_count=len(commits),
            analyzed_count=analyzed_count,
            source_commits=source_commits,
        )

        header = ReleaseNoteHeader(
            product_name=product_name,
            version=version,
            release_date=datetime.utcnow().strftime("%Y-%m-%d"),
            theme=synthesized.get("theme", "Various improvements and fixes."),
        )

        # Build sections from synthesized content
        highlights = [
            Highlight(emoji=h["emoji"], type=h["type"], summary=h["summary"])
            for h in synthesized.get("highlights", [])
        ]

        features = [
            Feature(
                title=f["title"],
                description=f["description"],
                user_benefit=f["user_benefit"],
                commits=f.get("commit_refs", []),
            )
            for f in synthesized.get("features", [])
        ]

        improvements = [
            Improvement(summary=i["summary"], commits=i.get("commit_refs", []))
            for i in synthesized.get("improvements", [])
        ]

        fixes = [
            BugFix(summary=f["summary"], commits=f.get("commit_refs", []))
            for f in synthesized.get("fixes", [])
        ]

        deprecations = [
            Deprecation(
                what=d["what"],
                reason=d["reason"],
                migration=d["migration"],
                commits=d.get("commit_refs", []),
            )
            for d in synthesized.get("deprecations", [])
        ]

        return ReleaseNote(
            metadata=metadata,
            header=header,
            highlights=highlights,
            features=features,
            improvements=improvements,
            fixes=fixes,
            deprecations=deprecations,
        )

    def _prepare_artifacts_for_synthesis(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
    ) -> List[Dict[str, Any]]:
        """Prepare commit artifacts data for LLM synthesis."""
        result = []
        for commit in commits:
            artifact = artifacts.get(commit.sha)
            if artifact is None:
                continue

            result.append({
                "sha": commit.short_sha,
                "category": artifact.category.value,
                "intent_summary": artifact.intent_summary,
                "behavior_before": artifact.behavior_before,
                "behavior_after": artifact.behavior_after,
                "is_breaking": artifact.is_breaking,
                "technical_highlights": artifact.technical_highlights,
                "impact_scope": artifact.impact_scope.value,
            })

        return result

    def _synthesize_with_llm(
        self,
        product_name: str,
        version: str,
        artifacts_data: List[Dict[str, Any]],
        provider: "BaseLLMProvider",
    ) -> Dict[str, Any]:
        """Use LLM to synthesize release note content."""
        from ..llm.prompts import (
            RELEASE_NOTE_SYSTEM_PROMPT,
            build_release_note_synthesis_prompt,
            format_artifacts_for_synthesis,
        )
        from ..llm.schemas import ReleaseNoteSynthesisSchema

        # Format artifacts for the prompt
        artifacts_summary = format_artifacts_for_synthesis(artifacts_data)

        # Build the prompt
        user_prompt = build_release_note_synthesis_prompt(
            product_name, version, artifacts_summary
        )

        # Call the LLM
        response = provider.extract_structured(
            user_prompt,
            ReleaseNoteSynthesisSchema,
            system_prompt=RELEASE_NOTE_SYSTEM_PROMPT,
        )

        if response.parsed:
            return response.parsed

        # Fallback to heuristic if LLM fails
        return self._synthesize_heuristic_from_data(artifacts_data)

    def _synthesize_heuristic(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
    ) -> Dict[str, Any]:
        """Generate synthesized content using heuristics (no LLM)."""
        artifacts_data = self._prepare_artifacts_for_synthesis(commits, artifacts)
        return self._synthesize_heuristic_from_data(artifacts_data)

    def _synthesize_heuristic_from_data(
        self,
        artifacts_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate synthesized content from prepared artifacts data."""
        # Group by category
        by_category: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in artifacts_data:
            by_category[item["category"]].append(item)

        # Build highlights
        highlights = []
        breaking_items = [a for a in artifacts_data if a.get("is_breaking")]

        # Add feature highlight
        if by_category.get("feature"):
            feat = by_category["feature"][0]
            highlights.append({
                "emoji": "🚀",
                "type": "new",
                "summary": feat["intent_summary"][:60],
            })

        # Add improvement highlight
        if by_category.get("performance"):
            perf = by_category["performance"][0]
            highlights.append({
                "emoji": "✨",
                "type": "improved",
                "summary": perf["intent_summary"][:60],
            })

        # Add fix highlight
        if by_category.get("fix"):
            fix = by_category["fix"][0]
            highlights.append({
                "emoji": "🛠️",
                "type": "fixed",
                "summary": fix["intent_summary"][:60],
            })

        # Add security highlight
        if by_category.get("security"):
            sec = by_category["security"][0]
            highlights.append({
                "emoji": "🔒",
                "type": "security",
                "summary": sec["intent_summary"][:60],
            })

        # Add breaking change highlight
        if breaking_items:
            highlights.append({
                "emoji": "⚠️",
                "type": "breaking",
                "summary": breaking_items[0]["intent_summary"][:60],
            })

        # Build features
        features = [
            {
                "title": f["intent_summary"][:50],
                "description": f["intent_summary"],
                "user_benefit": f.get("behavior_after") or "Enhances functionality.",
                "commit_refs": [f["sha"]],
            }
            for f in by_category.get("feature", [])
        ]

        # Build improvements
        improvements = [
            {"summary": i["intent_summary"], "commit_refs": [i["sha"]]}
            for i in by_category.get("performance", [])
        ]
        improvements.extend([
            {"summary": i["intent_summary"], "commit_refs": [i["sha"]]}
            for i in by_category.get("refactor", [])
            if i.get("impact_scope") != "internal"
        ])

        # Build fixes
        fixes = [
            {"summary": f["intent_summary"], "commit_refs": [f["sha"]]}
            for f in by_category.get("fix", [])
        ]
        fixes.extend([
            {"summary": s["intent_summary"], "commit_refs": [s["sha"]]}
            for s in by_category.get("security", [])
        ])

        # Build deprecations
        deprecations = [
            {
                "what": b["intent_summary"],
                "reason": "API or behavior change required.",
                "migration": b.get("behavior_after") or "See documentation for details.",
                "commit_refs": [b["sha"]],
            }
            for b in breaking_items
        ]

        # Generate theme
        feature_count = len(by_category.get("feature", []))
        fix_count = len(by_category.get("fix", []))
        perf_count = len(by_category.get("performance", []))

        theme_parts = []
        if feature_count > 0:
            theme_parts.append(f"{feature_count} new feature{'s' if feature_count > 1 else ''}")
        if fix_count > 0:
            theme_parts.append(f"{fix_count} bug fix{'es' if fix_count > 1 else ''}")
        if perf_count > 0:
            theme_parts.append("performance improvements")

        theme = f"This release includes {', '.join(theme_parts)}." if theme_parts else "Various improvements and fixes."

        return {
            "theme": theme,
            "highlights": highlights[:5],
            "features": features,
            "improvements": improvements,
            "fixes": fixes,
            "deprecations": deprecations,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Report Data Classes
# ─────────────────────────────────────────────────────────────────────────────


class ChangelogReport:
    """Structured changelog data ready for formatting."""

    def __init__(
        self,
        by_category: Dict[ChangeCategory, List[Tuple[CommitInfo, CommitArtifact]]],
        unanalyzed: List[CommitInfo],
    ) -> None:
        self.by_category = by_category
        self.unanalyzed = unanalyzed

    @property
    def features(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.FEATURE, [])

    @property
    def fixes(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.FIX, [])

    @property
    def security(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.SECURITY, [])

    @property
    def performance(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.PERFORMANCE, [])

    @property
    def refactors(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.REFACTOR, [])

    @property
    def chores(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        return self.by_category.get(ChangeCategory.CHORE, [])

    @property
    def breaking_changes(self) -> List[Tuple[CommitInfo, CommitArtifact]]:
        """All breaking changes across categories."""
        return [
            (c, a)
            for items in self.by_category.values()
            for c, a in items
            if a.is_breaking
        ]


class ReleaseNotesReport:
    """Structured release notes data ready for formatting."""

    def __init__(
        self,
        user_facing: List[Tuple[CommitInfo, CommitArtifact]],
        internal: List[Tuple[CommitInfo, CommitArtifact]],
        total_commits: int,
        analyzed_count: int,
    ) -> None:
        self.user_facing = user_facing
        self.internal = internal
        self.total_commits = total_commits
        self.analyzed_count = analyzed_count


class ImpactReport:
    """Structured impact analysis data ready for formatting."""

    def __init__(
        self,
        total_commits: int,
        analyzed_count: int,
        scope_distribution: Dict[str, int],
        breaking_changes: List[Tuple[CommitInfo, CommitArtifact]],
        technical_highlights: List[str],
    ) -> None:
        self.total_commits = total_commits
        self.analyzed_count = analyzed_count
        self.scope_distribution = scope_distribution
        self.breaking_changes = breaking_changes
        self.technical_highlights = technical_highlights

    @property
    def breaking_count(self) -> int:
        return len(self.breaking_changes)

