from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel


class StopReason(StrEnum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_USE = "tool_use"
    ERROR = "error"
    INTERRUPTED = "interrupted"


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


# =================================================================================================
# Stream Parts - yielded by providers during streaming
# =================================================================================================


class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str

    def merge(self, other: TextPart) -> TextPart:
        return TextPart(text=self.text + other.text)


class ThinkPart(BaseModel):
    type: Literal["think"] = "think"
    think: str
    signature: str | None = None

    def merge(self, other: ThinkPart) -> ThinkPart:
        signature = self.signature or other.signature
        return ThinkPart(think=self.think + other.think, signature=signature)


class ToolCallStart(BaseModel):
    type: Literal["tool_call_start"] = "tool_call_start"
    id: str
    name: str
    index: int  # Tool call index for correlating deltas
    arguments: dict[str, Any] | None = None


class ToolCallDelta(BaseModel):
    type: Literal["tool_call_delta"] = "tool_call_delta"
    index: int  # Correlates with ToolCallStart.index
    arguments_delta: str


class StreamDone(BaseModel):
    type: Literal["done"] = "done"
    stop_reason: StopReason


class StreamError(BaseModel):
    type: Literal["error"] = "error"
    error: str


StreamPart = TextPart | ThinkPart | ToolCallStart | ToolCallDelta | StreamDone | StreamError


# =================================================================================================
# Message Types - canonical provider-agnostic conversation interface
# Used for conversation history and cross-provider normalization
# =================================================================================================


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ThinkingContent(BaseModel):
    type: Literal["thinking"] = "thinking"
    thinking: str
    signature: str | None = None


class ImageContent(BaseModel):
    type: Literal["image"] = "image"
    data: str  # base64 encoded
    mime_type: str


class ToolCall(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    id: str
    name: str
    arguments: dict[str, Any]


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str | list[TextContent | ImageContent]


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: list[TextContent | ThinkingContent | ToolCall]
    usage: Usage | None = None
    stop_reason: StopReason | None = None


class ToolResultMessage(BaseModel):
    role: Literal["tool_result"] = "tool_result"
    tool_call_id: str
    tool_name: str
    content: list[TextContent | ImageContent]
    display: str | None = None  # Formatted for UI display (Rich markup supported)
    is_error: bool = False
    file_changes: FileChanges | None = None


Message = UserMessage | AssistantMessage | ToolResultMessage


# =================================================================================================
# Tool Definition
# =================================================================================================


class ToolParameter(BaseModel):
    type: str
    description: str | None = None
    enum: list[str] | None = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


class FileChanges(BaseModel):
    path: str
    added: int = 0
    removed: int = 0


class ToolResult(BaseModel):
    success: bool
    result: str | None = None  # Raw result (sent to LLM)
    images: list[ImageContent] | None = None  # Images to include in result
    display: str | None = None  # Formatted for UI display (Rich markup supported)
    file_changes: FileChanges | None = None  # Track +/- lines for edit/write tools
