from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Deps:
    user_id: int
