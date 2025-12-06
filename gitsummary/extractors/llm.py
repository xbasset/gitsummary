"""LLM-powered semantic extraction.

This module provides LLM-based extraction with a pluggable provider
interface. It enables high-quality semantic understanding while
allowing different LLM backends (OpenAI, Claude, local models, etc.).

The LLMExtractor integrates with the llm/ package which provides:
- Multiple provider implementations (OpenAI, Anthropic, Ollama)
- Structured output support via Pydantic schemas
- Unified configuration and API key management
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Dict, Optional

from ..core import ChangeCategory, CommitDiff, CommitInfo, ImpactScope
from ..tracing import trace_manager
from .base import ExtractionResult

logger = logging.getLogger(__name__)

# Legacy type alias for backwards compatibility
# Takes: commit_info, diff_patch -> Returns: dict with extracted fields or None
LLMProvider = Callable[[CommitInfo, str], Optional[Dict[str, object]]]


def _null_provider(commit: CommitInfo, diff_patch: str) -> Optional[Dict[str, object]]:
    """Default null provider that returns None, triggering heuristic fallback."""
    return None


# Global LLM provider (legacy interface, can be set by CLI or tests)
_llm_provider: LLMProvider = _null_provider


def set_llm_provider(provider: LLMProvider) -> None:
    """Set the global LLM provider for artifact extraction (legacy interface).

    For new code, prefer using the llm/ package directly with get_provider().

    Args:
        provider: A callable that takes (CommitInfo, diff_patch) and returns
                  a dict with extracted fields or None.
    """
    global _llm_provider
    _llm_provider = provider


def get_llm_provider() -> LLMProvider:
    """Get the current LLM provider (legacy interface)."""
    return _llm_provider


class LLMExtractor:
    """LLM-powered semantic extractor.

    Uses an LLM provider to extract semantic information from commits.
    Supports both the legacy callable interface and the new provider architecture.

    The extractor can be initialized with:
    1. An explicit legacy provider function
    2. A provider name (uses the llm/ registry)
    3. Nothing (uses global provider or falls back to null)

    Example with new provider architecture:
        >>> extractor = LLMExtractor(provider_name="openai")
        >>> result = extractor.extract(commit, diff, diff_patch)

    Example with legacy interface:
        >>> set_llm_provider(my_custom_provider)
        >>> extractor = LLMExtractor()
        >>> result = extractor.extract(commit, diff, diff_patch)
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        provider_name: Optional[str] = None,
    ) -> None:
        """Initialize with an optional explicit provider.

        Args:
            provider: Legacy provider function. If None, uses the global provider.
            provider_name: Name of provider from llm/ registry (e.g., "openai").
                          Takes precedence over legacy provider if both are set.
        """
        self._legacy_provider = provider
        self._provider_name = provider_name
        self._llm_provider = None  # Lazy-loaded from llm/ package

    def _get_provider(self):
        """Get the LLM provider, initializing if needed."""
        if self._llm_provider is not None:
            return self._llm_provider

        try:
            from ..llm import get_provider

            # If an explicit provider name is supplied, use it; otherwise fall
            # back to the configured default provider (e.g., openai).
            self._llm_provider = get_provider(self._provider_name)
            return self._llm_provider
        except Exception as e:
            logger.warning(
                f"Failed to initialize LLM provider "
                f"'{self._provider_name or 'default'}': {e}"
            )
            return None

        return None

    def extract(
        self,
        commit: CommitInfo,
        diff: Optional[CommitDiff] = None,
        diff_patch: str = "",
    ) -> ExtractionResult:
        """Extract semantic information using LLM.

        Tries the new provider architecture first, falls back to legacy
        provider if not configured, then returns empty result if no
        provider is available.

        Args:
            commit: The commit information.
            diff: Optional structured diff data (unused, LLM uses raw patch).
            diff_patch: Raw unified diff text for LLM analysis.

        Returns:
            ExtractionResult with fields populated by LLM, or empty if unavailable.
        """
        # Try new provider architecture first
        llm_provider = self._get_provider()
        if llm_provider is not None:
            try:
                return self._extract_with_provider(llm_provider, commit, diff_patch)
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")
                return ExtractionResult()

        # Fall back to legacy provider
        legacy_provider = self._legacy_provider or get_llm_provider()
        llm_result = legacy_provider(commit, diff_patch)

        if llm_result is None:
            return ExtractionResult()

        # Parse legacy result into ExtractionResult
        return self._parse_llm_result(llm_result)

    def _extract_with_provider(
        self,
        provider,
        commit: CommitInfo,
        diff_patch: str,
    ) -> ExtractionResult:
        """Extract using the new provider architecture with structured outputs."""
        from ..llm.prompts import COMMIT_ANALYSIS_SYSTEM_PROMPT, build_commit_analysis_prompt
        from ..llm.schemas import CommitExtractionSchema

        # Build prompt
        prompt = build_commit_analysis_prompt(commit, diff_patch)

        # Call provider with structured output
        response = None
        started = time.time()
        success = False
        try:
            response = provider.extract_structured(
                prompt=prompt,
                schema=CommitExtractionSchema,
                system_prompt=COMMIT_ANALYSIS_SYSTEM_PROMPT,
            )
            success = response.success
        finally:
            duration = time.time() - started
            parsed_payload = None
            raw_text = None
            refusal = None
            model_name = None
            token_usage = None
            if response is not None:
                parsed_payload = (
                    response.parsed.model_dump()  # type: ignore[attr-defined]
                    if hasattr(response.parsed, "model_dump")
                    else response.parsed
                )
                raw_text = response.raw_text
                refusal = response.refusal
                model_name = response.model
                token_usage = {
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                }
            trace_manager.log_llm_call(
                provider=getattr(provider, "name", None),
                model=model_name,
                system_prompt=COMMIT_ANALYSIS_SYSTEM_PROMPT,
                prompt=prompt,
                input_context={
                    "commit_sha": commit.sha,
                    "commit_summary": commit.summary,
                    "diff_present": bool(diff_patch),
                },
                response=parsed_payload,
                raw_text=raw_text,
                refusal=refusal,
                token_usage=token_usage,
                success=success,
                duration_seconds=duration,
            )

        if not response.success or response.parsed is None:
            if response.refusal:
                logger.warning(f"LLM refused to analyze commit: {response.refusal}")
            return ExtractionResult()

        # Convert to ExtractionResult
        return self._parse_llm_result(response.parsed)

    def _parse_llm_result(self, result: Dict[str, object]) -> ExtractionResult:
        """Parse LLM provider result into ExtractionResult."""
        category = None
        if "category" in result:
            try:
                category = ChangeCategory(result["category"])
            except ValueError:
                pass

        impact_scope = None
        if "impact_scope" in result:
            try:
                impact_scope = ImpactScope(result["impact_scope"])
            except ValueError:
                pass

        return ExtractionResult(
            intent_summary=result.get("intent_summary"),  # type: ignore
            category=category,
            behavior_before=result.get("behavior_before"),  # type: ignore
            behavior_after=result.get("behavior_after"),  # type: ignore
            impact_scope=impact_scope,
            is_breaking=result.get("is_breaking"),  # type: ignore
            technical_highlights=result.get("technical_highlights", []),  # type: ignore
        )


def create_openai_provider_function(
    api_key: Optional[str] = None,
    model: str = "gpt-5.1",
) -> LLMProvider:
    """Create a legacy-compatible provider function using the new OpenAI provider.

    This is a convenience function for code that uses the legacy set_llm_provider()
    interface but wants to use the new OpenAI structured output implementation.

    Args:
        api_key: OpenAI API key. If None, uses environment variable.
        model: Model to use (default: gpt-5.1 for best structured outputs).

    Returns:
        A callable compatible with set_llm_provider().

    Example:
        >>> provider = create_openai_provider_function()
        >>> set_llm_provider(provider)
    """
    from ..llm import ProviderConfig, get_provider
    from ..llm.prompts import COMMIT_ANALYSIS_SYSTEM_PROMPT, build_commit_analysis_prompt
    from ..llm.schemas import CommitExtractionSchema

    # Initialize provider
    config = ProviderConfig(api_key=api_key, model=model)
    llm = get_provider("openai", config)

    def provider_function(commit: CommitInfo, diff_patch: str) -> Optional[Dict[str, object]]:
        """Extract commit information using OpenAI."""
        try:
            prompt = build_commit_analysis_prompt(commit, diff_patch)
            response = llm.extract_structured(
                prompt=prompt,
                schema=CommitExtractionSchema,
                system_prompt=COMMIT_ANALYSIS_SYSTEM_PROMPT,
            )
            return response.parsed
        except Exception as e:
            logger.warning(f"OpenAI extraction failed: {e}")
            return None

    return provider_function
