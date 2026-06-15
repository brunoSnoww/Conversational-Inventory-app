"""Shared domain constants — single source for DB enum, API, services, and AI tools."""

from __future__ import annotations

from django.db import models


class ProductUnit(models.TextChoices):
    KG = "kg", "kg"
    G = "g", "g"
    L = "L", "L"
    ML = "mL", "mL"
    UNIT = "unit", "unit"


VALID_PRODUCT_UNITS = frozenset(ProductUnit.values)


def product_units_label() -> str:
    return ", ".join(ProductUnit.values)
