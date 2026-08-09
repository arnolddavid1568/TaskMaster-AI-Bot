"""
Bounded async task queue for CPU/IO heavy operations (PDF merges, OCR,
image conversion, archive extraction, etc). Keeps the bot's event loop
free so incoming updates keep getting handled while big jobs run.

Usage:
    from utils.task_queue import task_queue
    await task_queue.submit(some_blocking_function, arg1, arg2)

`submit` runs blocking functions in a thread pool (via run_in_executor)
behind a semaphore that caps concurrency, and a queue that caps how much
work can be backlogged at once.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import config

logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self, max_concurrent: int = None, max_queue_size: int = None):
        self.max_concurrent = max_concurrent or config.MAX_CONCURRENT_TASKS
        self.max_queue_size = max_queue_size or config.MAX_QUEUE_SIZE
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._executor = ThreadPoolExecutor(max_workers=self.max_concurrent)
        self._in_flight = 0
        self._queued = 0

    @property
    def is_full(self) -> bool:
        return self._queued >= self.max_queue_size

    @property
    def status(self) -> str:
        return f"{self._in_flight} running / {self._queued} queued (max {self.max_concurrent} concurrent)"

    async def submit(self, func, *args, **kwargs):
        """Runs a blocking function off the event loop, respecting concurrency caps."""
        if self.is_full:
            raise RuntimeError("Task queue is full. Please try again in a moment.")

        self._queued += 1
        dequeued = False
        try:
            async with self._semaphore:
                self._queued -= 1
                dequeued = True
                self._in_flight += 1
                loop = asyncio.get_running_loop()
                try:
                    result = await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))
                    return result
                finally:
                    self._in_flight -= 1
        finally:
            if not dequeued:
                self._queued -= 1


task_queue = TaskQueue()
