import { AppShell, Burger, Button, Group, NavLink, Text, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { navItems } from '../routes';
import { APP_NAME } from './theme';

function navActive(pathname: string, to: string, end?: boolean) {
  if (end || to === '/') {
    return pathname === to;
  }
  return pathname === to || pathname.startsWith(`${to}/`);
}

export function AppShellLayout() {
  const { session, logout } = useAuth();
  const location = useLocation();
  const [opened, { toggle }] = useDisclosure();

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 200, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="xs" wrap="nowrap">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Toggle navigation" />
            <Title order={4}>{APP_NAME}</Title>
            <Text size="sm" c="dimmed" visibleFrom="sm">
              {session?.email}
            </Text>
          </Group>
          <Group gap="sm" wrap="nowrap">
            <Button variant="subtle" size="xs" onClick={logout}>
              Logout
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            component={Link}
            to={item.to}
            label={item.label}
            active={navActive(location.pathname, item.to, 'end' in item ? item.end : undefined)}
            mb={4}
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
