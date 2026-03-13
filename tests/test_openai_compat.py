from kon.llm.base import ProviderConfig
from kon.llm.providers.openai_codex_responses import OpenAICodexResponsesProvider
from kon.llm.providers.openai_compat import supports_developer_role
from kon.llm.providers.openai_completions import _detect_compat
from kon.llm.providers.openai_responses import OpenAIResponsesProvider


def test_supports_developer_role_for_openai_api() -> None:
    assert supports_developer_role("openai", "https://api.openai.com/v1") is True


def test_supports_developer_role_for_local_openai_compatible_api() -> None:
    assert supports_developer_role("openai", "http://127.0.0.1:1234/v1") is False


def test_supports_developer_role_for_zhipu() -> None:
    assert supports_developer_role("zhipu", "https://api.z.ai/api/coding/paas/v4") is False


def test_detect_compat_disables_developer_role_for_local_api() -> None:
    compat = _detect_compat("openai", "http://127.0.0.1:1234/v1")

    assert compat.supports_developer_role is False
    assert compat.supports_reasoning_effort is True


def test_openai_responses_uses_system_for_local_api() -> None:
    provider = OpenAIResponsesProvider(
        ProviderConfig(
            api_key="test-key",
            base_url="http://127.0.0.1:1234/v1",
            model="qwen/qwen3.5-35b-a3b",
            provider="openai",
        )
    )

    messages = provider._convert_messages([], "You are helpful")

    assert messages[0]["role"] == "system"


def test_openai_responses_uses_developer_for_openai_api() -> None:
    provider = OpenAIResponsesProvider(
        ProviderConfig(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="gpt-5",
            provider="openai",
        )
    )

    messages = provider._convert_messages([], "You are helpful")

    assert messages[0]["role"] == "developer"


def test_openai_codex_request_uses_session_for_prompt_caching() -> None:
    provider = OpenAICodexResponsesProvider(
        ProviderConfig(
            base_url="https://chatgpt.com/backend-api",
            model="gpt-5.4",
            provider="openai-codex",
            session_id="session-123",
        )
    )

    body = provider._build_request_body([], "You are helpful", None, None)
    headers = provider._build_headers("token", "account")

    assert body["prompt_cache_key"] == "session-123"
    assert headers["session_id"] == "session-123"
    assert headers["conversation_id"] == "session-123"


def test_openai_codex_request_omits_prompt_cache_fields_without_session() -> None:
    provider = OpenAICodexResponsesProvider(
        ProviderConfig(
            base_url="https://chatgpt.com/backend-api", model="gpt-5.4", provider="openai-codex"
        )
    )

    body = provider._build_request_body([], "You are helpful", None, None)
    headers = provider._build_headers("token", "account")

    assert "prompt_cache_key" not in body
    assert "session_id" not in headers
    assert "conversation_id" not in headers
