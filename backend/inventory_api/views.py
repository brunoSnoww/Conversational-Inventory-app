from __future__ import annotations

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory_api.models import Product, ProductFinancialsView, ProductStockView, PurchaseOrder, SalesOrder
from inventory_api.serializers import (
    FinancialsSerializer,
    ProductSerializer,
    ProductUpdateSerializer,
    ProductWriteSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderUpdateSerializer,
    PurchaseOrderWriteSerializer,
    SalesOrderSerializer,
    SalesOrderUpdateSerializer,
    SalesOrderWriteSerializer,
    StockAddSerializer,
    StockMovementSerializer,
    StockMovementUpdateSerializer,
    StockMovementWriteSerializer,
    StockSerializer,
)
from services import inventory as svc


class ProductViewSet(viewsets.ViewSet):
    def _aggregate_map(self, user_id: int, product_ids: list[int] | None = None) -> dict[int, ProductFinancialsView]:
        qs = ProductFinancialsView.objects.filter(user_id=user_id)
        if product_ids is not None:
            qs = qs.filter(product_id__in=product_ids)
        return {int(row.product_id): row for row in qs}

    def list(self, request):
        qs = Product.objects.filter(user_id=request.user.user_id).order_by("-product_id")
        product_ids = [int(p.product_id) for p in qs]
        return Response(
            ProductSerializer(
                qs,
                many=True,
                context={"aggregates": self._aggregate_map(request.user.user_id, product_ids)},
            ).data
        )

    def create(self, request):
        ser = ProductWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = svc.register_product_sync(request.user.user_id, **ser.validated_data)
        except svc.InvalidUnit as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        product = Product.objects.get(pk=result.product_id)
        return Response(
            ProductSerializer(
                product,
                context={"aggregates": self._aggregate_map(request.user.user_id, [result.product_id])},
            ).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        product = Product.objects.filter(user_id=request.user.user_id, product_id=pk).first()
        if product is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(
            ProductSerializer(
                product,
                context={"aggregates": self._aggregate_map(request.user.user_id, [int(pk)])},
            ).data
        )

    def update(self, request, pk=None):
        ser = ProductUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if not ser.validated_data:
            return Response({"detail": "At least one field required."}, status=status.HTTP_400_BAD_REQUEST)
        return self._save_product_update(request, pk, ser.validated_data)

    def partial_update(self, request, pk=None):
        ser = ProductUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return self._save_product_update(request, pk, ser.validated_data)

    def _save_product_update(self, request, pk, validated_data):
        try:
            result = svc.update_product_sync(request.user.user_id, int(pk), **validated_data)
        except svc.UnknownProduct:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except svc.InvalidUnit as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        product = Product.objects.get(pk=result.product_id)
        return Response(
            ProductSerializer(
                product,
                context={"aggregates": self._aggregate_map(request.user.user_id, [result.product_id])},
            ).data
        )

    def destroy(self, request, pk=None):
        try:
            svc.delete_product_sync(request.user.user_id, int(pk))
        except svc.UnknownProduct:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StockViewSet(viewsets.ViewSet):
    def list(self, request):
        qs = ProductStockView.objects.filter(user_id=request.user.user_id).order_by("sku")
        return Response(StockSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], url_path="add")
    def add(self, request):
        ser = StockAddSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            result = svc.add_stock_sync(
                request.user.user_id,
                sku=data["sku"],
                quantity=data["quantity"],
                unit_cost=data.get("unit_cost"),
            )
        except svc.UnknownProduct as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"sku": result.sku, "quantity_on_hand": result.remaining})


class StockMovementViewSet(viewsets.ViewSet):
    def list(self, request):
        product_id = request.query_params.get("product_id")
        pid = int(product_id) if product_id else None
        rows = svc.list_stock_movements_sync(request.user.user_id, product_id=pid)
        sku_by_product = {int(r["product_id"]): r["sku"] for r in rows}
        from inventory_api.models import StockMovement

        objs = []
        for r in rows:
            obj = StockMovement(
                stock_movement_id=int(r["stock_movement_id"]),
                user_id=request.user.user_id,
                product_id=int(r["product_id"]),
                quantity_delta=r["quantity_delta"],
                unit_cost=r["unit_cost"],
                source=r["source"],
                source_id=r["source_id"],
                created_at=r["created_at"],
            )
            objs.append(obj)
        return Response(
            StockMovementSerializer(objs, many=True, context={"sku_by_product": sku_by_product}).data
        )

    def retrieve(self, request, pk=None):
        try:
            row = svc.get_stock_movement_sync(request.user.user_id, int(pk))
        except svc.InventoryError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        from inventory_api.models import StockMovement

        obj = StockMovement(
            stock_movement_id=int(row["stock_movement_id"]),
            user_id=request.user.user_id,
            product_id=int(row["product_id"]),
            quantity_delta=row["quantity_delta"],
            unit_cost=row["unit_cost"],
            source=row["source"],
            source_id=row["source_id"],
            created_at=row["created_at"],
        )
        return Response(
            StockMovementSerializer(
                obj,
                context={"sku_by_product": {int(row["product_id"]): row["sku"]}},
            ).data
        )

    def create(self, request):
        ser = StockMovementWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            row = svc.create_manual_stock_movement_sync(
                request.user.user_id,
                sku=data["sku"],
                quantity=data["quantity"],
                unit_cost=data.get("unit_cost"),
            )
        except svc.UnknownProduct as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._movement_response(request, row), status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        ser = StockMovementUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        if not ser.validated_data:
            return Response({"detail": "At least one field required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            row = svc.update_manual_stock_movement_sync(
                request.user.user_id, int(pk), **ser.validated_data
            )
        except svc.InsufficientStock as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._movement_response(request, row))

    def update(self, request, pk=None):
        ser = StockMovementUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if not ser.validated_data:
            return Response({"detail": "At least one field required."}, status=status.HTTP_400_BAD_REQUEST)
        return self.partial_update(request, pk)

    def destroy(self, request, pk=None):
        try:
            svc.delete_manual_stock_movement_sync(request.user.user_id, int(pk))
        except svc.InsufficientStock as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _movement_response(self, request, row: dict) -> dict:
        from inventory_api.models import StockMovement

        obj = StockMovement(
            stock_movement_id=int(row["stock_movement_id"]),
            user_id=request.user.user_id,
            product_id=int(row["product_id"]),
            quantity_delta=row["quantity_delta"],
            unit_cost=row.get("unit_cost"),
            source=row["source"],
            source_id=row.get("source_id"),
            created_at=row["created_at"],
        )
        return StockMovementSerializer(
            obj,
            context={"sku_by_product": {int(row["product_id"]): row["sku"]}},
        ).data


class PurchaseOrderViewSet(viewsets.ViewSet):
    def list(self, request):
        qs = PurchaseOrder.objects.filter(user_id=request.user.user_id).order_by("-purchase_order_id")
        return Response(PurchaseOrderSerializer(qs, many=True).data)

    def create(self, request):
        ser = PurchaseOrderWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            result = svc.create_purchase_order_sync(
                request.user.user_id,
                sku=data["sku"],
                quantity=data["quantity"],
                total_cost=data["total_cost"],
            )
        except svc.UnknownProduct as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        po = PurchaseOrder.objects.get(pk=result.purchase_order_id)
        body = PurchaseOrderSerializer(po).data
        body["remaining_stock"] = result.remaining
        return Response(body, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        po = PurchaseOrder.objects.filter(user_id=request.user.user_id, purchase_order_id=pk).first()
        if po is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(PurchaseOrderSerializer(po).data)

    def partial_update(self, request, pk=None):
        ser = PurchaseOrderUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        if not ser.validated_data:
            return Response({"detail": "At least one field required."}, status=status.HTTP_400_BAD_REQUEST)
        return self._save_po_update(request, pk, ser.validated_data)

    def update(self, request, pk=None):
        ser = PurchaseOrderUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if not ser.validated_data:
            return Response({"detail": "At least one field required."}, status=status.HTTP_400_BAD_REQUEST)
        return self._save_po_update(request, pk, ser.validated_data)

    def _save_po_update(self, request, pk, validated_data):
        try:
            result = svc.update_purchase_order_sync(request.user.user_id, int(pk), **validated_data)
        except svc.OrderNotFound:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except svc.UnknownProduct as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except svc.InsufficientStock as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        po = PurchaseOrder.objects.get(pk=result.purchase_order_id)
        body = PurchaseOrderSerializer(po).data
        body["remaining_stock"] = result.remaining
        return Response(body)

    def destroy(self, request, pk=None):
        try:
            svc.delete_purchase_order_sync(request.user.user_id, int(pk))
        except svc.OrderNotFound:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except svc.InsufficientStock as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SalesOrderViewSet(viewsets.ViewSet):
    def list(self, request):
        qs = SalesOrder.objects.filter(user_id=request.user.user_id).order_by("-sales_order_id")
        return Response(SalesOrderSerializer(qs, many=True).data)

    def create(self, request):
        ser = SalesOrderWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            result = svc.record_sale_sync(
                request.user.user_id,
                sku=data["sku"],
                quantity=data["quantity"],
                unit_price=data["unit_price"],
            )
        except svc.UnknownProduct as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except svc.InsufficientStock as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        so = SalesOrder.objects.get(pk=result.sales_order_id)
        body = SalesOrderSerializer(so).data
        body["revenue"] = result.revenue
        body["remaining_stock"] = result.remaining
        return Response(body, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        so = SalesOrder.objects.filter(user_id=request.user.user_id, sales_order_id=pk).first()
        if so is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(SalesOrderSerializer(so).data)

    def partial_update(self, request, pk=None):
        ser = SalesOrderUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        if not ser.validated_data:
            return Response({"detail": "At least one field required."}, status=status.HTTP_400_BAD_REQUEST)
        return self._save_so_update(request, pk, ser.validated_data)

    def update(self, request, pk=None):
        ser = SalesOrderUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if not ser.validated_data:
            return Response({"detail": "At least one field required."}, status=status.HTTP_400_BAD_REQUEST)
        return self._save_so_update(request, pk, ser.validated_data)

    def _save_so_update(self, request, pk, validated_data):
        try:
            result = svc.update_sales_order_sync(request.user.user_id, int(pk), **validated_data)
        except svc.OrderNotFound:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except svc.UnknownProduct as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except svc.InsufficientStock as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        so = SalesOrder.objects.get(pk=result.sales_order_id)
        body = SalesOrderSerializer(so).data
        body["revenue"] = result.revenue
        body["remaining_stock"] = result.remaining
        return Response(body)

    def destroy(self, request, pk=None):
        try:
            svc.delete_sales_order_sync(request.user.user_id, int(pk))
        except svc.OrderNotFound:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except svc.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FinancialsViewSet(viewsets.ViewSet):
    def retrieve(self, request, pk=None):
        row = ProductFinancialsView.objects.filter(
            user_id=request.user.user_id
        ).filter(Q(product_id=pk) | Q(sku__iexact=pk)).first()
        if row is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(FinancialsSerializer(row).data)
