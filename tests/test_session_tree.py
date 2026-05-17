from kon.core.types import AssistantMessage, StopReason, TextContent, UserMessage
from kon.session import LeafEntry, MessageEntry, Session


def test_tree_navigation_branches_without_overwriting(tmp_path, monkeypatch):
    monkeypatch.setattr(Session, "get_sessions_dir", staticmethod(lambda _cwd: tmp_path))
    session = Session.create(str(tmp_path), provider="openai", model_id="gpt-test")

    root_id = session.append_message(UserMessage(content="root"))
    session.append_message(
        AssistantMessage(content=[TextContent(text="root answer")], stop_reason=StopReason.STOP)
    )
    original_leaf = session.leaf_id

    session.move_to(root_id)
    branch_id = session.append_message(UserMessage(content="branch"))

    assert session.leaf_id == branch_id
    assert [m.content for m in session.messages if isinstance(m, UserMessage)] == [
        "root",
        "branch",
    ]
    assert session.get_entry(original_leaf) is not None
    assert len([e for e in session.all_entries if isinstance(e, MessageEntry)]) == 3


def test_leaf_navigation_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(Session, "get_sessions_dir", staticmethod(lambda _cwd: tmp_path))
    session = Session.create(str(tmp_path), provider="openai", model_id="gpt-test")
    root_id = session.append_message(UserMessage(content="root"))
    session.append_message(
        AssistantMessage(content=[TextContent(text="root answer")], stop_reason=StopReason.STOP)
    )
    session.move_to(root_id)
    session.ensure_persisted()

    loaded = Session.load(session.session_file)

    assert loaded.leaf_id == root_id
    assert [m.content for m in loaded.messages if isinstance(m, UserMessage)] == ["root"]
    assert any(isinstance(e, LeafEntry) for e in loaded.all_entries)
