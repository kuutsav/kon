from kon import get_config
from kon.core.types import StopReason
from kon.events import AgentEndEvent, ToolApprovalEvent, TurnStartEvent
from kon.ui.app import Kon


def _make_app() -> Kon:
    return Kon(cwd=".")


def test_should_notify_for_event_respects_config() -> None:
    app = _make_app()
    get_config()._parsed.notifications.enabled = False

    assert app._should_notify_for_event(AgentEndEvent(stop_reason=StopReason.STOP)) is False
    assert app._should_notify_for_event(ToolApprovalEvent(future=None)) is False


def test_should_notify_for_event_notifies_for_configured_events() -> None:
    app = _make_app()
    get_config()._parsed.notifications.enabled = True

    assert app._should_notify_for_event(AgentEndEvent(stop_reason=StopReason.STOP)) is True
    assert app._should_notify_for_event(ToolApprovalEvent(future=None)) is True
    assert app._should_notify_for_event(TurnStartEvent(turn=1)) is False


def test_should_notify_for_event_skips_interrupted_agent_end() -> None:
    app = _make_app()
    get_config()._parsed.notifications.enabled = True

    assert app._should_notify_for_event(AgentEndEvent(stop_reason=StopReason.INTERRUPTED)) is False
