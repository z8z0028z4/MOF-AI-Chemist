# LLM Provider Contract / LLM Provider 合約

Status: draft implementation contract
Date: 2026-05-29

This contract defines how to add OpenRouter and future LLM providers without spreading provider-specific behavior across RAG, proposal, knowledge, and text-interaction services.

本文件定義新增 OpenRouter 與未來 LLM provider 時的邊界，避免 provider 細節散落到 RAG、proposal、knowledge、text-interaction 等服務。

## Current Local State

Current provider-related surfaces:

- `backend/core/llm_client.py`
  - Initializes OpenAI and Gemini clients directly.
  - Routes by model prefix: `gpt-5*`, `gemini-*`, or fallback chat completions.
  - Owns OpenAI Responses structured output and Gemini structured output calls.
- `backend/core/gemini_client.py`
  - Wraps `google-genai`.
  - Supports text and structured content.
  - Sanitizes schemas for Gemini compatibility.
- `backend/core/generation.py`
  - Public generation facade used by higher-level services.
  - Restricts structured calls to `gpt-5*` and `gemini-*`.
- `backend/core/llm_manager.py`
  - Older LangChain/OpenAI manager path.
  - Prompt-based JSON parsing still exists here.
- `backend/core/model_config.py`
  - Current model selection and model parameter source.

Problem:

- Provider routing is based on model string prefixes.
- Structured output logic is provider-specific inside one client class.
- The older prompt-then-parse path can create false confidence: mock success does not prove provider structured-output compatibility.

## External Reference Snapshot

Checked official OpenRouter docs on 2026-05-29:

- OpenRouter structured outputs use `response_format` with `type: "json_schema"` and a `json_schema` object containing `name`, optional `strict`, and `schema`.
- OpenRouter documents strict schema mode and recommends checking model support before using structured outputs.
- OpenRouter's API is similar to the OpenAI Chat API, but OpenRouter routes across providers and models, so provider support must be treated as capability-based, not assumed from one model name.

Reference URLs:

- https://openrouter.ai/docs/guides/features/structured-outputs
- https://openrouter.ai/docs/api/reference/overview

Before implementation, re-check the official docs and the selected model's supported parameters because model support can change.

## Contract Goals

- One service-facing API for text and structured generation.
- Provider adapters hide SDK/API differences.
- Structured output must validate against local schema after the provider returns.
- Free/low-cost OpenRouter models can be used for opt-in external smoke tests, not for the default unit loop.
- Demo mode remains separate from provider fallbacks.

## Non-Goals

- Do not select a permanent production model in this contract.
- Do not require network/API keys for unit tests.
- Do not remove Gemini or OpenAI while adding OpenRouter.
- Do not add new dependencies unless implementation proves the standard OpenAI-compatible client is insufficient.

## Provider Interface

Recommended modules:

```text
backend/core/llm_provider.py
backend/core/providers/
  __init__.py
  base.py
  openai_provider.py
  gemini_provider.py
  openrouter_provider.py
  fake_provider.py
```

Minimal interface:

```python
class LLMProvider:
    provider_name: str

    def generate_text(self, request: TextGenerationRequest) -> TextGenerationResult:
        ...

    def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResult:
        ...

    def supports(self, capability: str, model: str) -> bool:
        ...
```

Request/result data should be plain dataclasses or Pydantic models, depending on current repo style.

Required request fields:

- `model`
- `messages` or normalized `prompt`
- `temperature`
- `max_tokens` or `max_output_tokens`
- `timeout`
- `schema` for structured generation
- optional `metadata` for feature name, request ID, and user-visible operation

Required result fields:

- `text` for text generation
- `data` for structured generation
- `provider`
- `model`
- `raw_response_id` when available
- `usage` when available
- `finish_reason` when available
- `warnings`

## Provider Selection

Provider selection must not rely only on model prefix once OpenRouter is added.

Recommended selection order:

1. Explicit provider setting from backend settings or request context.
2. Model config entry, for example `{ provider: "openrouter", model: "google/gemini-..." }`.
3. Legacy prefix fallback only for backward compatibility.

Provider examples:

```text
provider=openai, model=gpt-5-mini
provider=gemini, model=gemini-3-flash-preview
provider=openrouter, model=<openrouter model id>
provider=fake, model=fake-structured
```

Do not encode provider-specific names directly into RAG/proposal services.

## Structured Output Rules

All structured generation must follow this sequence:

1. Build schema through existing schema manager.
2. Sanitize schema for the selected provider.
3. Send provider-native structured-output request when supported.
4. Parse provider response.
5. Validate parsed data against the local schema.
6. Return typed result or raise a provider error with actionable details.

OpenRouter request shape:

```json
{
  "model": "<model-id>",
  "messages": [{ "role": "user", "content": "..." }],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "ResearchProposal",
      "strict": true,
      "schema": {}
    }
  }
}
```

Validation is mandatory even when the provider claims strict schema support.

## OpenRouter Adapter Rules

OpenRouter should be implemented as an OpenAI-compatible chat-completions style adapter unless official docs or local testing proves that a dedicated client is needed.

Required behavior:

- Reads `OPENROUTER_API_KEY` from settings/env or user-provided settings flow.
- Uses OpenRouter base URL and Bearer auth.
- Sends optional app attribution headers only if configured.
- Sends `response_format` for structured output.
- Uses `require_parameters: true` or equivalent provider preference if supported and needed to avoid routing to models without structured output.
- Surfaces unsupported-parameter errors clearly.
- Records provider/model/finish reason/usage when present.

Forbidden behavior:

- Do not silently retry a failed structured request as plain text and parse JSON unless the caller explicitly opted into a repair mode.
- Do not fallback from OpenRouter to demo data.
- Do not fallback from OpenRouter to Gemini/OpenAI without explicit provider fallback policy.

## Test Strategy

Default tests:

- Use `fake_provider` for deterministic text and structured responses.
- Contract-test each provider adapter request builder without network.
- Validate schema sanitizer behavior with local fixtures.
- Validate failure paths: invalid schema, unsupported model capability, malformed provider response.

External smoke tests:

- Mark with `@pytest.mark.external`.
- Require explicit `OPENROUTER_API_KEY`.
- Use a free/low-cost model only if it currently supports `response_format: json_schema`.
- Assert both provider success and local schema validation.
- Keep external smoke narrow: one tiny schema and one production-like schema.

Recommended first tests:

```text
tests/test_llm_provider_contract.py
tests/test_openrouter_provider.py
tests/test_llm_provider_external.py
```

## Migration Plan

1. Add provider contract types and fake provider tests.
2. Wrap existing OpenAI/Gemini behavior behind adapters without changing service behavior.
3. Move provider selection out of `LLMClient.call_llm` prefix logic.
4. Add OpenRouter adapter with local request-builder tests.
5. Add external OpenRouter smoke behind `external`.
6. Update Settings/API-key flow after backend provider contract is stable.
7. Only then update proposal/RAG/knowledge services to depend on the provider facade.

## Acceptance Criteria

The provider layer is ready when:

- Higher-level services call one provider facade.
- Unit tests pass without network or real keys.
- OpenRouter external smoke can be run manually with a key.
- Structured outputs are locally validated after every provider call.
- Provider fallback behavior is explicit and tested.
- Demo mode remains independent from provider failures.
