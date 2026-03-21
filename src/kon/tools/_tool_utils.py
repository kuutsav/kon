import asyncio
from contextlib import suppress
from typing import TypeVar

T = TypeVar("T")


class ToolCancelledError(Exception):
    pass


async def await_task_or_cancel(work: asyncio.Task[T], cancel_event: asyncio.Event | None) -> T:
    if not cancel_event:
        return await work

    cancel = asyncio.create_task(cancel_event.wait())
    try:
        done, pending = await asyncio.wait([work, cancel], return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        if cancel in done and cancel_event.is_set():
            if not work.done():
                work.cancel()
                with suppress(asyncio.CancelledError):
                    await work
            raise ToolCancelledError

        return work.result()
    finally:
        if not cancel.done():
            cancel.cancel()
            with suppress(asyncio.CancelledError):
                await cancel


async def communicate_or_cancel(
    proc: asyncio.subprocess.Process, cancel_event: asyncio.Event | None
) -> tuple[bytes, bytes]:
    comm_task = asyncio.create_task(proc.communicate())
    if not cancel_event:
        return await comm_task

    cancel = asyncio.create_task(cancel_event.wait())
    try:
        done, pending = await asyncio.wait(
            [comm_task, cancel], return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        if cancel in done and cancel_event.is_set():
            if proc.returncode is None:
                with suppress(ProcessLookupError):
                    proc.kill()
                with suppress(ProcessLookupError):
                    await proc.wait()
            if not comm_task.done():
                comm_task.cancel()
                with suppress(asyncio.CancelledError):
                    await comm_task
            raise ToolCancelledError

        return comm_task.result()
    finally:
        if not cancel.done():
            cancel.cancel()
            with suppress(asyncio.CancelledError):
                await cancel


def truncate_lines_by_bytes(
    lines: list[str], max_output_bytes: int, marker: str = "[output truncated]"
) -> tuple[str, bool]:
    total_bytes = 0
    result_lines: list[str] = []

    for line in lines:
        line_bytes = len(line.encode("utf-8"))
        if total_bytes + line_bytes <= max_output_bytes:
            total_bytes += line_bytes
            result_lines.append(line)
        else:
            result_lines.append(marker)
            return "\n".join(result_lines), True

    return "\n".join(result_lines), False
