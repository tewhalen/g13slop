"""Helper functions and classes for async operations."""

import asyncio
import contextlib
import typing


async def run_periodic(callback, interval_ms: int, *, initial_delay_ms: int = 0):
    """Run a callback periodically at the specified interval in milliseconds."""
    loop = asyncio.get_running_loop()
    if initial_delay_ms:
        await asyncio.sleep(initial_delay_ms / 1000.0)
    next_at = loop.time()
    step = interval_ms / 1000.0
    try:
        while True:
            next_at += step
            await asyncio.sleep(max(0.0, next_at - loop.time()))
            await callback()
    except asyncio.CancelledError:
        return


class PeriodicComponent:
    """Mix-in class for components that need to run periodic tasks."""

    _tasks_to_start: list[typing.Coroutine]
    _tasks: list[asyncio.Task]

    def start_tasks(self, tg: asyncio.TaskGroup):
        """Start any periodic tasks needed by this component."""
        # the tasks will be added to _tasks by __init__
        # this needs to kick them off and add them to the provided TaskGroup
        started_tasks = []
        for task in self._tasks_to_start:
            new_task = tg.create_task(task)
            started_tasks.append(new_task)
        self._tasks = started_tasks

    async def stop_tasks(self):
        """Stop any periodic tasks needed by this component."""
        for task in self._tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks = []
