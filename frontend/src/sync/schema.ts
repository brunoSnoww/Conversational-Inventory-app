import { column, Schema, Table } from '@powersync/web';

/**
 * Snowflake ids are `column.text` — JSON numbers lose precision in JS.
 * Sync streams cast Postgres bigint columns to text (see powersync/config.yaml).
 */
const product = new Table({
  product_id: column.text,
  user_id: column.text,
  name: column.text,
  description: column.text,
  sku: column.text,
  unit: column.text,
  created_at: column.text,
  updated_at: column.text,
});

const purchase_order = new Table({
  purchase_order_id: column.text,
  user_id: column.text,
  product_id: column.text,
  quantity: column.text,
  total_cost: column.text,
  guid: column.text,
  created_at: column.text,
});

const sales_order = new Table({
  sales_order_id: column.text,
  user_id: column.text,
  product_id: column.text,
  quantity: column.text,
  unit_price: column.text,
  guid: column.text,
  created_at: column.text,
});

const stock_movement = new Table({
  stock_movement_id: column.text,
  user_id: column.text,
  product_id: column.text,
  quantity_delta: column.text,
  unit_cost: column.text,
  source: column.text,
  source_id: column.text,
  created_at: column.text,
});

const chat_message = new Table(
  {
    chat_message_id: column.text,
    user_id: column.text,
    role: column.text,
    content: column.text,
    created_at: column.text,
  },
  { trackMetadata: true },
);

export const AppSchema = new Schema({
  product,
  purchase_order,
  sales_order,
  stock_movement,
  chat_message,
});
