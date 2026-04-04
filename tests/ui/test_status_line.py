from kon.ui.widgets import StatusLine


def test_status_line_formats_without_turn_tps(monkeypatch):
    status = StatusLine()
    status._start_time = 100.0
    status._tool_calls = 1

    monkeypatch.setattr("kon.ui.widgets.time.time", lambda: 104.0)

    rendered = status._format_complete_status()
    assert rendered.plain == "4s • 1x"
