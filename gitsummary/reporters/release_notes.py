"""Release notes report builders and synthesis strategies."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..core import ChangeCategory, CommitArtifact, CommitInfo, ImpactScope
from ..reports.release_notes import (
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


class ReleaseNotesClassifier:
    """Classifies commits into user-facing vs internal buckets."""

    def classify(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
    ) -> ReleaseNotesReport:
        user_facing: List[Tuple[CommitInfo, CommitArtifact]] = []
        internal: List[Tuple[CommitInfo, CommitArtifact]] = []

        for commit in commits:
            artifact = artifacts.get(commit.sha)
            if artifact is None:
                continue

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


class ReleaseNoteSynthesizer:
    """Strategy object for producing ReleaseNote artifacts."""

    def __init__(self, provider: Optional["BaseLLMProvider"] = None) -> None:
        self.provider = provider

    def synthesize(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
        *,
        product_name: str,
        version: str,
        revision_range: str,
    ) -> ReleaseNote:
        """Generate a release note using LLM or heuristics."""
        tip_commit = commits[0].sha if commits else ""
        artifacts_data = self._prepare_artifacts_for_synthesis(commits, artifacts)

        if self.provider is not None:
            synthesized = self._synthesize_with_llm(product_name, version, artifacts_data)
        else:
            synthesized = self._synthesize_heuristic_from_data(artifacts_data)

        source_commits = [
            SourceCommit(sha=c.short_sha, category=artifacts[c.sha].category.value)
            for c in commits
            if c.sha in artifacts and artifacts[c.sha] is not None
        ]

        analyzed_count = sum(1 for a in artifacts.values() if a is not None)

        metadata = ReleaseNoteMetadata(
            generated_at=datetime.utcnow(),
            generator_version="0.2.0",
            llm_provider=self.provider.name if self.provider else None,
            llm_model=self.provider.get_model() if self.provider else None,
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
    ) -> Dict[str, Any]:
        from ..llm.prompts_release_note import (
            RELEASE_NOTE_SYSTEM_PROMPT,
            build_release_note_synthesis_prompt,
            format_artifacts_for_synthesis,
        )
        from ..llm.schemas_release_note import ReleaseNoteSynthesisSchema

        if self.provider is None:
            return self._synthesize_heuristic_from_data(artifacts_data)

        artifacts_summary = format_artifacts_for_synthesis(artifacts_data)
        user_prompt = build_release_note_synthesis_prompt(
            product_name, version, artifacts_summary
        )

        response = self.provider.extract_structured(
            user_prompt,
            ReleaseNoteSynthesisSchema,
            system_prompt=RELEASE_NOTE_SYSTEM_PROMPT,
        )

        if response.parsed:
            return response.parsed

        return self._synthesize_heuristic_from_data(artifacts_data)

    def _synthesize_heuristic_from_data(
        self,
        artifacts_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        by_category: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in artifacts_data:
            by_category[item["category"]].append(item)

        highlights = []
        breaking_items = [a for a in artifacts_data if a.get("is_breaking")]

        if by_category.get("feature"):
            feat = by_category["feature"][0]
            highlights.append({
                "emoji": "🚀",
                "type": "new",
                "summary": feat["intent_summary"][:60],
            })

        if by_category.get("performance"):
            perf = by_category["performance"][0]
            highlights.append({
                "emoji": "✨",
                "type": "improved",
                "summary": perf["intent_summary"][:60],
            })

        if by_category.get("fix"):
            fix = by_category["fix"][0]
            highlights.append({
                "emoji": "🛠️",
                "type": "fixed",
                "summary": fix["intent_summary"][:60],
            })

        if by_category.get("security"):
            sec = by_category["security"][0]
            highlights.append({
                "emoji": "🔒",
                "type": "security",
                "summary": sec["intent_summary"][:60],
            })

        if breaking_items:
            highlights.append({
                "emoji": "⚠️",
                "type": "breaking",
                "summary": breaking_items[0]["intent_summary"][:60],
            })

        features = [
            {
                "title": f["intent_summary"][:50],
                "description": f["intent_summary"],
                "user_benefit": f.get("behavior_after") or "Enhances functionality.",
                "commit_refs": [f["sha"]],
            }
            for f in by_category.get("feature", [])
        ]

        improvements = [
            {"summary": i["intent_summary"], "commit_refs": [i["sha"]]}
            for i in by_category.get("performance", [])
        ]
        improvements.extend([
            {"summary": i["intent_summary"], "commit_refs": [i["sha"]]}
            for i in by_category.get("refactor", [])
            if i.get("impact_scope") != "internal"
        ])

        fixes = [
            {"summary": f["intent_summary"], "commit_refs": [f["sha"]]}
            for f in by_category.get("fix", [])
        ]
        fixes.extend([
            {"summary": s["intent_summary"], "commit_refs": [s["sha"]]}
            for s in by_category.get("security", [])
        ])

        deprecations = [
            {
                "what": b["intent_summary"],
                "reason": "API or behavior change required.",
                "migration": b.get("behavior_after") or "See documentation for details.",
                "commit_refs": [b["sha"]],
            }
            for b in breaking_items
        ]

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
