"""Shared domain constants — single source for DB enum, API, services, and AI tools."""

from __future__ import annotations

from enum import StrEnum


class ProductUnit(StrEnum):
    KG = "kg"
    G = "g"
    L = "L"
    ML = "mL"
    UNIT = "unit"


VALID_PRODUCT_UNITS = frozenset(u.value for u in ProductUnit)


def product_units_label() -> str:
    return ", ".join(u.value for u in ProductUnit)
