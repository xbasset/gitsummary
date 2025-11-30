"""Tests for extractor base types.

Tests the ExtractionResult dataclass and merge functionality.
"""

from __future__ import annotations

import pytest

from gitsummary.core import ChangeCategory, ImpactScope
from gitsummary.extractors.base import ExtractionResult


class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""

    def test_default_values(self) -> None:
        """Test that ExtractionResult has appropriate defaults."""
        result = ExtractionResult()
        assert result.intent_summary is None
        assert result.category is None
        assert result.behavior_before is None
        assert result.behavior_after is None
        assert result.impact_scope is None
        assert result.is_breaking is None
        assert result.technical_highlights == []

    def test_creation_with_all_fields(
        self, complete_extraction: ExtractionResult
    ) -> None:
        """Test creating ExtractionResult with all fields."""
        assert complete_extraction.intent_summary == "Add user authentication"
        assert complete_extraction.category == ChangeCategory.FEATURE
        assert complete_extraction.behavior_before == "No authentication"
        assert complete_extraction.behavior_after == "Users can log in"
        assert complete_extraction.impact_scope == ImpactScope.PUBLIC_API
        assert complete_extraction.is_breaking is False
        assert len(complete_extraction.technical_highlights) == 1

    def test_merge_with_fallback_uses_primary(
        self, complete_extraction: ExtractionResult, empty_extraction: ExtractionResult
    ) -> None:
        """Test that merge prefers primary values over fallback."""
        merged = complete_extraction.merge_with(empty_extraction)
        
        assert merged.intent_summary == complete_extraction.intent_summary
        assert merged.category == complete_extraction.category
        assert merged.impact_scope == complete_extraction.impact_scope

    def test_merge_with_fallback_fills_gaps(
        self, partial_extraction: ExtractionResult, complete_extraction: ExtractionResult
    ) -> None:
        """Test that merge fills gaps with fallback values."""
        merged = partial_extraction.merge_with(complete_extraction)
        
        # Partial has these
        assert merged.intent_summary == "Partial extraction"
        assert merged.category == ChangeCategory.FIX
        
        # Fallback fills these
        assert merged.behavior_before == "No authentication"
        assert merged.behavior_after == "Users can log in"
        assert merged.impact_scope == ImpactScope.PUBLIC_API

    def test_merge_preserves_explicit_false(self) -> None:
        """Test that explicit False is_breaking is preserved in merge."""
        primary = ExtractionResult(is_breaking=False)
        fallback = ExtractionResult(is_breaking=True)
        
        merged = primary.merge_with(fallback)
        assert merged.is_breaking is False

    def test_merge_uses_fallback_when_none(self) -> None:
        """Test that None is_breaking uses fallback."""
        primary = ExtractionResult(is_breaking=None)
        fallback = ExtractionResult(is_breaking=True)
        
        merged = primary.merge_with(fallback)
        assert merged.is_breaking is True

    def test_merge_prefers_primary_technical_highlights(self) -> None:
        """Test that primary highlights are preferred."""
        primary = ExtractionResult(technical_highlights=["Primary highlight"])
        fallback = ExtractionResult(technical_highlights=["Fallback highlight"])
        
        merged = primary.merge_with(fallback)
        assert merged.technical_highlights == ["Primary highlight"]

    def test_merge_uses_fallback_highlights_when_empty(self) -> None:
        """Test that fallback highlights are used when primary is empty."""
        primary = ExtractionResult(technical_highlights=[])
        fallback = ExtractionResult(technical_highlights=["Fallback highlight"])
        
        merged = primary.merge_with(fallback)
        assert merged.technical_highlights == ["Fallback highlight"]

    def test_merge_chain(self) -> None:
        """Test chaining multiple merges."""
        first = ExtractionResult(intent_summary="First")
        second = ExtractionResult(category=ChangeCategory.FIX)
        third = ExtractionResult(impact_scope=ImpactScope.INTERNAL)
        
        result = first.merge_with(second).merge_with(third)
        
        assert result.intent_summary == "First"
        assert result.category == ChangeCategory.FIX
        assert result.impact_scope == ImpactScope.INTERNAL

