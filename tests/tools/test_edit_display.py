from rich.text import Text

from kon import config
from kon.tools.edit import format_diff_display


def test_format_diff_display_short_lines_not_truncated() -> None:
    short = "+2 short line"
    display = format_diff_display(short)
    assert "..." not in display
    assert "short line" in display


def test_format_diff_display_truncates_long_lines() -> None:
    long_added = "+2 " + "x" * 300
    long_removed = "-2 " + "y" * 300

    display = format_diff_display(f"{long_added}\n{long_removed}")
    lines = display.split("\n")

    added_color = config.ui.colors.diff_added
    removed_color = config.ui.colors.diff_removed

    assert len(lines) == 2
    assert lines[0].startswith(f"[{added_color}]")
    assert lines[0].endswith("...[/" + added_color + "]")
    assert lines[1].startswith(f"[{removed_color}]")
    assert lines[1].endswith("...[/" + removed_color + "]")


def test_format_diff_display_escapes_regex_bracket_literals() -> None:
    line = r' 40 _PASTE_MARKER_RE = re.compile(r"\[paste #(\d+)\]")'

    display = format_diff_display(line)
    text = Text.from_markup(display)

    assert text.plain == line
    assert [span.style for span in text.spans] == ["dim"]
