from rich import box
from rich.panel import Panel
from rich.text import Text

from kon import config

_LOGO = ("░█░█░█▀█░█▀█", "░█▀▄░█░█░█░█", "░▀░▀░▀▀▀░▀░▀")

_SHORTCUT_ROWS = (
    (("/", "slash commands"), ("@", "files/dirs"), ("tab", "complete paths"), ("↑/↓", "history")),
    (("shift+tab", "permissions"), ("esc", "to interrupt"), ("shift+enter", "add newline")),
    (("ctrl+c", "clear input"), ("ctrl+c x2", "exit"), ("enter", "queue"), ("alt+enter", "steer")),
    (("↑/↓", "select queue"), ("ctrl+t", "cycle thinking"), ("ctrl+shift+t", "toggle thinking")),
)


def build_welcome(version: str) -> tuple[Text, Panel]:
    accent = config.ui.colors.accent
    dim = config.ui.colors.dim
    muted = config.ui.colors.muted
    border_color = config.ui.colors.border

    logo = Text()
    for i, line in enumerate(_LOGO):
        logo.append(line, style=accent)
        if i == len(_LOGO) - 1:
            logo.append(f" v{version}", style=dim)
        logo.append("\n")
    logo.append("\n")

    shortcuts = Text()
    for row_idx, row in enumerate(_SHORTCUT_ROWS):
        for item_idx, (key, desc) in enumerate(row):
            if item_idx > 0:
                shortcuts.append(" • ", style=dim)
            shortcuts.append(key, style=muted)
            shortcuts.append(f" {desc}", style=dim)
        if row_idx < len(_SHORTCUT_ROWS) - 1:
            shortcuts.append("\n")

    panel = Panel(
        shortcuts,
        title=None,
        title_align="left",
        box=box.SQUARE,
        border_style=border_color,
        padding=(0, 1),
        expand=False,
    )

    return logo, panel
