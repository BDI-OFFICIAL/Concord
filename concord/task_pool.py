import asyncio
import logging
from typing import Callable, Dict, Optional

from curl_cffi import AsyncSession

logger = logging.getLogger("Concord")


class TaskPool:
    def __init__(
            self,
            task_queue: asyncio.Queue,
            num_workers: int,
            tasks_per_worker: int,
            session_params: Optional[Dict] = None,
            run_continuously: bool = True,

    ):
        """
        TaskPool is designed to execute a user-specified function concurrently using asynchronous requests,
        using curl_cffi's AsyncSession. It manages multiple workers and tasks per worker.

        The pool allows you to pass a queue of data (arguments) that will be processed by a number of workers.
        Each worker creates a single AsyncSession instance and runs multiple concurrent tasks using that session.
        The total amount of concurrent requests is determined by (workers * tasks_per_worker).
        For example, 5 workers and 10 tasks per worker will result in your app sending not more than 50 requests at once.

        You can also provide custom parameters to configure the curl_cffi's AsyncSession
        (for example, timeout, impersonate settings, proxy configurations, etc.) via the `session_params` parameter.

        Args:
            task_queue (asyncio.Queue):
                An asyncio queue containing the data to be processed by the user-defined function.
            num_workers (int):
                The number of worker instances to run. Each worker creates one AsyncSession instance.
            tasks_per_worker (int):
                The number of concurrent tasks each worker will run.
                Total concurrent requests = num_workers * tasks_per_worker.
            session_params (Optional[Dict]):
                A dictionary of additional keyword arguments to pass to the AsyncSession constructor.
                This allows customization of session behavior (e.g., passing proxy settings, custom timeout, etc.).
                Defaults to None which means the session will use the built-in reasonable defaults.
            run_continuously (bool):
                A flag that controls how TaskPool handles Queue exhaustion. If set to False, it will gracefully
                shut down all tasks and exit. Otherwise, when set to the default value of True - will process them,
                blocking execution of the code after the "run" function.

        Note:
            - Start with lower num_workers and tasks_per_worker counts
            (e.g., 5 workers and 10 tasks_per_worker) and gradually tune for your needs.
            - Ensure that your processing function accepts element from queue as its first parameter.
            - Ensure that your processing function accepts an AsyncSession instance as its second parameter.
        """
        self.task_queue = task_queue
        self.num_workers = num_workers
        self.tasks_per_worker = tasks_per_worker
        self.session_params = session_params
        self.run_continuously = run_continuously

    async def _task_handler(self, function: Callable, session: AsyncSession, *args, **kwargs):
        data = await self.task_queue.get()

        try:
            await function(data, session, *args, **kwargs)

        except Exception as e:
            logger.error(f"Task failure: {e.__class__.__name__}: {e}")

        finally:
            self.task_queue.task_done()

    async def _worker_loop(self, function: Callable, *args, **kwargs):
        active_tasks = set()

        session_params = self.session_params or {"timeout": 30, "impersonate": "chrome"}

        while True:
            try:
                async with AsyncSession(**session_params) as session:
                    while True:
                        while len(active_tasks) < self.tasks_per_worker:
                            task = asyncio.create_task(
                                self._task_handler(function=function, session=session, *args, **kwargs)
                            )

                            active_tasks.add(task)

                            task.add_done_callback(active_tasks.discard)

                        await asyncio.sleep(0.2)

            except Exception as e:
                logger.error(f"Worker loop failure: {e.__class__.__name__}: {e}")

                for thread in active_tasks:
                    thread.cancel()

    async def run(self, function: Callable):
        """
        Starts the task pool with the specified user function.

        If `self.run_continuously` is True, the process will run indefinitely until externally canceled.
        Otherwise, it will wait until all tasks in the queue are processed before shutting down.

        Args:
            function (Callable):
                The user-provided function to execute on each task. This function must accept at least two arguments:
                the data from the queue and an AsyncSession instance.
        """
        worker_tasks = [
            asyncio.create_task(self._worker_loop(function)) for _ in range(self.num_workers)
        ]

        try:
            if self.run_continuously:
                await asyncio.Future()
            else:
                await self.task_queue.join()
                for worker in worker_tasks:
                    worker.cancel()
                await asyncio.gather(*worker_tasks, return_exceptions=True)

        except asyncio.CancelledError:
            for worker in worker_tasks:
                worker.cancel()
            await asyncio.gather(*worker_tasks, return_exceptions=True)
