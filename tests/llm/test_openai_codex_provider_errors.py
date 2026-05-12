import pytest

from kon.core.types import StreamDone, TextPart
from kon.llm.base import LLMStream, ProviderConfig
from kon.llm.providers.openai_codex_responses import (
    _WS_FALLBACK_SESSIONS,
    CodexTransportError,
    OpenAICodexResponsesProvider,
    _format_provider_error,
)


def test_format_provider_error_preserves_non_empty_message():
    err = RuntimeError("boom")
    assert _format_provider_error(err) == "boom"


def test_format_provider_error_falls_back_for_empty_message():
    err = TimeoutError()
    message = _format_provider_error(err)
    assert "TimeoutError" in message
    assert "without an error message" in message


def test_resolve_websocket_url_uses_ws_scheme_and_codex_responses_path():
    provider = OpenAICodexResponsesProvider(
        ProviderConfig(base_url="https://chatgpt.com/backend-api", model="gpt-5.4")
    )
    assert provider._resolve_websocket_url() == "wss://chatgpt.com/backend-api/codex/responses"


def test_websocket_headers_use_beta_and_request_id():
    provider = OpenAICodexResponsesProvider(
        ProviderConfig(session_id="session-123", model="gpt-5.4")
    )
    headers = provider._build_websocket_headers("token", "account")
    assert headers["OpenAI-Beta"] == "responses_websockets=2026-02-06"
    assert headers["session_id"] == "session-123"
    assert headers["x-client-request-id"] == "session-123"
    assert "accept" not in headers
    assert "content-type" not in headers


@pytest.mark.asyncio
async def test_stream_falls_back_to_sse_when_websocket_fails_before_events(monkeypatch):
    provider = OpenAICodexResponsesProvider(
        ProviderConfig(session_id="session-fallback", model="gpt-5.4")
    )
    _WS_FALLBACK_SESSIONS.discard("session-fallback")

    async def fail_websocket(*args, **kwargs):
        raise CodexTransportError("websocket unavailable")
        yield

    async def sse_events(*args, **kwargs):
        yield {"type": "response.output_text.delta", "delta": "ok"}
        yield {"type": "response.completed", "response": {"status": "completed"}}

    monkeypatch.setattr(provider, "_stream_websocket_events", fail_websocket)
    monkeypatch.setattr(provider, "_stream_sse_events", sse_events)

    parts = [
        part
        async for part in provider._stream_codex(
            token="token",
            account_id="account",
            messages=[],
            system_prompt=None,
            tools=None,
            temperature=None,
            max_tokens=None,
            llm_stream=LLMStream(),
        )
    ]

    assert isinstance(parts[0], TextPart)
    assert parts[0].text == "ok"
    assert isinstance(parts[1], StreamDone)
    assert "session-fallback" in _WS_FALLBACK_SESSIONS
