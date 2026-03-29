"""Tests for OpenAI provider request shaping."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel

from gitsummary.llm.base import ProviderConfig, SkippableLLMError
from gitsummary.llm.providers import openai_provider as provider_module
from gitsummary.llm.providers.openai_provider import OpenAIProvider


class _Schema(BaseModel):
    intent_summary: str


def _mock_parse_response() -> SimpleNamespace:
    usage = SimpleNamespace(input_tokens=1, output_tokens=2, total_tokens=3)
    return SimpleNamespace(
        usage=usage,
        output=[],
        output_parsed=_Schema(intent_summary="ok"),
        output_text='{"intent_summary":"ok"}',
    )


def test_gpt5_models_omit_temperature_in_responses_parse() -> None:
    """GPT-5 family models should not receive explicit temperature."""
    client = MagicMock()
    client.responses.parse.return_value = _mock_parse_response()

    with patch("gitsummary.llm.providers.openai_provider.OpenAI", return_value=client):
        provider = OpenAIProvider(
            ProviderConfig(api_key="sk-test", model="gpt-5-nano", temperature=0.7)
        )
        provider.extract_structured(prompt="test", schema=_Schema, system_prompt="system")

    kwargs = client.responses.parse.call_args.kwargs
    assert kwargs["model"] == "gpt-5-nano"
    assert "temperature" not in kwargs
    assert kwargs["reasoning"] == {"effort": "minimal"}


def test_non_gpt5_models_keep_temperature_in_responses_parse() -> None:
    """Non GPT-5 models keep explicit temperature behavior."""
    client = MagicMock()
    client.responses.parse.return_value = _mock_parse_response()

    with patch("gitsummary.llm.providers.openai_provider.OpenAI", return_value=client):
        provider = OpenAIProvider(
            ProviderConfig(api_key="sk-test", model="gpt-4.1", temperature=0.3)
        )
        provider.extract_structured(prompt="test", schema=_Schema, system_prompt="system")

    kwargs = client.responses.parse.call_args.kwargs
    assert kwargs["model"] == "gpt-4.1"
    assert kwargs["temperature"] == 0.3
    assert "reasoning" not in kwargs


def test_gpt52_uses_low_reasoning_effort() -> None:
    """gpt-5.2 should receive a supported reasoning effort."""
    client = MagicMock()
    client.responses.parse.return_value = _mock_parse_response()

    with patch("gitsummary.llm.providers.openai_provider.OpenAI", return_value=client):
        provider = OpenAIProvider(
            ProviderConfig(api_key="sk-test", model="gpt-5.2", temperature=0.7)
        )
        provider.extract_structured(prompt="test", schema=_Schema, system_prompt="system")

    kwargs = client.responses.parse.call_args.kwargs
    assert kwargs["model"] == "gpt-5.2"
    assert "temperature" not in kwargs
    assert kwargs["reasoning"] == {"effort": "low"}


def test_structured_parse_handles_output_item_with_none_content() -> None:
    """Provider should tolerate Responses API items where content is None."""
    client = MagicMock()
    usage = SimpleNamespace(input_tokens=1, output_tokens=2, total_tokens=3)
    client.responses.parse.return_value = SimpleNamespace(
        usage=usage,
        output=[SimpleNamespace(content=None)],
        output_parsed=_Schema(intent_summary="ok"),
        output_text='{"intent_summary":"ok"}',
    )

    with patch("gitsummary.llm.providers.openai_provider.OpenAI", return_value=client):
        provider = OpenAIProvider(
            ProviderConfig(api_key="sk-test", model="gpt-5-nano")
        )
        response = provider.extract_structured(
            prompt="test", schema=_Schema, system_prompt="system"
        )

    assert response.parsed is not None
    assert response.parsed["intent_summary"] == "ok"


def test_openai_timeout_env_override_applies_to_client(monkeypatch) -> None:
    """Provider should honor explicit timeout env overrides."""
    client = MagicMock()
    client.responses.parse.return_value = _mock_parse_response()
    monkeypatch.setenv("GITSUMMARY_OPENAI_TIMEOUT_SECONDS", "45")

    with patch("gitsummary.llm.providers.openai_provider.OpenAI", return_value=client) as mock_openai:
        OpenAIProvider(ProviderConfig(api_key="sk-test", model="gpt-5-nano"))

    assert mock_openai.call_args.kwargs["timeout"] == 45.0


def test_timeout_errors_retry_then_skip() -> None:
    """Timeouts should retry to budget, then surface as skippable skips."""
    client = MagicMock()
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    client.responses.parse.side_effect = provider_module.APITimeoutError(request=request)

    with patch("gitsummary.llm.providers.openai_provider.OpenAI", return_value=client):
        provider = OpenAIProvider(
            ProviderConfig(api_key="sk-test", model="gpt-5-nano", max_retries=1, retry_delay=0)
        )
        with pytest.raises(SkippableLLMError) as exc_info:
            provider.extract_structured(prompt="test", schema=_Schema, system_prompt="system")

    assert exc_info.value.reason == "llm_timeout"
    assert client.responses.parse.call_count == 2


def test_context_length_errors_are_skippable() -> None:
    """Oversized prompt rejections should become skippable, not generic failures."""
    client = MagicMock()
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(400, request=request)

    with patch("gitsummary.llm.providers.openai_provider.OpenAI", return_value=client):
        provider = OpenAIProvider(ProviderConfig(api_key="sk-test", model="gpt-5-nano"))
        with pytest.raises(SkippableLLMError) as exc_info:
            with patch.object(
                provider._client.responses,
                "parse",
                side_effect=provider_module.BadRequestError(
                    "context_length_exceeded",
                    response=response,
                    body={"error": {"code": "context_length_exceeded"}},
                ),
            ):
                provider.extract_structured(prompt="test", schema=_Schema, system_prompt="system")

    assert exc_info.value.reason == "llm_context_length_exceeded"
