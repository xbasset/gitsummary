"""Reporter service for generating reports from artifacts.

This service provides high-level report generation capabilities,
transforming stored artifacts into various output formats.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..core import CommitArtifact, CommitInfo
from ..reports.release_notes import ReleaseNote
from ..reporters import (
    ChangelogBuilder,
    ChangelogReport,
    ImpactBuilder,
    ImpactReport,
    ReleaseNoteSynthesizer,
    ReleaseNotesClassifier,
    ReleaseNotesReport,
)


class ReporterService:
    """Service for generating reports from commit artifacts.

    Provides methods for generating changelogs, release notes,
    and impact analyses from stored artifacts.
    """

    def __init__(self) -> None:
        self._changelog_builder = ChangelogBuilder()
        self._impact_builder = ImpactBuilder()
        self._release_notes_classifier = ReleaseNotesClassifier()

    def generate_changelog(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
        *,
        include_unanalyzed: bool = False,
    ) -> "ChangelogReport":
        """Generate a changelog report from commits and their artifacts."""
        return self._changelog_builder.build(
            commits, artifacts, include_unanalyzed=include_unanalyzed
        )

    def generate_release_notes(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
    ) -> "ReleaseNotesReport":
        """Generate release notes focusing on user-facing changes."""
        return self._release_notes_classifier.classify(commits, artifacts)

    def generate_impact_report(
        self,
        commits: List[CommitInfo],
        artifacts: Dict[str, Optional[CommitArtifact]],
    ) -> "ImpactReport":
        """Generate an impact analysis report."""
        return self._impact_builder.build(commits, artifacts)

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
        """Generate user-facing release notes using LLM synthesis."""
        synthesizer = ReleaseNoteSynthesizer(provider)
        return synthesizer.synthesize(
            commits,
            artifacts,
            product_name=product_name,
            version=version,
            revision_range=revision_range,
        )
