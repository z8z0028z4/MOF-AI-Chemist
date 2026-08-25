"""
Unit tests for provider-client demo-mode guards (TODO 13.0 card a, defense-in-depth):
- GeminiClient.generate_content / generate_structured_content / *_sync refuse to call
  the real API when demo mode is active for at least one stage.
- LLMClient.call_llm / call_structured_llm apply the same guard.
- env_manager.get_provider_key refuses to return provider keys under demo mode.

Written FIRST per TDD: these guards don't exist yet, so all should fail (RED)
before implementation. No real network calls / real clients are needed:
monkeypatched env vars + demo_config.reset_cache_for_tests() are sufficient.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


def _set_demo_mode_on(monkeypatch):
    _set_demo_mode_off(monkeypatch)
    monkeypatch.setenv("DEMO_MOCK_PROPOSAL", "true")


def _set_demo_mode_off(monkeypatch):
    from backend.core import demo_config

    for var in (
        "DEMO_MOCK_PROPOSAL",
        "DEMO_MOCK_GENERATE_NEW_IDEA",
        "DEMO_MOCK_PROPERTY_PREDICTION",
        "DEMO_MOCK_EXPERIMENT_DETAIL",
    ):
        monkeypatch.setenv(var, "false")
    demo_config.reset_cache_for_tests()


class TestGeminiClientGuard:
    @pytest.mark.asyncio
    async def test_generate_content_allows_unchecked_active_stage_when_another_stage_is_demo(
        self, monkeypatch
    ):
        from backend.core import demo_config
        from backend.core.gemini_client import GeminiClient

        _set_demo_mode_on(monkeypatch)
        client = GeminiClient.__new__(GeminiClient)
        client.client = SimpleNamespace(
            aio=SimpleNamespace(
                models=SimpleNamespace(
                    generate_content=AsyncMock(return_value=SimpleNamespace(text="allowed"))
                )
            )
        )

        with demo_config.stage_context("generate_new_idea"):
            result = await client.generate_content("gemini-3-pro-preview", "hello")

        assert result == "allowed"

    @pytest.mark.asyncio
    async def test_generate_content_raises_llmerror_when_demo_mode_active(self, monkeypatch):
        from backend.core.gemini_client import GeminiClient
        from backend.utils.exceptions import LLMError

        _set_demo_mode_on(monkeypatch)
        client = GeminiClient.__new__(GeminiClient)  # bypass real __init__/network client setup
        client.client = None
        client.api_key = None

        with pytest.raises(LLMError):
            await client.generate_content("gemini-3-pro-preview", "hello")

    @pytest.mark.asyncio
    async def test_generate_structured_content_raises_llmerror_when_demo_mode_active(self, monkeypatch):
        from backend.core.gemini_client import GeminiClient
        from backend.utils.exceptions import LLMError

        _set_demo_mode_on(monkeypatch)
        client = GeminiClient.__new__(GeminiClient)
        client.client = None
        client.api_key = None

        with pytest.raises(LLMError):
            await client.generate_structured_content("gemini-3-pro-preview", "hello", {"type": "object"})

    def test_generate_content_sync_raises_llmerror_when_demo_mode_active(self, monkeypatch):
        from backend.core.gemini_client import GeminiClient
        from backend.utils.exceptions import LLMError

        _set_demo_mode_on(monkeypatch)
        client = GeminiClient.__new__(GeminiClient)
        client.client = None
        client.api_key = None

        with pytest.raises(LLMError):
            client.generate_content_sync("gemini-3-pro-preview", "hello")

    def test_generate_structured_content_sync_raises_llmerror_when_demo_mode_active(self, monkeypatch):
        from backend.core.gemini_client import GeminiClient
        from backend.utils.exceptions import LLMError

        _set_demo_mode_on(monkeypatch)
        client = GeminiClient.__new__(GeminiClient)
        client.client = None
        client.api_key = None

        with pytest.raises(LLMError):
            client.generate_structured_content_sync("gemini-3-pro-preview", "hello", {"type": "object"})

    def test_init_logs_warning_when_demo_mode_active(self, monkeypatch, caplog):
        from backend.core.gemini_client import GeminiClient

        _set_demo_mode_on(monkeypatch)
        with caplog.at_level("WARNING"):
            client = GeminiClient()

        assert any("demo mode" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_generate_content_does_not_raise_llmerror_for_demo_reason_when_demo_mode_off(self, monkeypatch):
        """Off-mode must not raise the demo-mode guard error (it may still fail for other
        reasons, e.g. no client configured, but not because of the demo guard)."""
        from backend.core.gemini_client import GeminiClient
        from backend.utils.exceptions import LLMError

        _set_demo_mode_off(monkeypatch)
        client = GeminiClient.__new__(GeminiClient)
        client.client = None
        client.api_key = None

        with pytest.raises(LLMError) as exc_info:
            await client.generate_content("gemini-3-pro-preview", "hello")
        assert "demo mode" not in str(exc_info.value).lower()


class TestLLMClientGuard:
    def test_call_llm_allows_unchecked_active_stage_when_another_stage_is_demo(self, monkeypatch):
        from backend.core import demo_config
        from backend.core.llm_client import LLMClient

        _set_demo_mode_on(monkeypatch)
        client = LLMClient.__new__(LLMClient)
        client.gemini_client = MagicMock()
        client.gemini_client.generate_content_sync.return_value = "allowed"

        with demo_config.stage_context("generate_new_idea"):
            result = client.call_llm("hello", "gemini-3-pro-preview", {})

        assert result == "allowed"
        client.gemini_client.generate_content_sync.assert_called_once()

    def test_call_llm_raises_llmerror_for_gemini_model_when_demo_mode_active(self, monkeypatch):
        from backend.core.llm_client import LLMClient
        from backend.utils.exceptions import LLMError

        _set_demo_mode_on(monkeypatch)
        client = LLMClient.__new__(LLMClient)  # bypass real client init (no network/API keys needed)
        client.client = None
        client.gemini_client = None

        with pytest.raises(LLMError):
            client.call_llm("hello", "gemini-3-pro-preview", {})

    def test_call_structured_llm_raises_llmerror_for_gemini_model_when_demo_mode_active(self, monkeypatch):
        from backend.core.llm_client import LLMClient
        from backend.utils.exceptions import LLMError

        _set_demo_mode_on(monkeypatch)
        client = LLMClient.__new__(LLMClient)
        client.client = None
        client.gemini_client = None

        with pytest.raises(LLMError):
            client.call_structured_llm("hello", {"type": "object"}, "gemini-3-pro-preview", {})


class TestEnvManagerProviderKeyGuard:
    def test_get_provider_key_allows_unchecked_active_stage_when_another_stage_is_demo(
        self, monkeypatch, tmp_path
    ):
        from backend.core import demo_config
        from backend.core.env_manager import EnvManager

        _set_demo_mode_on(monkeypatch)
        manager = EnvManager()
        manager.env_file = tmp_path / ".env"
        manager.write_env_file({"OPENAI_API_KEY": "test-key"})

        with demo_config.stage_context("generate_new_idea"):
            key = manager.get_provider_key("OPENAI_API_KEY")

        assert key == "test-key"

    def test_get_provider_key_returns_none_when_demo_mode_active(self, monkeypatch, tmp_path):
        from backend.core.env_manager import EnvManager

        _set_demo_mode_on(monkeypatch)
        manager = EnvManager()
        manager.env_file = tmp_path / ".env"
        manager.write_env_file({"OPENAI_API_KEY": "sk-real-looking-key"})

        assert manager.get_provider_key("OPENAI_API_KEY") is None

    def test_get_provider_key_delegates_when_demo_mode_off(self, monkeypatch, tmp_path):
        from backend.core.env_manager import EnvManager

        _set_demo_mode_off(monkeypatch)
        manager = EnvManager()
        manager.env_file = tmp_path / ".env"
        manager.write_env_file({"OPENAI_API_KEY": "sk-real-looking-key"})

        assert manager.get_provider_key("OPENAI_API_KEY") == "sk-real-looking-key"

    def test_get_provider_key_logs_warning_when_refusing(self, monkeypatch, tmp_path, caplog):
        from backend.core.env_manager import EnvManager

        _set_demo_mode_on(monkeypatch)
        manager = EnvManager()
        manager.env_file = tmp_path / ".env"
        manager.write_env_file({"OPENAI_API_KEY": "sk-real-looking-key"})

        with caplog.at_level("WARNING"):
            manager.get_provider_key("OPENAI_API_KEY")

        assert any("demo mode" in record.message.lower() for record in caplog.records)
