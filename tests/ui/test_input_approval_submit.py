from kon.ui.input import InputBox


class FakeFuture:
    def __init__(self) -> None:
        self._done = False

    def done(self) -> bool:
        return self._done


class FakeApp:
    def __init__(self) -> None:
        self._approval_future = FakeFuture()
        self.keys: list[str] = []

    def on_key(self, event) -> None:
        self.keys.append(event.key)


class FakeInputBox:
    def __init__(self, text: str) -> None:
        self.app = FakeApp()
        self._is_completing = False
        self.text = text
        self.submitted = False

    def _do_submit(self, steer: bool = False) -> None:
        self.submitted = True


def test_empty_input_enter_forwards_to_pending_approval() -> None:
    input_box = FakeInputBox("")

    InputBox.action_submit(input_box)  # type: ignore[arg-type]

    assert input_box.app.keys == ["enter"]
    assert input_box.submitted is False


def test_nonempty_input_enter_does_not_forward_to_pending_approval() -> None:
    input_box = FakeInputBox("hello")

    InputBox.action_submit(input_box)  # type: ignore[arg-type]

    assert input_box.app.keys == []
    assert input_box.submitted is True
