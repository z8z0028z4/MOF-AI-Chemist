"""OpenRouter structured-output provider and persistent eligible catalog."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import quote

import httpx

from backend.config import DATA_DIR
from backend.core.llm_provider import (
    GenerationResult,
    ProviderUnavailableError,
    parse_and_validate_structured,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CATALOG_SCHEMA_VERSION = 1
_REQUIRED_PARAMETERS = {"response_format", "structured_outputs"}
_PRIORITY = ("openai/", "anthropic/", "google/")


def _model_url_path(model_id: str) -> str:
    """Encode a model ID while retaining its vendor namespace separator."""
    return quote(model_id, safe="/")


@dataclass(frozen=True)
class CatalogItem:
    id: str
    name: str
    vendor_rank: int

    @property
    def vendor(self) -> str:
        return self.id.split("/", 1)[0].casefold() if "/" in self.id else "other"


def sort_catalog_items(items: list[CatalogItem]) -> list[CatalogItem]:
    return sorted(items, key=lambda item: (item.vendor_rank, item.name.casefold(), item.id))


def _has_required_parameters(parameters: Any) -> bool:
    return (
        isinstance(parameters, (list, tuple, set))
        and all(isinstance(item, str) for item in parameters)
        and _REQUIRED_PARAMETERS <= set(parameters)
    )


def _model_is_text_capable(model: dict[str, Any]) -> bool:
    architecture = model.get("architecture")
    if not isinstance(architecture, dict):
        return False
    inputs, outputs = architecture.get("input_modalities"), architecture.get("output_modalities")
    return (
        isinstance(inputs, (list, tuple, set))
        and isinstance(outputs, (list, tuple, set))
        and "text" in inputs
        and "text" in outputs
    )


def _eligible_endpoint(endpoint: dict[str, Any]) -> bool:
    if not isinstance(endpoint, dict) or isinstance(endpoint.get("status"), bool):
        return False
    status = endpoint.get("status")
    if isinstance(status, dict):
        status = status.get("code", status.get("status"))
    try:
        available = int(status) == 0
    except (TypeError, ValueError):
        return False
    return available and _has_required_parameters(endpoint.get("supported_parameters"))


def normalize_catalog(
    models: list[dict[str, Any]],
    endpoints_by_model: Optional[dict[str, list[dict[str, Any]]]] = None,
) -> list[CatalogItem]:
    items: list[CatalogItem] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = model.get("id")
        if not isinstance(model_id, str) or not model_id:
            continue
        endpoints = (endpoints_by_model or {}).get(model_id)
        if not (
            _has_required_parameters(model.get("supported_parameters"))
            and _model_is_text_capable(model)
            and isinstance(endpoints, list)
            and all(isinstance(endpoint, dict) for endpoint in endpoints)
            and any(_eligible_endpoint(endpoint) for endpoint in endpoints)
        ):
            continue
        rank = next((i for i, prefix in enumerate(_PRIORITY) if model_id.startswith(prefix)), len(_PRIORITY))
        items.append(CatalogItem(model_id, model.get("name") or model_id, rank))
    return sort_catalog_items(items)


def _endpoint_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("endpoints")
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("OpenRouter endpoint response is malformed")
    return payload


class OpenRouterCatalog:
    def __init__(
        self,
        api_key_getter: Callable[[], Optional[str]],
        client: Any = None,
        catalog_path: str | Path | None = None,
    ):
        self.api_key_getter = api_key_getter
        self.client = client or httpx.Client(timeout=30)
        self.catalog_path = Path(catalog_path) if catalog_path else Path(DATA_DIR) / "openrouter" / "eligible_catalog.json"
        self.stale = False
        self.error: Optional[str] = None
        self._cached: Optional[list[CatalogItem]] = None

    def load(self, refresh: bool = False, cursor: Optional[str] = None, page_size: Optional[int] = None) -> dict[str, Any]:
        del cursor, page_size  # pagination is deliberately internal
        if not self.api_key_getter():
            self._cached = None
            raise ProviderUnavailableError("OpenRouter API key is required before loading models")
        if not refresh:
            persisted = self._read_catalog()
            if persisted is not None:
                self._cached, self.stale, self.error = persisted, False, None
                return self._result(persisted)
        try:
            items = self._scan_complete()
            self._write_catalog(items)
            self._cached, self.stale, self.error = items, False, None
            return self._result(items)
        except Exception as exc:
            self.stale = True
            self.error = "OpenRouter catalog refresh failed; showing the last successful list"
            fallback = self._cached or self._read_catalog()
            if fallback:
                self._cached = fallback
                return self._result(fallback, stale=True, error=f"{self.error}: {exc}")
            raise ProviderUnavailableError("Unable to load the OpenRouter model catalog; refresh and try again") from exc

    def contains(self, model_id: str, refresh: bool = False) -> bool:
        """Fresh targeted check; never trusts the persisted catalog."""
        if not self.api_key_getter():
            raise ProviderUnavailableError("OpenRouter API key is required")
        try:
            response = self.client.get(
                f"{OPENROUTER_BASE_URL}/model/{_model_url_path(model_id)}", headers=self._headers()
            )
            response.raise_for_status()
            envelope = response.json()
            model = envelope.get("data") if isinstance(envelope, dict) else None
            if not isinstance(model, dict):
                return False
            endpoint_response = self.client.get(
                f"{OPENROUTER_BASE_URL}/models/{_model_url_path(model_id)}/endpoints", headers=self._headers()
            )
            endpoint_response.raise_for_status()
            endpoints_payload = endpoint_response.json()
            endpoints = _endpoint_list(endpoints_payload.get("data", endpoints_payload) if isinstance(endpoints_payload, dict) else endpoints_payload)
            return bool(normalize_catalog([model], {model_id: endpoints}))
        except Exception as exc:
            raise ProviderUnavailableError("OpenRouter model availability check failed; refresh and reselect a model") from exc

    def _scan_complete(self) -> list[CatalogItem]:
        models: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = self.client.get(
                f"{OPENROUTER_BASE_URL}/models?limit=100&offset={offset}", headers=self._headers()
            )
            response.raise_for_status()
            envelope = response.json()
            if not isinstance(envelope, dict) or not isinstance(envelope.get("data"), list):
                raise ValueError("OpenRouter models response is malformed")
            page = envelope["data"]
            models.extend(page)
            pagination = envelope.get("pagination")
            has_more = pagination.get("has_more") if isinstance(pagination, dict) else len(page) == 100
            if not has_more:
                break
            next_offset = pagination.get("next_cursor") if isinstance(pagination, dict) else None
            try:
                offset = int(next_offset) if next_offset is not None else offset + len(page)
            except (TypeError, ValueError) as exc:
                raise ValueError("OpenRouter pagination cursor is malformed") from exc
            if not page:
                raise ValueError("OpenRouter pagination did not advance")
        endpoints: dict[str, list[dict[str, Any]]] = {}
        for model in models:
            if not isinstance(model, dict) or not isinstance(model.get("id"), str):
                raise ValueError("OpenRouter model page contains malformed records")
            model_id = model["id"]
            response = self.client.get(f"{OPENROUTER_BASE_URL}/models/{_model_url_path(model_id)}/endpoints", headers=self._headers())
            response.raise_for_status()
            payload = response.json()
            endpoints[model_id] = _endpoint_list(payload.get("data", payload) if isinstance(payload, dict) else payload)
        return normalize_catalog(models, endpoints)

    def _read_catalog(self) -> Optional[list[CatalogItem]]:
        try:
            payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema_version") != CATALOG_SCHEMA_VERSION or not isinstance(payload.get("models"), list):
                return None
            items = []
            for item in payload["models"]:
                if not isinstance(item, dict):
                    return None
                model_id, name = item.get("id"), item.get("name")
                eligibility = item.get("eligibility")
                if (
                    not isinstance(model_id, str) or not model_id or "/" not in model_id
                    or not isinstance(name, str) or not name.strip()
                    or not isinstance(eligibility, dict)
                    or eligibility != {"model_structured_outputs": True, "text_to_text_endpoint": True}
                ):
                    return None
                rank = next((i for i, prefix in enumerate(_PRIORITY) if model_id.startswith(prefix)), len(_PRIORITY))
                if item.get("vendor") != model_id.split("/", 1)[0].casefold() or item.get("vendor_rank") != rank:
                    return None
                items.append(CatalogItem(model_id, name, rank))
            return sort_catalog_items(items)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def _write_catalog(self, items: list[CatalogItem]) -> None:
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": CATALOG_SCHEMA_VERSION, "models": [{
            "id": i.id,
            "name": i.name,
            "vendor": i.vendor,
            "vendor_rank": i.vendor_rank,
            "eligibility": {"model_structured_outputs": True, "text_to_text_endpoint": True},
        } for i in items]}
        fd, temporary = tempfile.mkstemp(prefix=".eligible_catalog.", suffix=".tmp", dir=self.catalog_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.catalog_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _result(self, items: list[CatalogItem], stale: bool = False, error: Optional[str] = None) -> dict[str, Any]:
        return {"models": items, "stale": stale, "error": error, "has_more": False, "next_cursor": None}

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key_getter()}", "Content-Type": "application/json"}


class OpenRouterProvider:
    name = "openrouter"

    def __init__(self, api_key_getter: Callable[[], Optional[str]], client: Any = None, catalog: Optional[OpenRouterCatalog] = None):
        self.api_key_getter = api_key_getter
        self.client = client or httpx.Client(timeout=120)
        self.catalog = catalog or OpenRouterCatalog(api_key_getter, self.client)

    def generate_text(self, prompt: str, model: str, **kwargs) -> str:
        self._assert_currently_eligible(model)
        response = self.client.post(f"{OPENROUTER_BASE_URL}/chat/completions", headers=self._headers(), json={"model": model, "messages": [{"role": "user", "content": prompt}], "provider": {"require_parameters": True}})
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def generate_structured(self, prompt: str, model: str, schema: dict[str, Any], schema_name: str = "StructuredOutput", **kwargs) -> GenerationResult:
        self._assert_currently_eligible(model)
        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}}, "provider": {"require_parameters": True}}
        response = self.client.post(f"{OPENROUTER_BASE_URL}/chat/completions", headers=self._headers(), json=body)
        response.raise_for_status()
        payload = response.json()
        choice = payload["choices"][0]
        data = parse_and_validate_structured(choice["message"].get("content"), schema)
        return GenerationResult(data, self.name, model, payload.get("id"), payload.get("usage"), choice.get("finish_reason"))

    def _assert_currently_eligible(self, model: str) -> None:
        if hasattr(self.catalog, "contains"):
            eligible = self.catalog.contains(model, refresh=True)
        else:
            data = self.catalog.load(refresh=True)
            eligible = not data.get("stale") and any(item.id == model for item in data.get("models", []))
        if not eligible:
            raise ProviderUnavailableError(f"OpenRouter model '{model}' is unavailable or no longer supports structured output; refresh and reselect a model")

    def _headers(self) -> dict[str, str]:
        key = self.api_key_getter()
        if not key:
            raise ProviderUnavailableError("OpenRouter API key is required")
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
