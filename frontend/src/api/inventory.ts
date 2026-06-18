import { apiFetch } from './client';
import type { Product, PurchaseOrder, SalesOrder, StockAddResult } from './types';

export function createProduct(
  accessToken: string,
  body: { name: string; sku: string; unit: string; description?: string },
) {
  return apiFetch<Product>('/api/products/', {
    method: 'POST',
    accessToken,
    body: JSON.stringify(body),
  });
}

export function createPurchaseOrder(
  accessToken: string,
  body: { sku: string; quantity: string; total_cost: string },
) {
  return apiFetch<PurchaseOrder>('/api/purchase-orders/', {
    method: 'POST',
    accessToken,
    body: JSON.stringify(body),
  });
}

export function createSalesOrder(
  accessToken: string,
  body: { sku: string; quantity: string; unit_price: string },
) {
  return apiFetch<SalesOrder>('/api/sales-orders/', {
    method: 'POST',
    accessToken,
    body: JSON.stringify(body),
  });
}

export function addStock(
  accessToken: string,
  body: { sku: string; quantity: string; unit_cost?: string | null },
) {
  return apiFetch<StockAddResult>('/api/stock/add/', {
    method: 'POST',
    accessToken,
    body: JSON.stringify(body),
  });
}
