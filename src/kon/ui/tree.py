from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

from kon import config
from kon.core.types import AssistantMessage, TextContent, ToolCall, ToolResultMessage, UserMessage
from kon.session import (
    CompactionEntry,
    CustomMessageEntry,
    MessageEntry,
    ModelChangeEntry,
    SessionEntry,
    SessionInfoEntry,
    ThinkingLevelChangeEntry,
    TreeNode,
)
from kon.tools import get_tool
from kon.tools._tool_utils import shorten_path


@dataclass
class GutterInfo:
    position: int
    show: bool


@dataclass
class FlatNode:
    node: TreeNode
    indent: int
    show_connector: bool
    is_last: bool
    gutters: list[GutterInfo]
    is_virtual_root_child: bool


class TreeSelector(Widget):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("up", "move_up", "Move", priority=True),
        Binding("down", "move_down", "Move", priority=True),
        Binding("left,pageup", "page_up", "Page", priority=True),
        Binding("right,pagedown", "page_down", "Page", priority=True),
        Binding("enter", "select", "Select", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    DEFAULT_CSS = """
    TreeSelector {
        height: auto;
        display: none;
        padding: 0 1;
    }

    TreeSelector.-visible {
        display: block;
    }
    """

    class Selected(Message):
        def __init__(self, entry_id: str) -> None:
            super().__init__()
            self.entry_id = entry_id

    class Cancelled(Message):
        pass

    _visible: reactive[bool] = reactive(False, repaint=False)
    _render_key: reactive[int] = reactive(0)

    def __init__(self, id: str | None = None) -> None:
        super().__init__(id=id)
        self._flat_nodes: list[FlatNode] = []
        self._filtered_nodes: list[FlatNode] = []
        self._selected_index = 0
        self._current_leaf_id: str | None = None
        self._multiple_roots = False
        self._active_path_ids: set[str] = set()
        self._last_selected_id: str | None = None
        self._max_visible_lines = 10
        self._tool_calls_by_id: dict[str, ToolCall] = {}

    @property
    def is_visible(self) -> bool:
        return self._visible

    def show(self, tree: list[TreeNode], current_leaf_id: str | None, height: int = 24) -> None:
        self._current_leaf_id = current_leaf_id
        self._max_visible_lines = max(5, height // 2)
        self._tool_calls_by_id = self._collect_tool_calls(tree)
        self._multiple_roots = len(tree) > 1
        self._flat_nodes = self._flatten_tree(tree)
        self._filtered_nodes = list(self._flat_nodes)
        self._build_active_path()
        self._selected_index = self._find_nearest_visible_index(current_leaf_id)
        self._last_selected_id = (
            self._filtered_nodes[self._selected_index].node.entry.id
            if self._filtered_nodes
            else None
        )
        self._visible = True
        self._render_key += 1
        self.focus()

    def hide(self) -> None:
        self._visible = False
        self._flat_nodes = []
        self._filtered_nodes = []
        self._selected_index = 0
        self._last_selected_id = None
        self._render_key += 1

    def watch__visible(self, visible: bool) -> None:
        if visible:
            self.add_class("-visible")
        else:
            self.remove_class("-visible")

    def _collect_tool_calls(self, roots: list[TreeNode]) -> dict[str, ToolCall]:
        calls: dict[str, ToolCall] = {}
        stack = list(roots)
        while stack:
            node = stack.pop()
            entry = node.entry
            if isinstance(entry, MessageEntry) and isinstance(entry.message, AssistantMessage):
                for part in entry.message.content:
                    if isinstance(part, ToolCall):
                        calls[part.id] = part
            stack.extend(node.children)
        return calls

    def _flatten_tree(self, roots: list[TreeNode]) -> list[FlatNode]:
        result: list[FlatNode] = []
        contains_active: dict[str, bool] = {}

        def mark(node: TreeNode) -> bool:
            has = self._current_leaf_id is not None and node.entry.id == self._current_leaf_id
            for child in node.children:
                has = mark(child) or has
            contains_active[node.entry.id] = has
            return has

        for root in roots:
            mark(root)

        ordered_roots = sorted(
            roots, key=lambda n: contains_active.get(n.entry.id, False), reverse=True
        )
        multiple_roots = len(roots) > 1
        stack: list[tuple[TreeNode, int, bool, bool, bool, list[GutterInfo], bool]] = []
        for index in range(len(ordered_roots) - 1, -1, -1):
            stack.append(
                (
                    ordered_roots[index],
                    1 if multiple_roots else 0,
                    multiple_roots,
                    multiple_roots,
                    index == len(ordered_roots) - 1,
                    [],
                    multiple_roots,
                )
            )

        while stack:
            (
                node,
                indent,
                just_branched,
                show_connector,
                is_last,
                gutters,
                is_virtual_root_child,
            ) = stack.pop()
            result.append(
                FlatNode(node, indent, show_connector, is_last, gutters, is_virtual_root_child)
            )

            children = node.children
            multiple_children = len(children) > 1
            active_children = [c for c in children if contains_active.get(c.entry.id, False)]
            other_children = [c for c in children if not contains_active.get(c.entry.id, False)]
            ordered_children = active_children + other_children

            if multiple_children or (just_branched and indent > 0):
                child_indent = indent + 1
            else:
                child_indent = indent

            connector_displayed = show_connector and not is_virtual_root_child
            display_indent = max(0, indent - 1) if self._multiple_roots else indent
            connector_position = max(0, display_indent - 1)
            child_gutters = (
                [*gutters, GutterInfo(connector_position, not is_last)]
                if connector_displayed
                else gutters
            )

            for index in range(len(ordered_children) - 1, -1, -1):
                stack.append(
                    (
                        ordered_children[index],
                        child_indent,
                        multiple_children,
                        multiple_children,
                        index == len(ordered_children) - 1,
                        child_gutters,
                        False,
                    )
                )

        return result

    def _build_active_path(self) -> None:
        self._active_path_ids.clear()
        by_id = {flat.node.entry.id: flat.node.entry for flat in self._flat_nodes}
        current_id = self._current_leaf_id
        while current_id:
            self._active_path_ids.add(current_id)
            current_id = by_id.get(current_id).parent_id if by_id.get(current_id) else None

    def _find_nearest_visible_index(self, entry_id: str | None) -> int:
        if not self._filtered_nodes:
            return 0
        entry_map = {flat.node.entry.id: flat.node.entry for flat in self._flat_nodes}
        visible = {flat.node.entry.id: i for i, flat in enumerate(self._filtered_nodes)}
        current_id = entry_id
        while current_id is not None:
            if current_id in visible:
                return visible[current_id]
            current_id = entry_map.get(current_id).parent_id if entry_map.get(current_id) else None
        return len(self._filtered_nodes) - 1

    def _entry_plain_text(self, entry: SessionEntry) -> str:
        if isinstance(entry, MessageEntry):
            message = entry.message
            if isinstance(message, UserMessage):
                if isinstance(message.content, str):
                    return message.content
                return "".join(
                    part.text if isinstance(part, TextContent) else "[image]"
                    for part in message.content
                )
            if isinstance(message, AssistantMessage):
                return "".join(
                    part.text for part in message.content if isinstance(part, TextContent)
                )
            if isinstance(message, ToolResultMessage):
                return message.tool_name
        if isinstance(entry, CustomMessageEntry):
            return entry.content
        if isinstance(entry, CompactionEntry):
            return entry.summary
        if isinstance(entry, ModelChangeEntry):
            return entry.model_id
        if isinstance(entry, ThinkingLevelChangeEntry):
            return entry.thinking_level
        if isinstance(entry, SessionInfoEntry):
            return entry.name or ""
        return ""

    def _entry_display_text(self, entry: SessionEntry, selected: bool) -> Text:
        colors = config.ui.colors
        text = Text()
        if isinstance(entry, MessageEntry):
            message = entry.message
            if isinstance(message, UserMessage):
                text.append("user: ", style=colors.accent)
                text.append(self._normalize(self._entry_plain_text(entry)))
            elif isinstance(message, AssistantMessage):
                text.append("assistant: ", style=colors.success)
                content = self._normalize(self._entry_plain_text(entry))
                text.append(content or "(no content)", style=None if content else colors.dim)
            elif isinstance(message, ToolResultMessage):
                text.append(self._format_tool_result(message), style=colors.dim)
        elif isinstance(entry, CustomMessageEntry):
            text.append(f"[{entry.custom_type}]: ", style=colors.info)
            text.append(self._normalize(entry.content))
        elif isinstance(entry, CompactionEntry):
            text.append(
                f"[compaction: {round(entry.tokens_before / 1000)}k tokens]", style=colors.accent
            )
        elif isinstance(entry, ModelChangeEntry):
            text.append(f"[model: {entry.model_id}]", style=colors.dim)
        elif isinstance(entry, ThinkingLevelChangeEntry):
            text.append(f"[thinking: {entry.thinking_level}]", style=colors.dim)
        elif isinstance(entry, SessionInfoEntry):
            text.append(f"[title: {entry.name or 'empty'}]", style=colors.dim)
        if selected:
            text.stylize("bold")
        return text

    def _format_tool_result(self, message: ToolResultMessage) -> str:
        call = self._tool_calls_by_id.get(message.tool_call_id)
        name = call.name if call else message.tool_name
        tool = get_tool(name)
        if tool and call:
            try:
                params = tool.params(**call.arguments)
                return f"[{name}: {tool.format_call(params)}]"
            except Exception:
                pass
        if call and call.arguments:
            return f"[{name}: {self._format_tool_args(call.arguments)}]"
        return f"[{name}]"

    def _format_tool_args(self, args: dict[str, object]) -> str:
        for key in ("path", "file_path", "command", "pattern", "url"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return shorten_path(value.strip())[:80]
        if not args:
            return ""
        return str(args)[:80]

    def _normalize(self, value: str) -> str:
        return value.replace("\n", " ").replace("\t", " ").strip()[:200]

    def render(self) -> Text:
        _ = self._render_key
        out = Text()
        if not self._visible:
            return out

        colors = config.ui.colors
        out.append("\n")
        out.append("─" * max(10, self.size.width or 80), style=colors.border)
        out.append("\n  Session Tree\n", style=f"bold {colors.title}")
        out.append("  ↑/↓ move • ←/→ page\n", style=colors.dim)
        out.append("─" * max(10, self.size.width or 80), style=colors.border)
        out.append("\n\n")

        if not self._filtered_nodes:
            out.append("  No entries found\n", style=colors.dim)
            out.append("  (0/0)", style=colors.dim)
            return out

        start = max(
            0,
            min(
                self._selected_index - self._max_visible_lines // 2,
                len(self._filtered_nodes) - self._max_visible_lines,
            ),
        )
        end = min(start + self._max_visible_lines, len(self._filtered_nodes))
        for index in range(start, end):
            flat = self._filtered_nodes[index]
            entry = flat.node.entry
            selected = index == self._selected_index
            line = Text()
            line.append(
                "› ",  # noqa: RUF001 - match pi tree cursor
                style=colors.accent if selected else "",
            ) if selected else line.append("  ")
            display_indent = max(0, flat.indent - 1) if self._multiple_roots else flat.indent
            connector = (
                "└─ "
                if flat.show_connector and not flat.is_virtual_root_child and flat.is_last
                else "├─ "
                if flat.show_connector and not flat.is_virtual_root_child
                else ""
            )
            connector_position = display_indent - 1 if connector else -1
            prefix_chars: list[str] = []
            for char_index in range(display_indent * 3):
                level = char_index // 3
                pos = char_index % 3
                gutter = next((g for g in flat.gutters if g.position == level), None)
                if gutter:
                    prefix_chars.append("│" if pos == 0 and gutter.show else " ")
                elif connector and level == connector_position:
                    if pos == 0:
                        prefix_chars.append("└" if flat.is_last else "├")
                    elif pos == 1:
                        prefix_chars.append("─")
                    else:
                        prefix_chars.append(" ")
                else:
                    prefix_chars.append(" ")
            line.append("".join(prefix_chars), style=colors.dim)
            if entry.id in self._active_path_ids:
                line.append("• ", style=colors.accent)
            line.append_text(self._entry_display_text(entry, selected))
            if selected:
                line.stylize(f"on {colors.panel_alt}")
            out.append_text(line)
            out.append("\n")

        out.append(f"  ({self._selected_index + 1}/{len(self._filtered_nodes)})", style=colors.dim)
        out.append("\n")
        out.append("─" * max(10, self.size.width or 80), style=colors.border)
        return out

    def action_move_up(self) -> None:
        if self._filtered_nodes:
            self._selected_index = (
                len(self._filtered_nodes) - 1
                if self._selected_index == 0
                else self._selected_index - 1
            )
            self._last_selected_id = self._filtered_nodes[self._selected_index].node.entry.id
            self._render_key += 1

    def action_move_down(self) -> None:
        if self._filtered_nodes:
            self._selected_index = (
                0
                if self._selected_index == len(self._filtered_nodes) - 1
                else self._selected_index + 1
            )
            self._last_selected_id = self._filtered_nodes[self._selected_index].node.entry.id
            self._render_key += 1

    def action_page_up(self) -> None:
        self._selected_index = max(0, self._selected_index - self._max_visible_lines)
        self._render_key += 1

    def action_page_down(self) -> None:
        self._selected_index = min(
            max(0, len(self._filtered_nodes) - 1), self._selected_index + self._max_visible_lines
        )
        self._render_key += 1

    def action_select(self) -> None:
        if self._filtered_nodes:
            self.post_message(
                self.Selected(self._filtered_nodes[self._selected_index].node.entry.id)
            )

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())
