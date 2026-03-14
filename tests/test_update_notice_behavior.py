from kon.ui.app import Kon


def _make_app() -> Kon:
    return Kon(cwd=".")


def test_show_pending_update_notice_shows_once_when_idle(fake_chat) -> None:
    app = _make_app()
    chat = fake_chat

    app.query_one = lambda *args, **kwargs: chat  # type: ignore[method-assign]
    app._startup_complete = True
    app._is_running = False
    app._pending_update_notice_version = "1.2.3"

    app._show_pending_update_notice_if_idle()
    app._show_pending_update_notice_if_idle()

    assert chat.versions == ["1.2.3"]
    assert app._update_notice_shown is True
    assert app._pending_update_notice_version is None


def test_show_pending_update_notice_waits_until_not_running(fake_chat) -> None:
    app = _make_app()
    chat = fake_chat

    app.query_one = lambda *args, **kwargs: chat  # type: ignore[method-assign]
    app._startup_complete = True
    app._pending_update_notice_version = "1.2.3"

    app._is_running = True
    app._show_pending_update_notice_if_idle()
    assert chat.versions == []

    app._is_running = False
    app._show_pending_update_notice_if_idle()
    assert chat.versions == ["1.2.3"]
