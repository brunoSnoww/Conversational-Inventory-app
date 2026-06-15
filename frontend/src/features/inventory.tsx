import { FormEvent, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  Anchor,
  Button,
  Group,
  Select,
  Stack,
  TextInput,
} from '@mantine/core';

import { PRODUCT_UNITS, type ProductUnit } from '../api/types';
import {
  useAddStock,
  useCreateProduct,
  useCreatePurchaseOrder,
  useCreateSalesOrder,
} from '../hooks/useInventory';
import { routes } from '../routes';
import {
  useDashboard,
  useProductBySku,
  usePurchaseOrders,
  useSalesOrders,
  useStockMovements,
} from '../sync';
import { ErrorText, Muted, Page, Section, SyncQuery, friendlyError, useSyncing } from './ui';
import {
  ProductDetailTable,
  ProductTable,
  PurchaseOrderTable,
  SalesOrderTable,
  StockMovementTable,
} from './tables';

function ProductForm() {
  const createProduct = useCreateProduct();
  const [sku, setSku] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [unit, setUnit] = useState<ProductUnit>('unit');

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await createProduct.mutateAsync({ name: name.trim(), sku: sku.trim(), unit, description: description.trim() });
  }

  return (
    <form onSubmit={onSubmit}>
      <Stack gap="sm">
        <Group align="flex-end" wrap="wrap">
          <TextInput label="SKU" placeholder="SKU" value={sku} onChange={(e) => setSku(e.currentTarget.value)} required style={{ flex: 1, minWidth: 100 }} />
          <TextInput label="Name" placeholder="Name" value={name} onChange={(e) => setName(e.currentTarget.value)} required style={{ flex: 1, minWidth: 120 }} />
          <Select
            label="Unit"
            data={PRODUCT_UNITS.map((u) => ({ value: u, label: u }))}
            value={unit}
            onChange={(v) => setUnit((v ?? 'unit') as ProductUnit)}
            allowDeselect={false}
            style={{ width: 100 }}
          />
          <Button type="submit" loading={createProduct.isPending}>Create</Button>
        </Group>
        <TextInput label="Description" placeholder="Description" value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
        {createProduct.error && <ErrorText>{createProduct.error.message}</ErrorText>}
      </Stack>
    </form>
  );
}

function StockForm() {
  const addStock = useAddStock();
  const [sku, setSku] = useState('');
  const [quantity, setQuantity] = useState('');
  const [unitCost, setUnitCost] = useState('');

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const cost = unitCost.trim();
    await addStock.mutateAsync({ sku: sku.trim(), quantity, unit_cost: cost ? cost : null });
  }

  return (
    <form onSubmit={onSubmit}>
      <Stack gap="sm">
        <Group align="flex-end" wrap="wrap">
          <TextInput label="SKU" value={sku} onChange={(e) => setSku(e.currentTarget.value)} required style={{ flex: 1, minWidth: 100 }} />
          <TextInput label="Qty" value={quantity} onChange={(e) => setQuantity(e.currentTarget.value)} required style={{ width: 100 }} />
          <TextInput label="Unit cost" placeholder="optional" value={unitCost} onChange={(e) => setUnitCost(e.currentTarget.value)} style={{ width: 140 }} />
          <Button type="submit" loading={addStock.isPending}>Add</Button>
        </Group>
        {addStock.error && <ErrorText>{addStock.error.message}</ErrorText>}
      </Stack>
    </form>
  );
}

function PurchaseForm() {
  const createPo = useCreatePurchaseOrder();
  const [sku, setSku] = useState('');
  const [quantity, setQuantity] = useState('');
  const [totalCost, setTotalCost] = useState('');

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await createPo.mutateAsync({ sku: sku.trim(), quantity, total_cost: totalCost });
  }

  return (
    <form onSubmit={onSubmit}>
      <Stack gap="sm">
        <Group align="flex-end" wrap="wrap">
          <TextInput label="SKU" value={sku} onChange={(e) => setSku(e.currentTarget.value)} required style={{ flex: 1, minWidth: 100 }} />
          <TextInput label="Qty" value={quantity} onChange={(e) => setQuantity(e.currentTarget.value)} required style={{ width: 100 }} />
          <TextInput label="Total cost" value={totalCost} onChange={(e) => setTotalCost(e.currentTarget.value)} required style={{ width: 120 }} />
          <Button type="submit" loading={createPo.isPending}>PO</Button>
        </Group>
        {createPo.error && <ErrorText>{createPo.error.message}</ErrorText>}
      </Stack>
    </form>
  );
}

function SalesForm() {
  const createSo = useCreateSalesOrder();
  const [sku, setSku] = useState('');
  const [quantity, setQuantity] = useState('');
  const [unitPrice, setUnitPrice] = useState('');

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await createSo.mutateAsync({ sku: sku.trim(), quantity, unit_price: unitPrice });
  }

  return (
    <form onSubmit={onSubmit}>
      <Stack gap="sm">
        <Group align="flex-end" wrap="wrap">
          <TextInput label="SKU" value={sku} onChange={(e) => setSku(e.currentTarget.value)} required style={{ flex: 1, minWidth: 100 }} />
          <TextInput label="Qty" value={quantity} onChange={(e) => setQuantity(e.currentTarget.value)} required style={{ width: 100 }} />
          <TextInput label="Unit price" value={unitPrice} onChange={(e) => setUnitPrice(e.currentTarget.value)} required style={{ width: 120 }} />
          <Button type="submit" loading={createSo.isPending}>Sell</Button>
        </Group>
        {createSo.error && <ErrorText>{createSo.error.message}</ErrorText>}
      </Stack>
    </form>
  );
}

export function DashboardPage() {
  const { syncing, syncError, syncStatus } = useSyncing();
  const dashboard = useDashboard();

  return (
    <Page title="Dashboard">
      {syncError ? (
        <ErrorText>{syncError}</ErrorText>
      ) : dashboard.error && syncStatus === 'ready' ? (
        <ErrorText>{friendlyError(dashboard.error.message)}</ErrorText>
      ) : syncing && !dashboard.data?.length ? (
        <Muted>Loading…</Muted>
      ) : (
        <ProductTable products={dashboard.data ?? []} />
      )}
    </Page>
  );
}

export function ProductsPage() {
  const { syncing, syncError, syncStatus } = useSyncing();
  const dashboard = useDashboard();

  return (
    <Page title="Products">
      <ProductForm />
      <Section title="Catalog">
        {syncError ? (
          <ErrorText>{syncError}</ErrorText>
        ) : dashboard.error && syncStatus === 'ready' ? (
          <ErrorText>{friendlyError(dashboard.error.message)}</ErrorText>
        ) : syncing && !dashboard.data?.length ? (
          <Muted>Loading…</Muted>
        ) : (
          <ProductTable products={dashboard.data ?? []} linkSkus />
        )}
      </Section>
    </Page>
  );
}

export function ProductDetailPage() {
  const { sku } = useParams<{ sku: string }>();
  const { syncing } = useSyncing();
  const product = useProductBySku(sku);

  if (!sku) {
    return (
      <Page title="Product">
        <ErrorText>Missing product SKU.</ErrorText>
        <Anchor component={Link} to={routes.products} size="sm">
          Back to products
        </Anchor>
      </Page>
    );
  }

  const row = product.data?.[0];
  return (
    <Page title={sku}>
      <Anchor component={Link} to={routes.products} size="sm" mb="sm">
        ← Products
      </Anchor>
      {product.error ? (
        <ErrorText>{friendlyError(product.error.message)}</ErrorText>
      ) : syncing && !row ? (
        <Muted>Loading…</Muted>
      ) : !row ? (
        <Muted>No product found for SKU {sku}.</Muted>
      ) : (
        <ProductDetailTable row={row} />
      )}
    </Page>
  );
}

export function StockPage() {
  const { syncing } = useSyncing();
  const stockMovements = useStockMovements();

  return (
    <Page title="Stock">
      <StockForm />
      <Section title="Movements">
        <SyncQuery syncing={syncing} error={stockMovements.error} data={stockMovements.data} empty={<StockMovementTable rows={[]} />}>
          {(rows) => <StockMovementTable rows={rows} />}
        </SyncQuery>
      </Section>
    </Page>
  );
}

export function PurchasesPage() {
  const { syncing } = useSyncing();
  const purchaseOrders = usePurchaseOrders();

  return (
    <Page title="Purchases">
      <PurchaseForm />
      <Section title="History">
        <SyncQuery syncing={syncing} error={purchaseOrders.error} data={purchaseOrders.data} empty={<PurchaseOrderTable rows={[]} />}>
          {(rows) => <PurchaseOrderTable rows={rows} />}
        </SyncQuery>
      </Section>
    </Page>
  );
}

export function SalesPage() {
  const { syncing } = useSyncing();
  const salesOrders = useSalesOrders();

  return (
    <Page title="Sales">
      <SalesForm />
      <Section title="History">
        <SyncQuery syncing={syncing} error={salesOrders.error} data={salesOrders.data} empty={<SalesOrderTable rows={[]} />}>
          {(rows) => <SalesOrderTable rows={rows} />}
        </SyncQuery>
      </Section>
    </Page>
  );
}

export function ActivityPage() {
  const { syncing } = useSyncing();
  const purchaseOrders = usePurchaseOrders();
  const salesOrders = useSalesOrders();
  const stockMovements = useStockMovements();

  return (
    <Page title="Activity">
      <Section title="Purchase orders">
        <SyncQuery syncing={syncing} error={purchaseOrders.error} data={purchaseOrders.data} empty={<PurchaseOrderTable rows={[]} />}>
          {(rows) => <PurchaseOrderTable rows={rows} />}
        </SyncQuery>
      </Section>
      <Section title="Sales orders">
        <SyncQuery syncing={syncing} error={salesOrders.error} data={salesOrders.data} empty={<SalesOrderTable rows={[]} />}>
          {(rows) => <SalesOrderTable rows={rows} />}
        </SyncQuery>
      </Section>
      <Section title="Stock movements">
        <SyncQuery syncing={syncing} error={stockMovements.error} data={stockMovements.data} empty={<StockMovementTable rows={[]} />}>
          {(rows) => <StockMovementTable rows={rows} />}
        </SyncQuery>
      </Section>
    </Page>
  );
}

