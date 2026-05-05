import asyncio
from abc import ABC, abstractmethod

from pydantic import BaseModel

from ..core.types import ToolResult


class BaseTool[T: BaseModel](ABC):
    # UI model for tool blocks:
    # - format_call(params): short call text shown on the tool header
    # - ToolResult.ui_summary: one-line result summary appended to that header
    # - ToolResult.ui_details: multiline result body shown below the header
    # - format_preview(params): approval-time preview shown before execution
    name: str
    params: type[T]
    description: str
    mutating: bool = True
    tool_icon: str = "→"
    prompt_guidelines: tuple[str, ...] = ()

    @abstractmethod
    async def execute(
        self, params: T, cancel_event: asyncio.Event | None = None
    ) -> ToolResult: ...

    def format_call(self, params: T) -> str:
        data = params.model_dump(exclude_none=True)
        if not data:
            return ""
        parts = [f"{k}={v}" for k, v in data.items()]
        return " / ".join(parts)

    def format_preview(self, params: T) -> str | None:
        """Extended preview shown only during approval prompts. Returns None by default."""
        return None
