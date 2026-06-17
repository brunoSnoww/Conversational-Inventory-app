import { createTheme } from '@mantine/core';

export const APP_NAME = 'Kaizntree';

export const SHELL_BG = 'var(--mantine-color-gray-1)';
export const SHELL_PADDING = 'md';
export const SHELL_GAP = 'md';
export const SHELL_RADIUS = 'xl';
export const BRAND_FONT = 'Georgia, "Times New Roman", serif';

export const shellTextureStyle = {
  backgroundColor: SHELL_BG,
  backgroundImage: 'radial-gradient(var(--mantine-color-gray-3) 0.6px, transparent 0.6px)',
  backgroundSize: '18px 18px',
} as const;

export const PANEL_GAP = 'xl';

export const theme = createTheme({
  primaryColor: 'blue',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  defaultRadius: 'md',
});
