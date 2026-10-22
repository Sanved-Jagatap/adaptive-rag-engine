from unittest.mock import patch

from app.routing.query_router import OllamaRouterClient


def test_ollama_router_client_defaults_come_from_settings():
    # This is the exact bug reported in the debugging handoff: a hardcoded
    # model="llama3.1"/host="http://localhost:11434" silently diverged from
    # whatever the app was actually configured to use (e.g. a different
    # model name, or Ollama reachable via host.docker.internal instead of
    # localhost), and the router's LLM fallback used the wrong config with
    # no visible error — it just behaved as if the LLM call failed.
    from app.core.config import settings

    with patch.object(settings, "ollama_model", "llama3.2:latest"), patch.object(
        settings, "ollama_host", "http://host.docker.internal:11434"
    ), patch.object(settings, "ollama_timeout_seconds", 45.0):
        client = OllamaRouterClient()
        assert client.model == "llama3.2:latest"
        assert client.host == "http://host.docker.internal:11434"
        assert client.timeout == 45.0


def test_ollama_router_client_explicit_args_override_settings():
    client = OllamaRouterClient(model="custom-model", host="http://example.com:1234/", timeout=5.0)
    assert client.model == "custom-model"
    assert client.host == "http://example.com:1234"  # trailing slash stripped
    assert client.timeout == 5.0
