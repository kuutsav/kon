"""Tests for the mock LLM provider."""

import pytest

from kon.core.types import StreamDone, TextPart, ThinkPart, ToolCallDelta, ToolCallStart
from kon.llm.providers import MockProvider


@pytest.mark.asyncio
async def test_mock_provider_streams_response():
    """Test that mock provider streams thinking, text, two tool calls, and done."""
    provider = MockProvider()

    stream = await provider.stream([])
    parts = []
    async for part in stream:
        parts.append(part)

    assert len(parts) == 7
    assert isinstance(parts[0], ThinkPart)
    assert parts[0].think == "Let me think about this..."
    assert isinstance(parts[1], TextPart)
    assert parts[1].text == "I'll help you with that."
    assert isinstance(parts[2], ToolCallStart)
    assert parts[2].name == "read"
    assert parts[2].id == "call-1"
    assert isinstance(parts[3], ToolCallDelta)
    assert parts[3].arguments_delta == '{"path": "file.txt"}'
    assert isinstance(parts[4], ToolCallStart)
    assert parts[4].name == "bash"
    assert parts[4].id == "call-2"
    assert isinstance(parts[5], ToolCallDelta)
    assert parts[5].arguments_delta == '{"command": "ls -la"}'
    assert isinstance(parts[6], StreamDone)
    assert parts[6].stop_reason == "tool_use"


@pytest.mark.asyncio
async def test_mock_provider_reports_usage():
    """Test that mock provider reports usage stats."""
    provider = MockProvider()

    stream = await provider.stream([])
    async for _ in stream:
        pass

    assert stream.usage is not None
    assert stream.usage.input_tokens == 10
    assert stream.usage.output_tokens == 5
    assert stream.usage.cache_read_tokens == 2
    assert stream.usage.total_tokens == 17


@pytest.mark.asyncio
async def test_mock_provider_reports_response_id():
    """Test that mock provider reports a response ID."""
    provider = MockProvider()

    stream = await provider.stream([])
    async for _ in stream:
        pass

    assert stream.id == "mock-1"


@pytest.mark.asyncio
async def test_mock_provider_accepts_system_prompt():
    """Test that mock provider accepts system_prompt parameter."""
    provider = MockProvider()

    stream = await provider.stream([], system_prompt="You are a helpful assistant")

    parts = []
    async for part in stream:
        parts.append(part)

    assert len(parts) == 7


@pytest.mark.asyncio
async def test_mock_provider_accepts_tools():
    """Test that mock provider accepts tools parameter."""
    provider = MockProvider()

    stream = await provider.stream([], tools=[])

    parts = []
    async for part in stream:
        parts.append(part)

    assert len(parts) == 7


@pytest.mark.asyncio
async def test_mock_provider_accepts_temperature():
    """Test that mock provider accepts temperature parameter."""
    provider = MockProvider()

    stream = await provider.stream([], temperature=0.7)

    parts = []
    async for part in stream:
        parts.append(part)

    assert len(parts) == 7


@pytest.mark.asyncio
async def test_mock_provider_accepts_max_tokens():
    """Test that mock provider accepts max_tokens parameter."""
    provider = MockProvider()

    stream = await provider.stream([], max_tokens=1000)

    parts = []
    async for part in stream:
        parts.append(part)

    assert len(parts) == 7


def test_mock_provider_should_retry():
    """Test that mock provider never retries."""
    provider = MockProvider()
    assert provider.should_retry_for_error(RuntimeError("any error")) is False


@pytest.mark.asyncio
async def test_mock_provider_with_config():
    """Test that mock provider can be initialized with a config."""
    from kon.llm.base import ProviderConfig

    config = ProviderConfig(model="test-model", temperature=0.5)
    provider = MockProvider(config=config)

    stream = await provider.stream([])

    parts = []
    async for part in stream:
        parts.append(part)

    assert len(parts) == 7
