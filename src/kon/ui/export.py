import html
import json
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError
from rich.console import Console
from rich.errors import MarkupError, StyleSyntaxError
from rich.style import Style
from rich.table import Table
from rich.text import Text

from kon import config

from ..core.types import (
    AssistantMessage,
    ImageContent,
    TextContent,
    ThinkingContent,
    ToolCall,
    ToolResultMessage,
    UserMessage,
)
from ..session import (
    CompactionEntry,
    CustomMessageEntry,
    MessageEntry,
    ModelChangeEntry,
    Session,
    ThinkingLevelChangeEntry,
)
from ..tools import BaseTool, tools_by_name
from .formatting import CustomMarkdown, get_markdown_theme

CONSOLE_WIDTH = 120
MAX_HEADER_LINES = 2
MAX_RESULT_LINES = 20


def _render_markup_safe(content: str) -> Text:
    try:
        text = Text.from_markup(content)
    except MarkupError:
        return Text(content)
    for span in text.spans:
        style = span.style
        if isinstance(style, str):
            try:
                Style.parse(style)
            except StyleSyntaxError:
                return Text(content)
    return text


def _format_tool_call_msg(call_msg: str) -> Text:
    if not call_msg:
        return Text()
    lines = call_msg.split("\n")
    if len(lines) > MAX_HEADER_LINES:
        display_msg = "\n".join(lines[:MAX_HEADER_LINES])
        display_msg += f"\n... ({len(lines) - MAX_HEADER_LINES} more lines)"
        return _render_markup_safe(display_msg)
    return _render_markup_safe(call_msg)


def _format_tool_call(tool_call: ToolCall) -> str:
    tool = tools_by_name.get(tool_call.name)
    if not tool:
        return json.dumps(tool_call.arguments) if tool_call.arguments else ""
    try:
        params = tool.params(**tool_call.arguments)
        return tool.format_call(params)
    except (TypeError, KeyError, ValueError, ValidationError):
        return json.dumps(tool_call.arguments) if tool_call.arguments else ""


def _truncate_output(text: str, max_lines: int = MAX_RESULT_LINES) -> str:
    if not text:
        return text
    lines = text.split("\n")
    if len(lines) > max_lines:
        hidden = len(lines) - max_lines
        lines = lines[:max_lines]
        lines.append(f"... ({hidden} lines hidden)")
    return "\n".join(lines)


def _add_sep(console: Console) -> None:
    console.print()
    console.print("---")
    console.print()


def _print_metadata(console: Console, session: Session, model_id: str, provider: str) -> None:
    dim = config.ui.colors.dim
    counts = session.message_counts()
    token_totals = session.token_totals()

    model_str = model_id if provider == "unknown" else f"{model_id} ({provider})"

    token_parts = [f"↑{token_totals.input_tokens:,}", f"↓{token_totals.output_tokens:,}"]
    if token_totals.cache_read_tokens:
        token_parts.append(f"R{token_totals.cache_read_tokens:,}")
    if token_totals.cache_write_tokens:
        token_parts.append(f"W{token_totals.cache_write_tokens:,}")

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style=dim)
    table.add_column()
    table.add_row("ID", session.id)
    table.add_row("Directory", session.cwd)
    table.add_row("Created", session.created_at or "unknown")
    table.add_row("Model", model_str)
    table.add_row("Thinking", session.thinking_level)
    table.add_row(
        "Messages",
        (
            f"{counts.user_messages} user, {counts.assistant_messages} assistant, "
            f"{counts.tool_calls} tool calls"
        ),
    )
    table.add_row("Tokens", " ".join(token_parts))
    console.print(table)
    _add_sep(console)


def _print_system_prompt(console: Console, system_prompt: str) -> None:
    dim = config.ui.colors.dim
    console.print(Text(system_prompt, style=dim))
    _add_sep(console)


def _print_tools(console: Console, tools: list[BaseTool]) -> None:
    dim = config.ui.colors.dim

    for tool in tools:
        name = " ".join(w.capitalize() for w in tool.name.split("_"))
        header_text = Text()
        header_text.append(name, style="bold")
        header_text.append(f"  ({tool.name})", style=dim)
        console.print(header_text)
        console.print(Text(tool.description, style=dim))

        schema = tool.params.model_json_schema()
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        if properties:
            params_table = Table(show_header=True, box=None, padding=(0, 1))
            params_table.add_column("Parameter", style="bold")
            params_table.add_column("Type", style=config.ui.colors.accent)
            params_table.add_column("Description")

            for p_name, p_info in properties.items():
                p_type = p_info.get("type", "any")
                if p_name in required_fields:
                    p_type += "*"
                p_desc = p_info.get("description", "")
                params_table.add_row(p_name, p_type, p_desc)

            console.print(params_table)
        console.print()
    _add_sep(console)


def _print_conversation(console: Console, session: Session, tools: list[BaseTool]) -> None:
    dim = config.ui.colors.dim
    error_color = config.ui.colors.error

    for entry in session.entries:
        if isinstance(entry, MessageEntry):
            msg = entry.message

            if isinstance(msg, UserMessage):
                # Same rendering as UserBlock
                text = Text()
                text.append("> ", style="bold")
                if isinstance(msg.content, str):
                    text.append(msg.content)
                else:
                    for part in msg.content:
                        if isinstance(part, TextContent):
                            text.append(part.text)
                        elif isinstance(part, ImageContent):
                            text.append("[image]", style=dim)
                console.print(text)
                console.print()

            elif isinstance(msg, AssistantMessage):
                for part in msg.content:
                    if isinstance(part, TextContent) and part.text:
                        # Same as ContentBlock finalize → CustomMarkdown
                        md = CustomMarkdown(part.text)
                        console.print(md)
                        console.print()
                    elif isinstance(part, ThinkingContent) and part.thinking:
                        # Same as ThinkingBlock styling
                        console.print(Text(part.thinking, style=dim))
                        console.print()
                    elif isinstance(part, ToolCall):
                        # Same as ToolBlock._format_header
                        header_text = Text()
                        formatted_name = " ".join(w.capitalize() for w in part.name.split("_"))
                        header_text.append(formatted_name, style="bold")
                        call_msg = _format_tool_call(part)
                        if call_msg:
                            header_text.append(" ")
                            header_text.append_text(_format_tool_call_msg(call_msg))
                        console.print(header_text)

            elif isinstance(msg, ToolResultMessage):
                # Same as ToolBlock.set_result path in _render_session_entries
                if msg.ui_details:
                    result_text = msg.ui_details
                    markup = True
                else:
                    parts = [p.text for p in msg.content if isinstance(p, TextContent)]
                    result_text = _truncate_output("".join(parts))
                    markup = False

                if result_text:
                    if not msg.is_error:
                        rendered = (
                            _render_markup_safe(result_text) if markup else Text(result_text)
                        )
                    else:
                        rendered = Text(result_text, style=error_color)
                    console.print(rendered)
                console.print()

        elif isinstance(entry, ModelChangeEntry):
            console.print(Text(f"Model changed to {entry.model_id} ({entry.provider})", style=dim))
            console.print()
        elif isinstance(entry, ThinkingLevelChangeEntry):
            console.print(Text(f"Thinking level: {entry.thinking_level}", style=dim))
            console.print()
        elif isinstance(entry, CompactionEntry):
            console.print(Text("Context compacted", style=dim))
            console.print()
        elif isinstance(entry, CustomMessageEntry) and entry.display:
            console.print(Text(entry.content, style=dim))
            console.print()


_CODE_FORMAT = (
    "<pre style=\"font-family: 'JetBrains Mono', Menlo, 'DejaVu Sans Mono',"
    " consolas, 'Courier New', monospace; font-size: 13px; line-height: 1.6;"
    " color: #c9d1d9; padding: 2rem;"
    " max-width: 960px; margin: 0 auto; overflow-x: auto;"
    ' white-space: pre-wrap; word-wrap: break-word;">'
    '<code style="font-family: inherit">{code}</code></pre>'
)


def export_session_html(
    session: Session,
    system_prompt: str,
    tools: list[BaseTool],
    output_dir: str,
    model_id: str = "unknown",
    provider: str = "unknown",
    version: str | None = "0.0.0",
    title_color: str | None = "#d97706",
) -> Path:
    safe_version = str(version or "0.0.0")
    safe_title_color = str(title_color or "#d97706")

    console = Console(
        record=True,
        width=CONSOLE_WIDTH,
        force_terminal=True,
        no_color=False,
        theme=get_markdown_theme(),
    )

    _print_metadata(console, session, model_id, provider)
    _print_system_prompt(console, system_prompt)
    _print_tools(console, tools)
    _print_conversation(console, session, tools)

    rich_html = console.export_html(inline_styles=True, code_format=_CODE_FORMAT)

    export_session_id = session.session_file.stem if session.session_file else session.id
    filename = f"kon-session-{export_session_id}.html"
    output_path = Path(output_dir) / filename
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    page = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>kon v{html.escape(safe_version)} - {html.escape(export_session_id)}</title>
<style>
body {{ margin: 0; padding: 2rem 0; background: #282828; }}
.header {{
  max-width: 960px; margin: 0 auto 1rem; padding: 0 2rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}}
.header h1 {{ color: {html.escape(safe_title_color)}; font-size: 1.3rem; margin: 0 0 0.25rem; }}
.header p {{ color: #8b949e; font-size: 0.8rem; margin: 0; }}
</style>
</head>
<body>
<div class="header">
<h1>kon v{html.escape(safe_version)}</h1>
<p>exported {html.escape(now)}</p>
</div>
{rich_html}
</body>
</html>"""

    output_path.write_text(page, encoding="utf-8")
    return output_path
