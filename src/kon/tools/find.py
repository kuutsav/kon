import asyncio
import os

from pydantic import BaseModel, Field

from ..core.types import ToolResult
from ..tools_manager import ensure_tool
from ._tool_utils import (
    ToolCancelledError,
    communicate_or_cancel,
    shorten_path,
    truncate_lines_by_bytes,
)
from .base import BaseTool

MAX_RESULTS = 100
MAX_OUTPUT_BYTES = 20 * 1024


class FindParams(BaseModel):
    pattern: str = Field(
        description="Glob pattern to match files, e.g. '*.py', '**/*.json', or 'src/**/*.spec.ts'"
    )
    path: str | None = Field(
        description="Directory to search in (default: current directory)", default=None
    )


class FindTool(BaseTool):
    name = "find"
    tool_icon = "*"
    params = FindParams
    mutating = False
    prompt_guidelines = ("Use find to search for files by name/glob (NOT find or ls via bash)",)
    description = (
        "Search for files by glob pattern using fd. "
        "Returns matching file paths relative to the search directory, "
        "sorted by modification time."
        f"Respects .gitignore. Truncated to {MAX_RESULTS} results."
    )

    def format_call(self, params: FindParams) -> str:
        pattern = params.pattern.replace('"', '\\"')
        parts = [f'"{pattern}"']
        if params.path:
            parts.append(f"in {shorten_path(params.path)}")
        return " ".join(parts)

    async def execute(
        self, params: FindParams, cancel_event: asyncio.Event | None = None
    ) -> ToolResult:
        fd_path = await ensure_tool("fd", silent=True)
        if not fd_path:
            msg = "fd is not available and could not be downloaded"
            return ToolResult(success=False, result=msg, ui_summary=f"[red]{msg}[/red]")

        search_path = params.path or os.getcwd()
        if not os.path.isabs(search_path):
            search_path = os.path.join(os.getcwd(), search_path)

        if not os.path.exists(search_path):
            msg = f"Path not found: {search_path}"
            return ToolResult(success=False, result=msg, ui_summary=f"[red]{msg}[/red]")

        args = [
            fd_path,
            "--glob",
            "--color=never",
            "--hidden",
            "--max-results",
            str(MAX_RESULTS),
            params.pattern,
            search_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await communicate_or_cancel(proc, cancel_event)
        except ToolCancelledError:
            return ToolResult(success=False, result="Search aborted")

        exit_code = proc.returncode
        output = stdout.decode("utf-8", errors="replace").strip()
        error_output = stderr.decode("utf-8", errors="replace").strip()

        if exit_code not in (0, 1) and not output:
            msg = f"fd failed: {error_output}"
            return ToolResult(success=False, result=msg, ui_summary=f"[red]{msg}[/red]")

        if not output:
            return ToolResult(
                success=True,
                result="No files found matching pattern",
                ui_summary="[dim]No files found[/dim]",
            )

        lines = [line.strip() for line in output.split("\n") if line.strip()]

        # Relativize and collect mtime for sorting
        files: list[tuple[str, float]] = []
        for line in lines:
            if line.startswith(search_path):
                rel = line[len(search_path) :].lstrip(os.sep)
                rel = rel if rel else line
            else:
                rel = os.path.relpath(line, search_path)
            try:
                mtime = os.path.getmtime(line)
            except OSError:
                mtime = 0.0
            files.append((rel, mtime))

        files.sort(key=lambda f: f[1], reverse=True)

        relativized = [f[0] for f in files]
        truncated = len(relativized) >= MAX_RESULTS

        result_text, _ = truncate_lines_by_bytes(relativized, MAX_OUTPUT_BYTES)

        if truncated:
            result_text += (
                f"\n\n[{MAX_RESULTS} results limit reached; "
                "refine the pattern or path for more specific results]"
            )

        count = len(relativized)
        display = f"[dim]({count} files)[/dim]"

        return ToolResult(success=True, result=result_text, ui_summary=display)
