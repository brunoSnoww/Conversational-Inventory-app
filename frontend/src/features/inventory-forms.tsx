import { Button, Group, Select, Stack, TextInput } from '@mantine/core';
import { isNotEmpty, useForm } from '@mantine/form';

import { PRODUCT_UNITS, type ProductUnit } from '../api/types';
import {
  useAddStock,
  useCreateProduct,
  useCreatePurchaseOrder,
  useCreateSalesOrder,
} from '../hooks/useInventory';
import { ErrorText, friendlyError } from './ui';

const skuRule = isNotEmpty('SKU is required');
const qtyRule = isNotEmpty('Quantity is required');

export function ProductForm() {
  const createProduct = useCreateProduct();
  const form = useForm({
    initialValues: {
      sku: '',
      name: '',
      description: '',
      unit: 'unit' as ProductUnit,
    },
    validate: {
      sku: skuRule,
      name: isNotEmpty('Name is required'),
      unit: isNotEmpty('Unit is required'),
    },
  });

  return (
    <form
      onSubmit={form.onSubmit(async (values) => {
        const description = values.description.trim();
        await createProduct.mutateAsync({
          name: values.name.trim(),
          sku: values.sku.trim(),
          unit: values.unit,
          ...(description ? { description } : {}),
        });
        form.reset();
      })}
    >
      <Stack gap="sm">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="SKU"
            placeholder="SKU"
            withAsterisk
            style={{ flex: 1, minWidth: 100 }}
            {...form.getInputProps('sku')}
          />
          <TextInput
            label="Name"
            placeholder="Name"
            withAsterisk
            style={{ flex: 1, minWidth: 120 }}
            {...form.getInputProps('name')}
          />
          <Select
            label="Unit"
            data={PRODUCT_UNITS.map((u) => ({ value: u, label: u }))}
            allowDeselect={false}
            withAsterisk
            style={{ width: 100 }}
            {...form.getInputProps('unit')}
          />
          <TextInput
            label="Description"
            placeholder="Optional"
            style={{ flex: 1, minWidth: 160 }}
            {...form.getInputProps('description')}
          />
          <Button type="submit" loading={createProduct.isPending}>
            Create
          </Button>
        </Group>
        {createProduct.error && <ErrorText>{friendlyError(createProduct.error)}</ErrorText>}
      </Stack>
    </form>
  );
}

export function StockForm() {
  const addStock = useAddStock();
  const form = useForm({
    initialValues: { sku: '', quantity: '', unitCost: '' },
    validate: { sku: skuRule, quantity: qtyRule },
  });

  return (
    <form
      onSubmit={form.onSubmit(async (values) => {
        const cost = values.unitCost.trim();
        await addStock.mutateAsync({
          sku: values.sku.trim(),
          quantity: values.quantity,
          unit_cost: cost ? cost : null,
        });
        form.reset();
      })}
    >
      <Stack gap="sm">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="SKU"
            withAsterisk
            style={{ flex: 1, minWidth: 100 }}
            {...form.getInputProps('sku')}
          />
          <TextInput
            label="Qty"
            withAsterisk
            style={{ width: 100 }}
            {...form.getInputProps('quantity')}
          />
          <TextInput
            label="Unit cost"
            placeholder="Optional"
            style={{ width: 140 }}
            {...form.getInputProps('unitCost')}
          />
          <Button type="submit" loading={addStock.isPending}>
            Add
          </Button>
        </Group>
        {addStock.error && <ErrorText>{friendlyError(addStock.error)}</ErrorText>}
      </Stack>
    </form>
  );
}

export function PurchaseForm() {
  const createPo = useCreatePurchaseOrder();
  const form = useForm({
    initialValues: { sku: '', quantity: '', totalCost: '' },
    validate: {
      sku: skuRule,
      quantity: qtyRule,
      totalCost: isNotEmpty('Total cost is required'),
    },
  });

  return (
    <form
      onSubmit={form.onSubmit(async (values) => {
        await createPo.mutateAsync({
          sku: values.sku.trim(),
          quantity: values.quantity,
          total_cost: values.totalCost,
        });
        form.reset();
      })}
    >
      <Stack gap="sm">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="SKU"
            withAsterisk
            style={{ flex: 1, minWidth: 100 }}
            {...form.getInputProps('sku')}
          />
          <TextInput
            label="Qty"
            withAsterisk
            style={{ width: 100 }}
            {...form.getInputProps('quantity')}
          />
          <TextInput
            label="Total cost"
            withAsterisk
            style={{ width: 120 }}
            {...form.getInputProps('totalCost')}
          />
          <Button type="submit" loading={createPo.isPending}>
            PO
          </Button>
        </Group>
        {createPo.error && <ErrorText>{friendlyError(createPo.error)}</ErrorText>}
      </Stack>
    </form>
  );
}

export function SalesForm() {
  const createSo = useCreateSalesOrder();
  const form = useForm({
    initialValues: { sku: '', quantity: '', unitPrice: '' },
    validate: {
      sku: skuRule,
      quantity: qtyRule,
      unitPrice: isNotEmpty('Unit price is required'),
    },
  });

  return (
    <form
      onSubmit={form.onSubmit(async (values) => {
        await createSo.mutateAsync({
          sku: values.sku.trim(),
          quantity: values.quantity,
          unit_price: values.unitPrice,
        });
        form.reset();
      })}
    >
      <Stack gap="sm">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="SKU"
            withAsterisk
            style={{ flex: 1, minWidth: 100 }}
            {...form.getInputProps('sku')}
          />
          <TextInput
            label="Qty"
            withAsterisk
            style={{ width: 100 }}
            {...form.getInputProps('quantity')}
          />
          <TextInput
            label="Unit price"
            withAsterisk
            style={{ width: 120 }}
            {...form.getInputProps('unitPrice')}
          />
          <Button type="submit" loading={createSo.isPending}>
            Sell
          </Button>
        </Group>
        {createSo.error && <ErrorText>{friendlyError(createSo.error)}</ErrorText>}
      </Stack>
    </form>
  );
}
