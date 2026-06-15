from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from inventory_api.constants import ProductUnit
from inventory_api.models import (
    Product,
    ProductFinancialsView,
    ProductStockView,
    PurchaseOrder,
    SalesOrder,
    StockMovement,
)


def format_margin_percent(profit: Decimal, total_cost: Decimal) -> str | None:
    if total_cost == 0:
        return None
    return f"{(profit / total_cost) * 100:.2f}"


class ProductSerializer(serializers.ModelSerializer):
    quantity_on_hand = serializers.SerializerMethodField()
    total_qty_purchased = serializers.SerializerMethodField()
    total_qty_sold = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()
    profit = serializers.SerializerMethodField()
    margin_percent = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "product_id",
            "name",
            "description",
            "sku",
            "unit",
            "created_at",
            "updated_at",
            "quantity_on_hand",
            "total_qty_purchased",
            "total_qty_sold",
            "total_cost",
            "total_revenue",
            "profit",
            "margin_percent",
        ]
        read_only_fields = fields

    def _aggregate(self, obj: Product) -> ProductFinancialsView | None:
        return self.context.get("aggregates", {}).get(obj.product_id)

    def get_quantity_on_hand(self, obj: Product) -> str:
        row = self._aggregate(obj)
        return str(row.quantity_on_hand) if row else "0"

    def get_total_qty_purchased(self, obj: Product) -> str:
        row = self._aggregate(obj)
        return str(row.total_qty_purchased) if row else "0"

    def get_total_qty_sold(self, obj: Product) -> str:
        row = self._aggregate(obj)
        return str(row.total_qty_sold) if row else "0"

    def get_total_cost(self, obj: Product) -> str:
        row = self._aggregate(obj)
        return str(row.total_cost) if row else "0.00"

    def get_total_revenue(self, obj: Product) -> str:
        row = self._aggregate(obj)
        return str(row.total_revenue) if row else "0.00"

    def get_profit(self, obj: Product) -> str:
        row = self._aggregate(obj)
        return str(row.profit) if row else "0.00"

    def get_margin_percent(self, obj: Product) -> str | None:
        row = self._aggregate(obj)
        if row is None:
            return None
        return format_margin_percent(row.profit, row.total_cost)


class ProductWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    sku = serializers.CharField(max_length=64)
    unit = serializers.ChoiceField(choices=ProductUnit.choices)
    description = serializers.CharField(max_length=2000, required=False, default="")


class ProductUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    unit = serializers.ChoiceField(choices=ProductUnit.choices, required=False)


class StockAddSerializer(serializers.Serializer):
    sku = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=20, decimal_places=4)
    unit_cost = serializers.DecimalField(max_digits=20, decimal_places=2, required=False, allow_null=True)


class PurchaseOrderWriteSerializer(serializers.Serializer):
    sku = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=20, decimal_places=4)
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2)


class PurchaseOrderUpdateSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(max_digits=20, decimal_places=4, required=False)
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)


class SalesOrderWriteSerializer(serializers.Serializer):
    sku = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=20, decimal_places=4)
    unit_price = serializers.DecimalField(max_digits=20, decimal_places=2)


class SalesOrderUpdateSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(max_digits=20, decimal_places=4, required=False)
    unit_price = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)


class StockMovementWriteSerializer(serializers.Serializer):
    sku = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=20, decimal_places=4)
    unit_cost = serializers.DecimalField(max_digits=20, decimal_places=2, required=False, allow_null=True)


class StockMovementUpdateSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(max_digits=20, decimal_places=4, required=False)
    unit_cost = serializers.DecimalField(max_digits=20, decimal_places=2, required=False, allow_null=True)


class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = ["purchase_order_id", "product_id", "quantity", "total_cost", "guid", "created_at"]
        read_only_fields = fields


class SalesOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrder
        fields = ["sales_order_id", "product_id", "quantity", "unit_price", "guid", "created_at"]
        read_only_fields = fields


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductStockView
        fields = ["product_id", "sku", "name", "unit", "quantity_on_hand"]
        read_only_fields = fields


class StockMovementSerializer(serializers.ModelSerializer):
    sku = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            "stock_movement_id",
            "product_id",
            "sku",
            "quantity_delta",
            "unit_cost",
            "source",
            "source_id",
            "created_at",
        ]
        read_only_fields = fields

    def get_sku(self, obj: StockMovement) -> str:
        return self.context.get("sku_by_product", {}).get(obj.product_id, "")


class FinancialsSerializer(serializers.ModelSerializer):
    margin_percent = serializers.SerializerMethodField()

    class Meta:
        model = ProductFinancialsView
        fields = [
            "product_id",
            "sku",
            "name",
            "unit",
            "quantity_on_hand",
            "total_qty_purchased",
            "total_qty_sold",
            "total_cost",
            "total_revenue",
            "profit",
            "margin_percent",
        ]
        read_only_fields = fields

    def get_margin_percent(self, obj: ProductFinancialsView) -> str | None:
        return format_margin_percent(obj.profit, obj.total_cost)
