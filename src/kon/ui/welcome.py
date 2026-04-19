from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kon import config

_LOGO = (
    "   ▄█   ▄█▄  ▄██████▄  ███▄▄▄▄   ",
    "  ███ ▄███▀ ███    ███ ███▀▀▀██▄ ",
    "  ███▐██▀   ███    ███ ███   ███ ",
    " ▄█████▀    ███    ███ ███   ███ ",
    "▀▀█████▄    ███    ███ ███   ███ ",
    "  ███▐██▄   ███    ███ ███   ███ ",
    "  ███ ▀███▄ ███    ███ ███   ███ ",
    "  ███   ▀█▀  ▀██████▀   ▀█   █▀  ",
    "  ▀                               ",
)

_LEFT_HINTS = (
    ("/", "commands"),
    ("@", "files / dirs"),
    ("esc", "interrupt"),
    ("tab", "complete path"),
    ("ctrl+c", "clear input"),
    ("ctrl+c x2", "exit"),
)

_RIGHT_HINTS = (
    ("shift+enter", "newline"),
    ("ctrl+t", "thinking"),
    ("shift+tab", "thinking level"),
    ("↑/↓", "history"),
    ("enter", "queue msg"),
    ("alt+enter", "steer agent"),
)


def build_welcome(version: str) -> tuple[Text, Panel]:
    accent = config.ui.colors.accent
    dim = config.ui.colors.dim
    muted = config.ui.colors.muted
    border_color = config.ui.colors.border

    # Logo
    logo = Text()
    for line in _LOGO:
        logo.append(line, style=accent)
        logo.append("\n")

    # Shortcuts table
    table = Table(
        show_header=False,
        show_edge=False,
        show_lines=False,
        box=None,
        padding=(0, 5),
        pad_edge=False,
        expand=False,
    )
    table.add_column(no_wrap=True)
    table.add_column(no_wrap=True)

    for (lk, ld), (rk, rd) in zip(_LEFT_HINTS, _RIGHT_HINTS, strict=True):
        left = Text()
        left.append(lk, style=dim)
        left.append(f" {ld}", style=muted)
        right = Text()
        right.append(rk, style=dim)
        right.append(f" {rd}", style=muted)
        table.add_row(left, right)

    title = Text(f"v{version}", style=accent)

    panel = Panel(
        table,
        title=title,
        title_align="left",
        box=box.SQUARE,
        border_style=border_color,
        padding=(0, 1),
        expand=False,
    )

    return logo, panel
