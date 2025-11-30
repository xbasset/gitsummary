"""Pytest configuration and shared fixtures.

This module provides fixtures used across multiple test modules,
including mock commit data and artifacts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import pytest

from gitsummary.core import (
    ChangeCategory,
    CommitArtifact,
    CommitDiff,
    CommitInfo,
    DiffStat,
    FileDiff,
    ImpactScope,
)
from gitsummary.extractors.base import ExtractionResult


# ─────────────────────────────────────────────────────────────────────────────
# CommitInfo Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def simple_commit() -> CommitInfo:
    """A simple feature commit."""
    return CommitInfo(
        sha="abc1234567890abcdef1234567890abcdef123456",
        short_sha="abc1234",
        author_name="Test Author",
        author_email="test@example.com",
        date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        summary="feat: add user authentication",
        body="This commit adds basic user authentication\nwith username and password.",
        parent_shas=["def5678901234567890abcdef5678901234567890"],
    )


@pytest.fixture
def fix_commit() -> CommitInfo:
    """A bug fix commit."""
    return CommitInfo(
        sha="fix7890123456789abcdef7890123456789abcdef",
        short_sha="fix7890",
        author_name="Test Author",
        author_email="test@example.com",
        date=datetime(2024, 1, 16, 14, 20, 0, tzinfo=timezone.utc),
        summary="fix: resolve null pointer exception in login",
        body="Fixed a bug where login would fail if credentials were empty.",
        parent_shas=["abc1234567890abcdef1234567890abcdef123456"],
    )


@pytest.fixture
def breaking_commit() -> CommitInfo:
    """A breaking change commit."""
    return CommitInfo(
        sha="brk4567890123456789abcdefghijklmnopqrstuv",
        short_sha="brk4567",
        author_name="Test Author",
        author_email="test@example.com",
        date=datetime(2024, 1, 17, 9, 0, 0, tzinfo=timezone.utc),
        summary="feat!: redesign authentication API",
        body="BREAKING CHANGE: The auth endpoint signature has changed.",
        parent_shas=["fix7890123456789abcdef7890123456789abcdef"],
    )


@pytest.fixture
def merge_commit() -> CommitInfo:
    """A merge commit with multiple parents."""
    return CommitInfo(
        sha="mrg9012345678901234567890123456789012345",
        short_sha="mrg9012",
        author_name="Test Author",
        author_email="test@example.com",
        date=datetime(2024, 1, 18, 11, 45, 0, tzinfo=timezone.utc),
        summary="Merge branch 'feature/auth' into main",
        body="",
        parent_shas=[
            "abc1234567890abcdef1234567890abcdef123456",
            "def5678901234567890abcdef5678901234567890",
        ],
    )


@pytest.fixture
def security_commit() -> CommitInfo:
    """A security fix commit."""
    return CommitInfo(
        sha="sec1234567890123456789012345678901234567",
        short_sha="sec1234",
        author_name="Security Team",
        author_email="security@example.com",
        date=datetime(2024, 1, 19, 8, 0, 0, tzinfo=timezone.utc),
        summary="fix: patch SQL injection vulnerability",
        body="CVE-2024-1234: Fixes SQL injection in user search.",
        parent_shas=["mrg9012345678901234567890123456789012345"],
    )


@pytest.fixture
def docs_commit() -> CommitInfo:
    """A documentation-only commit."""
    return CommitInfo(
        sha="doc0987654321098765432109876543210987654",
        short_sha="doc0987",
        author_name="Doc Writer",
        author_email="docs@example.com",
        date=datetime(2024, 1, 20, 15, 30, 0, tzinfo=timezone.utc),
        summary="docs: update README with usage examples",
        body="Added examples for the new authentication API.",
        parent_shas=["sec1234567890123456789012345678901234567"],
    )


@pytest.fixture
def chore_commit() -> CommitInfo:
    """A chore/maintenance commit."""
    return CommitInfo(
        sha="chr5432109876543210987654321098765432109",
        short_sha="chr5432",
        author_name="Bot",
        author_email="bot@example.com",
        date=datetime(2024, 1, 21, 0, 0, 0, tzinfo=timezone.utc),
        summary="chore: update dependencies",
        body="Bumped all dependencies to latest versions.",
        parent_shas=["doc0987654321098765432109876543210987654"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Diff Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def simple_diff() -> CommitDiff:
    """A simple diff with one file changed."""
    return CommitDiff(
        sha="abc1234567890abcdef1234567890abcdef123456",
        files=[
            FileDiff(
                path="src/auth.py",
                old_path=None,
                status="M",
                insertions=25,
                deletions=5,
                patch="",
                hunks=[],
            )
        ],
        stat=DiffStat(insertions=25, deletions=5),
    )


@pytest.fixture
def multi_file_diff() -> CommitDiff:
    """A diff with multiple files changed."""
    return CommitDiff(
        sha="fix7890123456789abcdef7890123456789abcdef",
        files=[
            FileDiff(
                path="src/auth.py",
                old_path=None,
                status="M",
                insertions=10,
                deletions=3,
                patch="",
                hunks=[],
            ),
            FileDiff(
                path="tests/test_auth.py",
                old_path=None,
                status="A",
                insertions=50,
                deletions=0,
                patch="",
                hunks=[],
            ),
            FileDiff(
                path="README.md",
                old_path=None,
                status="M",
                insertions=5,
                deletions=2,
                patch="",
                hunks=[],
            ),
        ],
        stat=DiffStat(insertions=65, deletions=5),
    )


@pytest.fixture
def docs_only_diff() -> CommitDiff:
    """A diff with only documentation files changed."""
    return CommitDiff(
        sha="doc0987654321098765432109876543210987654",
        files=[
            FileDiff(
                path="README.md",
                old_path=None,
                status="M",
                insertions=20,
                deletions=5,
                patch="",
                hunks=[],
            ),
            FileDiff(
                path="docs/api.md",
                old_path=None,
                status="A",
                insertions=100,
                deletions=0,
                patch="",
                hunks=[],
            ),
        ],
        stat=DiffStat(insertions=120, deletions=5),
    )


@pytest.fixture
def test_only_diff() -> CommitDiff:
    """A diff with only test files changed."""
    return CommitDiff(
        sha="test123456789012345678901234567890123456",
        files=[
            FileDiff(
                path="tests/test_auth.py",
                old_path=None,
                status="M",
                insertions=30,
                deletions=10,
                patch="",
                hunks=[],
            ),
            FileDiff(
                path="tests/test_user.py",
                old_path=None,
                status="A",
                insertions=50,
                deletions=0,
                patch="",
                hunks=[],
            ),
        ],
        stat=DiffStat(insertions=80, deletions=10),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Artifact Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def feature_artifact() -> CommitArtifact:
    """A feature artifact."""
    return CommitArtifact(
        commit_hash="abc1234567890abcdef1234567890abcdef123456",
        intent_summary="Add user authentication with username and password support",
        category=ChangeCategory.FEATURE,
        behavior_before="Users could not log in to the system",
        behavior_after="Users can authenticate using username and password",
        impact_scope=ImpactScope.PUBLIC_API,
        is_breaking=False,
        technical_highlights=[
            "Added class `AuthService`",
            "Implemented password hashing with bcrypt",
        ],
    )


@pytest.fixture
def fix_artifact() -> CommitArtifact:
    """A bug fix artifact."""
    return CommitArtifact(
        commit_hash="fix7890123456789abcdef7890123456789abcdef",
        intent_summary="Fix null pointer exception when credentials are empty",
        category=ChangeCategory.FIX,
        behavior_before="Login crashed with empty credentials",
        behavior_after="Login properly validates and rejects empty credentials",
        impact_scope=ImpactScope.INTERNAL,
        is_breaking=False,
        technical_highlights=["Added error handling"],
    )


@pytest.fixture
def breaking_artifact() -> CommitArtifact:
    """A breaking change artifact."""
    return CommitArtifact(
        commit_hash="brk4567890123456789abcdefghijklmnopqrstuv",
        intent_summary="Redesign authentication API with new endpoint structure",
        category=ChangeCategory.FEATURE,
        behavior_before="Auth endpoint accepted positional parameters",
        behavior_after="Auth endpoint requires named parameters in JSON body",
        impact_scope=ImpactScope.PUBLIC_API,
        is_breaking=True,
        technical_highlights=[
            "Changed endpoint from /auth to /api/v2/auth",
            "Removed deprecated fields",
        ],
    )


@pytest.fixture
def security_artifact() -> CommitArtifact:
    """A security fix artifact."""
    return CommitArtifact(
        commit_hash="sec1234567890123456789012345678901234567",
        intent_summary="Patch SQL injection vulnerability in user search",
        category=ChangeCategory.SECURITY,
        behavior_before="User search was vulnerable to SQL injection",
        behavior_after="User search uses parameterized queries",
        impact_scope=ImpactScope.INTERNAL,
        is_breaking=False,
        technical_highlights=["Added parameterized queries", "Added input validation"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# ExtractionResult Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def complete_extraction() -> ExtractionResult:
    """A fully populated extraction result."""
    return ExtractionResult(
        intent_summary="Add user authentication",
        category=ChangeCategory.FEATURE,
        behavior_before="No authentication",
        behavior_after="Users can log in",
        impact_scope=ImpactScope.PUBLIC_API,
        is_breaking=False,
        technical_highlights=["Added AuthService"],
    )


@pytest.fixture
def partial_extraction() -> ExtractionResult:
    """A partially populated extraction result."""
    return ExtractionResult(
        intent_summary="Partial extraction",
        category=ChangeCategory.FIX,
        behavior_before=None,
        behavior_after=None,
        impact_scope=None,
        is_breaking=None,
        technical_highlights=[],
    )


@pytest.fixture
def empty_extraction() -> ExtractionResult:
    """An empty extraction result (all defaults)."""
    return ExtractionResult()


# ─────────────────────────────────────────────────────────────────────────────
# List Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def commit_list(
    simple_commit: CommitInfo,
    fix_commit: CommitInfo,
    breaking_commit: CommitInfo,
    docs_commit: CommitInfo,
) -> List[CommitInfo]:
    """A list of diverse commits for testing."""
    return [simple_commit, fix_commit, breaking_commit, docs_commit]


@pytest.fixture
def artifact_list(
    feature_artifact: CommitArtifact,
    fix_artifact: CommitArtifact,
    breaking_artifact: CommitArtifact,
) -> List[CommitArtifact]:
    """A list of diverse artifacts for testing."""
    return [feature_artifact, fix_artifact, breaking_artifact]

