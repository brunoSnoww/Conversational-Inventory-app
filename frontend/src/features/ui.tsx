import type { ReactNode } from 'react';
import { Alert, Center, Paper, Stack, Text, Title } from '@mantine/core';

import { formatError } from '../api/client';
import { PANEL_GAP, SHELL_RADIUS } from '../app/theme';
import { useSyncStatus } from '../sync';

const loginCardProps = {
  bg: 'white',
  radius: SHELL_RADIUS,
  p: 'xl',
} as const;

export function Panel({ children, fill }: { children: ReactNode; fill?: boolean }) {
  return (
    <Stack
      gap="sm"
      style={
        fill
          ? { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }
          : undefined
      }
    >
      {children}
    </Stack>
  );
}

export function Page({
  title,
  label,
  description,
  children,
  narrow,
  fill,
}: {
  title: string;
  label?: string;
  description?: string;
  children: ReactNode;
  narrow?: boolean;
  fill?: boolean;
}) {
  const header = (
    <div>
      {label ? (
        <Text size="xs" c="dimmed" tt="uppercase" fw={500} lts={0.8}>
          {label}
        </Text>
      ) : null}
      <Title order={1} mt={label ? 6 : 0} fw={700}>
        {title}
      </Title>
      {description ? (
        <Text size="sm" c="dimmed" mt={8}>
          {description}
        </Text>
      ) : null}
    </div>
  );

  if (narrow) {
    return (
      <Center mih="70vh">
        <Paper {...loginCardProps} maw={420} w="100%">
          <Stack gap="lg">
            {header}
            {children}
          </Stack>
        </Paper>
      </Center>
    );
  }

  const fillStyle = fill
    ? {
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column' as const,
        overflow: 'hidden' as const,
      }
    : { flex: 1, minHeight: 0, overflowY: 'auto' as const };

  return (
    <Stack gap={PANEL_GAP} style={fillStyle}>
      {header}
      <Stack gap={PANEL_GAP} style={fill ? fillStyle : undefined}>
        {children}
      </Stack>
    </Stack>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Stack gap="sm">
      <Title order={4} c="dimmed" fw={500}>
        {title}
      </Title>
      {children}
    </Stack>
  );
}

export function Muted({ children }: { children: ReactNode }) {
  return (
    <Text size="sm" c="dimmed">
      {children}
    </Text>
  );
}

export function ErrorText({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <Alert color="red" variant="light" title={title}>
      {children}
    </Alert>
  );
}

export function friendlyError(err: unknown): string {
  const message = formatError(err);
  if (/load failed|failed to fetch|networkerror|network error/i.test(message)) {
    return 'Could not reach the server. Check your connection and try again.';
  }
  if (/sync|powersync|token|mutation|sqlite|replica|__inventory/i.test(message)) {
    return 'Something went wrong. Please try again.';
  }
  return message;
}

export function useSyncing() {
  const { status, error } = useSyncStatus();
  return {
    syncing: status !== 'ready',
    syncError: error ? friendlyError(error) : null,
  };
}

export function SyncQuery<T>({
  syncing,
  syncError,
  error,
  data,
  empty,
  children,
}: {
  syncing: boolean;
  syncError?: string | null;
  error: Error | undefined;
  data: T[] | undefined;
  empty: ReactNode;
  children: (rows: T[]) => ReactNode;
}) {
  if (syncError) {
    return <ErrorText>{syncError}</ErrorText>;
  }
  if (syncing && !data?.length) {
    return <Muted>Loading…</Muted>;
  }
  if (error) {
    return <ErrorText>{friendlyError(error)}</ErrorText>;
  }
  if (!data?.length) {
    return empty;
  }
  return <>{children(data)}</>;
}
