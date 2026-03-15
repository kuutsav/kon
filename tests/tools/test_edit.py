import pytest

from kon.tools.edit import EditParams, EditTool


@pytest.fixture
def edit_tool():
    return EditTool()


@pytest.fixture
def text_file(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("line1\nline2\nline3\nline2\nline5")
    return f


@pytest.mark.asyncio
async def test_edit_single_replace(edit_tool, text_file):
    result = await edit_tool.execute(
        EditParams(path=str(text_file), old_string="line2", new_string="replaced")
    )
    assert result.success
    assert "+1" in result.result
    assert "-1" in result.result

    content = text_file.read_text()
    assert content == "line1\nreplaced\nline3\nline2\nline5"


@pytest.mark.asyncio
async def test_edit_replace_all(edit_tool, text_file):
    result = await edit_tool.execute(
        EditParams(
            path=str(text_file), old_string="line2", new_string="replaced", replace_all=True
        )
    )
    assert result.success
    assert "+2" in result.result
    assert "-2" in result.result

    content = text_file.read_text()
    assert content == "line1\nreplaced\nline3\nreplaced\nline5"


@pytest.mark.asyncio
async def test_edit_not_found(edit_tool, text_file):
    result = await edit_tool.execute(
        EditParams(path=str(text_file), old_string="nonexistent", new_string="replaced")
    )
    assert not result.success
    assert "not found" in result.result
    assert "not found" in result.display


@pytest.mark.asyncio
async def test_edit_file_not_found(edit_tool, tmp_path):
    result = await edit_tool.execute(
        EditParams(
            path=str(tmp_path / "nonexistent.py"), old_string="line1", new_string="replaced"
        )
    )
    assert not result.success
    assert "File not found" in result.result
    assert "File not found" in result.display


@pytest.mark.asyncio
async def test_edit_multiline(edit_tool, text_file):
    result = await edit_tool.execute(
        EditParams(path=str(text_file), old_string="line2\nline3", new_string="new2\nnew3\nnew4")
    )
    assert result.success

    content = text_file.read_text()
    assert content == "line1\nnew2\nnew3\nnew4\nline2\nline5"
