import { apiFetch } from './client';
import type { AuthSession, Product, PurchaseOrder, SalesOrder, StockAddResult } from './types';

type AuthResponseDto = {
  user_id: string;
  email: string;
  access: string;
  refresh: string;
};

function parseAuthResponse(data: AuthResponseDto): AuthSession {
  if (typeof data.user_id !== 'string' || !data.user_id) {
    throw new Error('Auth response missing user_id');
  }
  return {
    userId: data.user_id,
    email: data.email,
    access: data.access,
    refresh: data.refresh,
  };
}

export async function register(email: string, password: string): Promise<AuthSession> {
  const data = await apiFetch<AuthResponseDto>('/api/auth/register/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  return parseAuthResponse(data);
}

export async function login(email: string, password: string): Promise<AuthSession> {
  const data = await apiFetch<AuthResponseDto>('/api/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  return parseAuthResponse(data);
}

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
