"""Enumeration types for the gitsummary domain.

These enums represent the classification vocabulary used throughout
the artifact schema and extraction logic.
"""

from __future__ import annotations

from enum import Enum


class ImpactScope(str, Enum):
    """The scope of the impact of a change.

    Used to classify how broadly a change affects the codebase
    and its consumers.
    """

    PUBLIC_API = "public_api"  # Changes external interfaces, endpoints, or public methods
    INTERNAL = "internal"  # Refactoring, internal logic, private methods
    DEPENDENCY = "dependency"  # Bumping versions, adding/removing libraries
    CONFIG = "config"  # Changing defaults, environment variables, or flags
    DOCS = "docs"  # Documentation only (README, comments, etc.)
    TEST = "test"  # Tests only
    UNKNOWN = "unknown"  # Cannot determine scope


class ChangeCategory(str, Enum):
    """The primary category of a change.

    Based on conventional commit types, but semantic rather than syntactic.
    """

    FEATURE = "feature"
    FIX = "fix"
    SECURITY = "security"
    PERFORMANCE = "performance"
    REFACTOR = "refactor"
    CHORE = "chore"

