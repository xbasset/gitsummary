"""Tests for OpenAI provider request shaping."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from gitsummary.llm.base import ProviderConfig
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
