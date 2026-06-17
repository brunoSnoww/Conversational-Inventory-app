from __future__ import annotations

import uuid
from decimal import Decimal

from ai.idempotency import tool_guid


def test_tool_guid_stable_for_same_inputs():
    a = tool_guid(42, "create_purchase_order", sku="CB-01", quantity=Decimal("100"), total_cost=Decimal("200"))
    b = tool_guid(42, "create_purchase_order", sku="CB-01", quantity=Decimal("100"), total_cost=Decimal("200"))
    assert a == b
    assert isinstance(a, uuid.UUID)


def test_tool_guid_differs_by_tool_or_args():
    base = tool_guid(42, "create_purchase_order", sku="CB-01", quantity=Decimal("100"), total_cost=Decimal("200"))
    other_tool = tool_guid(42, "record_sale", sku="CB-01", quantity=Decimal("100"), total_cost=Decimal("200"))
    other_qty = tool_guid(42, "create_purchase_order", sku="CB-01", quantity=Decimal("50"), total_cost=Decimal("200"))
    other_turn = tool_guid(99, "create_purchase_order", sku="CB-01", quantity=Decimal("100"), total_cost=Decimal("200"))
    assert base != other_tool
    assert base != other_qty
    assert base != other_turn


def test_tool_guid_none_without_chat_message_id():
    assert tool_guid(None, "record_sale", sku="A", quantity=Decimal("1"), unit_price=Decimal("2")) is None
