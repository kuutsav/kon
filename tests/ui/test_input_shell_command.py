from kon.ui.input import InputBox


class _FakeSelection:
    def __init__(self, row: int, col: int) -> None:
        self.end = (row, col)


class _FakeTextArea:
    def __init__(self, text: str) -> None:
        self.text = text
        self.cleared = False
        self.selection = _FakeSelection(0, len(text))

    def clear(self) -> None:
        self.text = ""
        self.cleared = True
        self.selection = _FakeSelection(0, 0)

    def insert(self, text: str) -> None:
        row, col = self.selection.end
        if row != 0:
            row = 0
            col = len(self.text)
        self.text = self.text[:col] + text + self.text[col:]
        self.selection = _FakeSelection(0, col + len(text))


class _TestableInputBox(InputBox):
    def __init__(self, text: str = "") -> None:
        super().__init__(cwd="/tmp")
        self._fake_textarea = _FakeTextArea(text)
        self.posted_messages: list[InputBox.Submitted] = []

    def query_one(self, *args, **kwargs):  # type: ignore[override]
        return self._fake_textarea

    def post_message(self, message: InputBox.Submitted):  # type: ignore[override]
        self.posted_messages.append(message)


def test_detect_shell_command_with_valid_command():
    input_box = _TestableInputBox()

    # Test with a valid shell command
    command, add_to_history = input_box._detect_shell_command("!ls -la")
    assert command == "ls -la"
    assert add_to_history is False


def test_detect_shell_command_with_empty_command():
    input_box = _TestableInputBox()

    # Test with empty command after !
    command, add_to_history = input_box._detect_shell_command("!")
    assert command == ""
    assert add_to_history is False


def test_detect_shell_command_with_whitespace():
    input_box = _TestableInputBox()

    # Test with command that has leading/trailing whitespace
    command, _ = input_box._detect_shell_command("!  echo hello  ")
    assert command == "echo hello"


def test_detect_shell_command_without_exclamation():
    input_box = _TestableInputBox()

    # Test with text that doesn't start with !
    command, _ = input_box._detect_shell_command("echo hello")
    assert command is None


def test_detect_shell_command_with_complex_command():
    input_box = _TestableInputBox()

    # Test with a more complex shell command
    command, add_to_history = input_box._detect_shell_command(
        "!!grep -r 'pattern' /path/to/dir | wc -l"
    )
    assert command == "grep -r 'pattern' /path/to/dir | wc -l"
    assert add_to_history is True


def test_submit_shell_command_posts_correct_message():
    input_box = _TestableInputBox("!ls -la")

    input_box._do_submit()

    assert len(input_box.posted_messages) == 1
    message = input_box.posted_messages[0]
    assert message.text == "!ls -la"
    assert message.shell_cmd == "ls -la"
    assert message.steer is False
    assert input_box._fake_textarea.cleared is True


def test_submit_normal_text_when_no_shell_command():
    input_box = _TestableInputBox("hello world")

    input_box._do_submit()

    assert len(input_box.posted_messages) == 1
    message = input_box.posted_messages[0]
    assert message.text == "hello world"
    assert message.shell_cmd is None
    assert message.steer is False


def test_submit_empty_text_does_nothing():
    input_box = _TestableInputBox("")

    input_box._do_submit()

    assert len(input_box.posted_messages) == 0


def test_submit_shell_command_with_steer():
    input_box = _TestableInputBox("!echo test")

    # Simulate steer submission
    input_box._do_submit(steer=True)

    assert len(input_box.posted_messages) == 1
    message = input_box.posted_messages[0]
    assert message.text == "!echo test"
    assert message.shell_cmd == "echo test"
    assert message.steer is True
