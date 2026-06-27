from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.deps import CurrentUser, get_current_user
from app.inventory.helpers import (
    empty_patch_response,
    run_inventory,
    serialize_financial_row,
    serialize_product,
    serialize_purchase_order,
    serialize_sales_order,
    serialize_stock,
    serialize_stock_movement,
)
from app.inventory.schemas import (
    ProductUpdate,
    ProductWrite,
    PurchaseOrderUpdate,
    PurchaseOrderWrite,
    SalesOrderUpdate,
    SalesOrderWrite,
    StockAdd,
    StockMovementUpdate,
    StockMovementWrite,
)
from services import inventory as svc
from services.container import build_inventory_services

router = APIRouter(tags=["inventory"])


def _services():
    return build_inventory_services()


@router.get("/products/")
def list_products(user: Annotated[CurrentUser, Depends(get_current_user)]) -> list[dict]:
    services = _services()
    rows = services.product_repo.list_rows_by_user(user.user_id)
    product_ids = [int(r["product_id"]) for r in rows]
    aggregates = services.reporting_repo.get_financials_map(user.user_id, product_ids)
    return [serialize_product(r, aggregates.get(int(r["product_id"]))) for r in rows]


@router.post("/products/", status_code=status.HTTP_201_CREATED)
def create_product(body: ProductWrite, user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict:
    result = run_inventory(
        lambda: svc.register_product_sync(
            user.user_id,
            name=body.name,
            sku=body.sku,
            unit=body.unit.value,
            description=body.description,
        )
    )
    services = _services()
    row = services.product_repo.get_row_by_id(user.user_id, result.product_id)
    assert row is not None
    aggregates = services.reporting_repo.get_financials_map(user.user_id, [result.product_id])
    return serialize_product(row, aggregates.get(result.product_id))


@router.get("/products/{product_id}/")
def retrieve_product(product_id: int, user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict:
    services = _services()
    row = services.product_repo.get_row_by_id(user.user_id, product_id)
    if row is None:
        raise HTTPException(status_code=404)
    aggregates = services.reporting_repo.get_financials_map(user.user_id, [product_id])
    return serialize_product(row, aggregates.get(product_id))


@router.patch("/products/{product_id}/")
def partial_update_product(
    product_id: int,
    body: ProductUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        empty_patch_response()
    return _save_product_update(user, product_id, payload)


@router.put("/products/{product_id}/")
def update_product(
    product_id: int,
    body: ProductUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        empty_patch_response()
    return _save_product_update(user, product_id, payload)


def _save_product_update(user: CurrentUser, product_id: int, payload: dict) -> dict:
    if "unit" in payload and payload["unit"] is not None:
        payload["unit"] = payload["unit"].value if hasattr(payload["unit"], "value") else payload["unit"]
    result = run_inventory(lambda: svc.update_product_sync(user.user_id, product_id, **payload))
    services = _services()
    row = services.product_repo.get_row_by_id(user.user_id, result.product_id)
    assert row is not None
    aggregates = services.reporting_repo.get_financials_map(user.user_id, [result.product_id])
    return serialize_product(row, aggregates.get(result.product_id))


@router.delete("/products/{product_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, user: Annotated[CurrentUser, Depends(get_current_user)]) -> Response:
    run_inventory(lambda: svc.delete_product_sync(user.user_id, product_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/stock/")
def list_stock(user: Annotated[CurrentUser, Depends(get_current_user)]) -> list[dict]:
    rows = _services().stock_repo.list_stock_levels(user.user_id)
    return [serialize_stock(r) for r in rows]


@router.post("/stock/add/")
def add_stock(body: StockAdd, user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict:
    result = run_inventory(
        lambda: svc.add_stock_sync(
            user.user_id,
            sku=body.sku,
            quantity=body.quantity,
            unit_cost=body.unit_cost,
        )
    )
    return {"sku": result.sku, "quantity_on_hand": str(result.remaining)}


@router.get("/stock-movements/")
def list_stock_movements(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    product_id: Annotated[str | None, Query()] = None,
) -> list[dict]:
    pid: int | None = None
    if product_id is not None:
        try:
            pid = int(product_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="product_id must be an integer.") from exc
    rows = svc.list_stock_movements_sync(user.user_id, product_id=pid)
    return [serialize_stock_movement(r) for r in rows]


@router.get("/stock-movements/{movement_id}/")
def retrieve_stock_movement(movement_id: int, user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict:
    try:
        row = svc.get_stock_movement_sync(user.user_id, movement_id)
    except svc.InventoryError as exc:
        raise HTTPException(status_code=404) from exc
    return serialize_stock_movement(row)


@router.post("/stock-movements/", status_code=status.HTTP_201_CREATED)
def create_stock_movement(
    body: StockMovementWrite,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    row = run_inventory(
        lambda: svc.create_manual_stock_movement_sync(
            user.user_id,
            sku=body.sku,
            quantity=body.quantity,
            unit_cost=body.unit_cost,
        )
    )
    return serialize_stock_movement(row)


@router.patch("/stock-movements/{movement_id}/")
def partial_update_stock_movement(
    movement_id: int,
    body: StockMovementUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        empty_patch_response()
    row = run_inventory(
        lambda: svc.update_manual_stock_movement_sync(user.user_id, movement_id, **payload)
    )
    return serialize_stock_movement(row)


@router.put("/stock-movements/{movement_id}/")
def update_stock_movement(
    movement_id: int,
    body: StockMovementUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    return partial_update_stock_movement(movement_id, body, user)


@router.delete("/stock-movements/{movement_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_stock_movement(
    movement_id: int,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    run_inventory(lambda: svc.delete_manual_stock_movement_sync(user.user_id, movement_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/purchase-orders/")
def list_purchase_orders(user: Annotated[CurrentUser, Depends(get_current_user)]) -> list[dict]:
    rows = _services().purchase_order_repo.list_by_user(user.user_id)
    return [serialize_purchase_order(r) for r in rows]


@router.post("/purchase-orders/", status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    body: PurchaseOrderWrite,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    result = run_inventory(
        lambda: svc.create_purchase_order_sync(
            user.user_id,
            sku=body.sku,
            quantity=body.quantity,
            total_cost=body.total_cost,
        )
    )
    row = _services().purchase_order_repo.get_row_by_id(user.user_id, result.purchase_order_id)
    assert row is not None
    return serialize_purchase_order(row, remaining_stock=str(result.remaining))


@router.get("/purchase-orders/{order_id}/")
def retrieve_purchase_order(order_id: int, user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict:
    row = _services().purchase_order_repo.get_row_by_id(user.user_id, order_id)
    if row is None:
        raise HTTPException(status_code=404)
    return serialize_purchase_order(row)


@router.patch("/purchase-orders/{order_id}/")
def partial_update_purchase_order(
    order_id: int,
    body: PurchaseOrderUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        empty_patch_response()
    return _save_po_update(user, order_id, payload)


@router.put("/purchase-orders/{order_id}/")
def update_purchase_order(
    order_id: int,
    body: PurchaseOrderUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        empty_patch_response()
    return _save_po_update(user, order_id, payload)


def _save_po_update(user: CurrentUser, order_id: int, payload: dict) -> dict:
    result = run_inventory(lambda: svc.update_purchase_order_sync(user.user_id, order_id, **payload))
    row = _services().purchase_order_repo.get_row_by_id(user.user_id, result.purchase_order_id)
    assert row is not None
    return serialize_purchase_order(row, remaining_stock=str(result.remaining))


@router.delete("/purchase-orders/{order_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_order(order_id: int, user: Annotated[CurrentUser, Depends(get_current_user)]) -> Response:
    run_inventory(lambda: svc.delete_purchase_order_sync(user.user_id, order_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sales-orders/")
def list_sales_orders(user: Annotated[CurrentUser, Depends(get_current_user)]) -> list[dict]:
    rows = _services().sales_order_repo.list_by_user(user.user_id)
    return [serialize_sales_order(r) for r in rows]


@router.post("/sales-orders/", status_code=status.HTTP_201_CREATED)
def create_sales_order(
    body: SalesOrderWrite,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    result = run_inventory(
        lambda: svc.record_sale_sync(
            user.user_id,
            sku=body.sku,
            quantity=body.quantity,
            unit_price=body.unit_price,
        )
    )
    row = _services().sales_order_repo.get_row_by_id(user.user_id, result.sales_order_id)
    assert row is not None
    return serialize_sales_order(
        row,
        revenue=str(result.revenue),
        remaining_stock=str(result.remaining),
    )


@router.get("/sales-orders/{order_id}/")
def retrieve_sales_order(order_id: int, user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict:
    row = _services().sales_order_repo.get_row_by_id(user.user_id, order_id)
    if row is None:
        raise HTTPException(status_code=404)
    return serialize_sales_order(row)


@router.patch("/sales-orders/{order_id}/")
def partial_update_sales_order(
    order_id: int,
    body: SalesOrderUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        empty_patch_response()
    return _save_so_update(user, order_id, payload)


@router.put("/sales-orders/{order_id}/")
def update_sales_order(
    order_id: int,
    body: SalesOrderUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        empty_patch_response()
    return _save_so_update(user, order_id, payload)


def _save_so_update(user: CurrentUser, order_id: int, payload: dict) -> dict:
    result = run_inventory(lambda: svc.update_sales_order_sync(user.user_id, order_id, **payload))
    row = _services().sales_order_repo.get_row_by_id(user.user_id, result.sales_order_id)
    assert row is not None
    return serialize_sales_order(
        row,
        revenue=str(result.revenue),
        remaining_stock=str(result.remaining),
    )


@router.delete("/sales-orders/{order_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_sales_order(order_id: int, user: Annotated[CurrentUser, Depends(get_current_user)]) -> Response:
    run_inventory(lambda: svc.delete_sales_order_sync(user.user_id, order_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/financials/{sku}/")
def retrieve_financials(sku: str, user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict:
    row = _services().reporting_repo.get_financials_by_id_or_sku(user.user_id, sku)
    if row is None:
        raise HTTPException(status_code=404)
    return serialize_financial_row(row)
