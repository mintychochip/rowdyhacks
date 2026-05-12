from unittest.mock import patch

from app.assistant.llm import LLMClient, get_llm_client
from app.config import settings


class TestGetLlmClient:
    """Test the get_llm_client factory and its precedence rules."""

    def test_get_llm_client_uses_passed_model(self):
        """When a model is passed, it should be used directly."""
        client = get_llm_client(model="gpt-4")
        assert client.model == "gpt-4"

    def test_get_llm_client_resolves_base_url(self):
        """llm_base_url should take precedence over poolside_api_url."""
        with patch.object(settings, "llm_base_url", "https://custom.api/v1"):
            with patch.object(settings, "poolside_api_url", "https://poolside.ai/v1"):
                client = get_llm_client()
                assert client.api_url == "https://custom.api/v1"

    def test_get_llm_client_falls_back_to_poolside_url(self):
        """When llm_base_url is empty, fall back to poolside_api_url."""
        with patch.object(settings, "llm_base_url", ""):
            with patch.object(settings, "poolside_api_url", "https://poolside.ai/v1"):
                client = get_llm_client()
                assert client.api_url == "https://poolside.ai/v1"

    def test_get_llm_client_resolves_api_key(self):
        """llm_api_key should take precedence over poolside_api_key."""
        with patch.object(settings, "llm_api_key", "custom-key"):
            with patch.object(settings, "poolside_api_key", "poolside-key"):
                client = get_llm_client()
                assert client.api_key == "custom-key"

    def test_get_llm_client_falls_back_to_poolside_key(self):
        """When llm_api_key is empty, fall back to poolside_api_key."""
        with patch.object(settings, "llm_api_key", ""):
            with patch.object(settings, "poolside_api_key", "poolside-key"):
                client = get_llm_client()
                assert client.api_key == "poolside-key"

    def test_get_llm_client_resolves_model_from_llm_model(self):
        """When no model arg is passed, use llm_model if set."""
        with patch.object(settings, "llm_model", "gpt-3.5-turbo"):
            with patch.object(settings, "assistant_model", "old-model"):
                client = get_llm_client()
                assert client.model == "gpt-3.5-turbo"

    def test_get_llm_client_falls_back_to_assistant_model(self):
        """When llm_model is empty, fall back to assistant_model."""
        with patch.object(settings, "llm_model", ""):
            with patch.object(settings, "assistant_model", "fallback-model"):
                client = get_llm_client()
                assert client.model == "fallback-model"


class TestLLMClientConstruction:
    """Test that LLMClient uses passed parameters correctly."""

    def test_llm_client_uses_passed_params(self):
        client = LLMClient(base_url="https://custom.api", api_key="custom-key", model="custom-model")
        assert client.api_url == "https://custom.api"
        assert client.api_key == "custom-key"
        assert client.model == "custom-model"

    def test_llm_client_falls_back_to_defaults(self):
        client = LLMClient()
        assert client.api_url == settings.poolside_api_url
        assert client.api_key == settings.get_poolside_key()
        assert client.model == settings.assistant_model
