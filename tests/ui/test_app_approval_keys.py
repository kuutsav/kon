from kon.permissions import ApprovalResponse
from kon.ui.app import Kon


class FakeKeyEvent:
    def __init__(self, key: str) -> None:
        self.key = key
        self.prevented = False
        self.stopped = False

    def prevent_default(self) -> None:
        self.prevented = True

    def stop(self) -> None:
        self.stopped = True


class FakeChat:
    def __init__(self) -> None:
        self.selections: list[tuple[str, ApprovalResponse]] = []

    def update_tool_approval_selection(self, tool_id: str, selection: ApprovalResponse) -> None:
        self.selections.append((tool_id, selection))


class FakeFuture:
    def __init__(self) -> None:
        self._done = False
        self._result: ApprovalResponse | None = None

    def done(self) -> bool:
        return self._done

    def set_result(self, result: ApprovalResponse) -> None:
        self._done = True
        self._result = result

    def result(self) -> ApprovalResponse | None:
        return self._result


class FakeKon:
    def __init__(self, future: FakeFuture) -> None:
        self._approval_future = future
        self._approval_selection = ApprovalResponse.APPROVE
        self._approval_tool_id = "tool-1"
        self.chat = FakeChat()
        self.cleared = False

    def query_one(self, selector, widget_type):
        assert selector == "#chat-log"
        return self.chat

    def _clear_approval_state(self) -> None:
        self.cleared = True


def test_approval_left_right_toggles_selection_without_submitting() -> None:
    future = FakeFuture()
    app = FakeKon(future)

    left = FakeKeyEvent("left")
    Kon.on_key(app, left)  # type: ignore[arg-type]

    assert app._approval_selection == ApprovalResponse.DENY
    assert not future.done()
    assert app.chat.selections == [("tool-1", ApprovalResponse.DENY)]
    assert left.prevented is True
    assert left.stopped is True
    assert app.cleared is False

    right = FakeKeyEvent("right")
    Kon.on_key(app, right)  # type: ignore[arg-type]

    assert app._approval_selection == ApprovalResponse.APPROVE
    assert not future.done()
    assert app.chat.selections[-1] == ("tool-1", ApprovalResponse.APPROVE)


def test_approval_enter_submits_current_selection() -> None:
    future = FakeFuture()
    app = FakeKon(future)
    app._approval_selection = ApprovalResponse.DENY

    event = FakeKeyEvent("enter")
    Kon.on_key(app, event)  # type: ignore[arg-type]

    assert future.result() == ApprovalResponse.DENY
    assert event.prevented is True
    assert event.stopped is True
    assert app.cleared is True
