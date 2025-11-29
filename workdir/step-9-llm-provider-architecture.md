# Step 9: LLM Provider Architecture

## Overview

This step implements a pluggable LLM provider architecture for gitsummary, starting with OpenAI's Responses API with structured outputs. The architecture is designed to support multiple providers (OpenAI, Anthropic, Ollama, etc.) with a unified interface.

## Design Decisions

### 1. Architecture Pattern: Strategy + Factory

We chose a combination of Strategy and Factory patterns:

- **Strategy Pattern**: Each provider implements `BaseLLMProvider` interface, making them interchangeable at runtime
- **Factory Pattern**: `ProviderRegistry` handles instantiation based on configuration

This enables:
- Easy swapping of providers via CLI flags or config
- Provider-specific optimizations while maintaining a common interface
- Graceful degradation when providers are unavailable

### 2. Package Structure

```
gitsummary/llm/
├── __init__.py          # Public API exports
├── base.py              # BaseLLMProvider abstract class
├── config.py            # API key and configuration management
├── registry.py          # Provider factory and registration
├── schemas.py           # Pydantic schemas for structured outputs
├── prompts.py           # Prompt templates for commit analysis
└── providers/
    ├── __init__.py
    ├── openai_provider.py     # OpenAI Responses API implementation
    ├── anthropic_provider.py  # Placeholder for Anthropic Claude
    └── ollama_provider.py     # Placeholder for local Ollama
```

### 3. Structured Outputs with the Responses API

We leverage OpenAI's new Responses API (`client.responses.parse()`) for guaranteed JSON schema compliance:

```python
response = client.responses.parse(
    model="gpt-5.1",
    input=[
        {"role": "system", "content": "Extract the information."},
        {"role": "user", "content": prompt},
    ],
    text_format=CommitExtractionSchema,
)
event = response.output_parsed
```

The Responses API is the latest generation API from OpenAI, offering:
- Native Pydantic model support via `text_format` parameter
- Guaranteed schema conformance
- Simplified response structure with `output_parsed`
- Streaming support with `client.responses.stream()`

API Reference: https://platform.openai.com/docs/api-reference/responses

### 4. API Key Management

Keys are loaded with clear priority order:

1. **Environment variables**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.
2. **.env file**: In workspace root or current directory
3. **Config file**: `~/.config/gitsummary/config`
4. **Interactive prompt**: For first-time setup, with option to save

This respects CI/CD environments while being user-friendly locally.

### 5. CLI Integration

New flags added to `gitsummary analyze`:

```bash
# Use specific provider
gitsummary analyze HEAD~5..HEAD --provider openai

# Specify model
gitsummary analyze HEAD --provider openai --model gpt-4o-mini

# Disable LLM (heuristic only)
gitsummary analyze HEAD --no-llm

# Environment variables also work
GITSUMMARY_PROVIDER=anthropic gitsummary analyze HEAD
```

### 6. Backwards Compatibility

The existing `extractors/llm.py` module maintains backwards compatibility:

- `set_llm_provider()` / `get_llm_provider()` still work
- `LLMExtractor` can use either legacy or new providers
- `create_openai_provider_function()` bridges old and new APIs

## Schema Design

The `CommitExtractionSchema` mirrors `CommitArtifact` fields with detailed descriptions that guide the LLM:

```python
class CommitExtractionSchema(BaseModel):
    intent_summary: str = Field(
        ...,
        description="A concise, one-sentence summary of what this commit *actually* does..."
    )
    category: Literal["feature", "fix", "security", "performance", "refactor", "chore"]
    behavior_before: Optional[str]
    behavior_after: Optional[str]
    impact_scope: Literal["public_api", "internal", "dependency", "config", "docs", "test", "unknown"]
    is_breaking: bool
    technical_highlights: List[str]
```

## Provider Implementation Guide

To add a new provider:

1. Create `gitsummary/llm/providers/<name>_provider.py`
2. Inherit from `BaseLLMProvider`
3. Implement:
   - `name`, `display_name`, `default_model` class attributes
   - `is_available()` class method
   - `extract_structured()` method
4. Register in `registry.py`'s `_register_builtin_providers()`

Example skeleton:

```python
class MyProvider(BaseLLMProvider):
    name = "myprovider"
    display_name = "My Provider"
    default_model = "my-model"

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.environ.get("MYPROVIDER_API_KEY"))

    def extract_structured(self, prompt, schema, system_prompt=None):
        # Implementation here
        pass
```

## Files Changed

### New Files
- `gitsummary/llm/__init__.py`
- `gitsummary/llm/base.py`
- `gitsummary/llm/config.py`
- `gitsummary/llm/registry.py`
- `gitsummary/llm/schemas.py`
- `gitsummary/llm/prompts.py`
- `gitsummary/llm/providers/__init__.py`
- `gitsummary/llm/providers/openai_provider.py`
- `gitsummary/llm/providers/anthropic_provider.py`
- `gitsummary/llm/providers/ollama_provider.py`

### Modified Files
- `gitsummary/extractors/llm.py` - Integrated with new provider architecture
- `gitsummary/extractors/__init__.py` - Added new exports
- `gitsummary/services/analyzer.py` - Added provider_name parameter
- `gitsummary/cli/commands/analyze.py` - Added CLI flags
- `requirements.txt` - Added openai and python-dotenv

## Testing Checklist

- [ ] `gitsummary analyze HEAD --no-llm` works (heuristic only)
- [ ] `gitsummary analyze HEAD --provider openai` works with valid key
- [ ] API key prompt appears when key is missing and terminal is interactive
- [ ] Saved keys in config file are loaded on subsequent runs
- [ ] `--dry-run` outputs structured artifacts
- [ ] Error handling for rate limits and authentication failures
- [ ] Fallback to heuristics when LLM fails

## Next Steps

1. **Testing**: Add unit tests for provider infrastructure
2. **Anthropic Implementation**: Complete Claude provider with tool_use
3. **Ollama Implementation**: Support local models via JSON mode
4. **Batch Mode**: Optimize for analyzing multiple commits efficiently
5. **Cost Tracking**: Add token usage reporting

