import { Link, useParams } from 'react-router-dom';
import { Anchor } from '@mantine/core';

import { routes } from '../routes';
import {
  useDashboard,
  useProductBySku,
  usePurchaseOrders,
  useSalesOrders,
  useStockMovements,
} from '../sync';
import { ProductForm, PurchaseForm, SalesForm, StockForm } from './inventory-forms';
import { ErrorText, Muted, Page, Panel, Section, SyncQuery, friendlyError, useSyncing } from './ui';
import {
  ProductDetailTable,
  ProductTable,
  PurchaseOrderTable,
  SalesOrderTable,
  StockMovementTable,
} from './tables';

export function DashboardPage() {
  const { syncing, syncError } = useSyncing();
  const dashboard = useDashboard();

  return (
    <Page title="Dashboard">
      <Panel>
        <SyncQuery
          syncing={syncing}
          syncError={syncError}
          error={dashboard.error}
          data={dashboard.data}
          empty={<ProductTable products={[]} />}
        >
          {(rows) => <ProductTable products={rows} />}
        </SyncQuery>
      </Panel>
    </Page>
  );
}

export function ProductsPage() {
  const { syncing, syncError } = useSyncing();
  const dashboard = useDashboard();

  return (
    <Page title="Products">
      <Panel>
        <ProductForm />
      </Panel>
      <Section title="Catalog">
        <SyncQuery
          syncing={syncing}
          syncError={syncError}
          error={dashboard.error}
          data={dashboard.data}
          empty={<ProductTable products={[]} />}
        >
          {(rows) => <ProductTable products={rows} linkSkus />}
        </SyncQuery>
      </Section>
    </Page>
  );
}

export function ProductDetailPage() {
  const { sku } = useParams<{ sku: string }>();
  const { syncing, syncError } = useSyncing();
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
    <Page label={sku} title={row?.name ?? sku}>
      <Panel>
        <Anchor component={Link} to={routes.products} size="sm">
          ← Items
        </Anchor>
        {syncError ? (
          <ErrorText>{syncError}</ErrorText>
        ) : product.error ? (
          <ErrorText>{friendlyError(product.error.message)}</ErrorText>
        ) : syncing && !row ? (
          <Muted>Loading…</Muted>
        ) : !row ? (
          <Muted>No product found for SKU {sku}.</Muted>
        ) : (
          <ProductDetailTable row={row} />
        )}
      </Panel>
    </Page>
  );
}

export function StockPage() {
  const { syncing, syncError } = useSyncing();
  const stockMovements = useStockMovements();

  return (
    <Page title="Stock">
      <Panel>
        <StockForm />
      </Panel>
      <Section title="Movements">
        <SyncQuery
          syncing={syncing}
          syncError={syncError}
          error={stockMovements.error}
          data={stockMovements.data}
          empty={<StockMovementTable rows={[]} />}
        >
          {(rows) => <StockMovementTable rows={rows} />}
        </SyncQuery>
      </Section>
    </Page>
  );
}

export function PurchasesPage() {
  const { syncing, syncError } = useSyncing();
  const purchaseOrders = usePurchaseOrders();

  return (
    <Page title="Purchases">
      <Panel>
        <PurchaseForm />
      </Panel>
      <Section title="History">
        <SyncQuery
          syncing={syncing}
          syncError={syncError}
          error={purchaseOrders.error}
          data={purchaseOrders.data}
          empty={<PurchaseOrderTable rows={[]} />}
        >
          {(rows) => <PurchaseOrderTable rows={rows} />}
        </SyncQuery>
      </Section>
    </Page>
  );
}

export function SalesPage() {
  const { syncing, syncError } = useSyncing();
  const salesOrders = useSalesOrders();

  return (
    <Page title="Sales">
      <Panel>
        <SalesForm />
      </Panel>
      <Section title="History">
        <SyncQuery
          syncing={syncing}
          syncError={syncError}
          error={salesOrders.error}
          data={salesOrders.data}
          empty={<SalesOrderTable rows={[]} />}
        >
          {(rows) => <SalesOrderTable rows={rows} />}
        </SyncQuery>
      </Section>
    </Page>
  );
}

export function ActivityPage() {
  const { syncing, syncError } = useSyncing();
  const purchaseOrders = usePurchaseOrders();
  const salesOrders = useSalesOrders();
  const stockMovements = useStockMovements();

  return (
    <Page title="Activity">
      <Section title="Purchase orders">
        <SyncQuery
          syncing={syncing}
          syncError={syncError}
          error={purchaseOrders.error}
          data={purchaseOrders.data}
          empty={<PurchaseOrderTable rows={[]} />}
        >
          {(rows) => <PurchaseOrderTable rows={rows} />}
        </SyncQuery>
      </Section>
      <Section title="Sales orders">
        <SyncQuery
          syncing={syncing}
          syncError={syncError}
          error={salesOrders.error}
          data={salesOrders.data}
          empty={<SalesOrderTable rows={[]} />}
        >
          {(rows) => <SalesOrderTable rows={rows} />}
        </SyncQuery>
      </Section>
      <Section title="Stock movements">
        <SyncQuery
          syncing={syncing}
          syncError={syncError}
          error={stockMovements.error}
          data={stockMovements.data}
          empty={<StockMovementTable rows={[]} />}
        >
          {(rows) => <StockMovementTable rows={rows} />}
        </SyncQuery>
      </Section>
    </Page>
  );
}
