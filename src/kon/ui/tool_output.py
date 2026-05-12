from rich.markup import escape
from rich.text import Text

from kon import config


def format_expand_hint(hidden_lines: int) -> Text:
    colors = config.ui.colors
    text = Text()
    text.append(f"... ({hidden_lines} lines hidden • ", style=colors.dim)
    text.append("ctrl+o", style=colors.muted)
    text.append(" to expand)", style=colors.dim)
    return text


def escape_tool_output_text(text: str) -> str:
    return "\n".join(escape(line) for line in text.split("\n"))


def truncate_tool_output_text(
    text: str, max_lines: int = 5, escape_lines: bool = True
) -> tuple[str, bool]:
    if not text:
        return text, False

    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text, False

    hidden = len(lines) - max_lines
    visible = [escape(line) if escape_lines else line for line in lines[:max_lines]]
    hint = format_expand_hint(hidden_lines=hidden)
    visible.append(hint.markup)
    return "\n".join(visible), True
