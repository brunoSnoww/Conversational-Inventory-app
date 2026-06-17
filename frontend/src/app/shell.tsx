import {
  ChatCenteredDotsIcon,
  DiamondsFourIcon,
  HouseIcon,
  MoneyIcon,
  NotebookIcon,
  ShoppingCartIcon,
  SignOutIcon,
  StorefrontIcon,
} from '@phosphor-icons/react';
import { Box, Burger, Drawer, Flex, Group, NavLink, Paper, Stack, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import type { Icon } from '@phosphor-icons/react';
import { NavLink as RouterNavLink, Outlet } from 'react-router-dom';

import kaizntreeLogo from '../assets/kaizntree.png';
import { useAuth } from '../auth/AuthContext';
import { navItems, type NavIconId } from '../routes';
import { APP_NAME, BRAND_FONT, SHELL_GAP, SHELL_PADDING, SHELL_RADIUS, shellTextureStyle } from './theme';

const NAV_ICONS: Record<NavIconId, Icon> = {
  home: HouseIcon,
  items: DiamondsFourIcon,
  stock: StorefrontIcon,
  purchases: ShoppingCartIcon,
  sales: MoneyIcon,
  activity: NotebookIcon,
  chat: ChatCenteredDotsIcon,
};

const SIDEBAR_WIDTH = 200;
const ICON_SIZE = 22;
const CONTENT_HEIGHT = 'calc(100vh - 2 * var(--mantine-spacing-md) - 3.25rem - var(--mantine-spacing-md))';

const shellTexture = shellTextureStyle;

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const { logout } = useAuth();

  return (
    <Stack h="100%" justify="space-between" gap="xs">
      <Stack gap={4}>
        {navItems.map((item) => {
          const IconComponent = NAV_ICONS[item.icon];
          const end = 'end' in item ? item.end : false;
          return (
            <NavLink
              key={item.to}
              component={RouterNavLink}
              to={item.to}
              end={end}
              label={item.label}
              leftSection={<IconComponent size={ICON_SIZE} weight="regular" />}
              onClick={onNavigate}
              variant="light"
              color="gray"
              styles={{
                root: { borderRadius: 'var(--mantine-radius-md)' },
                label: { fontWeight: 400 },
              }}
            />
          );
        })}
      </Stack>
      <NavLink
        label="Log out"
        leftSection={<SignOutIcon size={ICON_SIZE} weight="regular" />}
        onClick={() => {
          onNavigate?.();
          logout();
        }}
        variant="subtle"
        color="gray"
        styles={{
          root: { borderRadius: 'var(--mantine-radius-md)' },
          label: { fontWeight: 400 },
        }}
      />
    </Stack>
  );
}

export function AppShellLayout() {
  const [mobileOpened, { toggle, close }] = useDisclosure();

  return (
    <Box mih="100vh" p={SHELL_PADDING} style={{ ...shellTexture, display: 'flex', flexDirection: 'column' }}>
      <Group justify="space-between" mb={SHELL_GAP} wrap="nowrap">
        <Group gap="sm" wrap="nowrap">
          <Burger opened={mobileOpened} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Toggle navigation" />
          <img src={kaizntreeLogo} alt="" width={36} height={36} />
          <Title order={3} ff={BRAND_FONT} c="dark" fw={700}>
            {APP_NAME}
          </Title>
        </Group>
      </Group>

      <Flex
        gap={SHELL_GAP}
        align="stretch"
        direction={{ base: 'column', sm: 'row' }}
        h={{ base: 'auto', sm: CONTENT_HEIGHT }}
        style={{ minHeight: 0 }}
      >
        <Paper
          bg="white"
          radius={SHELL_RADIUS}
          p="md"
          w={{ base: '100%', sm: SIDEBAR_WIDTH }}
          h={{ base: 'auto', sm: '100%' }}
          visibleFrom="sm"
          style={{ flexShrink: 0 }}
        >
          <SidebarNav />
        </Paper>

        <Drawer opened={mobileOpened} onClose={close} hiddenFrom="sm" title={APP_NAME} padding="md">
          <SidebarNav onNavigate={close} />
        </Drawer>

        <Paper
          bg="white"
          radius={SHELL_RADIUS}
          p={{ base: 'md', sm: 'xl' }}
          h={{ base: 'auto', sm: '100%' }}
          style={{ flex: 1, minWidth: 0, overflowY: 'auto' }}
        >
          <Outlet />
        </Paper>
      </Flex>
    </Box>
  );
}
