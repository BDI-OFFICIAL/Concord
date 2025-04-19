import asyncio
import logging
from typing import Callable, TypeVar

logger = logging.getLogger("Concord")
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

logger.propagate = True

QueueType = TypeVar("QueueType", bound=asyncio.Queue)


class AsyncRunner:
    def __init__(
            self,
            num_workers: int,
            tasks_per_worker: int,
            run_continuously: bool = True
    ):
        self.num_workers = num_workers
        self.tasks_per_worker = tasks_per_worker
        self.run_continuously = run_continuously

    async def _task_handler(self, function: Callable, *args, **kwargs):
        try:
            await function(*args, **kwargs)

        except Exception as e:
            logger.error(f"Task failure: {e.__class__.__name__}: {e}")

    async def _worker_loop(self, function: Callable, getter_function: Callable, *args, **kwargs):
        active_tasks = set()

        while True:
            try:
                while True:
                    while len(active_tasks) < self.tasks_per_worker:
                        try:
                            data = await getter_function()
                        except StopAsyncIteration:
                            return  # Exit worker when getter is done

                        task = asyncio.create_task(
                            self._task_handler(function=function, data=data, *args, **kwargs)
                        )

                        active_tasks.add(task)
                        task.add_done_callback(active_tasks.discard)

                    await asyncio.sleep(0.2)

            except Exception as e:
                logger.error(f"Worker loop failure: {e.__class__.__name__}: {e}")

    async def run(self, run_function: Callable, getter_function: Callable, *args, **kwargs):
        worker_tasks = [
            asyncio.create_task(
                self._worker_loop(run_function, getter_function, *args, **kwargs)
            ) for _ in range(self.num_workers)
        ]

        try:
            if self.run_continuously:
                return await asyncio.Future()

            return await asyncio.gather(*worker_tasks, return_exceptions=True)

        except asyncio.CancelledError:
            for worker in worker_tasks:
                worker.cancel()

            return await asyncio.gather(*worker_tasks, return_exceptions=True)
