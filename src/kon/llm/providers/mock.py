"""
Mock LLM provider for testing.

Yields a realistic streaming response (thinking, text, tool calls) for testing
agent loop and turn execution without making real API calls.

Scenarios (set via scenario parameter):
- "default": thinking → text → multiple tool calls
- "simple_text": just text, no thinking or tools
- "thinking_text_tool": thinking → text → single tool call
- "retries": fail twice, then succeed
- "retry_exhausted": always fail
- "non_retryable": fail with non-retryable error
- "stream_error": emit StreamError during streaming
- "unknown_tool": call unknown tool
- "long_text": multiple text chunks
- "tool_hang": emits a tool call and then never sends StreamDone
- "tool_with_many_chunks": tool call with many argument chunks for token counting tests
"""

import asyncio
from collections.abc import AsyncIterator

from ...core.types import (
    Message,
    StopReason,
    StreamDone,
    StreamError,
    TextPart,
    ThinkPart,
    ToolCallDelta,
    ToolCallStart,
    ToolDefinition,
    Usage,
)
from ..base import BaseProvider, LLMStream, ProviderConfig


class MockProvider(BaseProvider):
    name = "mock"

    def __init__(self, config: ProviderConfig | None = None, scenario: str = "default"):
        super().__init__(config or ProviderConfig())
        self.scenario = scenario
        self._attempt_count = 0

    async def _stream_impl(
        self,
        messages: list[Message],
        *,
        system_prompt: str | None = None,
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMStream:
        self._attempt_count += 1

        if self.scenario == "retries":
            if self._attempt_count < 3:
                raise ConnectionError("Rate limit")
        elif self.scenario == "retry_exhausted":
            raise ConnectionError("Always fails")
        elif self.scenario == "non_retryable":
            raise ValueError("Invalid input")

        llm_stream = LLMStream()
        llm_stream.set_iterator(self._get_iterator())
        llm_stream._id = "mock-1"
        llm_stream._usage = Usage(input_tokens=10, output_tokens=5, cache_read_tokens=2)

        return llm_stream

    def _get_iterator(self) -> AsyncIterator:
        match self.scenario:
            case "default":

                async def default_iter():
                    yield ThinkPart(think="Let me think about this...")
                    yield TextPart(text="I'll help you with that.")
                    yield ToolCallStart(id="call-1", name="read", index=0)
                    yield ToolCallDelta(index=0, arguments_delta='{"path": "file.txt"}')
                    yield ToolCallStart(id="call-2", name="bash", index=1)
                    yield ToolCallDelta(index=1, arguments_delta='{"command": "ls -la"}')
                    yield StreamDone(stop_reason=StopReason.TOOL_USE)

                return default_iter()

            case "simple_text":

                async def simple_iter():
                    yield TextPart(text="Hello, world!")
                    yield StreamDone(stop_reason=StopReason.STOP)

                return simple_iter()

            case "thinking_text_tool":

                async def flow_iter():
                    yield ThinkPart(think="I need to read the file")
                    yield TextPart(text="Let me check the file.")
                    yield ToolCallStart(id="call-1", name="read", index=0)
                    yield ToolCallDelta(index=0, arguments_delta='{"path": "test.txt"}')
                    yield StreamDone(stop_reason=StopReason.TOOL_USE)

                return flow_iter()

            case "stream_error":

                async def error_iter():
                    yield TextPart(text="Before error")
                    yield StreamError(error="Something went wrong")

                return error_iter()

            case "unknown_tool":

                async def unknown_iter():
                    yield ToolCallStart(id="call-1", name="unknown_tool", index=0)
                    yield ToolCallDelta(index=0, arguments_delta='{"arg": "value"}')
                    yield StreamDone(stop_reason=StopReason.TOOL_USE)

                return unknown_iter()

            case "long_text":

                async def long_iter():
                    for chunk in ["This ", "is ", "a ", "long ", "response", "."]:
                        yield TextPart(text=chunk)
                    yield StreamDone(stop_reason=StopReason.STOP)

                return long_iter()

            case "tool_hang":

                async def tool_hang_iter():
                    yield ToolCallStart(id="call-1", name="read", index=0)
                    yield ToolCallDelta(index=0, arguments_delta='{"path": "test.txt"}')
                    await asyncio.sleep(3600)

                return tool_hang_iter()

            case "tool_with_many_chunks":

                async def tool_with_many_chunks_iter():
                    # Tool call with many chunks to test token counting
                    # 24 chunks of 8 chars each = 192 chars = 48 tokens
                    # Should trigger token update events at chunks 12, 16, 20, 24
                    yield ToolCallStart(id="call-1", name="bash", index=0)
                    chunks = [
                        "aaaaaaa",
                        "bbbbbbb",
                        "ccccccc",
                        "ddddddd",
                        "eeeeeee",
                        "fffffff",
                        "ggggggg",
                        "hhhhhhh",
                        "iiiiiii",
                        "jjjjjjj",
                        "kkkkkkk",
                        "lllllll",
                        "mmmmmmm",
                        "nnnnnnn",
                        "ooooooo",
                        "ppppppp",
                        "qqqqqqq",
                        "rrrrrrr",
                        "sssssss",
                        "ttttttt",
                        "uuuuuuu",
                        "vvvvvvv",
                        "wwwwwww",
                        "xxxxxxxx",
                    ]
                    for chunk in chunks:
                        yield ToolCallDelta(index=0, arguments_delta=chunk)
                    yield StreamDone(stop_reason=StopReason.TOOL_USE)

                return tool_with_many_chunks_iter()

            case _:
                # Fallback to default
                async def default_iter():
                    yield ThinkPart(think="Let me think about this...")
                    yield TextPart(text="I'll help you with that.")
                    yield ToolCallStart(id="call-1", name="read", index=0)
                    yield ToolCallDelta(index=0, arguments_delta='{"path": "file.txt"}')
                    yield ToolCallStart(id="call-2", name="bash", index=1)
                    yield ToolCallDelta(index=1, arguments_delta='{"command": "ls -la"}')
                    yield StreamDone(stop_reason=StopReason.TOOL_USE)

                return default_iter()

    def should_retry_for_error(self, error: Exception) -> bool:
        if self.scenario == "retries" or self.scenario == "retry_exhausted":
            return isinstance(error, ConnectionError)
        return False
