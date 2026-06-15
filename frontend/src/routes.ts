export const routes = {
  login: '/login',
  dashboard: '/',
  products: '/products',
  productDetail: (sku: string) => `/products/${encodeURIComponent(sku)}`,
  stock: '/stock',
  purchases: '/purchases',
  sales: '/sales',
  activity: '/activity',
  chat: '/chat',
} as const;

export const navItems = [
  { to: routes.dashboard, label: 'Dashboard', end: true },
  { to: routes.products, label: 'Products' },
  { to: routes.stock, label: 'Stock' },
  { to: routes.purchases, label: 'Purchases' },
  { to: routes.sales, label: 'Sales' },
  { to: routes.activity, label: 'Activity' },
  { to: routes.chat, label: 'Chat' },
] as const;

export type AppRoute = (typeof routes)[keyof typeof routes];
