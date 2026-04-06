import asyncio

import pytest

from kon.tools.bash import BashParams, BashTool
from kon.tools.read import ReadParams, ReadTool


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.killed = False
        self.wait_called = False
        self.communicate_done = asyncio.Event()
        self.wait_started = asyncio.Event()
        self.communicate_started = asyncio.Event()

    async def communicate(self):
        self.communicate_started.set()
        await self.communicate_done.wait()
        self.returncode = -9
        return b"", b""

    def kill(self):
        self.killed = True
        self.returncode = -9
        self.communicate_done.set()

    async def wait(self):
        self.wait_called = True
        self.wait_started.set()
        await self.communicate_done.wait()
        self.returncode = -9
        return self.returncode


@pytest.mark.asyncio
async def test_read_directory_cancellation_waits_for_communicate_cleanup(tmp_path, monkeypatch):
    proc = FakeProcess()
    read_tool = ReadTool()

    async def mock_create_subprocess_exec(*args, **kwargs):
        return proc

    async def mock_ensure_tool(tool, silent=False):
        return "fd"

    monkeypatch.setattr("kon.tools.read.ensure_tool", mock_ensure_tool)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_create_subprocess_exec)

    cancel_event = asyncio.Event()
    cancel_event.set()

    result = await read_tool.execute(ReadParams(path=str(tmp_path)), cancel_event=cancel_event)

    assert result.success is False
    assert result.result == "Read aborted"
    assert proc.killed is True
    assert proc.wait_called is True
    assert proc.communicate_done.is_set() is True


@pytest.mark.asyncio
async def test_bash_cancellation_waits_for_communicate_cleanup(monkeypatch):
    proc = FakeProcess()
    bash_tool = BashTool()

    async def mock_create_subprocess_shell(*args, **kwargs):
        return proc

    async def mock_kill_process_tree(process):
        process.kill()
        await process.wait()

    monkeypatch.setattr(asyncio, "create_subprocess_shell", mock_create_subprocess_shell)
    monkeypatch.setattr("kon.tools.bash._kill_process_tree", mock_kill_process_tree)

    cancel_event = asyncio.Event()
    cancel_event.set()

    result = await bash_tool.execute(BashParams(command="sleep 10"), cancel_event=cancel_event)

    assert result.success is False
    assert result.result == "Command aborted"
    assert proc.killed is True
    assert proc.wait_called is True
    assert proc.communicate_done.is_set() is True
