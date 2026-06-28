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

export type NavIconId = 'home' | 'items' | 'stock' | 'purchases' | 'sales' | 'activity' | 'chat';

export const navItems = [
  { to: routes.dashboard, label: 'Home', icon: 'home' as const, end: true },
  { to: routes.products, label: 'Items', icon: 'items' as const },
  { to: routes.stock, label: 'Stock', icon: 'stock' as const },
  { to: routes.purchases, label: 'Purchase Orders', icon: 'purchases' as const },
  { to: routes.sales, label: 'Sales Orders', icon: 'sales' as const },
  { to: routes.activity, label: 'Activity', icon: 'activity' as const },
  { to: routes.chat, label: 'AI Chat', icon: 'chat' as const },
] as const;
