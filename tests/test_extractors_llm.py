"""Tests for LLM-based semantic extraction.

Tests the LLMExtractor class and its provider handling.
Uses mocking to avoid requiring actual LLM API access.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gitsummary.core import ChangeCategory, CommitInfo, ImpactScope
from gitsummary.extractors.llm import (
    LLMExtractor,
    get_llm_provider,
    set_llm_provider,
    _null_provider,
)
from gitsummary.extractors.base import ExtractionResult


class TestLegacyProviderInterface:
    """Tests for legacy provider interface functions."""

    def test_null_provider_returns_none(self, simple_commit: CommitInfo) -> None:
        """Test that the default null provider returns None."""
        result = _null_provider(simple_commit, "diff patch")
        assert result is None

    def test_set_and_get_llm_provider(self, simple_commit: CommitInfo) -> None:
        """Test setting and getting a custom LLM provider."""
        custom_provider = MagicMock(return_value={"intent_summary": "Test"})
        
        set_llm_provider(custom_provider)
        retrieved = get_llm_provider()
        
        assert retrieved is custom_provider
        
        # Reset to null provider
        set_llm_provider(_null_provider)


class TestLLMExtractor:
    """Tests for LLMExtractor class."""

    def test_init_with_defaults(self) -> None:
        """Test default initialization."""
        extractor = LLMExtractor()
        assert extractor._legacy_provider is None
        assert extractor._provider_name is None
        assert extractor._llm_provider is None

    def test_init_with_provider_name(self) -> None:
        """Test initialization with provider name."""
        extractor = LLMExtractor(provider_name="openai")
        assert extractor._provider_name == "openai"

    def test_init_with_legacy_provider(self) -> None:
        """Test initialization with legacy provider function."""
        custom_provider = MagicMock()
        extractor = LLMExtractor(provider=custom_provider)
        assert extractor._legacy_provider is custom_provider


class TestLLMExtractorExtract:
    """Tests for LLMExtractor.extract method."""

    def test_extract_returns_empty_result_when_no_provider(
        self, simple_commit: CommitInfo
    ) -> None:
        """Test that empty result is returned when no provider configured."""
        extractor = LLMExtractor()
        result = extractor.extract(simple_commit, diff_patch="")
        
        assert isinstance(result, ExtractionResult)
        assert result.intent_summary is None
        assert result.category is None

    def test_extract_uses_legacy_provider(
        self, simple_commit: CommitInfo
    ) -> None:
        """Test that legacy provider is used when configured."""
        legacy_provider = MagicMock(return_value={
            "intent_summary": "Legacy summary",
            "category": "feature",
            "impact_scope": "internal",
        })
        
        extractor = LLMExtractor(provider=legacy_provider)
        result = extractor.extract(simple_commit, diff_patch="+added")
        
        legacy_provider.assert_called_once()
        assert result.intent_summary == "Legacy summary"
        assert result.category == ChangeCategory.FEATURE

    def test_extract_with_global_legacy_provider(
        self, simple_commit: CommitInfo
    ) -> None:
        """Test that global legacy provider is used when no explicit provider."""
        global_provider = MagicMock(return_value={
            "intent_summary": "Global summary",
            "category": "fix",
        })
        
        # Set global provider
        set_llm_provider(global_provider)
        
        try:
            extractor = LLMExtractor()
            result = extractor.extract(simple_commit, diff_patch="")
            
            global_provider.assert_called_once()
            assert result.intent_summary == "Global summary"
            assert result.category == ChangeCategory.FIX
        finally:
            # Reset to null provider
            set_llm_provider(_null_provider)


class TestParseLLMResult:
    """Tests for _parse_llm_result method."""

    def test_parses_complete_result(self) -> None:
        """Test parsing a complete LLM result."""
        extractor = LLMExtractor()
        
        llm_result = {
            "intent_summary": "Add authentication feature",
            "category": "feature",
            "behavior_before": "No auth",
            "behavior_after": "Users can login",
            "impact_scope": "public_api",
            "is_breaking": False,
            "technical_highlights": ["Added class AuthService"],
        }
        
        result = extractor._parse_llm_result(llm_result)
        
        assert result.intent_summary == "Add authentication feature"
        assert result.category == ChangeCategory.FEATURE
        assert result.behavior_before == "No auth"
        assert result.behavior_after == "Users can login"
        assert result.impact_scope == ImpactScope.PUBLIC_API
        assert result.is_breaking is False
        assert "Added class AuthService" in result.technical_highlights

    def test_parses_minimal_result(self) -> None:
        """Test parsing a minimal LLM result."""
        extractor = LLMExtractor()
        
        llm_result = {
            "intent_summary": "Quick fix",
        }
        
        result = extractor._parse_llm_result(llm_result)
        
        assert result.intent_summary == "Quick fix"
        assert result.category is None
        assert result.behavior_before is None
        assert result.is_breaking is None
        assert result.technical_highlights == []

    def test_handles_invalid_category(self) -> None:
        """Test that invalid category is handled gracefully."""
        extractor = LLMExtractor()
        
        llm_result = {
            "intent_summary": "Test",
            "category": "invalid_category",
        }
        
        result = extractor._parse_llm_result(llm_result)
        
        # Invalid category should result in None
        assert result.category is None

    def test_handles_invalid_impact_scope(self) -> None:
        """Test that invalid impact_scope is handled gracefully."""
        extractor = LLMExtractor()
        
        llm_result = {
            "intent_summary": "Test",
            "impact_scope": "invalid_scope",
        }
        
        result = extractor._parse_llm_result(llm_result)
        
        # Invalid scope should result in None
        assert result.impact_scope is None

    def test_parses_all_categories(self) -> None:
        """Test that all valid categories are parsed."""
        extractor = LLMExtractor()
        
        for category in ChangeCategory:
            llm_result = {"category": category.value}
            result = extractor._parse_llm_result(llm_result)
            assert result.category == category

    def test_parses_all_impact_scopes(self) -> None:
        """Test that all valid impact scopes are parsed."""
        extractor = LLMExtractor()
        
        for scope in ImpactScope:
            llm_result = {"impact_scope": scope.value}
            result = extractor._parse_llm_result(llm_result)
            assert result.impact_scope == scope


class TestGetProvider:
    """Tests for _get_provider method."""

    def test_returns_none_when_no_provider_name(self) -> None:
        """Test that None is returned when no provider name set."""
        extractor = LLMExtractor()
        result = extractor._get_provider()
        assert result is None

    def test_caches_provider(self) -> None:
        """Test that provider is cached after initialization."""
        extractor = LLMExtractor()
        
        mock_provider = MagicMock()
        extractor._llm_provider = mock_provider
        
        # Should return cached provider
        result = extractor._get_provider()
        assert result is mock_provider

    def test_handles_provider_init_error(self) -> None:
        """Test that provider initialization errors are handled."""
        extractor = LLMExtractor(provider_name="nonexistent")
        
        with patch("gitsummary.extractors.llm.logger") as mock_logger:
            result = extractor._get_provider()
        
        # Should return None on error
        assert result is None


class TestExtractWithNewProvider:
    """Tests for extract method when using new provider architecture.
    
    Note: These tests cover the integration with the new provider architecture.
    The _extract_with_provider method is tested indirectly through extract()
    since the imports happen inside the method.
    """

    def test_new_provider_is_tried_first(self, simple_commit: CommitInfo) -> None:
        """Test that new provider architecture is tried before legacy."""
        extractor = LLMExtractor(provider_name="test")
        
        mock_provider = MagicMock()
        mock_provider.extract_structured.side_effect = Exception("Provider error")
        
        with patch.object(extractor, "_get_provider", return_value=mock_provider):
            result = extractor.extract(simple_commit, diff_patch="")
        
        # Should return empty result due to error
        assert isinstance(result, ExtractionResult)
        assert result.intent_summary is None
        mock_provider.extract_structured.assert_called_once()
