from __future__ import annotations

import pytest

from scripts import sync_demo_safety_images as sync


@pytest.mark.unit
def test_tls_verification_defaults_to_system_store(monkeypatch):
    for variable in sync._CA_BUNDLE_ENV_VARS:
        monkeypatch.delenv(variable, raising=False)
    assert sync.tls_verify_setting() is True


@pytest.mark.unit
def test_tls_verification_accepts_existing_explicit_bundle(tmp_path, monkeypatch):
    bundle = tmp_path / "ca-bundle.pem"
    bundle.write_text("test CA bundle", encoding="utf-8")
    monkeypatch.setenv("DEMO_CA_BUNDLE", str(bundle))
    assert sync.tls_verify_setting() == str(bundle)


@pytest.mark.unit
def test_tls_verification_rejects_missing_explicit_bundle(monkeypatch):
    monkeypatch.setenv("DEMO_CA_BUNDLE", "/missing/ca-bundle.pem")
    with pytest.raises(ValueError, match="CA bundle does not exist"):
        sync.tls_verify_setting()


@pytest.mark.unit
def test_download_passes_strict_tls_setting(monkeypatch, tmp_path):
    response = type("Response", (), {
        "headers": {"Content-Type": "image/svg+xml"},
        "content": b"<svg />",
        "raise_for_status": lambda self: None,
    })()
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return response

    monkeypatch.setattr(sync.requests, "get", fake_get)
    monkeypatch.setattr(sync, "tls_verify_setting", lambda: str(tmp_path / "bundle.pem"))
    sync._download("https://example.test/icon.svg")
    assert calls == [("https://example.test/icon.svg", {"timeout": 30, "verify": str(tmp_path / "bundle.pem")})]
