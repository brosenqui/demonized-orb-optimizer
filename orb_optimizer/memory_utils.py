"""Memory management utilities for the Orb Optimizer."""

from __future__ import annotations

import gc
import functools
import psutil
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def monitor_memory(
    memory_limit_mb: int = 1024,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to monitor memory usage and force cleanup if needed.

    Args:
        memory_limit_mb: Memory limit in MB before forcing garbage collection
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            process = psutil.Process()
            if process.memory_info().rss > memory_limit_mb * 1024 * 1024:
                gc.collect()
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_memory_usage_mb() -> float:
    """Get current memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)
