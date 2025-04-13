# concord
[![Python versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-green)](https://www.python.org/downloads/)

A simple but powerful wrapper around `curl_cffi` implementing async pool of tasks.

Just initialize `TaskPool` class, and you're ready to run()!

---

## Features

- **Asyncio-Friendly**: Built for seamless integration with Python's `asyncio` ecosystem.
- **Lightweight**: Minimal dependencies and straightforward API.
- **Simple**: Pass all arguments and run().

---

## Installation

Install the package via pip:

```bash
pip install https://github.com/BDI-OFFICIAL/concord/archive/refs/heads/main.zip
```

---

## Usage Example
Here’s an examples of how to use the library.

### Example 1
Run the queue and wait for tasks to finish.

`run_continuously=False`

```python
import asyncio

from concord import TaskPool
from curl_cffi import AsyncSession


async def your_function(link_from_queue: str, session: AsyncSession):
    # Here you write you code that will use curl_cffi and data from queue
    # You can pass any data you want as the first argument.
    # If you need to pass more arguments than one - you can pass Tuple and unpack it.
    response = await session.get(link_from_queue)
    print(response.text)


async def example():
    some_queue = asyncio.Queue()

    for n in range(100):
        await some_queue.put("localhost:8000")

    task_pool = TaskPool(
        task_queue=some_queue, num_workers=5, tasks_per_worker=10, run_continuously=False
    )

    await task_pool.run(your_function)


if __name__ == '__main__':
    asyncio.run(example())
```

### Example 2
Process data while program is running.

`run_continuously=True`

```python
import asyncio
from datetime import datetime

from concord import TaskPool
from curl_cffi import AsyncSession


async def your_function(link_from_queue: str, session: AsyncSession):
    # Here you write you code that will use curl_cffi and data from queue
    # You can pass any data you want as the first argument.
    # If you need to pass more arguments than one - you can pass Tuple and unpack it.
    response = await session.get(link_from_queue)
    print(response.text)


async def add_data_to_queue(queue: asyncio.Queue):
    while True:
        await queue.put(f"localhost:8000/{datetime.now().timestamp()}")
        await asyncio.sleep(1)


async def example():
    some_queue = asyncio.Queue()

    task_pool = TaskPool(
        task_queue=some_queue, num_workers=5, tasks_per_worker=10, run_continuously=True  # it's a default setting
    )

    # This blocks execution of the program.
    # You might want to put all your async code in the asyncio.gather() to run alongside each other
    await asyncio.gather(
        await add_data_to_queue(some_queue),
        await task_pool.run(your_function)
    )


if __name__ == '__main__':
    asyncio.run(example())
```


### Configuration
The `TaskPool` class accepts the following parameters:

- `task_queue`: An asyncio queue containing the data to be processed
- `num_workers`: The number of worker instances.
- `tasks_per_worker`: The number of concurrent tasks each worker will run
- `session_params`: A dictionary of additional keyword arguments for curl_cffi's AsyncSession.
- `run_continuously`: A flag that controls whether TaskPool wait for new tasks indefinitely or shuts down.

---

## License
This project is licensed under the MIT License.