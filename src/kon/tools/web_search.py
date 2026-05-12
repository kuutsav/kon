import asyncio

from ddgs import DDGS
from pydantic import BaseModel, Field

from ..core.types import ToolResult
from ._tool_utils import ToolCancelledError, await_task_or_cancel
from .base import BaseTool


class WebSearchParams(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(
        description="Number of results to return (default 10)", default=10, ge=1, le=10
    )


class WebSearchTool(BaseTool):
    name = "web_search"
    tool_icon = "%"
    mutating = False
    params = WebSearchParams
    prompt_guidelines = ("Use web_search/web_fetch instead of curl/wget via bash",)
    description = (
        "Search the web using DuckDuckGo. Returns titles, URLs, and snippets for each result. "
        "Use web_fetch to read full page content from a result URL."
    )

    def format_call(self, params: WebSearchParams) -> str:
        query = params.query.replace('"', '\\"')
        return f'"{query}"'

    async def execute(
        self, params: WebSearchParams, cancel_event: asyncio.Event | None = None
    ) -> ToolResult:
        def _search() -> list[dict]:
            return list(DDGS().text(params.query, max_results=params.max_results))

        try:
            work = asyncio.create_task(asyncio.to_thread(_search))
            results = await await_task_or_cancel(work, cancel_event)
        except ToolCancelledError:
            return ToolResult(success=False, result="Search aborted")
        except Exception as e:
            return ToolResult(success=False, ui_summary=f"[red]Search failed: {e}[/red]")

        if not results:
            return ToolResult(
                success=True, result="No results found", ui_summary="[dim]No results found[/dim]"
            )

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.get('title', '(no title)')}")
            lines.append(f"   {r.get('href', '')}")
            lines.append(f"   {r.get('body', '')}")
            lines.append("")

        result_text = "\n".join(lines).strip()
        ui_summary = f"[dim]({len(results)} results)[/dim]"

        return ToolResult(success=True, result=result_text, ui_summary=ui_summary)
