import asyncio
from copy import deepcopy

from pydantic import BaseModel, Field
from trafilatura import extract, fetch_url
from trafilatura.settings import DEFAULT_CONFIG

from ..core.types import ToolResult
from ._tool_utils import ToolCancelledError, await_task_or_cancel
from .base import BaseTool

MAX_CHARS = 80_000
MAX_CHARS_PER_LINE = 2000
DOWNLOAD_TIMEOUT = 5

_download_config = deepcopy(DEFAULT_CONFIG)
_download_config["DEFAULT"]["DOWNLOAD_TIMEOUT"] = str(DOWNLOAD_TIMEOUT)


class WebFetchParams(BaseModel):
    url: str = Field(description="URL of the web page to fetch and extract content from")


class WebFetchTool(BaseTool):
    name = "web_fetch"
    tool_icon = "*"
    mutating = False
    params = WebFetchParams
    description = (
        "Fetch a web page and extract its main content as clean text. "
        "Strips navigation, ads, and boilerplate. "
        "Use web_search first to find relevant URLs (if not provided by the user)."
    )

    def format_call(self, params: WebFetchParams) -> str:
        url = params.url
        return url[:77] + "..." if len(url) > 80 else url

    async def execute(
        self, params: WebFetchParams, cancel_event: asyncio.Event | None = None
    ) -> ToolResult:
        def _fetch_and_extract() -> str | None:
            html = fetch_url(params.url, config=_download_config)
            if not html:
                return None
            return extract(
                html,
                output_format="txt",
                include_comments=False,
                include_tables=True,
                favor_precision=True,
                config=_download_config,
            )

        try:
            work = asyncio.create_task(asyncio.to_thread(_fetch_and_extract))
            content = await await_task_or_cancel(work, cancel_event)
        except ToolCancelledError:
            return ToolResult(success=False, result="Fetch aborted")
        except Exception as e:
            return ToolResult(success=False, ui_summary=f"[red]Fetch failed: {e}[/red]")

        if not content:
            return ToolResult(
                success=False, ui_summary=f"[red]Could not extract content from {params.url}[/red]"
            )

        lines = content.split("\n")
        lines = [line[:MAX_CHARS_PER_LINE] for line in lines]
        content = "\n".join(lines)

        char_count = len(content)
        truncated = char_count > MAX_CHARS
        if truncated:
            cut = content.rfind("\n", 0, MAX_CHARS)
            content = content[: cut if cut > 0 else MAX_CHARS] + "\n\n[content truncated]"

        ui_summary = f"[dim]({char_count:,} chars)[/dim]"
        if truncated:
            ui_summary += " [yellow](truncated)[/yellow]"

        return ToolResult(success=True, result=content, ui_summary=ui_summary)
