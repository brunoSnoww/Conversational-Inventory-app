/**
 * REST write hooks. Reads come from PowerSync (see `sync/hooks.ts`).
 *
 * Writes go through Django REST (validation, ledger side effects, oversell
 * checks). Results replicate back via PowerSync, so mutations do NOT invalidate
 * any read cache — the watched queries update reactively.
 */
import { useMutation } from '@tanstack/react-query';

import {
  addStock,
  createProduct,
  createPurchaseOrder,
  createSalesOrder,
} from '../api/inventory';
import { useAuth } from '../auth/AuthContext';

export function useCreateProduct() {
  const { session } = useAuth();
  return useMutation({
    mutationFn: (body: { name: string; sku: string; unit: string; description?: string }) =>
      createProduct(session!.access, body),
  });
}

export function useCreatePurchaseOrder() {
  const { session } = useAuth();
  return useMutation({
    mutationFn: (body: { sku: string; quantity: string; total_cost: string }) =>
      createPurchaseOrder(session!.access, body),
  });
}

export function useCreateSalesOrder() {
  const { session } = useAuth();
  return useMutation({
    mutationFn: (body: { sku: string; quantity: string; unit_price: string }) =>
      createSalesOrder(session!.access, body),
  });
}

export function useAddStock() {
  const { session } = useAuth();
  return useMutation({
    mutationFn: (body: { sku: string; quantity: string; unit_cost?: string | null }) =>
      addStock(session!.access, body),
  });
}
