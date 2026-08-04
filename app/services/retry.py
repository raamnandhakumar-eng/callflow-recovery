import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def with_retry(
    operation: Callable[[], Awaitable[T]], retries: int, base_delay_seconds: float = 0.15
) -> T:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await operation()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= retries:
                break
            await asyncio.sleep(base_delay_seconds * (2**attempt))
    assert last_error is not None
    raise last_error
