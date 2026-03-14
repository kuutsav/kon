import pytest

from kon import reset_config


class FakeChat:
    """Reusable minimal chat sink for UI tests."""

    def __init__(self) -> None:
        self.compaction_tokens: int | None = None
        self.errors: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.statuses: list[str] = []
        self.versions: list[str] = []

    def add_compaction_message(self, tokens_before: int) -> None:
        self.compaction_tokens = tokens_before

    def add_info_message(self, message: str, error: bool = False, warning: bool = False) -> None:
        if error:
            self.errors.append(message)
        elif warning:
            self.warnings.append(message)
        else:
            self.infos.append(message)

    def add_update_available_message(self, latest_version: str) -> None:
        self.versions.append(latest_version)

    def show_status(self, message: str) -> None:
        self.statuses.append(message)


@pytest.fixture
def fake_chat() -> FakeChat:
    return FakeChat()


def pytest_runtest_teardown(item, nextitem):
    reset_config()
