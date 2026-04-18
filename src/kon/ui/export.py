"""Standalone session HTML export.

By design this module parses session JSONL directly and avoids coupling itself to
other Kon internals. The only allowed Kon dependency here is the tool registry,
used to look up tool descriptions and parameter schemas for rendering.
"""

import html
import json
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..tools import tools_by_name

CONFIG_DIR_NAME = ".kon"
MAX_RESULT_LINES = 10

_CSS = """\
:root {
  --bg0: #282828; --bg1: #3c3836; --bg2: #504945;
  --fg: #ebdbb2; --fg2: #bdae93; --fg3: #a89984; --fg4: #928374;
  --red: #fb4934; --green: #b8bb26; --yellow: #fabd2f;
  --blue: #83a598; --orange: #fe8019; --purple: #d3869b;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: var(--bg0);
  color: var(--fg);
  font-family: 'SF Mono', 'JetBrains Mono', 'Menlo', monospace;
  font-size: 12px;
  line-height: 1.5;
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
}
a { color: var(--blue); }
.header {
  margin-bottom: 16px;
}
.header h1 { font-size: 14px; color: var(--orange); font-weight: 600; }
.header .meta { color: var(--fg4); font-size: 11px; margin-top: 4px; }
.msg-user {
  color: var(--green);
  white-space: pre-wrap;
}
.msg-assistant .text {
  color: var(--fg);
  white-space: pre-wrap;
}
.msg-assistant > * + * {
  margin-top: 6px;
}
.thinking {
  color: var(--fg4);
  font-style: italic;
  font-size: 11px;
  white-space: pre-wrap;
}
.system-section {
  color: var(--purple);
  padding: 8px 12px;
  margin: 8px 0;
  background: rgba(211,134,155,0.06);
  font-size: 11px;
}
.system-section .section-label {
  color: var(--purple);
  font-weight: 600;
  font-size: 11px;
  opacity: 0.7;
}
.system-content {
  white-space: pre-wrap;
}
.system-section .section-label + .system-content {
  margin-top: 4px;
}
.system-section .section-label + .tool-def {
  margin-top: 10px;
}
.tool-def {
  color: var(--purple);
  font-size: 11px;
}
.tool-def + .tool-def {
  margin-top: 10px;
}
.tool-def-inner {
  margin-top: 2px;
}
.tool-def .tool-name {
  font-weight: 600;
  white-space: pre-wrap;
}
.tool-def .tool-name::before { content: "* "; }
.tool-def .tool-desc {
  margin-top: 2px;
  color: var(--purple);
  opacity: 0.7;
  white-space: pre-wrap;
}
.tool-def .tool-params {
  margin-top: 2px;
  color: var(--purple);
  white-space: pre-wrap;
}
.system-msg {
  color: var(--fg4);
  font-style: italic;
  font-size: 11px;
  white-space: pre-wrap;
  margin: 8px 0;
}
.sep {
  border-top: 1px solid var(--bg2);
  margin: 8px 0;
}
.tool-block {
  background: var(--bg1);
  padding: 6px 8px;
  border-radius: 3px;
}
.tool-header { color: var(--yellow); font-weight: 600; }
.tool-call-args {
  color: var(--fg2);
  white-space: pre-wrap;
  font-size: 11px;
  margin-top: 2px;
}
.tool-result {
  color: var(--fg3);
  white-space: pre-wrap;
  font-size: 11px;
  overflow-x: auto;
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px solid var(--bg2);
}
.tool-result.error { color: var(--red); }
"""

_RICH_TAG_RE = re.compile(r"\[/?(?:[a-zA-Z0-9#._-]+)\]")


@dataclass(frozen=True)
class TokenTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True)
class SessionExportData:
    session_id: str
    session_file: Path
    created_at: str | None
    system_prompt: str | None
    tools: list[Any] | None
    entries: list[dict[str, Any]]
    model_id: str
    provider: str
    tokens: TokenTotals


def _strip_rich_markup(text: str) -> str:
    return _RICH_TAG_RE.sub("", text)


def _esc(text: str) -> str:
    return html.escape(_strip_rich_markup(text))


def _safe_cwd(cwd: str) -> str:
    return cwd.replace("/", "-").replace("\\", "-").strip("-")


def _get_sessions_dir(cwd: str) -> Path:
    return Path.home() / CONFIG_DIR_NAME / "sessions" / _safe_cwd(cwd)


def _read_session_header(path: Path) -> dict[str, Any] | None:
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            return data if data.get("type") == "header" else None
    return None


def _resolve_session_file(cwd: str, session_id: str) -> Path:
    normalized_id = session_id.strip().lower()
    if not normalized_id:
        raise ValueError("Session ID cannot be empty")

    sessions_dir = _get_sessions_dir(cwd)
    if not sessions_dir.exists():
        raise FileNotFoundError(f"No sessions found for cwd: {cwd}")

    exact_matches: list[Path] = []
    prefix_matches: list[Path] = []

    for path in sessions_dir.glob("*.jsonl"):
        try:
            header = _read_session_header(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not header:
            continue
        current_id = str(header.get("id", "")).lower()
        if current_id == normalized_id:
            exact_matches.append(path)
        elif current_id.startswith(normalized_id):
            prefix_matches.append(path)

    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise ValueError(f"Session ID is ambiguous: {session_id}")
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if len(prefix_matches) > 1:
        raise ValueError(f"Session ID prefix is ambiguous: {session_id}")
    raise FileNotFoundError(f"Session not found: {session_id}")


def _token_totals(entries: list[dict[str, Any]]) -> TokenTotals:
    input_tokens = 0
    output_tokens = 0
    cache_read_tokens = 0
    cache_write_tokens = 0

    for entry in entries:
        if entry.get("type") != "message":
            continue
        message = entry.get("message") or {}
        if message.get("role") != "assistant":
            continue
        usage = message.get("usage") or {}
        input_tokens += int(usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("output_tokens") or 0)
        cache_read_tokens += int(usage.get("cache_read_tokens") or 0)
        cache_write_tokens += int(usage.get("cache_write_tokens") or 0)

    return TokenTotals(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
    )


def _last_model(entries: list[dict[str, Any]]) -> tuple[str, str]:
    for entry in reversed(entries):
        if entry.get("type") == "model_change":
            return str(entry.get("model_id") or "unknown"), str(entry.get("provider") or "unknown")
    return "unknown", "unknown"


def _load_session_export_data(path: Path) -> SessionExportData:
    header: dict[str, Any] | None = None
    entries: list[dict[str, Any]] = []

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data.get("type") == "header" and header is None:
                header = data
            else:
                entries.append(data)

    if not header:
        raise ValueError(f"Invalid session file (missing header): {path}")

    model_id, provider = _last_model(entries)
    return SessionExportData(
        session_id=str(header.get("id") or path.stem),
        session_file=path,
        created_at=header.get("timestamp"),
        system_prompt=header.get("system_prompt"),
        tools=header.get("tools"),
        entries=entries,
        model_id=model_id,
        provider=provider,
        tokens=_token_totals(entries),
    )


def _escape_inline_newlines(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")


def _format_arg_value(value: Any) -> str:
    if isinstance(value, str):
        return _truncate_inline(_escape_inline_newlines(value))
    try:
        rendered = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        rendered = str(value)
    return _truncate_inline(_escape_inline_newlines(rendered))


def _format_aligned_kv_lines(items: list[tuple[str, str]]) -> list[str]:
    if not items:
        return []
    max_width = max(len(key) for key, _ in items)
    lines: list[str] = []
    for key, value in items:
        prefix = f"{key.ljust(max_width)} :"
        lines.append(f"{prefix} {value}" if value else prefix)
    return lines


def _format_tool_call_args(tool_call: dict[str, Any] | None) -> str:
    if tool_call is None:
        return ""

    arguments = tool_call.get("arguments")
    if not arguments:
        return ""
    if isinstance(arguments, dict):
        items = [(str(key), _format_arg_value(value)) for key, value in arguments.items()]
        return "\n".join(_format_aligned_kv_lines(items))
    if isinstance(arguments, str):
        return _truncate_inline(_escape_inline_newlines(arguments))
    try:
        rendered = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        rendered = str(arguments)
    return _truncate_inline(_escape_inline_newlines(rendered))


def _truncate(text: str, max_lines: int = MAX_RESULT_LINES) -> str:
    if not text:
        return text

    lines = text.split("\n")
    if len(lines) > max_lines:
        hidden = len(lines) - max_lines
        lines = lines[:max_lines]
        lines.append(f"... ({hidden} lines hidden)")
    return "\n".join(lines)


def _truncate_inline(text: str, max_chars: int = 72) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 4].rstrip() + " ..."


def _format_name(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split("_"))


def _iter_content_parts(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, list):
        return [part for part in content if isinstance(part, dict)]
    return []


def _render_message_content(content: Any) -> str:
    if isinstance(content, str):
        return _esc(content)

    parts: list[str] = []
    for part in _iter_content_parts(content):
        part_type = part.get("type")
        if part_type == "text":
            parts.append(_esc(str(part.get("text") or "")))
        elif part_type == "image":
            parts.append('<span style="color:var(--fg4)">[image]</span>')
    return "".join(parts)


def _extract_text_content(content: Any) -> str:
    parts: list[str] = []
    for part in _iter_content_parts(content):
        part_type = part.get("type")
        if part_type == "text":
            parts.append(str(part.get("text") or ""))
        elif part_type == "image":
            parts.append("[image]")
    return "".join(parts)


def _schema_param_lines(schema: dict[str, Any] | None) -> list[str]:
    if not isinstance(schema, dict):
        return []

    props = schema.get("properties")
    if not isinstance(props, dict):
        return []

    items: list[tuple[str, str]] = []
    for param_name, param_value in props.items():
        if not isinstance(param_value, dict):
            items.append((str(param_name), ""))
            continue
        param_desc = str(param_value.get("description") or "").strip()
        param_type = str(param_value.get("type") or "").strip()
        if param_desc:
            items.append((str(param_name), param_desc))
        elif param_type:
            items.append((str(param_name), param_type))
        else:
            items.append((str(param_name), ""))
    return _format_aligned_kv_lines(items)


def _tool_definition_parts(tool_item: Any) -> tuple[str, str | None, list[str]]:
    if isinstance(tool_item, str):
        tool = tools_by_name.get(tool_item)
        if tool:
            return (
                tool_item,
                tool.description,
                _schema_param_lines(tool.params.model_json_schema()),
            )
        return tool_item, None, []

    if not isinstance(tool_item, dict):
        return str(tool_item), None, []

    name = str(tool_item.get("name") or tool_item.get("id") or "unknown")
    description = tool_item.get("description")
    desc = str(description) if isinstance(description, str) and description else None
    schema = tool_item.get("parameters") or tool_item.get("params")
    param_lines = _schema_param_lines(schema)
    if desc or param_lines:
        return name, desc, param_lines

    tool = tools_by_name.get(name)
    if tool:
        return name, tool.description, _schema_param_lines(tool.params.model_json_schema())
    return name, None, []


class HtmlBuilder:
    def __init__(self) -> None:
        self._parts: list[str] = []
        self._assistant_open = False
        self._last_block_kind: str | None = None

    def _append(self, text: str) -> None:
        self._parts.append(text)

    def _before_chat_block(self) -> None:
        self.close_assistant()
        if self._last_block_kind == "chat":
            self._append('<div class="sep"></div>')
        self._last_block_kind = "chat"

    def open_assistant(self) -> None:
        if not self._assistant_open:
            self._before_chat_block()
            self._append('<div class="msg msg-assistant">')
            self._assistant_open = True

    def close_assistant(self) -> None:
        if self._assistant_open:
            self._append("</div>")
            self._assistant_open = False

    def header(self, version: str, session: SessionExportData) -> None:
        token_parts = [f"↑{session.tokens.input_tokens:,}", f"↓{session.tokens.output_tokens:,}"]
        if session.tokens.cache_read_tokens:
            token_parts.append(f"R{session.tokens.cache_read_tokens:,}")
        if session.tokens.cache_write_tokens:
            token_parts.append(f"W{session.tokens.cache_write_tokens:,}")

        model_str = (
            session.model_id
            if session.provider == "unknown"
            else f"{session.model_id} ({session.provider})"
        )
        created = session.created_at or "unknown"
        if "T" in created:
            with suppress(ValueError):
                created = datetime.fromisoformat(created).strftime("%Y-%m-%d %H:%M")

        self._append('<div class="header">')
        self._append(f"<h1>kon {_esc(version)}</h1>")
        self._append(
            f'<div class="meta">session {session.session_id[:8]}'
            f" · {_esc(created)} · {_esc(model_str)}"
            f" · {' '.join(token_parts)}</div>"
        )
        self._append("</div>")

    def user_message(self, message: dict[str, Any]) -> None:
        self._before_chat_block()
        self._append(
            f'<div class="msg-user">&gt; {_render_message_content(message.get("content"))}</div>'
        )

    def assistant_text(self, text: str) -> None:
        self.open_assistant()
        self._append(f'<div class="text">{_esc(text)}</div>')

    def thinking(self, text: str) -> None:
        self.open_assistant()
        self._append(f'<div class="thinking">{_esc(text)}</div>')

    def tool_block(self, name: str, args: str, result_text: str = "", error: bool = False) -> None:
        self.open_assistant()
        parts = [f'<div class="tool-header">{_esc(name)}</div>']
        if args:
            parts.append(f'<div class="tool-call-args">{_esc(args)}</div>')
        if result_text:
            klass = "tool-result error" if error else "tool-result"
            parts.append(f'<div class="{klass}">{_esc(result_text)}</div>')
        self._append(f'<div class="tool-block">{"".join(parts)}</div>')

    def system_section(self, system_prompt: str | None, tools: list[Any] | None) -> None:
        self.close_assistant()
        self._last_block_kind = "system"
        if system_prompt:
            self._append('<div class="system-section">')
            self._append('<div class="section-label">System Prompt</div>')
            self._append(f'<div class="system-content">{_esc(system_prompt)}</div>')
            self._append("</div>")
        if tools:
            self._append('<div class="system-section">')
            self._append('<div class="section-label">Tools</div>')
            for tool_item in tools:
                name, description, param_lines = _tool_definition_parts(tool_item)
                self._append('<div class="tool-def">')
                self._append('<div class="tool-def-inner">')
                self._append(f'<div class="tool-name">{_esc(name)}</div>')
                if description:
                    self._append(f'<div class="tool-desc">{_esc(description)}</div>')
                if param_lines:
                    params_html = "<br>".join(_esc(line) for line in param_lines)
                    self._append(f'<div class="tool-params">{params_html}</div>')
                self._append("</div>")
                self._append("</div>")
            self._append("</div>")

    def system_message(self, text: str) -> None:
        self.close_assistant()
        self._last_block_kind = "system"
        self._append(f'<div class="system-msg">{_esc(text)}</div>')

    def build(self) -> str:
        self.close_assistant()
        body = "\n".join(self._parts)
        return f"""\
<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"UTF-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>kon - Export</title>
<style>
{_CSS}
</style>
</head>
<body>
{body}
</body>
</html>"""


class ExportRenderer:
    def __init__(self, builder: HtmlBuilder) -> None:
        self.builder = builder
        self.pending_tool_calls: dict[str, dict[str, Any]] = {}
        self.in_assistant_turn = False

    def _flush_pending_tool_calls(self) -> None:
        for tool_call in self.pending_tool_calls.values():
            self.builder.tool_block(
                _format_name(str(tool_call.get("name") or "tool")),
                _format_tool_call_args(tool_call),
            )
        self.pending_tool_calls.clear()

    def _end_assistant_turn(self) -> None:
        if not self.in_assistant_turn:
            return
        self._flush_pending_tool_calls()
        self.builder.close_assistant()
        self.in_assistant_turn = False

    def _pop_pending_tool_call(self, tool_call_id: str) -> dict[str, Any] | None:
        tool_call = self.pending_tool_calls.pop(tool_call_id, None)
        if tool_call is not None:
            return tool_call

        normalized_id = tool_call_id.split("|", 1)[0]
        if normalized_id != tool_call_id:
            tool_call = self.pending_tool_calls.pop(normalized_id, None)
            if tool_call is not None:
                return tool_call

        for pending_id in list(self.pending_tool_calls):
            if pending_id.split("|", 1)[0] == normalized_id:
                return self.pending_tool_calls.pop(pending_id)
        return None

    def render_entry(self, entry: dict[str, Any]) -> None:
        entry_type = entry.get("type")

        if entry_type == "message":
            message = entry.get("message") or {}
            role = message.get("role")

            if role == "user":
                self._end_assistant_turn()
                self.builder.user_message(message)
                return

            if role == "assistant":
                self.in_assistant_turn = True
                for part in _iter_content_parts(message.get("content")):
                    part_type = part.get("type")
                    if part_type == "text" and part.get("text"):
                        self.builder.assistant_text(str(part.get("text") or ""))
                    elif part_type == "thinking" and part.get("thinking"):
                        self.builder.thinking(str(part.get("thinking") or ""))
                    elif part_type == "tool_call" and part.get("id"):
                        self.pending_tool_calls[str(part.get("id"))] = part
                return

            if role == "tool_result":
                self.in_assistant_turn = True
                tool_call_id = str(message.get("tool_call_id") or "")
                tool_call = self._pop_pending_tool_call(tool_call_id)
                tool_name = str(message.get("tool_name") or "tool")
                name = (
                    _format_name(str(tool_call.get("name") or tool_name))
                    if tool_call
                    else _format_name(tool_name)
                )
                args = _format_tool_call_args(tool_call)

                if message.get("is_error"):
                    text = _extract_text_content(message.get("content")).strip()
                    result = f"-- {text} --" if text else ""
                    self.builder.tool_block(name, args, result_text=result, error=True)
                    return

                result_source = message.get("ui_details")
                if not isinstance(result_source, str) or not result_source:
                    result_source = _extract_text_content(message.get("content"))
                self.builder.tool_block(name, args, result_text=_truncate(result_source))
                return

        self._end_assistant_turn()

        if entry_type == "model_change":
            model_id = entry.get("model_id") or "unknown"
            provider = entry.get("provider") or "unknown"
            self.builder.system_message(f"Model changed to {model_id} ({provider})")
        elif entry_type == "thinking_level_change":
            self.builder.system_message(
                f"Thinking level: {entry.get('thinking_level') or 'unknown'}"
            )
        elif entry_type == "compaction":
            self.builder.system_message("Context compacted")
        elif entry_type == "custom_message" and entry.get("display", True):
            self.builder.system_message(str(entry.get("content") or ""))

    def finish(self) -> None:
        self._end_assistant_turn()


def export_session_html(cwd: str, session_id: str, output_dir: str, version: str = "") -> Path:
    session_file = _resolve_session_file(cwd, session_id)
    session = _load_session_export_data(session_file)

    builder = HtmlBuilder()
    builder.header(version, session)
    if session.system_prompt or session.tools:
        builder.system_section(session.system_prompt, session.tools)

    renderer = ExportRenderer(builder)
    for entry in session.entries:
        renderer.render_entry(entry)
    renderer.finish()

    output_path = Path(output_dir) / f"kon-session-{session.session_file.stem}.html"
    output_path.write_text(builder.build(), encoding="utf-8")
    return output_path
