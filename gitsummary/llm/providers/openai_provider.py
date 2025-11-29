"""OpenAI provider implementation using the Responses API.

This provider uses OpenAI's official Python SDK with the new Responses API
and structured outputs (via Pydantic models) for reliable semantic extraction.

The Responses API is the latest generation API from OpenAI that supports:
- Structured outputs with `text_format` parameter
- Native Pydantic model support via `client.responses.parse()`
- Streaming with `client.responses.stream()`

API Reference: https://platform.openai.com/docs/api-reference/responses
Guide: https://platform.openai.com/docs/guides/structured-outputs?api-mode=responses

Requires:
- openai>=1.0.0 (pip install openai)
- OPENAI_API_KEY environment variable or config file

Supported Models:
- gpt-5.1 (default, latest model with best capabilities)
- gpt-4.1 (previous generation)
- gpt-4o-2024-08-06 (for structured outputs)
- gpt-4o-mini (faster, cheaper)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

from ..base import (
    BaseLLMProvider,
    LLMResponse,
    ProviderAuthenticationError,
    ProviderConfig,
    ProviderError,
    ProviderNotAvailableError,
    ProviderRateLimitError,
)

# Check for OpenAI availability
try:
    import openai
    from openai import APIConnectionError, APIError, AuthenticationError, OpenAI, RateLimitError

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None  # type: ignore
    OpenAI = None  # type: ignore


T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider using the Responses API with structured output support.

    Uses OpenAI's Responses API (`client.responses.parse()`) for reliable
    structured data extraction conforming to Pydantic schemas.

    The Responses API is the new recommended API for OpenAI interactions,
    replacing the older Chat Completions API for most use cases.

    Example:
        >>> provider = OpenAIProvider(ProviderConfig(api_key="sk-..."))
        >>> response = provider.extract_structured(
        ...     prompt="Analyze this commit...",
        ...     schema=CommitAnalysis
        ... )
        >>> if response.success:
        ...     analysis = response.parsed
    """

    name = "openai"
    display_name = "OpenAI"
    default_model = "gpt-5.1"  # Latest model with best capabilities

    # Models that support structured outputs
    STRUCTURED_OUTPUT_MODELS = {
        "gpt-5.1",
        "gpt-4.1",
        "gpt-4o-2024-08-06",
        "gpt-4o-mini",
        "gpt-4o-mini-2024-07-18",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4-turbo-2024-04-09",
    }

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        """Initialize the OpenAI provider.

        Args:
            config: Provider configuration with API key and model settings.

        Raises:
            ProviderNotAvailableError: If openai package is not installed.
        """
        if not OPENAI_AVAILABLE:
            raise ProviderNotAvailableError(
                "OpenAI provider requires the 'openai' package. "
                "Install it with: pip install openai"
            )

        super().__init__(config)

        # Initialize the client
        self._client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.api_base,
            timeout=self.config.timeout,
            max_retries=0,  # We handle retries ourselves for better control
        )

    def _validate_config(self) -> None:
        """Validate OpenAI-specific configuration."""
        if not self.config.api_key:
            raise ProviderNotAvailableError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or provide it in the configuration."
            )

    @classmethod
    def is_available(cls) -> bool:
        """Check if OpenAI provider is available.

        Returns True if:
        - openai package is installed
        - API key is configured (via env var or will be prompted)
        """
        if not OPENAI_AVAILABLE:
            return False

        # Check for API key in environment
        return bool(
            os.environ.get("OPENAI_API_KEY")
            or os.environ.get("GITSUMMARY_OPENAI_KEY")
        )

    def extract_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Extract structured data using OpenAI's Responses API.

        Uses the `client.responses.parse()` method which guarantees
        the response conforms to the provided Pydantic schema.

        Args:
            prompt: The user prompt with content to analyze.
            schema: Pydantic model class for the expected output.
            system_prompt: Optional system prompt for context.

        Returns:
            LLMResponse with parsed data or error information.

        Raises:
            ProviderError: On unrecoverable API errors.
        """
        model = self.get_model()
        input_messages = self._build_input(prompt, system_prompt)

        # Attempt with retries
        last_error: Optional[Exception] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return self._make_request(model, input_messages, schema)
            except ProviderRateLimitError as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2**attempt)
                    time.sleep(delay)
                    continue
                raise
            except (ProviderAuthenticationError, ProviderError):
                raise
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay)
                    continue

        raise ProviderError(f"Request failed after {self.config.max_retries + 1} attempts: {last_error}")

    def _build_input(
        self,
        prompt: str,
        system_prompt: Optional[str],
    ) -> list[Dict[str, str]]:
        """Build the input array for the Responses API request."""
        input_messages = []

        if system_prompt:
            input_messages.append({"role": "system", "content": system_prompt})

        input_messages.append({"role": "user", "content": prompt})

        return input_messages

    def _make_request(
        self,
        model: str,
        input_messages: list[Dict[str, str]],
        schema: Type[T],
    ) -> LLMResponse:
        """Make a single API request using the Responses API with structured output parsing."""
        try:
            # Use the Responses API with text_format for structured outputs
            response = self._client.responses.parse(
                model=model,
                input=input_messages,  # type: ignore
                text_format=schema,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
            )

            # Build response object
            llm_response = LLMResponse(
                model=model,
                provider=self.name,
                prompt_tokens=response.usage.input_tokens if response.usage else 0,
                completion_tokens=response.usage.output_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )

            # Check for refusal in output
            if response.output:
                for output_item in response.output:
                    if hasattr(output_item, 'content'):
                        for content_item in output_item.content:
                            if hasattr(content_item, 'type') and content_item.type == 'refusal':
                                llm_response.refusal = getattr(content_item, 'refusal', 'Model refused to respond')
                                return llm_response

            # Extract parsed content from output_parsed
            if hasattr(response, 'output_parsed') and response.output_parsed is not None:
                # Convert Pydantic model to dict
                if isinstance(response.output_parsed, BaseModel):
                    llm_response.parsed = response.output_parsed.model_dump()
                else:
                    llm_response.parsed = dict(response.output_parsed)
                llm_response.is_structured = True
            elif response.output_text:
                # Fallback to parsing JSON from output_text
                try:
                    llm_response.parsed = json.loads(response.output_text)
                    llm_response.is_structured = True
                except json.JSONDecodeError:
                    llm_response.raw_text = response.output_text

            return llm_response

        except AuthenticationError as e:
            raise ProviderAuthenticationError(
                f"OpenAI authentication failed. Check your API key. Error: {e}"
            ) from e

        except RateLimitError as e:
            raise ProviderRateLimitError(
                f"OpenAI rate limit exceeded. Please wait and retry. Error: {e}"
            ) from e

        except APIConnectionError as e:
            raise ProviderError(
                f"Failed to connect to OpenAI API. Check your network. Error: {e}"
            ) from e

        except APIError as e:
            raise ProviderError(f"OpenAI API error: {e}") from e

    def extract_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Extract free-form text response using the Responses API (non-structured).

        For simpler use cases where structured output isn't needed.
        """
        model = self.get_model()
        input_messages = self._build_input(prompt, system_prompt)

        try:
            # Use basic responses.create for non-structured output
            response = self._client.responses.create(
                model=model,
                input=input_messages,  # type: ignore
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
            )

            return LLMResponse(
                raw_text=response.output_text or "",
                model=model,
                provider=self.name,
                prompt_tokens=response.usage.input_tokens if response.usage else 0,
                completion_tokens=response.usage.output_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )

        except Exception as e:
            raise ProviderError(f"OpenAI request failed: {e}") from e
