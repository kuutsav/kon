import json

import pytest

from kon.core.types import (
    AssistantMessage,
    StopReason,
    TextContent,
    ThinkingContent,
    ToolCall,
    Usage,
    UserMessage,
)
from kon.session import (
    CompactionEntry,
    CustomMessageEntry,
    MessageEntry,
    ModelChangeEntry,
    Session,
    SessionInfoEntry,
    ThinkingLevelChangeEntry,
)


@pytest.fixture
def user_message():
    return UserMessage(content="Hello, how are you?")


@pytest.fixture
def assistant_message():
    return AssistantMessage(
        content=[TextContent(text="I'm doing well, thanks!")],
        usage=Usage(input_tokens=10, output_tokens=5),
        stop_reason=StopReason.STOP,
    )


@pytest.fixture
def thinking_message():
    return AssistantMessage(
        content=[
            ThinkingContent(thinking="Let me think about this...", signature=None),
            TextContent(text="Here's my answer."),
        ],
        usage=Usage(input_tokens=10, output_tokens=15),
        stop_reason=StopReason.STOP,
    )


def test_round_trip_basic_messages(tmp_path, user_message, assistant_message, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    # Create session
    session = Session.create("/test/project")

    # Append messages
    msg1_id = session.append_message(user_message)
    msg2_id = session.append_message(assistant_message)

    assert msg1_id != msg2_id
    assert session.leaf_id == msg2_id

    # Save to disk (should happen automatically)
    assert session.session_file is not None
    assert session.session_file.exists()

    # Load session
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)

    # Verify session metadata
    assert loaded_session.id == session.id
    assert loaded_session.cwd == session.cwd

    # Verify messages
    assert len(loaded_session.messages) == 2
    assert loaded_session.messages[0].content == user_message.content
    assert loaded_session.messages[1].content == assistant_message.content
    # Type narrowing for AssistantMessage
    assert isinstance(loaded_session.messages[1], AssistantMessage)
    assert loaded_session.messages[1].usage is not None
    assert loaded_session.messages[1].usage.input_tokens == 10
    assert loaded_session.messages[1].usage.output_tokens == 5
    assert loaded_session.messages[1].stop_reason == StopReason.STOP


def test_round_trip_with_thinking(tmp_path, thinking_message, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")
    session.append_message(thinking_message)

    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)

    assert len(loaded_session.messages) == 1
    content = loaded_session.messages[0].content
    assert len(content) == 2
    assert isinstance(content[0], ThinkingContent)
    assert content[0].thinking == "Let me think about this..."
    assert isinstance(content[1], TextContent)


def test_round_trip_all_entry_types(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")

    # Add various entry types
    msg_id = session.append_message(UserMessage(content="Test message"))
    session.append_thinking_level_change("high")
    session.append_model_change("openai", "gpt-4")
    session.append_compaction(
        summary="Compacted session",
        first_kept_entry_id=msg_id,
        tokens_before=1000,
        details={"removed": 5},
    )
    session.append_custom_message("error", "Something went wrong")
    info_id = session.append_session_info("My Test Session")
    # Add assistant message to trigger persistence
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    # Verify in-memory state
    assert len(session.entries) == 7
    assert session.leaf_id != info_id  # Assistant message is now the leaf

    # Load and verify
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)

    assert len(loaded_session.entries) == 7

    # Check each entry type
    entries = loaded_session.entries
    assert isinstance(entries[0], MessageEntry)
    assert isinstance(entries[1], ThinkingLevelChangeEntry)
    assert entries[1].thinking_level == "high"
    assert isinstance(entries[2], ModelChangeEntry)
    assert entries[2].provider == "openai"
    assert entries[2].model_id == "gpt-4"
    assert isinstance(entries[3], CompactionEntry)
    assert entries[3].summary == "Compacted session"
    assert entries[3].tokens_before == 1000
    assert entries[3].details == {"removed": 5}
    assert isinstance(entries[4], CustomMessageEntry)
    assert entries[4].custom_type == "error"
    assert entries[4].content == "Something went wrong"
    assert isinstance(entries[5], SessionInfoEntry)
    assert entries[5].name == "My Test Session"
    assert isinstance(entries[6], MessageEntry)
    assert entries[6].message.role == "assistant"


def test_round_trip_parent_id_linking(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")

    # Add messages and verify parent linking
    msg1_id = session.append_message(UserMessage(content="First"))
    msg2_id = session.append_message(AssistantMessage(content=[TextContent(text="Second")]))
    session.append_message(UserMessage(content="Third"))

    # Check parent relationships
    entries = session.entries
    assert entries[0].parent_id is None  # First message has no parent
    assert entries[1].parent_id == msg1_id
    assert entries[2].parent_id == msg2_id

    # Load and verify
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)

    loaded_entries = loaded_session.entries
    assert loaded_entries[0].parent_id is None
    assert loaded_entries[1].parent_id == msg1_id
    assert loaded_entries[2].parent_id == msg2_id


def test_round_trip_session_properties(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create(
        "/test/project", provider="anthropic", model_id="claude-3-opus", thinking_level="high"
    )

    # Check initial values
    assert session.model == ("anthropic", "claude-3-opus", None)
    assert session.thinking_level == "high"
    assert session.name is None

    # Change values
    session.set_model("openai", "gpt-4")
    session.set_thinking_level("low")
    session.append_session_info("Test Session")

    # Append messages to ensure persistence (need assistant message)
    session.append_message(UserMessage(content="Hello"))
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    # Load and verify
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)

    assert loaded_session.model == ("openai", "gpt-4", None)
    assert loaded_session.thinking_level == "low"
    assert loaded_session.name == "Test Session"


def test_round_trip_get_entry_by_id(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")

    msg1_id = session.append_message(UserMessage(content="First"))
    msg2_id = session.append_message(UserMessage(content="Second"))
    # Add assistant message to trigger persistence
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    # Load session
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)

    # Verify retrieval
    entry1 = loaded_session.get_entry(msg1_id)
    entry2 = loaded_session.get_entry(msg2_id)

    assert entry1 is not None
    assert isinstance(entry1, MessageEntry)
    assert entry1.message.content == "First"

    assert entry2 is not None
    assert isinstance(entry2, MessageEntry)
    assert entry2.message.content == "Second"


def test_round_trip_no_persistence_mode(tmp_path, monkeypatch):
    session = Session.create("/test/project", persist=False)

    session.append_message(UserMessage(content="Test"))

    # No file should be created
    assert session.session_file is None

    # Session should still have data in memory
    assert len(session.messages) == 1
    assert session.messages[0].content == "Test"


def test_round_trip_empty_session(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")

    # Empty session shouldn't persist (no assistant message)
    assert session.session_file is not None
    assert not session.session_file.exists()

    # Add a message and check persistence
    session.append_message(UserMessage(content="Test"))
    # Still shouldn't persist (no assistant message yet)
    assert not session.session_file.exists()

    # Add assistant message to trigger persistence
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))
    assert session.session_file.exists()

    # Load and verify
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)
    assert len(loaded_session.messages) == 2


def test_round_trip_multiple_messages(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")

    # Add 100 messages
    for i in range(50):
        session.append_message(UserMessage(content=f"User message {i}"))
        session.append_message(
            AssistantMessage(content=[TextContent(text=f"Assistant response {i}")])
        )

    assert len(session.messages) == 100

    # Load and verify all messages
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)

    assert len(loaded_session.messages) == 100
    for i in range(50):
        assert loaded_session.messages[i * 2].content == f"User message {i}"
        assert loaded_session.messages[i * 2 + 1].content == [
            TextContent(text=f"Assistant response {i}")
        ]


def test_round_trip_with_tool_calls(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")

    # Add assistant message with tool call
    tool_call = ToolCall(id="tool-123", name="bash", arguments={"command": "ls -la"})
    msg = AssistantMessage(
        content=[TextContent(text="I'll list the files:"), tool_call],
        usage=Usage(input_tokens=5, output_tokens=10),
    )
    session.append_message(msg)

    # Load and verify
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)

    assert len(loaded_session.messages) == 1
    content = loaded_session.messages[0].content
    assert len(content) == 2
    assert isinstance(content[0], TextContent)
    assert content[0].text == "I'll list the files:"
    assert isinstance(content[1], ToolCall)
    assert content[1].id == "tool-123"
    assert content[1].name == "bash"
    assert content[1].arguments == {"command": "ls -la"}


def test_round_trip_session_file_format(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")

    session.append_message(UserMessage(content="Test"))
    session.append_thinking_level_change("high")
    # Add assistant message to trigger persistence
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    # Read file directly
    assert session.session_file is not None
    with open(session.session_file) as f:
        lines = f.readlines()

    # Verify file structure (header + 3 entries)
    assert len(lines) == 4

    # Parse first line should be header
    header_data = json.loads(lines[0])
    assert header_data["type"] == "header"
    assert "id" in header_data
    assert "timestamp" in header_data

    # Remaining lines should be entries
    for line in lines[1:]:
        data = json.loads(line)
        assert "type" in data
        assert "id" in data
        assert "timestamp" in data


def test_round_trip_unique_entry_ids(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")

    ids = []
    for i in range(10):
        msg_id = session.append_message(UserMessage(content=f"Message {i}"))
        ids.append(msg_id)
    # Add assistant message to trigger persistence
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    # All IDs should be unique
    assert len(set(ids)) == 10

    # Load and verify IDs match
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)

    loaded_ids = [e.id for e in loaded_session.entries]
    # We have 11 entries (10 user messages + 1 assistant message)
    assert len(loaded_ids) == 11
    # First 10 should match our user messages
    assert loaded_ids[:10] == ids


def test_round_trip_mixed_content_types(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")

    # User message with simple text
    session.append_message(UserMessage(content="Simple text"))

    # Assistant with thinking + text + tool call
    tool_call = ToolCall(id="tool-1", name="read", arguments={"path": "file.txt"})
    session.append_message(
        AssistantMessage(
            content=[
                ThinkingContent(thinking="I need to read the file"),
                TextContent(text="I'll read the file for you."),
                tool_call,
            ],
            usage=Usage(input_tokens=5, output_tokens=15),
        )
    )

    # Load and verify
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)

    assert len(loaded_session.messages) == 2

    # First message
    assert loaded_session.messages[0].content == "Simple text"

    # Second message
    content = loaded_session.messages[1].content
    assert len(content) == 3
    assert isinstance(content[0], ThinkingContent)
    assert isinstance(content[1], TextContent)
    assert isinstance(content[2], ToolCall)


def test_round_trip_session_info_property(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")

    # Add initial name
    session.append_session_info("First Name")
    assert session.name == "First Name"

    # Change name
    session.append_session_info("Second Name")
    assert session.name == "Second Name"

    # Add assistant message to trigger persistence
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    # Load and verify last name wins
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)
    assert loaded_session.name == "Second Name"


def test_round_trip_model_property_changes(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project", provider="openai", model_id="gpt-3.5")

    assert session.model == ("openai", "gpt-3.5", None)

    session.set_model("anthropic", "claude-3")
    assert session.model == ("anthropic", "claude-3", None)

    session.set_model("google", "gemini-pro")
    assert session.model == ("google", "gemini-pro", None)

    # Add assistant message to trigger persistence
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    # Load and verify latest model
    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)
    assert loaded_session.model == ("google", "gemini-pro", None)


def test_round_trip_model_base_url_persistence(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project", provider="openai", model_id="gpt-3.5")
    session.append_model_change("openai", "custom-model", "http://localhost:8080/v1")
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    assert session.model == ("openai", "custom-model", "http://localhost:8080/v1")

    assert session.session_file is not None
    loaded_session = Session.load(session.session_file)
    assert loaded_session.model == ("openai", "custom-model", "http://localhost:8080/v1")


def test_get_last_assistant_text_ignores_thinking_and_tools():
    session = Session.in_memory("/test/project")
    session.append_message(UserMessage(content="Hello"))
    session.append_message(
        AssistantMessage(
            content=[
                ThinkingContent(thinking="Reasoning..."),
                TextContent(text="Final answer"),
                ToolCall(id="tool-1", name="bash", arguments={"command": "pwd"}),
            ]
        )
    )

    assert session.get_last_assistant_text() == "Final answer"


def test_get_last_assistant_text_returns_none_when_latest_has_no_text():
    session = Session.in_memory("/test/project")
    session.append_message(AssistantMessage(content=[ThinkingContent(thinking="Only thinking")]))

    assert session.get_last_assistant_text() is None


def test_continue_by_id_exact_match(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    resumed = Session.continue_by_id("/test/project", session.id)
    assert resumed.id == session.id


def test_continue_by_id_unique_prefix_match(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    prefix = session.id[:8]
    resumed = Session.continue_by_id("/test/project", prefix)
    assert resumed.id == session.id


def test_continue_by_id_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("kon.session.Session.get_sessions_dir", lambda cwd: tmp_path)

    session = Session.create("/test/project")
    session.append_message(AssistantMessage(content=[TextContent(text="Response")]))

    with pytest.raises(FileNotFoundError):
        Session.continue_by_id("/test/project", "does-not-exist")
