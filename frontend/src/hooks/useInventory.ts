/**
 * REST write hooks. Reads come from PowerSync (`sync/hooks.ts`).
 */
import { useMutation } from '@tanstack/react-query';

import {
  addStock,
  createProduct,
  createPurchaseOrder,
  createSalesOrder,
} from '../api/inventory';
import { useAuth } from '../auth/AuthContext';

function useAuthedMutation<TBody>(fn: (token: string, body: TBody) => Promise<unknown>) {
  const { session } = useAuth();
  return useMutation({ mutationFn: (body: TBody) => fn(session!.access, body) });
}

export function useCreateProduct() {
  return useAuthedMutation(createProduct);
}

export function useCreatePurchaseOrder() {
  return useAuthedMutation(createPurchaseOrder);
}

export function useCreateSalesOrder() {
  return useAuthedMutation(createSalesOrder);
}

export function useAddStock() {
  return useAuthedMutation(addStock);
}
