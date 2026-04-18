from kon.core.types import (
    AssistantMessage,
    FileChanges,
    TextContent,
    ToolCall,
    ToolResultMessage,
    Usage,
    UserMessage,
)
from kon.session import Session


def test_session_token_totals_file_changes_and_message_counts() -> None:
    session = Session.in_memory()
    session.append_message(UserMessage(content="hello"))
    session.append_message(
        AssistantMessage(
            content=[ToolCall(id="t1", name="read", arguments={"path": "a.txt"})],
            usage=Usage(
                input_tokens=100, output_tokens=50, cache_read_tokens=10, cache_write_tokens=5
            ),
        )
    )
    session.append_message(
        ToolResultMessage(
            tool_call_id="t1",
            tool_name="read",
            content=[TextContent(text="content")],
            file_changes=FileChanges(path="a.txt", added=3, removed=1),
        )
    )
    session.append_message(
        AssistantMessage(
            content=[TextContent(text="done")],
            usage=Usage(
                input_tokens=20, output_tokens=30, cache_read_tokens=0, cache_write_tokens=2
            ),
        )
    )

    totals = session.token_totals()
    assert totals.input_tokens == 120
    assert totals.output_tokens == 80
    assert totals.cache_read_tokens == 10
    assert totals.cache_write_tokens == 7
    assert totals.context_tokens == 52
    assert totals.total_tokens == 217

    assert session.file_changes_summary() == {"a.txt": (3, 1)}

    counts = session.message_counts()
    assert counts.user_messages == 1
    assert counts.assistant_messages == 2
    assert counts.tool_calls == 1
    assert counts.tool_results == 1
    assert counts.total_messages == 3


def test_session_created_at_is_exposed() -> None:
    session = Session.in_memory()
    assert session.created_at is not None
