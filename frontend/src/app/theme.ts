import { createTheme } from '@mantine/core';

export const APP_NAME = 'Inventory';

const SHELL_BG = 'var(--mantine-color-gray-1)';
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

/** Reserve space for validation errors so fields do not jump when errors appear. */
const formFieldStyles = {
  root: {
    position: 'relative' as const,
    paddingBottom: '1.25rem',
  },
  error: {
    position: 'absolute' as const,
    left: 0,
    bottom: 0,
    marginTop: 0,
  },
};

export const theme = createTheme({
  primaryColor: 'blue',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  defaultRadius: 'md',
  components: {
    TextInput: { styles: formFieldStyles },
    PasswordInput: { styles: formFieldStyles },
    Select: { styles: formFieldStyles },
  },
});
