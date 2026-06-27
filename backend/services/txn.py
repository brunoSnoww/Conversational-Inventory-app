from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

from app.db.session import transaction

T = TypeVar("T")


def atomic(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        with transaction():
            return func(*args, **kwargs)

    return wrapper
