"""Provider-scoped discovery catalogs and advisory model detection."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
from urllib.parse import urlencode

import httpx

from backend.config import DATA_DIR


CATALOG_SCHEMA_VERSION = 1
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
GOOGLE_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _classify_detection_error(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status in (401, 403):
        return "authentication"
    if status == 400:
        return "schema_rejected"
    if status == 404:
        return "model_unavailable"
    if status == 429:
        return "rate_limit"
    if isinstance(exc, (ValueError, KeyError)) or exc.__class__.__name__ == "StructuredOutputError":
        return "schema_rejected"
    return "transient"


def _detection_message(exc: Exception) -> str:
    messages = {
        "timeout": "Model detection timed out; this does not establish incompatibility",
        "authentication": "Provider authentication or permission was rejected",
        "model_unavailable": "The selected model is unavailable",
        "rate_limit": "Provider rate limit reached; try again later",
        "schema_rejected": "Provider rejected the structured-output request or returned invalid JSON",
        "transient": "Model detection failed temporarily; this does not establish incompatibility",
    }
    return messages[_classify_detection_error(exc)]

# Retained as audit metadata only. Discovery candidates are not capability
# claims; compatibility is checked explicitly by the optional detector.
OFFICIAL_CAPABILITY_EVIDENCE: dict[str, dict[str, dict[str, Any]]] = {
    "openai": {
        "gpt-5": {"source_url": "https://platform.openai.com/docs/guides/structured-outputs", "structured_outputs": True},
        "gpt-5-mini": {"source_url": "https://platform.openai.com/docs/guides/structured-outputs", "structured_outputs": True},
        "gpt-4o-mini": {"source_url": "https://platform.openai.com/docs/guides/structured-outputs", "structured_outputs": True},
    },
    "google": {
        "models/gemini-2.5-pro": {"source_url": "https://ai.google.dev/gemini-api/docs/structured-output", "structured_outputs": True},
        "models/gemini-3-flash-preview": {"source_url": "https://ai.google.dev/gemini-api/docs/structured-output", "structured_outputs": True},
    },
}


@dataclass(frozen=True)
class ProviderCatalogItem:
    id: str
    name: str
    provider: str
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"value": self.id, "label": self.name, "provider": self.provider, "evidence": self.evidence}


class ProviderCatalog:
    """One isolated catalog adapter for OpenAI or Google."""

    def __init__(self, provider: str, api_key_getter: Callable[[], Optional[str]], client: Any = None,
                 catalog_path: str | Path | None = None,
                 evidence: Mapping[str, Mapping[str, Any]] | None = None):
        if provider not in {"openai", "google"}:
            raise ValueError("provider must be openai or google")
        self.provider = provider
        self.api_key_getter = api_key_getter
        self.client = client or httpx.Client(timeout=30)
        self.catalog_path = Path(catalog_path) if catalog_path else Path(DATA_DIR) / provider / "eligible_catalog.json"
        self.evidence = dict(evidence if evidence is not None else OFFICIAL_CAPABILITY_EVIDENCE[provider])
        self.stale = False
        self.error: Optional[str] = None

    def load(self, refresh: bool = False) -> dict[str, Any]:
        if not self.api_key_getter():
            self.stale = False
            self.error = f"{self.provider.title()} API key is required before loading models"
            return self._result([])
        if not refresh:
            cached = self._read_catalog()
            if cached is not None:
                self.stale, self.error = False, None
                return self._result(cached)
        try:
            items = self.normalize(self._discover())
            self._write_catalog(items)
            self.stale, self.error = False, None
            return self._result(items)
        except Exception:
            self.stale = True
            # Upstream exception text may contain request URLs, query keys, or
            # provider payloads. Keep the public/persisted state generic.
            self.error = f"{self.provider.title()} catalog refresh failed; showing the last successful list"
            cached = self._read_catalog()
            if cached is not None:
                return self._result(cached)
            return self._result([])

    def normalize(self, records: list[dict[str, Any]]) -> list[ProviderCatalogItem]:
        items = []
        for record in records:
            if not isinstance(record, dict):
                continue
            model_id = record.get("id") or (record.get("name") if self.provider == "google" else None)
            if self.provider == "google" and isinstance(model_id, str) and not model_id.startswith("models/"):
                model_id = f"models/{model_id}"
            fact = self.evidence.get(model_id) if isinstance(model_id, str) else None
            if not isinstance(model_id, str) or not model_id:
                continue
            name = record.get("display_name") or record.get("name") or model_id.removeprefix("models/")
            if not isinstance(name, str) or not name.strip():
                continue
            audit = {}
            if isinstance(fact, dict) and isinstance(fact.get("source_url"), str) and fact["source_url"].startswith("https://"):
                audit = {"source_url": fact["source_url"]}
            items.append(ProviderCatalogItem(model_id, name, self.provider, audit))
        return sorted(items, key=lambda item: (item.name.casefold(), item.id))

    def contains(self, model_id: str) -> bool:
        return any(item.id == model_id and self._valid_item(item) for item in self._read_catalog() or [])

    def _valid_item(self, item: ProviderCatalogItem) -> bool:
        return (
            item.provider == self.provider
            and isinstance(item.id, str)
            and isinstance(item.name, str)
            and isinstance(item.evidence, dict)
        )

    def detect_structured_output(self, model_id: str) -> dict[str, Any]:
        """Run one minimal native request for one selected model.

        The response is deliberately reduced to a stable advisory result and
        never persisted. Google catalog IDs retain ``models/`` storage form;
        only this adapter converts them to the SDK/HTTP wire name.
        """
        if not self.api_key_getter():
            return {"status": "authentication", "message": "API key is required"}
        from backend.core.schema_manager import create_experimental_detail_schema
        from backend.core.llm_provider import (
            extract_structured_text,
            parse_and_validate_structured,
            sanitize_schema_for_gemini,
        )

        schema = create_experimental_detail_schema()
        try:
            if self.provider == "openai":
                response = self.client.post("https://api.openai.com/v1/responses", headers=self._headers(), json={
                    "model": model_id,
                    "input": [{"role": "user", "content": "Return a valid experimental detail JSON object."}],
                    "text": {"format": {"type": "json_schema", "name": "ExperimentalDetail", "strict": True, "schema": schema}},
                })
                response.raise_for_status()
                raw = extract_structured_text(response.json())
            else:
                wire_name = model_id.removeprefix("models/")
                gemini_schema = sanitize_schema_for_gemini(schema)
                response = self.client.post(f"{GOOGLE_MODELS_URL}/{wire_name}:generateContent", params={"key": self.api_key_getter()}, json={
                    "contents": [{"parts": [{"text": "Return a valid experimental detail JSON object."}]}],
                    "generationConfig": {"responseMimeType": "application/json", "responseSchema": gemini_schema},
                })
                response.raise_for_status()
                payload = response.json()
                raw = payload["candidates"][0]["content"]["parts"][0]["text"]
            parse_and_validate_structured(raw, schema)
            return {"status": "success", "message": "Model returned valid structured output"}
        except Exception as exc:
            return {"status": _classify_detection_error(exc), "message": _detection_message(exc)}

    def _discover(self) -> list[dict[str, Any]]:
        if self.provider == "openai":
            response = self.client.get(OPENAI_MODELS_URL, headers=self._headers())
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ValueError("OpenAI models response is malformed")
            return payload["data"]
        records: list[dict[str, Any]] = []
        page_token: Optional[str] = None
        while True:
            params = {"pageSize": "1000", "key": self.api_key_getter()}
            if page_token:
                params["pageToken"] = page_token
            response = self.client.get(f"{GOOGLE_MODELS_URL}?{urlencode(params)}", headers={"Content-Type": "application/json"})
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
                raise ValueError("Google models response is malformed")
            records.extend(payload["models"])
            page_token = payload.get("nextPageToken")
            if page_token is None:
                return records
            if not isinstance(page_token, str) or not page_token:
                raise ValueError("Google pagination token is malformed")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key_getter()}", "Content-Type": "application/json"}

    def _read_catalog(self) -> Optional[list[ProviderCatalogItem]]:
        try:
            payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != CATALOG_SCHEMA_VERSION or payload.get("provider") != self.provider or not isinstance(payload.get("models"), list):
                return None
            items = []
            for item in payload["models"]:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item.get("provider") != self.provider:
                    return None
                evidence = item.get("evidence")
                if not isinstance(evidence, dict):
                    return None
                candidate = ProviderCatalogItem(item["id"], item.get("name", item["id"]), self.provider, evidence)
                if not isinstance(candidate.name, str) or not candidate.name.strip() or not self._valid_item(candidate):
                    return None
                items.append(candidate)
            return items
        except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError):
            return None

    def _write_catalog(self, items: list[ProviderCatalogItem]) -> None:
        if any(not self._valid_item(item) for item in items):
            raise ValueError("Catalog contains an invalid provider capability record")
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": CATALOG_SCHEMA_VERSION, "provider": self.provider,
                   "models": [{"id": i.id, "name": i.name, "provider": i.provider, "evidence": i.evidence} for i in items]}
        fd, temporary = tempfile.mkstemp(prefix=".eligible_catalog.", suffix=".tmp", dir=self.catalog_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, self.catalog_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _result(self, items: list[ProviderCatalogItem]) -> dict[str, Any]:
        return {"provider": self.provider, "models": items, "stale": self.stale, "error": self.error}


def provider_catalogs(key_getter: Callable[[str], Optional[str]] | None = None) -> dict[str, ProviderCatalog]:
    getter = key_getter or (lambda provider: None)
    return {provider: ProviderCatalog(provider, lambda p=provider: getter(p)) for provider in ("openai", "google")}
