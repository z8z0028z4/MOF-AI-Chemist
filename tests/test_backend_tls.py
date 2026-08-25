import pytest
from unittest.mock import MagicMock


@pytest.mark.unit
def test_tls_verify_defaults_to_verified_system_store(monkeypatch):
    from backend.core import tls

    for variable in tls._CA_BUNDLE_ENV_VARS:
        monkeypatch.delenv(variable, raising=False)

    assert tls.tls_verify_setting() is True


@pytest.mark.unit
def test_tls_verify_uses_existing_enterprise_bundle(monkeypatch, tmp_path):
    from backend.core import tls

    bundle = tmp_path / "ITRIRoot256.pem"
    bundle.write_text("synthetic CA bundle", encoding="utf-8")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(bundle))
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    assert tls.tls_verify_setting() == str(bundle)


@pytest.mark.unit
def test_tls_verify_rejects_missing_explicit_bundle(monkeypatch):
    from backend.core import tls

    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/missing/ITRIRoot256.pem")
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    with pytest.raises(ValueError, match="configured CA bundle does not exist"):
        tls.tls_verify_setting()


@pytest.mark.unit
def test_europepmc_request_uses_resolved_tls_setting(monkeypatch):
    from backend.services import europepmc_handler

    response = MagicMock(status_code=200)
    response.json.return_value = {"resultList": {"result": []}}
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        return response

    monkeypatch.setattr(europepmc_handler, "tls_verify_setting", lambda: "/ca.pem")
    monkeypatch.setattr(europepmc_handler.requests, "get", fake_get)

    assert europepmc_handler.search_source(["mof"]) == []
    assert calls == [{"verify": "/ca.pem"}]


@pytest.mark.unit
def test_llm_client_passes_verified_httpx_client_to_openai(monkeypatch, tmp_path):
    import httpx
    from backend.core import llm_client

    bundle = tmp_path / "ITRIRoot256.pem"
    bundle.write_text("synthetic CA bundle", encoding="utf-8")
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["http_client"] = kwargs["http_client"]

    class FakeHttpClient:
        def __init__(self, **kwargs):
            self.verify = kwargs["verify"]

        def close(self):
            pass

    monkeypatch.setattr(llm_client, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(httpx, "Client", FakeHttpClient)
    monkeypatch.setattr(llm_client, "HAS_GEMINI", False)
    monkeypatch.setattr(llm_client, "tls_verify_setting", lambda: str(bundle))

    client = llm_client.LLMClient()

    assert client.client is not None
    assert captured["http_client"].verify == str(bundle)
    captured["http_client"].close()
    assert not hasattr(client, "disable_ssl_verify")
    assert "DISABLE_SSL_VERIFY" not in vars(llm_client)
