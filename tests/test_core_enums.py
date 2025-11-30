"""Tests for core enumeration types.

Tests the enums in gitsummary.core.enums including
ImpactScope and ChangeCategory.
"""

from __future__ import annotations

import pytest

from gitsummary.core import ChangeCategory, ImpactScope


class TestImpactScope:
    """Tests for ImpactScope enum."""

    def test_all_values_exist(self) -> None:
        """Test that all expected impact scopes exist."""
        expected = [
            "public_api",
            "internal",
            "dependency",
            "config",
            "docs",
            "test",
            "unknown",
        ]
        actual = [scope.value for scope in ImpactScope]
        assert sorted(actual) == sorted(expected)

    def test_public_api_value(self) -> None:
        """Test PUBLIC_API enum value."""
        assert ImpactScope.PUBLIC_API.value == "public_api"

    def test_internal_value(self) -> None:
        """Test INTERNAL enum value."""
        assert ImpactScope.INTERNAL.value == "internal"

    def test_is_string_enum(self) -> None:
        """Test that ImpactScope is a string enum and has correct value."""
        assert isinstance(ImpactScope.PUBLIC_API.value, str)
        assert ImpactScope.PUBLIC_API.value == "public_api"

    def test_enum_from_value(self) -> None:
        """Test creating enum from string value."""
        scope = ImpactScope("public_api")
        assert scope == ImpactScope.PUBLIC_API

    def test_invalid_value_raises(self) -> None:
        """Test that invalid value raises ValueError."""
        with pytest.raises(ValueError):
            ImpactScope("invalid_scope")


class TestChangeCategory:
    """Tests for ChangeCategory enum."""

    def test_all_values_exist(self) -> None:
        """Test that all expected categories exist."""
        expected = ["feature", "fix", "security", "performance", "refactor", "chore"]
        actual = [cat.value for cat in ChangeCategory]
        assert sorted(actual) == sorted(expected)

    def test_feature_value(self) -> None:
        """Test FEATURE enum value."""
        assert ChangeCategory.FEATURE.value == "feature"

    def test_fix_value(self) -> None:
        """Test FIX enum value."""
        assert ChangeCategory.FIX.value == "fix"

    def test_security_value(self) -> None:
        """Test SECURITY enum value."""
        assert ChangeCategory.SECURITY.value == "security"

    def test_performance_value(self) -> None:
        """Test PERFORMANCE enum value."""
        assert ChangeCategory.PERFORMANCE.value == "performance"

    def test_refactor_value(self) -> None:
        """Test REFACTOR enum value."""
        assert ChangeCategory.REFACTOR.value == "refactor"

    def test_chore_value(self) -> None:
        """Test CHORE enum value."""
        assert ChangeCategory.CHORE.value == "chore"

    def test_is_string_enum(self) -> None:
        """Test that ChangeCategory is a string enum and has correct value."""
        assert isinstance(ChangeCategory.FEATURE.value, str)
        assert ChangeCategory.FEATURE.value == "feature"

    def test_enum_from_value(self) -> None:
        """Test creating enum from string value."""
        category = ChangeCategory("fix")
        assert category == ChangeCategory.FIX

    def test_invalid_value_raises(self) -> None:
        """Test that invalid value raises ValueError."""
        with pytest.raises(ValueError):
            ChangeCategory("invalid_category")

