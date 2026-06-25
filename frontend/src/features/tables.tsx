import { Anchor, Table, type TableData } from '@mantine/core';
import { Link } from 'react-router-dom';

import { formatWhen } from '../lib/format';
import { routes } from '../routes';
import type {
  DashboardRow,
  ProductRow,
  PurchaseOrderRow,
  SalesOrderRow,
  StockMovementRow,
} from '../sync';
import { Muted } from './ui';

const TABLE_PROPS = {
  striped: true,
  highlightOnHover: true,
  tabularNums: true,
  withTableBorder: true,
  horizontalSpacing: 'sm',
  verticalSpacing: 'sm',
} as const;

function DataTable({
  data,
  emptyMessage,
  minWidth,
  maxHeight,
}: {
  data: TableData;
  emptyMessage: string;
  minWidth?: number;
  maxHeight?: number;
}) {
  if (!data.body?.length) {
    return <Muted>{emptyMessage}</Muted>;
  }

  const table = (
    <Table
      {...TABLE_PROPS}
      stickyHeader={Boolean(maxHeight)}
      stickyHeaderOffset={0}
      data={data}
    />
  );

  if (minWidth == null) {
    return table;
  }

  return (
    <Table.ScrollContainer minWidth={minWidth} maxHeight={maxHeight}>
      {table}
    </Table.ScrollContainer>
  );
}

export function ProductTable({
  products,
  linkSkus = false,
}: {
  products: DashboardRow[];
  linkSkus?: boolean;
}) {
  const data: TableData = {
    head: ['SKU', 'Name', 'Unit', 'On hand', 'Bought', 'Sold', 'Cost', 'Revenue', 'Profit', 'Margin'],
    body: products.map((p) => [
      linkSkus ? (
        <Anchor key={p.product_id} component={Link} to={routes.productDetail(p.sku)} size="sm">
          {p.sku}
        </Anchor>
      ) : (
        p.sku
      ),
      p.name,
      p.unit,
      p.quantity_on_hand,
      p.total_qty_purchased,
      p.total_qty_sold,
      p.total_cost,
      p.total_revenue,
      p.profit,
      p.margin_percent ?? '—',
    ]),
  };

  return <DataTable data={data} emptyMessage="No products yet." minWidth={960} />;
}

export function PurchaseOrderTable({ rows }: { rows: PurchaseOrderRow[] }) {
  const data: TableData = {
    head: ['ID', 'SKU', 'Product', 'Qty', 'Total cost', 'Created'],
    body: rows.map((po) => [
      po.purchase_order_id,
      po.product_sku,
      po.product_name,
      po.quantity,
      po.total_cost,
      formatWhen(po.created_at),
    ]),
  };

  return <DataTable data={data} emptyMessage="No purchase orders yet." minWidth={720} />;
}

export function SalesOrderTable({ rows }: { rows: SalesOrderRow[] }) {
  const data: TableData = {
    head: ['ID', 'SKU', 'Product', 'Qty', 'Unit price', 'Created'],
    body: rows.map((so) => [
      so.sales_order_id,
      so.product_sku,
      so.product_name,
      so.quantity,
      so.unit_price,
      formatWhen(so.created_at),
    ]),
  };

  return <DataTable data={data} emptyMessage="No sales orders yet." minWidth={720} />;
}

export function StockMovementTable({ rows }: { rows: StockMovementRow[] }) {
  const data: TableData = {
    head: ['ID', 'SKU', 'Delta', 'Unit cost', 'Source', 'Source ID', 'Created'],
    body: rows.map((sm) => [
      sm.stock_movement_id,
      sm.product_sku,
      sm.quantity_delta,
      sm.unit_cost ?? '—',
      sm.source,
      sm.source_id ?? '—',
      formatWhen(sm.created_at),
    ]),
  };

  return (
    <DataTable
      data={data}
      emptyMessage="No stock movements yet."
      minWidth={840}
      maxHeight={400}
    />
  );
}

export function ProductDetailTable({ row }: { row: ProductRow }) {
  return (
    <Table variant="vertical" layout="fixed" withTableBorder w="100%">
      <Table.Tbody>
        <Table.Tr>
          <Table.Th w={160}>Name</Table.Th>
          <Table.Td>{row.name}</Table.Td>
        </Table.Tr>
        <Table.Tr>
          <Table.Th>Description</Table.Th>
          <Table.Td>{row.description || '—'}</Table.Td>
        </Table.Tr>
        <Table.Tr>
          <Table.Th>Unit</Table.Th>
          <Table.Td>{row.unit}</Table.Td>
        </Table.Tr>
      </Table.Tbody>
    </Table>
  );
}
