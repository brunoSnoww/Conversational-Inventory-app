"""Unmanaged models — Goose owns schema."""

from __future__ import annotations

from django.db import models

from inventory_api.constants import ProductUnit

__all__ = ["ProductUnit", "StockMovementSource", "ChatMessageRole"]


class StockMovementSource(models.TextChoices):
    PURCHASE_ORDER = "PURCHASE_ORDER", "PURCHASE_ORDER"
    SALES_ORDER = "SALES_ORDER", "SALES_ORDER"
    MANUAL = "MANUAL", "MANUAL"


class ChatMessageRole(models.TextChoices):
    USER = "user", "user"
    ASSISTANT = "assistant", "assistant"


class Product(models.Model):
    product_id = models.BigIntegerField(primary_key=True)
    user_id = models.BigIntegerField()
    name = models.TextField()
    description = models.TextField()
    sku = models.TextField()
    unit = models.CharField(max_length=10)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "product"


class PurchaseOrder(models.Model):
    purchase_order_id = models.BigIntegerField(primary_key=True)
    user_id = models.BigIntegerField()
    product_id = models.BigIntegerField()
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    total_cost = models.DecimalField(max_digits=20, decimal_places=2)
    product_sku = models.TextField()
    product_name = models.TextField()
    guid = models.UUIDField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "purchase_order"


class SalesOrder(models.Model):
    sales_order_id = models.BigIntegerField(primary_key=True)
    user_id = models.BigIntegerField()
    product_id = models.BigIntegerField()
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    product_sku = models.TextField()
    product_name = models.TextField()
    guid = models.UUIDField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "sales_order"


class StockMovement(models.Model):
    stock_movement_id = models.BigIntegerField(primary_key=True)
    user_id = models.BigIntegerField()
    product_id = models.BigIntegerField()
    quantity_delta = models.DecimalField(max_digits=20, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    source = models.CharField(max_length=32)
    product_sku = models.TextField()
    source_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "stock_movement"


class ChatMessage(models.Model):
    chat_message_id = models.BigIntegerField(primary_key=True)
    user_id = models.BigIntegerField()
    role = models.CharField(max_length=16)
    content = models.TextField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "chat_message"


class ProductStockView(models.Model):
    user_id = models.BigIntegerField()
    product_id = models.BigIntegerField(primary_key=True)
    sku = models.TextField()
    name = models.TextField()
    unit = models.CharField(max_length=10)
    quantity_on_hand = models.DecimalField(max_digits=20, decimal_places=4)

    class Meta:
        managed = False
        db_table = "product_stock_view"


class ProductFinancialsView(models.Model):
    user_id = models.BigIntegerField()
    product_id = models.BigIntegerField(primary_key=True)
    sku = models.TextField()
    name = models.TextField()
    unit = models.CharField(max_length=10)
    quantity_on_hand = models.DecimalField(max_digits=20, decimal_places=4)
    total_qty_purchased = models.DecimalField(max_digits=20, decimal_places=4)
    total_cost = models.DecimalField(max_digits=20, decimal_places=2)
    total_qty_sold = models.DecimalField(max_digits=20, decimal_places=4)
    total_revenue = models.DecimalField(max_digits=20, decimal_places=2)
    profit = models.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        managed = False
        db_table = "product_financials_view"


class ProductFinancialsSummary(models.Model):
    product_id = models.BigIntegerField(primary_key=True)
    user_id = models.BigIntegerField()
    sku = models.TextField()
    name = models.TextField()
    unit = models.CharField(max_length=10)
    quantity_on_hand = models.DecimalField(max_digits=20, decimal_places=4)
    total_qty_purchased = models.DecimalField(max_digits=20, decimal_places=4)
    total_cost = models.DecimalField(max_digits=20, decimal_places=2)
    total_qty_sold = models.DecimalField(max_digits=20, decimal_places=4)
    total_revenue = models.DecimalField(max_digits=20, decimal_places=2)
    profit = models.DecimalField(max_digits=20, decimal_places=2)
    margin_percent = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "product_financials_summary"
