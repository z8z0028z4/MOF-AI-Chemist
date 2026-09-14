"""Provider-neutral generation contracts and explicit provider selection."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


class StructuredOutputError(RuntimeError):
    """The provider response was not valid data for the requested schema."""


class ProviderUnavailableError(RuntimeError):
    """The selected provider/model cannot currently satisfy the contract."""


def _response_value(response: Any, key: str) -> Any:
    if isinstance(response, Mapping):
        return response.get(key)
    return getattr(response, key, None)


def extract_structured_text(response: Any) -> Optional[str]:
    """Extract Responses text from SDK objects and REST-shaped mappings."""
    output_text = _response_value(response, "output_text")
    if isinstance(output_text, str) and output_text:
        return output_text
    output = _response_value(response, "output")
    if not isinstance(output, (list, tuple)):
        return None
    parts: list[str] = []
    for item in output:
        containers = [item]
        message = _response_value(item, "message")
        if message is not None:
            containers.append(message)
        for container in containers:
            content = _response_value(container, "content")
            if not isinstance(content, (list, tuple)):
                continue
            for entry in content:
                text = _response_value(entry, "text")
                if isinstance(text, str) and text:
                    parts.append(text)
    return "".join(parts) or None


def sanitize_schema_for_gemini(schema: Any) -> Any:
    """Apply the existing Gemini structured-schema compatibility transform."""
    if not isinstance(schema, dict):
        return schema
    sanitized = {key: value for key, value in schema.items()
                 if key not in {"title", "additionalProperties"}}
    if isinstance(sanitized.get("properties"), dict):
        sanitized["properties"] = {
            key: sanitize_schema_for_gemini(value)
            for key, value in sanitized["properties"].items()
        }
    if "items" in sanitized:
        sanitized["items"] = sanitize_schema_for_gemini(sanitized["items"])
    return sanitized


@dataclass(frozen=True)
class StructuredGenerationRequest:
    model: str
    messages: list[dict[str, str]]
    schema: dict[str, Any]
    schema_name: str = "StructuredOutput"
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationResult:
    data: Any
    provider: str
    model: str
    raw_response_id: Optional[str] = None
    usage: Optional[Mapping[str, Any]] = None
    finish_reason: Optional[str] = None
    warnings: tuple[str, ...] = ()


def validate_structured_data(data: Any, schema: Mapping[str, Any]) -> Any:
    """Validate provider data locally; never repair or scrape response text."""
    try:
        from jsonschema import ValidationError, validate
        validate(data, dict(schema))
    except ImportError:
        _validate_minimal(data, schema)
    except ValidationError as exc:
        raise StructuredOutputError(f"Structured output failed local schema validation: {exc.message}") from exc
    return data


def parse_and_validate_structured(raw: Any, schema: Mapping[str, Any]) -> Any:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StructuredOutputError("Provider returned malformed structured output") from exc
    if not isinstance(raw, (dict, list)):
        raise StructuredOutputError("Provider returned a non-JSON structured output")
    return validate_structured_data(raw, schema)


def _validate_minimal(data: Any, schema: Mapping[str, Any]) -> None:
    expected = schema.get("type")
    if expected == "object" and not isinstance(data, dict):
        raise StructuredOutputError("Structured output must be an object")
    if expected == "array" and not isinstance(data, list):
        raise StructuredOutputError("Structured output must be an array")
    if expected == "object":
        missing = set(schema.get("required", ())) - set(data)
        if missing:
            raise StructuredOutputError(f"Structured output is missing required fields: {sorted(missing)}")


class LLMProviderFacade:
    """Small service-facing facade; provider-specific wire formats stay in adapters."""

    def __init__(self, providers: Mapping[str, Any], provider_getter, model_getter):
        self.providers = providers
        self.provider_getter = provider_getter
        self.model_getter = model_getter

    def selected(self, model: Optional[str] = None):
        provider = self.provider_getter()
        selected_model = model or self.model_getter()
        try:
            adapter = self.providers[provider]
        except KeyError as exc:
            raise ProviderUnavailableError(f"Unsupported selected LLM provider: {provider}") from exc
        return adapter, provider, selected_model

    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        adapter, _, selected_model = self.selected(model)
        return adapter.generate_text(prompt, selected_model, **kwargs)

    def generate_structured(self, prompt: str, schema: dict[str, Any], model: Optional[str] = None, **kwargs) -> dict[str, Any]:
        adapter, provider, selected_model = self.selected(model)
        result = adapter.generate_structured(prompt, selected_model, schema, **kwargs)
        data = result.data if isinstance(result, GenerationResult) else result
        parse_and_validate_structured(data, schema)
        return data
