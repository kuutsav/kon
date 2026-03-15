import pytest

from kon.core.types import ToolResult
from kon.tools.bash import BashTool
from kon.tools.read import ReadParams, ReadTool


@pytest.fixture
def read_tool():
    return ReadTool()


@pytest.fixture
def text_file(tmp_path):
    f = tmp_path / "index.py"
    f.write_text("line1\nline2\nline3\nlong-line-number-4\nline-5\nline-6")
    return f


@pytest.mark.asyncio
async def test_read(read_tool, text_file, monkeypatch):
    monkeypatch.setattr("kon.tools.read.MAX_LINES_PER_FILE", 5)
    monkeypatch.setattr("kon.tools.read.MAX_CHARS_PER_LINE", 10)

    tool_result = await read_tool.execute(ReadParams(path=str(text_file)))
    lines = tool_result.result.split("\n")
    assert len(lines) == 6  # 5 lines + truncation
    assert lines[0] == "     1\tline1"
    assert lines[3] == "     4\tlong-line- [output truncated after 10 chars]"
    assert lines[-1] == "[output truncated after 5 lines]"

    tool_result = await read_tool.execute(ReadParams(path=str(text_file), offset=2, limit=3))
    lines = tool_result.result.split("\n")
    assert len(lines) == 4  # 3 lines + trailing ""
    assert lines[0] == "     2\tline2"
    assert lines[2] == "     4\tlong-line- [output truncated after 10 chars]"


@pytest.mark.asyncio
async def test_read_path_not_found(read_tool, tmp_path):
    result = await read_tool.execute(ReadParams(path=str(tmp_path / "nonexistent.txt")))
    assert not result.success
    assert "Path not found" in result.result
    assert "Path not found" in result.display


@pytest.mark.asyncio
async def test_read_not_a_file(read_tool, tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "somefile").write_text("x")
    # Symlink pointing to a dir is still not a file; but simplest: use a FIFO
    import os

    fifo_path = tmp_path / "myfifo"
    os.mkfifo(fifo_path)
    result = await read_tool.execute(ReadParams(path=str(fifo_path)))
    assert not result.success
    assert "Path is not a file" in result.result
    assert "Path is not a file" in result.display


@pytest.mark.asyncio
async def test_read_directory_runs_ls_and_appends_warning(read_tool, tmp_path, monkeypatch):
    called = {}

    async def mock_execute(self, params, cancel_event=None):
        called["command"] = params.command
        return ToolResult(success=True, result="total 0", display="[dim]total 0[/dim]")

    monkeypatch.setattr(BashTool, "execute", mock_execute)

    tool_result = await read_tool.execute(ReadParams(path=str(tmp_path)))

    assert called["command"] == f"ls -la {tmp_path}"
    assert tool_result.success is True
    assert tool_result.result == (
        "total 0\n\nWARNING: read tool is only supposed to be used for file reads; "
        "for listing dirs, used bash ls tool"
    )
