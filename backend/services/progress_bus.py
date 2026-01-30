import asyncio
import json
from typing import Dict, AsyncGenerator


class ProgressBus:
    def __init__(self) -> None:
        self._queues: Dict[str, asyncio.Queue] = {}

    def _queue(self, task_id: str) -> asyncio.Queue:
        if task_id not in self._queues:
            self._queues[task_id] = asyncio.Queue()
        return self._queues[task_id]

    async def publish(self, task_id: str, payload: Dict) -> None:
        q = self._queue(task_id)
        await q.put(payload)

    async def subscribe(self, task_id: str) -> AsyncGenerator[str, None]:
        q = self._queue(task_id)
        try:
            while True:
                item = await q.get()
                data = json.dumps(item, default=str)
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            return


progress_bus = ProgressBus()

